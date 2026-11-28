"""Full-wave simulation with openEMS (FDTD, free, https://openems.de) — optional "deep analysis".

FeedLab works without openEMS: the fast mode-matching / aperture models give results in seconds.
openEMS is an *option* the user chooses for a reference analysis, because an FDTD run takes from
minutes to hours.

`make_deep_script(geo, out_dir, cfg)` writes a self-contained Python script, modelled on the official
openEMS 'Conical Horn' tutorial (AddRotPoly + AddCircWaveGuidePort TE11 + NF2FF box), that computes

  * S11, input impedance and accepted power over the band;
  * far-field cuts (phi = 0/45/90°, complex E_theta/E_phi) at several frequencies;
  * a coarse full-sphere far field at f0 (true directivity, radiated power, BOR check);

and stores everything in `results.json` (format "feedlab-openems-results" v2), which
`feedlab.deep_analysis` turns into the deep analysis (phase centre, efficiency vs f/D, G/T, ...).
The script writes `status.json` at every stage, so FeedLab can follow a run in the background,
and on Windows it loads the openEMS DLLs from the installation folder by itself.

`make_script(...)` is the original single-run API, kept for compatibility.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from .geometry import FeedGeometry
from .patterns import Pattern

RESULTS_FORMAT = "feedlab-openems-results"


def openems_available() -> bool:
    """True if openEMS' Python bindings import in *this* interpreter (see openems_local for the full check)."""
    try:
        from . import openems_local
        openems_local.prepare_dll_path(openems_local.find_install())
        import openEMS  # noqa: F401
        import CSXCAD  # noqa: F401
        return True
    except Exception:
        return False


@dataclass
class DeepConfig:
    """Settings of one openEMS run. Frequencies in GHz."""
    f_lo: float | None = None             # default 0.9 f0
    f_hi: float | None = None             # default 1.1 f0
    cells_per_lambda: int = 100           # at f_hi, inside the feed (metal region): 100 keeps the machined
                                          # dimensions (Ivan: always 100); the free space uses air_cells_per_lambda
    air_cells_per_lambda: int = 20        # free space and PML around the feed (graded from the feed mesh);
                                          # >= cells_per_lambda or 0 = one uniform mesh, as before 0.4.28
    nr_ts: int = 600000                   # max timesteps (the fine feed mesh needs a small time step; the run
                                          # stops at end_db anyway)
    end_db: float = 40.0                  # stop when energy has decayed by this many dB
    port_mode: str = "TE11"
    n_freq: int = 201                     # points of the S11 sweep
    ff_freqs: list = field(default_factory=list)   # far-field frequencies; default f_lo, f0, f_hi
    theta_step: float = 1.0
    phi_cuts: list = field(default_factory=lambda: [0.0, 45.0, 90.0])
    sphere: bool = True                   # coarse full-sphere far field at f0
    sphere_step: float = 3.0
    pad_lambda: float = 0.5               # air between feed and PML (wavelengths at f0)
    dump_fields: bool = False             # E-field in the xz plane at f0 (VTK, ParaView)
    threads: int = 0                      # 0 = openEMS default (all cores)
    symmetry: int = 1                     # 1 full model, 2 half (PEC wall x = 0), 4 quarter (+ PMC wall y = 0)
    grading: float = 1.4                  # max ratio of neighbouring cells from the feed mesh to the air mesh
    min_cell_frac: float = 0.2            # merge mesh lines closer than this x feed cell (a tiny cell shrinks
                                          # the time step); 0.2 cell at 100 c/λ = λ/500, 0 = exact lines
    openems_root: str = ""                # filled in by openems_local when known
    label: str = ""

    def resolved(self, f0: float) -> "DeepConfig":
        c = DeepConfig(**asdict(self))
        c.f_lo = float(c.f_lo or 0.9 * f0)
        c.f_hi = float(c.f_hi or 1.1 * f0)
        if not c.ff_freqs:
            c.ff_freqs = sorted({round(c.f_lo, 6), round(f0, 6), round(c.f_hi, 6)})
        if not any(abs(f - f0) < 1e-9 for f in c.ff_freqs):
            c.ff_freqs = sorted(list(c.ff_freqs) + [f0])
        c.ff_freqs = [float(f) for f in c.ff_freqs]
        return c


