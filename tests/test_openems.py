"""openEMS integration: script generation, background jobs and deep analysis, with a fake openEMS
(tests/fake_openems) so that the whole chain runs without the real FDTD solver."""
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

from feedlab import deep_analysis, geometry, openems_local, openems_sim

ROOT = Path(__file__).resolve().parent.parent
FAKE = Path(__file__).resolve().parent / "fake_openems"


@pytest.fixture
def fake_env(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([str(FAKE), str(ROOT)]))
    monkeypatch.setenv("FEEDLAB_CONFIG", str(tmp_path / "cfg"))
    monkeypatch.setenv("FEEDLAB_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("OPENEMS_INSTALL_PATH", raising=False)
    return tmp_path


def _run_script(script, env_extra=None):
    env = os.environ.copy()
    env.update(env_extra or {})
    r = subprocess.run([sys.executable, "-u", str(script)], cwd=script.parent, capture_output=True, text=True, env=env,
                       timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    return r


@pytest.mark.parametrize("kind", ["pickett_potter", "w2imu", "ve4ma", "chaparral", "conical", "open_circular"])
def test_script_generates_and_compiles(tmp_path, kind):
    geo = geometry.build(kind, 47.088, fD=0.7)
    p = openems_sim.make_deep_script(geo, tmp_path, openems_sim.DeepConfig(cells_per_lambda=15))
    src = p.read_text()
    compile(src, str(p), "exec")
    cfg = json.loads((tmp_path / "feed.json").read_text())
    assert cfg["geometry"]["kind"] == kind and len(cfg["geometry"]["polys"]) >= 1
    assert cfg["config"]["ff_freqs"][1] == pytest.approx(47.088)


def test_rect_horn_refused(tmp_path):
    g = geometry.build_rect(10.368, 0.6, "WR-90")
    with pytest.raises(ValueError):
        openems_sim.make_deep_script(g, tmp_path)


def test_full_chain_with_fake_openems(fake_env):
    geo = geometry.build("pickett_potter", 47.088, fD=0.7)
    out = fake_env / "run"
    p = openems_sim.make_deep_script(geo, out, openems_sim.DeepConfig(cells_per_lambda=15, sphere_step=5))
    _run_script(p, {"FAKE_PC_MM": "2.5"})
    st = json.loads((out / "status.json").read_text())
    assert st["stage"] == "done"
    # v1 API still works
    old = openems_sim.load_results(out / "results.json")
    assert len(old["s11"]) == 201 and old["pattern"].theta_deg[-1] == 180
    r = deep_analysis.load(out)
    assert len(r.ff) == 3 and r.sphere is not None
    dish = deep_analysis.DishSpec("offset", 600, 0.7)
    a = deep_analysis.analyze(r, dish)
    # injected phase centre recovered (amplitude-only pattern + 2.5 mm shift)
    assert a["f0_detail"]["phase_center"]["d_mm"] == pytest.approx(2.5, abs=0.15)
    # BOR1 directivity == full-sphere directivity for a BOR1 field
    f0 = [x for x in a["per_freq"] if abs(x["f_ghz"] - 47.088) < 1e-6][0]
    assert a["sphere"]["D_dbi"] == pytest.approx(f0["D_bor_dbi"], abs=0.1)
    assert a["sphere"]["bor_dev_db"] < 0.05
    assert a["sphere"]["rad_eff"] == pytest.approx(0.98, abs=0.05)
    assert -40 < a["s11"]["s11_f0_db"] < -25
    assert 0.5 < a["f0_detail"]["eta_total"] < 0.9
    # exports
    html = deep_analysis.html_report(r, a, dish, fake_env / "rep.html")
    assert "deep analysis" in html.read_text()
    assert len(deep_analysis.export_csv(r, fake_env / "csv")) == 4
    assert len(deep_analysis.export_dat(r, fake_env / "dat")) == 6


def test_background_queue_and_progress(fake_env):
    geo = geometry.build("w2imu", 10.368, fD=0.6)
    jobs = [openems_local.create_job(geo, openems_sim.DeepConfig(cells_per_lambda=c, sphere=False), label=f"c{c}",
                                     study="conv") for c in (15, 20)]
    os.environ["FAKE_RUN_SECONDS"] = "1.5"
    try:
        openems_local.start_batch(jobs, sys.executable)
        seen_running = False
        t0 = time.time()
        while time.time() - t0 < 60:
            states = [openems_local.job_state(j) for j in jobs]
            if any(s["state"] == "running" and s["progress"] > 0 for s in states):
                seen_running = True
            if all(s["state"] == "done" for s in states):
                break
            time.sleep(0.2)
    finally:
        os.environ.pop("FAKE_RUN_SECONDS", None)
    assert all(s["state"] == "done" for s in states), [s["log_tail"][-500:] for s in states]
    assert seen_running
    assert len(openems_local.list_jobs()) == 2
    rows = deep_analysis.compare([(s["label"], deep_analysis.load(s["dir"])) for s in states],
                                 deep_analysis.DishSpec("prime", 900, 0.6, block_diam_mm=60))
    conv = deep_analysis.convergence(rows)
    assert conv["ok"] is True and len(conv["rows"]) == 2


def test_detection_and_bindings_check(fake_env, tmp_path):
    root = tmp_path / "oems" / "openEMS"
    (root / "python").mkdir(parents=True)
    (root / openems_local.EXE).write_text("")
    (root / "python" / "openEMS-0.37.0-cp313-cp313-win_amd64.whl").write_text("")
    (root / "python" / "CSXCAD-0.7.0-cp313-cp313-win_amd64.whl").write_text("")
    inst = openems_local.find_install(tmp_path / "oems")
    assert inst.found and inst.root == str(root) and inst.wheel_tags() == ["cp313"]
    assert len(openems_local.matching_wheels(inst, "cp313")) == 2
    c = openems_local.check_bindings(sys.executable, inst)
    assert c["ok"], c          # fake bindings on PYTHONPATH


def test_mesh_estimate_scales():
    geo = geometry.build("pickett_potter", 24.048, fD=0.7)
    a = openems_sim.mesh_estimate(geo, openems_sim.DeepConfig(cells_per_lambda=15, air_cells_per_lambda=0))
    b = openems_sim.mesh_estimate(geo, openems_sim.DeepConfig(cells_per_lambda=30, air_cells_per_lambda=0))
    assert 3.5 < b["cells"] / a["cells"] < 10 and b["time_min"] > a["time_min"]
    # graded air mesh and the half model cut the cells of a 100 c/λ run
    u = openems_sim.mesh_estimate(geo, openems_sim.DeepConfig(cells_per_lambda=100, air_cells_per_lambda=0))
    g = openems_sim.mesh_estimate(geo, openems_sim.DeepConfig(cells_per_lambda=100))
    h = openems_sim.mesh_estimate(geo, openems_sim.DeepConfig(cells_per_lambda=100, symmetry=2))
    assert g["cells"] < u["cells"] and abs(h["cells"] * 2 - g["cells"]) < 0.01 * g["cells"]


def test_deep_script_symmetry_and_grading(tmp_path):
    geo = geometry.build("w2imu_oe2igl", 10.368, fD=0.6)
    for sym in (1, 2, 4):
        s = openems_sim.make_deep_script(geo, tmp_path / str(sym), openems_sim.DeepConfig(symmetry=sym, grading=1.3),
                                         name="sim.py").read_text()
        compile(s, "sim.py", "exec")


def test_pick_windows_asset():
    rel = {"assets": [{"name": "openEMS_v0.37.0_src.zip"}, {"name": "openEMS_v0.37.0_win64_msvc.zip"},
                      {"name": "checksums.txt"}]}
    assert openems_local.pick_windows_asset(rel)["name"] == "openEMS_v0.37.0_win64_msvc.zip"


def test_extract_finds_root(tmp_path):
    import zipfile
    z = tmp_path / "o.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("openEMS/" + openems_local.EXE, "")
        zf.writestr("openEMS/python/openEMS-0.37.0-cp313-cp313-win_amd64.whl", "")
    root = openems_local.extract(z, tmp_path / "dest")
    assert root == (tmp_path / "dest" / "openEMS")


def test_guided_install_from_zip(fake_env, tmp_path):
    import zipfile
    z = tmp_path / "openEMS_win64.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("openEMS/" + openems_local.EXE, "")
        zf.writestr("openEMS/README.txt", "openEMS v0.37.0 Windows build")
    st = openems_local.guided_install(tmp_path / "target", zip_path=z, python=sys.executable,
                                      status_path=tmp_path / "st.json", run_test=True)
    assert st["state"] == "done", st
    assert openems_local.load_settings()["openems_root"].endswith("openEMS")
    s = openems_local.read_status(tmp_path / "st.json")
    assert s["steps_done"] == openems_local.INSTALL_STEPS


def test_far_field_not_rounded_to_zero():
    """openEMS far fields are ~1e-11 V/m: the script must keep significant digits (0.4.10 stored zeros)."""
    import numpy as np
    src = openems_sim._TEMPLATE
    ns = {}
    exec(src[src.index("def _l(a):"):src.index("def main(")], ns)
    v = ns["_l"](np.array([[1.234e-11, -5e-13], [0.0, 2e-12]]))
    assert v[0][0] == pytest.approx(1.234e-11) and v[1][1] == pytest.approx(2e-12)
    assert "--post" in src and "post_only" in src


def test_input_guide_wall_resolved_at_low_frequency(tmp_path):
    """Regression (0.4.25): the input guide that runs into the back PML had a fixed 0.5 mm wall; at 10 GHz the
    cells are ≈1.3 mm, the wall fell between mesh lines and the guide was open (S11 ≈ −2.6 dB). The wall must be
    at least two cells thick and have its own mesh lines."""
    from feedlab import geometry, openems_sim
    script = openems_sim.make_deep_script(geometry.build("iz0jny", 10.3682, fD=0.7), tmp_path).read_text(encoding="utf-8")
    assert "w_in = max(1.0, 2.0 * res)" in script
    assert "R_IN + w_in" in script and "R_IN + 0.5" not in script
