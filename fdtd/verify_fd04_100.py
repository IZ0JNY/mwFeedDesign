"""Re-simulate the f/D 0.4 corrugated design (axial_corrugated_fD0.40_best.json) at 100 cells/λ, half model,
at 10.368 GHz -> fdtd/results/fd04_verify_100cpl.json. The design is in wavelengths and the mesh cell is λ0/100,
so the run at 24.048 GHz is the same simulation scaled (identical result without metal losses).
FD04_SYM=4 (default): quarter model, the 8.4 λ head needs ~110 M cells as a half model (> 15 GB of RAM)."""
import os
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fdtd_eval as fe  # noqa: E402
import optimize as op  # noqa: E402

RES = Path(__file__).resolve().parent / "results"
best = json.loads((RES / "axial_corrugated_fD0.40_best.json").read_text())
fam = op.AxialCorrugated()
x = [best["x"][k] for k in fam.keys]
cfg = fe.EvalConfig(fD=0.4, cells_per_lambda=100, s11_weight=0.05, symmetry=int(os.environ.get("FD04_SYM", "4")))
out_p = RES / "fd04_verify_100cpl.json"
out = json.loads(out_p.read_text()) if out_p.exists() else {}
for f0 in [float(a) for a in (sys.argv[1:] or ["10.368"])]:
    geo = fam.build(x, f0, 0.4)
    from feedlab import openems_sim
    print(f0, "estimate", openems_sim.mesh_estimate(geo, openems_sim.DeepConfig(
        f_lo=f0 * 0.9, f_hi=f0 * 1.1, cells_per_lambda=100 / 1.1, symmetry=cfg.symmetry)), flush=True)
    r = fe.evaluate(geo, cfg, label=f"fd04 {f0} 100cpl")
    r["x"] = best["x"]
    out[f"{f0:g} sym{cfg.symmetry}"] = r
    out_p.write_text(json.dumps(out, indent=1, default=float))
    print(f0, "eta mean", r["eta_mean"], "S11 max", r["s11_max_db"], flush=True)