def geometry_payload(geo: FeedGeometry) -> dict:
    polys = [[[float(r) for r, _ in p], [float(z) for _, z in p]] for p in geo.polygons]
    return {"kind": geo.kind, "f0_ghz": float(geo.f_ghz), "params": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                                                                       for k, v in geo.params.items()},
            "polys": polys, "r_input": float(geo.r_input), "z_aperture": float(geo.z_aperture),
            "outer_radius": float(geo.outer_radius), "r_aperture": float(geo.r_aperture)}


def mesh_estimate(geo: FeedGeometry, cfg: DeepConfig) -> dict:
    """Rough size/time/RAM of the run (same mesh rules as the script, uniform-cell approximation)."""
    c = cfg.resolved(geo.f_ghz)
    C0 = 299792458.0
    lam_min = C0 / (c.f_hi * 1e9) * 1e3
    lam0 = C0 / (geo.f_ghz * 1e9) * 1e3
    res = lam_min / c.cells_per_lambda
    air = int(c.air_cells_per_lambda or 0)
    res_air = lam_min / air if 0 < air < c.cells_per_lambda else res
    pad = c.pad_lambda * lam0 + 10 * res_air
    z_back = -max(lam0, 3 * geo.r_input)
    # fine through the feed, graded (1.4) to the air cell, air cells to the PML
    import math as _m
    gr = float(c.grading or 1.4)
    n_grade = _m.log(res_air / res) / _m.log(gr) if res_air > res else 0.0
    grade_len = res * sum(gr ** k for k in range(int(n_grade)))
    def _n(fine_len, air_len):
        return fine_len / res + 2 * n_grade + max(0.0, air_len - 2 * grade_len) / res_air + 16
    nxy = _n(2 * geo.outer_radius, 2 * pad)
    nz = _n(geo.z_aperture, pad - z_back)
    cells = nxy * nxy * nz / int(c.symmetry or 1)
    # Courant step of a uniform mesh, and the ~ pulse length + ringing: empirical 8-30k steps for feeds
    dt = res * 1e-3 / (C0 * 3 ** 0.5)
    bw = (c.f_hi - c.f_lo) * 1e9
    # Gaussian pulse (~18/(2*pi*fc) long) plus the ringing of the feed down to the end criterion
    ts = min(c.nr_ts, int(3.0 * (18.0 / (2 * 3.14159 * 0.5 * bw * dt)) + 60 * (geo.z_aperture + 2 * pad) / res))
    speed_mcs = 100.0                      # typical desktop CPU, MCells/s (openEMS prints the real one)
    t_s = cells * ts / (speed_mcs * 1e6)
    return {"cells": int(cells), "nx": int(nxy), "nz": int(nz), "res_mm": res, "timesteps_est": int(ts),
            "ram_mb": cells * 90 / 1e6 + 150, "time_min": t_s / 60.0}


def make_deep_script(geo: FeedGeometry, out_dir: str | Path, cfg: DeepConfig | None = None,
                     name: str | None = None) -> Path:
    if not hasattr(geo, "polygons"):
        raise ValueError("lo script full-wave copre i feed a simmetria di rotazione (non la tromba rettangolare)")
    cfg = (cfg or DeepConfig()).resolved(geo.f_ghz)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"format": "feedlab-openems-config", "version": 2, "geometry": geometry_payload(geo),
               "config": asdict(cfg), "notes": list(geo.notes)}
    (out_dir / "feed.json").write_text(json.dumps(payload, indent=1))
    js = json.dumps(payload, ensure_ascii=True).replace("'", "\\u0027")
    path = out_dir / (name or f"sim_{geo.kind}.py")
    path.write_text(_TEMPLATE.replace("@@CONFIG@@", js).replace("@@NAME@@", path.name), encoding="utf-8")
    return path


