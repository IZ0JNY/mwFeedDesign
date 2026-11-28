# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ivan De Cesaris, IZ0JNY
"""One openEMS evaluation of a feed geometry, with a disk cache, and the illuminator figure of merit.

Figure of merit (FOM) for a dish of given (prime or offset-equivalent) f/D:
    eta_ill(f) = spillover x taper x phase x cross-pol  (Kildal/W1GHZ, feedlab.efficiency)
                 with the feed at ONE phase centre, found at f0 and kept for the whole band
    eta(f)     = eta_ill(f) x (1 - |S11(f)|^2)
    FOM        = mean of eta(f) over the far-field frequencies (default f0*(1-b), f0, f0*(1+b))
                 minus penalties (S11 above the limit, length above the limit).
Everything is computed from the openEMS far field (NF2FF) of feedlab.openems_sim; nothing from the fast models.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from feedlab import deep_analysis, efficiency, openems_sim
from feedlab.waveguide import wavelength_mm

RUNS = Path(os.environ.get("FDTD_RUNS", Path(__file__).resolve().parent / "runs"))
PY = os.environ.get("OPENEMS_PYTHON", "/opt/openEMS/venv/bin/python")


@dataclass
class EvalConfig:
    fD: float = 0.6                    # prime-focus or offset-equivalent f/D of the dish
    band: float = 0.02                 # far field at f0*(1-band), f0, f0*(1+band)
    exc_band: float = 0.10             # excitation f0*(1 +/- exc_band): a short pulse, ~4x fewer timesteps
    min_cell_frac: float = 0.2         # merge mesh lines closer than 0.2 cell (small cells shrink the time step)
    cells_per_lambda: int = 100        # feed region; >= 80 keeps the geometry within ~0.1 mm at 10 GHz
    air_cells_per_lambda: int = 20     # graded to this outside the feed (0 = uniform mesh)
    symmetry: int = 2                  # 1 full model, 2 half model (PEC wall x = 0, same result, 2x fewer cells)
    end_db: float = 30.0
    nr_ts: int = 400000                # ~6x the 16 c/λ count (time step scales with the cell)
    s11_max_db: float = -20.0          # penalty above this, anywhere in f0*(1 +/- band)
    s11_weight: float = 0.01           # penalty per dB above s11_max_db
    max_len_lambda: float = 12.0       # penalty above this feed length
    pad_lambda: float = 0.4
    threads: int = 0
    timeout_s: float = 72 * 3600


def _key(geo, cfg: EvalConfig) -> str:
    g = openems_sim.geometry_payload(geo)
    s = json.dumps({"polys": g["polys"], "r_in": g["r_input"], "f0": g["f0_ghz"],
                    "sim": [cfg.band, cfg.cells_per_lambda, cfg.end_db, cfg.pad_lambda]
                    + ([cfg.exc_band, cfg.min_cell_frac] if (cfg.exc_band, cfg.min_cell_frac) != (0.0, 0.0) else [])
                    + ([cfg.air_cells_per_lambda, cfg.symmetry] if cfg.cells_per_lambda > 30 else [])}, sort_keys=True)
    return hashlib.sha1(s.encode()).hexdigest()[:16]


def run_openems(geo, cfg: EvalConfig, label: str = "") -> Path:
    """Simulate (or reuse the cached run) and return the folder with results.json."""
    d = RUNS / _key(geo, cfg)
    res = d / "results.json"
    if res.exists():
        return d
    f0 = geo.f_ghz
    eb = max(cfg.exc_band, cfg.band)
    # the mesh rule of the script is "cells per wavelength at f_hi": keep the cell = λ0 / cells_per_lambda
    # (up to 0.4.28, <= 30 c/λ: cpl * (1 + eb), i.e. λ0 / 1.21 cpl; kept so the cached runs stay valid)
    cpl = int(round(cfg.cells_per_lambda * (1 + eb))) if cfg.cells_per_lambda <= 30 else \
        int(round(cfg.cells_per_lambda / (1 + eb)))
    dc = openems_sim.DeepConfig(f_lo=f0 * (1 - eb), f_hi=f0 * (1 + eb), cells_per_lambda=cpl,
                                ff_freqs=[f0 * (1 - cfg.band), f0, f0 * (1 + cfg.band)],
                                min_cell_frac=cfg.min_cell_frac, symmetry=cfg.symmetry if cfg.cells_per_lambda > 30 else 1,
                                air_cells_per_lambda=cfg.air_cells_per_lambda if cfg.cells_per_lambda > 30 else 0,
                                end_db=cfg.end_db, nr_ts=cfg.nr_ts, n_freq=int(round(20 * eb / 0.01)) + 1, theta_step=1.0, sphere=False, pad_lambda=cfg.pad_lambda,
                                threads=cfg.threads, label=label or geo.kind)
    script = openems_sim.make_deep_script(geo, d, dc, name="sim.py")
    with open(d / "sim.log", "w") as fh:
        p = subprocess.run([PY, "-u", str(script)], cwd=str(d), stdout=fh, stderr=subprocess.STDOUT,
                           timeout=cfg.timeout_s)
    if p.returncode != 0 or not res.exists():
        raise RuntimeError(f"openEMS failed, see {d / 'sim.log'}")
    # the raw field data is large and not needed after the far field: keep only json + log
    import shutil
    shutil.rmtree(d / "sim_data", ignore_errors=True)
    return d


def energy_decay_db(folder: Path) -> float:
    """Last energy level openEMS printed (dB below the peak); nan if unknown."""
    import re
    try:
        m = re.findall(r"\(-\s*([0-9.]+)dB\)", (folder / "sim.log").read_text(errors="replace"))
        return -float(m[-1]) if m else float("nan")
    except OSError:
        return float("nan")


def figure_of_merit(folder: Path, cfg: EvalConfig, length_mm: float | None = None) -> dict:
    r = deep_analysis.load(folder / "results.json")
    f0 = r.f0
    lam0 = wavelength_mm(f0)
    p0 = r.ff_at(f0).pattern()
    pc = deep_analysis.phase_center(p0, cfg.fD, lam0)
    freq = np.asarray(r.freq_ghz)
    s11 = np.asarray(r.s11)
    per = []
    for ff in r.ff:
        lam = wavelength_mm(ff.f_ghz)
        # same physical phase-centre position at every frequency
        e = efficiency.dish_efficiency(ff.pattern().shifted(pc["d_mm"] / lam), cfg.fD)
        g = abs(np.interp(ff.f_ghz, freq, s11.real) + 1j * np.interp(ff.f_ghz, freq, s11.imag))
        per.append({"f_ghz": ff.f_ghz, "eta_ill": e.total, "spill": e.spillover, "taper": e.illumination,
                    "phase": e.phase, "pol": e.polarization, "edge_taper_db": e.edge_taper_db,
                    "s11_db": 20 * math.log10(g + 1e-12), "eta": e.total * (1 - g * g)})
    inb = (freq >= f0 * (1 - cfg.band) - 1e-9) & (freq <= f0 * (1 + cfg.band) + 1e-9)
    s11_db_max = float(20 * np.log10(np.abs(s11[inb] if inb.any() else s11).max() + 1e-12))
    fom = float(np.mean([x["eta"] for x in per]))
    pen = 0.0
    if s11_db_max > cfg.s11_max_db:
        pen += cfg.s11_weight * (s11_db_max - cfg.s11_max_db)
    if length_mm is not None and length_mm / lam0 > cfg.max_len_lambda:
        pen += 0.01 * (length_mm / lam0 - cfg.max_len_lambda)
    # a run stopped by the timestep limit with the energy still high (trapped/closed cavity, instability) gives
    # meaningless far fields: rejected
    edb = energy_decay_db(folder)
    converged = not (np.isfinite(edb) and edb > -(cfg.end_db - 8))
    if not converged:
        pen += 1.0
    i0 = int(np.argmin([abs(x["f_ghz"] - f0) for x in per]))
    return {"fom": fom - pen, "energy_db": edb, "converged": converged, "eta_mean": fom, "penalty": pen, "eta_f0": per[i0]["eta"], "per_freq": per,
            "pc_mm": pc["d_mm"], "pc_lambda": pc["d_mm"] / lam0, "s11_max_db": s11_db_max,
            "cells": r.mesh.get("cells"), "fdtd_s": r.timing.get("fdtd_s")}


def evaluate(geo, cfg: EvalConfig, label: str = "", log: Path | None = None) -> dict:
    t0 = time.time()
    d = run_openems(geo, cfg, label)
    out = figure_of_merit(d, cfg, geo.length)
    out.update({"run": d.name, "label": label, "kind": geo.kind, "f0_ghz": geo.f_ghz, "fD": cfg.fD,
                "length_lambda": geo.length / wavelength_mm(geo.f_ghz),
                "params_mm": {k: v for k, v in geo.params.items() if isinstance(v, (int, float))},
                "wall_s": time.time() - t0})
    if log:
        with open(log, "a") as fh:
            fh.write(json.dumps(out) + "\n")
    return out
