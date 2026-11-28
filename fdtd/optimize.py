# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ivan De Cesaris, IZ0JNY
"""Iterative openEMS optimisation of a feed family for a dish f/D.

    python fdtd/optimize.py --family w2imu --fD 0.6 --budget 60
    python fdtd/optimize.py --family dualflare --fD 0.7 --method de --budget 150
    python fdtd/optimize.py --family profile --fD 0.6 --seed-mm      # seed from the fast mode-matching search
    python fdtd/optimize.py --family w2imu --fD 0.6 --confirm        # best design again at fine mesh

All dimensions are in wavelengths (the result scales to every band with the same f/D); the simulation
runs at --f0 (default 10.368 GHz). Every openEMS run is cached in fdtd/runs/<hash>/, so an interrupted
optimisation restarts where it stopped (Nelder-Mead and DE with a fixed seed replay the same points).
Every evaluation is appended to fdtd/results/<family>_fD<fD>.jsonl; the best one to *_best.json.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fdtd_eval as fe  # noqa: E402

from feedlab import geometry, horns, synth  # noqa: E402
from feedlab.waveguide import wavelength_mm  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"


# --------------------------------------------------------------------------------------------- families
# Each family: parameter names, bounds (in λ or degrees), a literature seed for a given f/D, and a builder.
class Family:
    name = ""
    keys: list[str] = []
    bounds: list[tuple[float, float]] = []

    def seed(self, fD: float) -> list[float]:
        raise NotImplementedError

    def seeds(self, fD: float) -> list[list[float]]:
        """Published designs of the family; the search starts from the best of them (openEMS)."""
        return [self.seed(fD)]

    def build(self, x, f0: float, fD: float):
        raise NotImplementedError


class W2IMU(Family):
    """Smooth-wall dual-mode horn: input guide A, cone of half-angle alpha, phasing section B x C (W1GHZ 6.5)."""
    name = "w2imu"
    keys = ["A", "B", "alpha_deg", "C"]
    bounds = [(0.70, 0.82), (1.20, 2.00), (8.0, 45.0), (0.3, 4.5)]

    def seed(self, fD):
        d = horns.w2imu(10.0, fD=fD)
        lam = wavelength_mm(10.0)
        return [d.dims_mm["input_diam"] / lam, d.dims_mm["aperture_diam_B"] / lam, d.dims_mm["flare_half_deg"],
                d.dims_mm["phasing_length_C"] / lam]

    def seeds(self, fD):
        out = [self.seed(fD)]
        lam = wavelength_mm(10.0)
        try:
            d = horns.w2imu_oe2igl(10.0, 4 * math.degrees(math.atan(1 / (4 * fD)))).dims_mm
            out.append([d["input_diam_A"] / lam, d["aperture_diam_B"] / lam, d["flare_half_deg"], d["length_C"] / lam])
        except Exception:
            pass
        return out

    def build(self, x, f0, fD):
        lam = wavelength_mm(f0)
        A, B, a, C = x
        return geometry.build("w2imu", f0, fD=fD, A=A * lam, B=B * lam, alpha=a, C=C * lam)


class DualFlare(Family):
    """Step + cone 1 + phasing cylinder + cone 2 (feedlab.geometry 'iz0jny')."""
    name = "dualflare"
    keys = list(synth.DF_KEYS)
    bounds = [(0.70, 0.80), (0.80, 1.25), (0.0, 0.6), (1.2, 2.0), (0.1, 1.5), (0.3, 2.5), (1.2, 2.6), (0.3, 3.0)]

    def seed(self, fD):
        fds = sorted(geometry.IZ0JNY_TABLE)
        x = float(min(max(fD, fds[0]), fds[-1]))
        v = [float(np.interp(x, fds, [geometry.IZ0JNY_TABLE[k][i] for k in fds])) for i in range(7)]
        return [0.76] + v

    def build(self, x, f0, fD):
        return geometry.build("iz0jny", f0, fD=fD, **synth.df_params(x, wavelength_mm(f0)))


class ProfileFamily(Family):
    """Free monotone PCHIP profile with an optional input step (feedlab.synth)."""
    name = "profile"
    keys = ["Di", "Ds", "Ls", "L", "Dap"] + [f"s{i}" for i in range(synth.K)]
    bounds = list(synth.BOUNDS)

    def seed(self, fD):
        # conical-ish start: Di 0.76, small step, 3.5 λ long, aperture from W2IMU's rule
        return [0.76, 0.95, 0.2, 3.5, min(2.35 * fD, 2.5)] + [0.5] * synth.K

    def build(self, x, f0, fD):
        return synth.geometry_for(synth.vec_to_profile(x), f0)


class AxialCorrugated(Family):
    """8 axial slots on a stepped face (CT1DMK concept, OE2IGL design guide v1.4). Slot width as a fraction
    of the pitch (the wall between slots stays positive); d2…d8 share one depth."""
    name = "axial_corrugated"
    keys = ["pitch", "w_frac", "axi", "delta", "Di", "Ds", "d1", "dk"]
    bounds = [(0.18, 0.48), (0.40, 0.90), (-0.05, 0.40), (0.0, 0.25), (0.62, 0.90), (0.62, 1.30), (0.15, 0.60),
              (0.18, 0.32)]

    def seed(self, fD):
        lam = wavelength_mm(10.0)
        d = horns.axial_corrugated_oe2igl(10.0, 4 * math.degrees(math.atan(1 / (4 * fD)))).dims_mm
        return [d["pitch"] / lam, d["w"] / d["pitch"], d["axi"] / lam, d["delta"] / lam, d["Di"] / lam,
                d["Ds"] / lam, d["d1"] / lam, d["d2_to_d8"] / lam]

    def build(self, x, f0, fD):
        lam = wavelength_mm(f0)
        pitch, wf, axi, delta, Di, Ds, d1, dk = x
        kw = {"pitch": pitch * lam, "w": wf * pitch * lam, "axi": axi * lam, "delta": delta * lam, "Di": Di * lam,
              "Ds": Ds * lam, "d1": d1 * lam, **{f"d{k}": dk * lam for k in range(2, 9)}}
        return geometry.build("axial_corrugated", f0, fD=fD, **kw)


FAMILIES = {f.name: f for f in (W2IMU(), DualFlare(), ProfileFamily(), AxialCorrugated())}


# --------------------------------------------------------------------------------------------- objective
class Objective:
    def __init__(self, fam: Family, cfg: fe.EvalConfig, f0: float, log: Path):
        self.fam, self.cfg, self.f0, self.log = fam, cfg, f0, log
        self.lo = np.array([b[0] for b in fam.bounds])
        self.hi = np.array([b[1] for b in fam.bounds])
        bf = log.with_name(log.stem + "_best.json")
        self.best = json.loads(bf.read_text()) if bf.exists() else None     # keep the best of earlier runs
        self.n = 0

    def to_x(self, u):
        return self.lo + np.clip(u, 0, 1) * (self.hi - self.lo)

    def to_u(self, x):
        return (np.asarray(x, float) - self.lo) / (self.hi - self.lo)

    def __call__(self, u):
        x = self.to_x(np.asarray(u, float))
        self.n += 1
        try:
            geo = self.fam.build(x, self.f0, self.cfg.fD)
            r = fe.evaluate(geo, self.cfg, label=f"{self.fam.name} #{self.n}")
        except Exception as e:                      # invalid geometry or failed run: bad, but keep going
            print(f"[{self.n}] failed: {e}", flush=True)
            return 1.0
        r["x"] = dict(zip(self.fam.keys, map(float, x)))
        with open(self.log, "a") as fh:
            fh.write(json.dumps(r, default=float) + "\n")
        if self.best is None or r["fom"] > self.best["fom"]:
            self.best = r
            (self.log.with_name(self.log.stem + "_best.json")).write_text(json.dumps(r, indent=1, default=float))
        print(f"[{self.n}] FOM {r['fom']:.4f} (eta {r['eta_mean']:.4f}, S11max {r['s11_max_db']:.1f} dB, "
              f"L {r['length_lambda']:.2f} λ, {r['wall_s']:.0f} s)  best {self.best['fom']:.4f}  "
              + " ".join(f"{k}={v:.3f}" for k, v in r["x"].items()), flush=True)
        return -r["fom"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--family", choices=sorted(FAMILIES), default="w2imu")
    ap.add_argument("--fD", type=float, default=0.6)
    ap.add_argument("--f0", type=float, default=10.368, help="simulation frequency, GHz (results in λ)")
    ap.add_argument("--band", type=float, default=0.02, help="relative half band for FOM and S11")
    ap.add_argument("--cpl", type=int, default=100, help="mesh cells per wavelength in the feed (always 100)")
    ap.add_argument("--method", choices=["nm", "de"], default="nm")
    ap.add_argument("--budget", type=int, default=60, help="max openEMS runs")
    ap.add_argument("--seed-mm", action="store_true", help="profile family: start from the mode-matching optimum")
    ap.add_argument("--x0", type=str, default="", help="JSON list: start point (λ/deg) instead of the literature seed")
    ap.add_argument("--confirm", action="store_true", help="only re-simulate the best design at --confirm-cpl")
    ap.add_argument("--confirm-cpl", type=int, default=100)
    ap.add_argument("--s11-max", type=float, default=-20.0)
    ap.add_argument("--s11-weight", type=float, default=0.01, help="FOM penalty per dB of S11 above --s11-max")
    ap.add_argument("--max-len", type=float, default=12.0, help="length limit, λ")
    a = ap.parse_args(argv)

    fam = FAMILIES[a.family]
    cfg = fe.EvalConfig(fD=a.fD, band=a.band, cells_per_lambda=a.cpl, s11_max_db=a.s11_max, s11_weight=a.s11_weight,
                         max_len_lambda=a.max_len)
    RESULTS.mkdir(parents=True, exist_ok=True)
    tag = f"{fam.name}_fD{a.fD:.2f}"
    log = RESULTS / f"{tag}.jsonl"

    if a.confirm:
        best = json.loads((RESULTS / f"{tag}_best.json").read_text())
        x = [best["x"][k] for k in fam.keys]
        cfg.cells_per_lambda = a.confirm_cpl
        out = {}
        cases = [(f"seed{i}", sx) for i, sx in enumerate(fam.seeds(a.fD))] + [("best", x)]
        for name, xx in cases:
            r = fe.evaluate(fam.build(xx, a.f0, a.fD), cfg, label=f"{fam.name} {name} confirm")
            r["x"] = dict(zip(fam.keys, map(float, xx)))
            out[name] = r
            print(f"{name}: eta mean {r['eta_mean']:.4f}  f0 {r['eta_f0']:.4f}  S11max {r['s11_max_db']:.1f} dB")
        (RESULTS / f"{tag}_confirm.json").write_text(json.dumps(out, indent=1, default=float))
        return out

    obj = Objective(fam, cfg, a.f0, log)
    if a.x0:
        x0 = json.loads(a.x0)
    elif a.seed_mm and fam.name == "profile":
        x0 = mm_seed(a.fD, a.f0)
    else:                                   # best published design of the family (each one is one run)
        cands = fam.seeds(a.fD)
        if len(cands) > 1:
            x0 = min(cands, key=lambda x: obj(np.clip(obj.to_u(x), 0, 1)))
        else:
            x0 = cands[0]
    u0 = np.clip(obj.to_u(x0), 0, 1)
    from scipy import optimize
    if a.method == "nm":
        n = len(u0)
        simplex = [u0] + [np.clip(u0 + 0.08 * np.eye(n)[i] * (1 if u0[i] < 0.9 else -1), 0, 1) for i in range(n)]
        res = optimize.minimize(obj, u0, method="Nelder-Mead", bounds=[(0, 1)] * n,
                                options={"maxfev": a.budget, "initial_simplex": np.array(simplex),
                                         "xatol": 2e-3, "fatol": 2e-4})
    else:
        pop = max(4, a.budget // (len(u0) * 6))
        init = np.vstack([u0, np.random.default_rng(1).random((pop * len(u0) - 1, len(u0)))])
        res = optimize.differential_evolution(obj, [(0, 1)] * len(u0), maxiter=10 ** 6, popsize=pop, init=init,
                                              seed=1, polish=False, tol=1e-4,
                                              callback=lambda *_ , **__: obj.n >= a.budget)
    print("best:", json.dumps({k: obj.best[k] for k in ("fom", "eta_mean", "eta_f0", "s11_max_db", "length_lambda", "x")},
                              default=float, indent=1))
    return obj.best


def mm_seed(fD: float, f0: float):
    """Quick global search with the fast mode-matching solver (feedlab.synth) as the FDTD start point."""
    from scipy import optimize

    def c(x):
        try:
            geo = synth.geometry_for(synth.vec_to_profile(x), f0)
            from feedlab import modematch
            lam = wavelength_mm(f0)
            r = modematch.simulate(geo.staircase(lam / 20), [f0], n_modes=10)
            pat = modematch.aperture_pattern(r, 0, f0, n_rho=24, n_phi=24, n_theta=181)
            from feedlab import efficiency
            d, e = efficiency.phase_center_by_efficiency(pat, fD, span_lambda=2.0, step=0.05)
            g = 10 ** (float(r.s11_db[0]) / 20)
            return -e * (1 - g * g)
        except Exception:
            return 1.0
    r = optimize.differential_evolution(c, synth.BOUNDS, maxiter=25, popsize=8, seed=1, polish=False)
    print(f"mode-matching seed: eta {-r.fun:.4f}", flush=True)
    return list(r.x)


if __name__ == "__main__":
    main()