def make_script(geo: FeedGeometry, out_dir: str | Path, f_lo: float | None = None, f_hi: float | None = None,
                cells_per_lambda: int = 20, port_mode: str = "TE11", nr_ts: int = 60000) -> Path:
    """Original API: one run, S11 over the band and cuts at f0 (plus f_lo/f_hi)."""
    cfg = DeepConfig(f_lo=f_lo, f_hi=f_hi, cells_per_lambda=cells_per_lambda, port_mode=port_mode, nr_ts=nr_ts)
    return make_deep_script(geo, out_dir, cfg)


def run(script: Path, log: Path | None = None, python: str | None = None) -> subprocess.Popen:
    """Run a script in a child process (foreground use). For background jobs see openems_local.start_batch."""
    from . import openems_local
    log = log or script.with_suffix(".log")
    fh = open(log, "w")
    env = openems_local.sim_env(openems_local.find_install())
    return subprocess.Popen([python or sys.executable, "-u", str(script)], cwd=str(script.parent), stdout=fh,
                            stderr=subprocess.STDOUT, env=env)


def _cplx(d, key):
    return np.array(d[key + "_re"], float) + 1j * np.array(d[key + "_im"], float)


def load_results(path: str | Path) -> dict:
    """Load results.json (v1 or v2). Returns the f0 pattern, S11 and the raw dictionary."""
    d = json.loads(Path(path).read_text())
    theta = np.array(d["theta"])
    phis = list(d.get("phis", [0.0, 45.0, 90.0]))
    Et = _cplx(d, "Et")
    Ep = _cplx(d, "Ep")
    i0 = int(np.argmin([abs(p - 0) for p in phis]))
    i90 = int(np.argmin([abs(p - 90) for p in phis]))
    i45 = int(np.argmin([abs(p - 45) for p in phis]))
    # BOR1 co-pol (Ludwig-3, x-polarised): E-plane (phi=0) -> E_theta, H-plane (phi=90) -> -E_phi
    pat = Pattern(theta, Et[:, i0], -Ep[:, i90], name=f"openEMS {d['meta']['kind']}")
    c45, s45 = np.cos(np.radians(phis[i45])), np.sin(np.radians(phis[i45]))
    co45 = Et[:, i45] * c45 - Ep[:, i45] * s45
    x45 = Et[:, i45] * s45 + Ep[:, i45] * c45
    ref = max(np.abs(pat.E).max(), np.abs(pat.H).max(), 1e-30)
    xpol45 = 20 * np.log10(np.abs(x45) / ref + 1e-15)
    s11 = _cplx(d, "s11")
    return {"pattern": pat, "freq_ghz": np.array(d["freq_ghz"]), "s11": s11, "Dmax_dbi": d.get("Dmax_dbi", float("nan")),
            "xpol45_db": xpol45, "co45": co45, "raw": d}


# --------------------------------------------------------------------------------------------------
# The generated script. Only @@CONFIG@@ / @@NAME@@ are substituted; everything else is plain Python
# that needs numpy + the openEMS/CSXCAD bindings (and h5py, which they use for the NF2FF).
_TEMPLATE = r'''# -*- coding: utf-8 -*-
"""FeedLab - openEMS full-wave "deep analysis" of a dish feed. Auto-generated.

Run:      python -u @@NAME@@            (openEMS >= 0.0.36 with its Python bindings)
Preview:  python @@NAME@@ --preview     (opens the model in AppCSXCAD, no simulation)
Post:     python @@NAME@@ --post        (only port + far field again from sim_data, after a full run)
Output:   results.json (load it in FeedLab, tab "Full-wave openEMS"), status.json, sim_data/
"""
import os, sys, json, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.loads(r"""@@CONFIG@@""")
G, C = CFG["geometry"], CFG["config"]
T_START = time.time()


def status(stage, **kw):
    d = dict(stage=stage, time=time.time(), elapsed=time.time() - T_START, pid=os.getpid())
    d.update(kw)
    tmp = os.path.join(HERE, "status.json.tmp")
    # Windows: the replace fails while FeedLab is reading status.json -> retry; a progress file must
    # never stop the simulation
    for i in range(40):
        try:
            with open(tmp, "w") as fh:
                json.dump(d, fh)
            os.replace(tmp, os.path.join(HERE, "status.json"))
            break
        except OSError:
            time.sleep(0.05)
    print("FEEDLAB:STAGE %s %s" % (stage, json.dumps(kw)), flush=True)


def setup_dlls():
    """Windows: the bindings need the openEMS folder (DLLs) on the DLL search path."""
    root = os.environ.get("OPENEMS_INSTALL_PATH") or C.get("openems_root") or ""
    if root and os.path.isdir(root):
        os.environ["OPENEMS_INSTALL_PATH"] = root
        os.environ["PATH"] = root + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(root)
            except OSError:
                pass
    return root


def build(sim_path):
    import numpy as np
    from CSXCAD import ContinuousStructure
    from openEMS import openEMS
    from openEMS.physical_constants import C0

    unit = 1e-3                                         # mm
    f0, f_lo, f_hi = G["f0_ghz"] * 1e9, C["f_lo"] * 1e9, C["f_hi"] * 1e9
    POLYS, R_IN, Z_AP, R_MAX = G["polys"], G["r_input"], G["z_aperture"], G["outer_radius"]
    lam_min = C0 / f_hi / unit
    res = lam_min / C["cells_per_lambda"]               # inside the feed
    air = int(C.get("air_cells_per_lambda") or 0)
    res_air = lam_min / air if 0 < air < C["cells_per_lambda"] else res     # free space and PML
    lam0 = C0 / f0 / unit

    FDTD = openEMS(NrTS=int(C["nr_ts"]), EndCriteria=10 ** (-C["end_db"] / 10.0))
    FDTD.SetGaussExcite(0.5 * (f_lo + f_hi), 0.5 * (f_hi - f_lo))
    # symmetry (BOR feed, x-polarised TE11): E tangential to x = 0 is zero -> PEC wall, H tangential to y = 0 is
    # zero -> PMC wall; only the quarter x, y >= 0 is computed (4x fewer cells), the far field is mirrored back
    NSYM = int(C.get("symmetry") or 1)          # 1 full, 2 half (PEC x = 0), 4 quarter (+ PMC y = 0)
    SYM, SYM_Y = NSYM >= 2, NSYM >= 4
    FDTD.SetBoundaryCond(["PEC" if SYM else "PML_8", "PML_8", "PMC" if SYM_Y else "PML_8", "PML_8"] + ["PML_8"] * 2)
    CSX = ContinuousStructure()
    FDTD.SetCSX(CSX)
    mesh = CSX.GetGrid()
    mesh.SetDeltaUnit(unit)

    pad = C["pad_lambda"] * lam0 + 10 * res_air
    z_back = -max(lam0, 3 * R_IN)                       # input guide runs into the back PML (matched)
    # wall of the input guide that runs into the back PML: at least two cells thick, with its own mesh lines
    # (a fixed 0.5 mm wall fell between the lines at 10 GHz, 1.3 mm cells, and the guide was open)
    w_in = max(1.0, 2.0 * res)
    xy = sorted(set([-R_MAX - pad, R_MAX + pad, 0.0, -R_IN, R_IN, -(R_IN + w_in), R_IN + w_in]
                    + [s * float(r) for p in POLYS for r in p[0] for s in (1, -1)]))
    dmin = float(C.get("min_cell_frac") or 0.0) * res

    def merge(lines, keep=()):
        """drop lines closer than dmin to the previous one (tiny cells shrink the time step)"""
        if dmin <= 0:
            return lines
        out = []
        for v in lines:
            if out and v - out[-1] < dmin:
                if v in keep:
                    out[-1] = v
                continue
            out.append(v)
        return out

    try:
        from CSXCAD.SmoothMeshLines import SmoothMeshLines
    except ImportError:                     # old CSXCAD without the module: plain subdivision, no grading
        def SmoothMeshLines(lines, max_res, ratio=1.4):
            v = sorted(set(float(x) for x in lines))
            out = [v[0]]
            for b in v[1:]:
                n = max(1, int(np.ceil((b - out[-1]) / max_res - 1e-9)))
                a0 = out[-1]
                out += [a0 + (b - a0) * k / n for k in range(1, n + 1)]
            return np.array(out)

    def graded(lines, lo, hi, ends, keep):
        """fine mesh (res) through the feed [lo, hi], graded (ratio 1.4) to res_air out to the domain ends"""
        inner = merge(sorted(set([v for v in lines if lo <= v <= hi] + [lo, hi])), keep)
        inner = list(SmoothMeshLines(np.array(inner), res, ratio=GR))
        allv = np.array(sorted(set(inner + [float(e) for e in ends] + [v for v in lines if not lo <= v <= hi])))
        return SmoothMeshLines(allv, res_air, ratio=GR)

    m_f = 2 * res
    GR = float(C.get("grading") or 1.4)
    half = graded([v for v in xy if v >= 0], 0.0, R_MAX + m_f, (0.0, R_MAX + pad), keep=(0.0, R_IN))
    full = sorted(set([-v for v in half] + list(half)))       # mirror of the half mesh: identical cells either way
    mesh.SetLines("x", half if SYM else full)
    mesh.SetLines("y", half if SYM_Y else full)
    zg = sorted(set([float(z) for p in POLYS for z in p[1]]))
    zl = graded(zg + [z_back, Z_AP + pad], min(zg) - m_f, Z_AP + m_f, (z_back, Z_AP + pad), keep=(z_back,))
    mesh.SetLines("z", zl)
    x_lines, y_lines, z_lines = mesh.GetLines("x"), mesh.GetLines("y"), mesh.GetLines("z")

    metal = CSX.AddMetal("feed")
    metal.AddRotPoly(points=np.array([[R_IN + w_in, R_IN + w_in, R_IN, R_IN], [z_back, 0.0, 0.0, z_back]]),
                     norm_dir="x", elevation=0, rot_axis="z", angle=[0, 2 * np.pi], priority=10)
    for p in POLYS:
        metal.AddRotPoly(points=np.array(p), norm_dir="x", elevation=0, rot_axis="z",
                         angle=[0, 2 * np.pi], priority=10)

    start = [0.0 if SYM else -R_IN, 0.0 if SYM_Y else -R_IN, z_lines[10]]
    stop = [R_IN, R_IN, z_lines[10] + 0.25 * lam0]
    # quarter model: the port box is the x, y >= 0 quarter, so the TE11 profile must be referred to the axis
    # (default origin is the box centre, which would put the mode off-axis)
    port = FDTD.AddCircWaveGuidePort(0, start, stop, "z", R_IN * unit, C["port_mode"], 0, 1,
                                     **({"local_origin": [0.0, 0.0, start[2]]} if SYM else {}))

    nf_start = [x_lines[0] if SYM else x_lines[10], y_lines[0] if SYM_Y else y_lines[10], z_lines[10]]
    nf_stop = [x_lines[-11], y_lines[-11], z_lines[-11]]
    if SYM:
        nf2ff = FDTD.CreateNF2FFBox("nf2ff", nf_start, nf_stop, directions=[0, 1, 0 if SYM_Y else 1, 1, 0, 1],
                                    mirror=[1, 0, 2 if SYM_Y else 0, 0, 0, 0])
    else:
        nf2ff = FDTD.CreateNF2FFBox("nf2ff", nf_start, nf_stop, directions=[1, 1, 1, 1, 0, 1])

    if C.get("dump_fields"):
        try:
            dump = CSX.AddDump("Ef_xz", dump_type=10, file_type=0, frequency=[f0])
            dump.AddBox([x_lines[0], 0, z_lines[0]], [x_lines[-1], 0, z_lines[-1]])
        except Exception as e:                           # optional
            print("field dump not available:", e, flush=True)

    info = dict(nx=len(x_lines), ny=len(y_lines), nz=len(z_lines),
                cells=len(x_lines) * len(y_lines) * len(z_lines), res_mm=res)
    return dict(FDTD=FDTD, CSX=CSX, port=port, nf2ff=nf2ff, unit=unit, info=info, Z_AP=Z_AP)


def preview():
    sim_path = os.path.join(HERE, "sim_data")
    m = build(sim_path)
    fn = os.path.join(HERE, "geometry.xml")
    m["CSX"].Write2XML(fn)
    exe = None
    try:
        from CSXCAD import AppCSXCAD_BIN
        exe = AppCSXCAD_BIN
    except Exception:
        root = os.environ.get("OPENEMS_INSTALL_PATH", "")
        for cand in ("AppCSXCAD.exe", "AppCSXCAD"):
            if root and os.path.exists(os.path.join(root, cand)):
                exe = os.path.join(root, cand)
        exe = exe or "AppCSXCAD"
    print("geometry written to", fn, "- opening", exe, flush=True)
    import subprocess
    subprocess.Popen([exe, fn])


def _l(a):
    """Array -> list with 9 significant digits relative to its largest value. openEMS fields are tiny
    (far field ~1e-11 V/m for its unit excitation): a fixed number of decimals would store zeros."""
    import numpy as np
    a = np.asarray(a, dtype=float)
    m = float(np.nanmax(np.abs(a))) if a.size else 0.0
    if not np.isfinite(m) or m == 0.0:
        return a.tolist()
    return a.round(int(8 - np.floor(np.log10(m)))).tolist()


def main(post_only=False):
    """post_only (--post): skip the FDTD run and only redo port + far field from the data already in
    sim_data (same script, same mesh): seconds instead of the whole simulation."""
    import numpy as np
    status("setup")
    sim_path = os.path.join(HERE, "sim_data")
    m = build(sim_path)
    t0 = time.time()
    if post_only:
        if not os.path.isdir(sim_path):
            raise RuntimeError("--post: sim_data not found, run the full simulation first")
    else:
        status("fdtd", **m["info"])
        kw = {"numThreads": int(C["threads"])} if int(C.get("threads") or 0) > 0 else {}
        try:
            m["FDTD"].Run(sim_path, cleanup=True, **kw)
        except TypeError:
            m["FDTD"].Run(sim_path, cleanup=True)
    t_fdtd = time.time() - t0

    status("port")
    port, nf2ff, unit = m["port"], m["nf2ff"], m["unit"]
    f_lo, f_hi, f0 = C["f_lo"] * 1e9, C["f_hi"] * 1e9, G["f0_ghz"] * 1e9
    freq = np.linspace(f_lo, f_hi, int(C["n_freq"]))
    port.CalcPort(sim_path, freq)
    s11 = port.uf_ref / port.uf_inc
    try:
        zin = port.uf_tot / port.if_tot
    except Exception:
        zin = np.full_like(s11, np.nan)
    pacc = 0.5 * np.real(port.uf_tot * np.conj(port.if_tot))       # accepted power (incident - reflected)
    pacc = int(C.get("symmetry") or 1) * pacc                    # the port sees 1/2 or 1/4 of the guide                                             # the port sees one quarter of the aperture

    center = [0, 0, m["Z_AP"] * unit]
    theta = np.arange(0.0, 180.0 + C["theta_step"] / 2, C["theta_step"])
    phis = np.array(C["phi_cuts"], float)
    ffreqs = [f * 1e9 for f in C["ff_freqs"]]
    status("nf2ff", part="cuts", n=len(ffreqs))
    r = nf2ff.CalcNF2FF(sim_path, ffreqs, theta, phis, center=center, outfile="nf2ff_cuts.h5",
                         read_cached=False)
    ff = []
    for i, f in enumerate(ffreqs):
        Et, Ep = np.asarray(r.E_theta[i]), np.asarray(r.E_phi[i])
        ff.append(dict(f_ghz=f / 1e9, theta=_l(theta), phis=_l(phis),
                       Et_re=_l(Et.real), Et_im=_l(Et.imag), Ep_re=_l(Ep.real), Ep_im=_l(Ep.imag),
                       Prad=float(np.real(r.Prad[i])), Dmax_nf2ff_dbi=float(10 * np.log10(np.real(r.Dmax[i]))),
                       Pacc=float(np.interp(f, freq, pacc))))
    sphere = None
    if C.get("sphere"):
        status("nf2ff", part="sphere")
        st = float(C["sphere_step"])
        th_s = np.arange(0.0, 180.0 + st / 2, st)
        ph_s = np.arange(0.0, 360.0, st)
        rs = nf2ff.CalcNF2FF(sim_path, f0, th_s, ph_s, center=center, outfile="nf2ff_sphere.h5",
                                read_cached=False)
        Et, Ep = np.asarray(rs.E_theta[0]), np.asarray(rs.E_phi[0])
        sphere = dict(f_ghz=f0 / 1e9, theta=_l(th_s), phi=_l(ph_s), Et_re=_l(Et.real), Et_im=_l(Et.imag),
                      Ep_re=_l(Ep.real), Ep_im=_l(Ep.imag), Prad=float(np.real(rs.Prad[0])),
                      Dmax_dbi=float(10 * np.log10(np.real(rs.Dmax[0]))), Pacc=float(np.interp(f0, freq, pacc)))

    i0 = int(np.argmin([abs(x["f_ghz"] - G["f0_ghz"]) for x in ff]))
    out = dict(format="feedlab-openems-results", version=2,
               meta=dict(kind=G["kind"], f0_ghz=G["f0_ghz"], params=G["params"], label=C.get("label", "")),
               geometry=G, config=C, mesh=m["info"],
               timing=dict(fdtd_s=t_fdtd, total_s=time.time() - T_START, post_only=bool(post_only)),
               freq_ghz=_l(freq / 1e9), s11_re=_l(s11.real), s11_im=_l(s11.imag),
               zin_re=_l(np.real(zin)), zin_im=_l(np.imag(zin)), pacc=_l(pacc),
               ff=ff, sphere=sphere, phase_ref="aperture plane z = Z_AP",
               # v1-compatible keys (cuts at f0)
               theta=ff[i0]["theta"], phis=ff[i0]["phis"], Et_re=ff[i0]["Et_re"], Et_im=ff[i0]["Et_im"],
               Ep_re=ff[i0]["Ep_re"], Ep_im=ff[i0]["Ep_im"],
               Dmax_dbi=(sphere or ff[i0]).get("Dmax_dbi", ff[i0]["Dmax_nf2ff_dbi"]), Prad=ff[i0]["Prad"],
               cells_per_lambda=C["cells_per_lambda"])
    with open(os.path.join(HERE, "results.json"), "w") as fh:
        json.dump(out, fh)
    s11_f0 = 20 * np.log10(abs(np.interp(f0, freq, s11.real) + 1j * np.interp(f0, freq, s11.imag)) + 1e-15)
    status("done", s11_f0_db=float(s11_f0), Dmax_dbi=float(out["Dmax_dbi"]), total_s=time.time() - T_START)
    print("S11 @ f0 = %.1f dB, Dmax = %.2f dBi, %.0f s" % (s11_f0, out["Dmax_dbi"], time.time() - T_START), flush=True)


if __name__ == "__main__":
    setup_dlls()
    try:
        if "--preview" in sys.argv:
            preview()
        else:
            main(post_only="--post" in sys.argv)
    except BaseException as e:
        status("error", error="%s: %s" % (type(e).__name__, e), trace=traceback.format_exc()[-4000:])
        traceback.print_exc()
        sys.exit(1)
'''
