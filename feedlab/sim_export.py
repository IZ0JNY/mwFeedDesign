# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ivan De Cesaris, IZ0JNY
"""Scripts to simulate the designed feed in other full-wave programs.

* `openems_zip(geo, ...)`: the self-contained openEMS Python script of `feedlab.openems_sim` (geometry and
  settings embedded, no FeedLab needed) + feed.json + a short README. It writes results.json, which FeedLab
  reads back (tab Full-wave openEMS > Results).
* `cst_macro(geo, ...)`: a CST Studio Suite VBA macro that builds the same model in the History List
  (units, frequency range, PEC body of revolution, input guide, waveguide port TE11, open boundaries,
  hexahedral mesh, far-field monitors, time-domain solver settings). The solver is not started.
* `cst_zip(geo, ...)`: the macro + README.

Both cover the feeds with rotational symmetry (all FeedLab feeds except the rectangular horn).
"""
from __future__ import annotations

import io
import json
import tempfile
import zipfile
from pathlib import Path

import numpy as np

from . import __version__, openems_sim
from .geometry import FeedGeometry
from .waveguide import wavelength_mm


def supported(geo) -> bool:
    return isinstance(geo, FeedGeometry) and hasattr(geo, "polygons")


def _check(geo):
    if not supported(geo):
        raise ValueError("gli script per i simulatori coprono i feed a simmetria di rotazione "
                         "(non la tromba rettangolare)")


def _freqs(f0: float, band_pct: float, n_ff: int) -> tuple[float, float, list[float]]:
    f_lo, f_hi = f0 * (1 - band_pct / 100.0), f0 * (1 + band_pct / 100.0)
    ffs = [float(x) for x in np.linspace(f_lo, f_hi, n_ff)] if n_ff > 1 else [float(f0)]
    if not any(abs(x - f0) < 1e-9 for x in ffs):
        ffs = sorted(ffs + [float(f0)])
    return f_lo, f_hi, ffs


def _title(geo) -> str:
    return f"FeedLab {__version__} - {geo.kind} @ {geo.f_ghz:g} GHz"


# ------------------------------------------------------------------------------------------------ openEMS
_OEMS_README = """\
{title}
Script openEMS / openEMS script

IT
  Serve openEMS con i binding Python (CSXCAD + openEMS), https://openems.de
  1) python -u {script}            simulazione completa (S11, lobi, sfera a f0) -> results.json
     python -u {script} --preview  solo il modello in AppCSXCAD, senza simulare
  2) Carica results.json in FeedLab, scheda Full-wave openEMS > Risultati.
  Geometria e impostazioni sono dentro lo script (copia leggibile in feed.json): non serve FeedLab.
  Banda {f_lo:.4g}-{f_hi:.4g} GHz, {cells} celle per lambda, lobi a {ffs} GHz.

EN
  Needs openEMS with its Python bindings (CSXCAD + openEMS), https://openems.de
  1) python -u {script}            full run (S11, patterns, sphere at f0) -> results.json
     python -u {script} --preview  model only in AppCSXCAD, no simulation
  2) Load results.json in FeedLab, tab Full-wave openEMS > Results.
  Geometry and settings are inside the script (readable copy in feed.json): FeedLab is not needed.
  Band {f_lo:.4g}-{f_hi:.4g} GHz, {cells} cells per lambda, patterns at {ffs} GHz.
"""


def openems_zip(geo, band_pct: float = 10.0, cells_per_lambda: int = 100, n_ff: int = 3,
                sphere: bool = True, end_db: float = 40.0) -> bytes:
    _check(geo)
    f_lo, f_hi, ffs = _freqs(geo.f_ghz, band_pct, n_ff)
    cfg = openems_sim.DeepConfig(f_lo=f_lo, f_hi=f_hi, cells_per_lambda=int(cells_per_lambda), ff_freqs=ffs,
                                 sphere=bool(sphere), end_db=float(end_db), label=geo.kind)
    buf = io.BytesIO()
    with tempfile.TemporaryDirectory() as td, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        p = openems_sim.make_deep_script(geo, td, cfg)
        z.write(p, p.name)
        z.write(Path(td) / "feed.json", "feed.json")
        z.writestr("LEGGIMI_README.txt", _OEMS_README.format(
            title=_title(geo), script=p.name, f_lo=f_lo, f_hi=f_hi, cells=int(cells_per_lambda),
            ffs=", ".join(f"{x:.4g}" for x in ffs)))
    return buf.getvalue()


# ------------------------------------------------------------------------------------------------ CST
def _n(v: float) -> str:
    """number for the VBA history (always '.' as decimal separator)"""
    s = f"{float(v):.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _clean_poly(p) -> list[tuple[float, float]]:
    """(r, z) points without repeats (CST refuses zero-length edges), not closed (closed by the macro)."""
    pts = []
    for r, z in p:
        q = (round(float(r), 6), round(float(z), 6))
        if not pts or abs(q[0] - pts[-1][0]) > 1e-6 or abs(q[1] - pts[-1][1]) > 1e-6:
            pts.append(q)
    while len(pts) > 1 and abs(pts[0][0] - pts[-1][0]) <= 1e-6 and abs(pts[0][1] - pts[-1][1]) <= 1e-6:
        pts.pop()
    return pts


def _history_block(caption: str, lines: list[str]) -> list[str]:
    """VBA that adds one command block to the CST History List (AddToHistory runs it and stores it)."""
    out = ["    sCmd = \"\""]
    for ln in lines:
        out.append("    sCmd = sCmd & \"" + ln.replace("\"", "\"\"") + "\" & vbLf")
    out.append(f"    AddToHistory \"{caption}\", sCmd")
    return out


def _rotate_block(name: str, component: str, pts: list[tuple[float, float]]) -> list[str]:
    ln = ["With Rotate", "     .Reset", f"     .Name \"{name}\"", f"     .Component \"{component}\"",
          "     .Material \"PEC\"", "     .Mode \"Pointlist\"", "     .StartAngle \"0.0\"", "     .Angle \"360\"",
          "     .Height \"0.0\"", "     .RadiusRatio \"1.0\"", "     .NSteps \"0\"", "     .SplitClosedEdges \"True\"",
          "     .SegmentedProfile \"False\"", "     .SimplifySolid \"True\"",
          "     .UseAdvancedSegmentedRotation \"True\"", "     .CutEndOff \"False\"",
          "     .Origin \"0.0\", \"0.0\", \"0.0\"", "     .Rvector \"1.0\", \"0.0\", \"0.0\"",
          "     .Zvector \"0.0\", \"0.0\", \"1.0\"", f"     .Point \"{_n(pts[0][0])}\", \"{_n(pts[0][1])}\""]
    ln += [f"     .LineTo \"{_n(r)}\", \"{_n(z)}\"" for r, z in pts[1:]]
    ln += [f"     .LineTo \"{_n(pts[0][0])}\", \"{_n(pts[0][1])}\"", "     .Create", "End With"]
    return ln


def cst_macro(geo, band_pct: float = 10.0, cells_per_lambda: int = 100, n_ff: int = 3,
              end_db: float = 40.0) -> str:
    """CST Studio Suite VBA macro (.bas): Home > Macros > Run Macro (or the VBA editor), in a new
    empty MW&RF&Optical project. Every step goes to the History List, so the model can be rebuilt/edited."""
    _check(geo)
    f0 = float(geo.f_ghz)
    f_lo, f_hi, ffs = _freqs(f0, band_pct, n_ff)
    lam0 = wavelength_mm(f0)
    r_in = float(geo.r_input)
    # input guide behind z = 0 (as in the openEMS script): the port sits on its back face, at zmin
    l_in = max(0.5 * lam0, 2 * r_in)
    w_in = max(1.0, 0.05 * lam0)
    polys = [_clean_poly(p) for p in geo.polygons]
    polys = [p for p in polys if len(p) >= 3]
    stub = [(r_in, -l_in), (r_in + w_in, -l_in), (r_in + w_in, 0.0), (r_in, 0.0)]
    solids = [("input_guide", stub)] + [(f"body_{i + 1}", p) for i, p in enumerate(polys)]

    L = ["' " + _title(geo), "' CST Studio Suite - macro VBA generata da FeedLab / VBA macro generated by FeedLab",
         "' IT: nuovo progetto vuoto (MW & RF & Optical), poi Home > Macros > Run Macro e scegli questo file.",
         "'     Ogni passo va nella History List. Il solutore NON parte da solo: controlla e premi Start.",
         "' EN: new empty project (MW & RF & Optical), then Home > Macros > Run Macro and pick this file.",
         "'     Every step goes to the History List. The solver is NOT started: check, then press Start.",
         f"' Feed: {geo.kind}, f0 = {f0:g} GHz, aperture diameter {2 * geo.r_aperture:.3f} mm, "
         f"length {geo.z_aperture:.3f} mm, input diameter {2 * r_in:.3f} mm (z = 0)",
         "' Units: mm, GHz. Feed axis = z, aperture towards +z, port TE11 polarised along x.",
         "", "Option Explicit", "", "Sub Main ()", "    Dim sCmd As String", ""]
    L += _history_block("define units", ["With Units", "     .Geometry \"mm\"", "     .Frequency \"GHz\"",
                                         "     .Time \"ns\"", "End With"])
    L += _history_block("define frequency range", [f"Solver.FrequencyRange \"{_n(f_lo)}\", \"{_n(f_hi)}\""])
    L += _history_block("define background", ["With Background", "     .ResetBackground", "     .Type \"Normal\"",
                                              "End With"])
    L += _history_block("define boundaries", ["With Boundary"]
                        + [f"     .{a} \"expanded open\"" for a in ("Xmin", "Xmax", "Ymin", "Ymax", "Zmin", "Zmax")]
                        + ["     .Xsymmetry \"none\"", "     .Ysymmetry \"none\"", "     .Zsymmetry \"none\"",
                           "End With"])
    for name, pts in solids:
        L += _history_block(f"define rotate: feed:{name}", _rotate_block(name, "feed", pts))
    for name, _ in solids[1:]:
        L += _history_block(f"boolean add shapes: feed:input_guide, feed:{name}",
                            [f"Solid.Add \"feed:input_guide\", \"feed:{name}\""])
    L += _history_block("define port: 1", [
        "With Port", "     .Reset", "     .PortNumber \"1\"", "     .NumberOfModes \"1\"",
        "     .AdjustPolarization \"True\"", "     .PolarizationAngle \"0.0\"", "     .ReferencePlaneDistance \"0\"",
        "     .Coordinates \"Free\"", "     .Orientation \"zmin\"", "     .PortOnBound \"True\"",
        "     .ClipPickedPortToBound \"False\"", f"     .Xrange \"{_n(-r_in)}\", \"{_n(r_in)}\"",
        f"     .Yrange \"{_n(-r_in)}\", \"{_n(r_in)}\"", f"     .Zrange \"{_n(-l_in)}\", \"{_n(-l_in)}\"",
        "     .Create", "End With"])
    L += _history_block("define mesh", [
        "With MeshSettings", "     .SetMeshType \"Hex\"", f"     .Set \"StepsPerWaveNear\", \"{int(cells_per_lambda)}\"",
        f"     .Set \"StepsPerWaveFar\", \"{min(int(cells_per_lambda), 20)}\"", "End With",
        "With Mesh", "     .MeshType \"PBA\"", "End With"])
    for f in ffs:
        L += _history_block(f"define farfield monitor: farfield (f={_n(f)})", [
            "With Monitor", "     .Reset", f"     .Name \"farfield (f={_n(f)})\"", "     .Domain \"Frequency\"",
            "     .FieldType \"Farfield\"", f"     .MonitorValue \"{_n(f)}\"", "     .ExportFarfieldSource \"False\"",
            "     .Create", "End With"])
    L += _history_block("define solver parameters", [
        "Mesh.SetCreator \"High Frequency\"", "With Solver", "     .Method \"Hexahedral\"",
        f"     .SteadyStateLimit \"{_n(-abs(end_db))}\"", "     .StimulationPort \"All\"",
        "     .StimulationMode \"All\"", "     .MeshAdaption \"False\"", "End With"])
    L += ["", "    ' Solver.Start   ' togli l'apostrofo per avviare subito / remove the quote to start at once",
          "End Sub", ""]
    return "\r\n".join(L)


_CST_README = """\
{title}
Macro CST Studio Suite / CST Studio Suite macro

IT
  1) CST Studio Suite: File > New > progetto vuoto MW & RF & Optical (o il modello Antenna > Horn).
  2) Home > Macros > Run Macro... e scegli {macro} (oppure aprila nel VBA Macro Editor e premi Run).
  3) La History List contiene unita (mm, GHz), banda {f_lo:.4g}-{f_hi:.4g} GHz, il feed in PEC
     (solido di rotazione + guida d'ingresso), la porta guida d'onda TE11 sul fondo della guida,
     contorni aperti, mesh esaedrica {cells} celle per lambda, monitor di campo lontano a {ffs} GHz.
  4) Controlla il modello e avvia il Time Domain Solver. Il campo lontano e in 2D/3D Results > Farfields.
  Il feed e in metallo perfetto (PEC): per le perdite assegna il materiale (es. rame) al componente feed.

EN
  1) CST Studio Suite: File > New > empty MW & RF & Optical project (or the Antenna > Horn template).
  2) Home > Macros > Run Macro... and pick {macro} (or open it in the VBA Macro Editor and press Run).
  3) The History List holds units (mm, GHz), band {f_lo:.4g}-{f_hi:.4g} GHz, the feed in PEC
     (body of revolution + input guide), the TE11 waveguide port at the back of the guide,
     open boundaries, hexahedral mesh {cells} cells per lambda, far-field monitors at {ffs} GHz.
  4) Check the model and start the Time Domain Solver. Far field: 2D/3D Results > Farfields.
  The feed is perfect metal (PEC): for losses assign a material (e.g. copper) to the feed component.
"""


def cst_zip(geo, band_pct: float = 10.0, cells_per_lambda: int = 100, n_ff: int = 3, end_db: float = 40.0,
            name: str | None = None) -> bytes:
    f_lo, f_hi, ffs = _freqs(geo.f_ghz, band_pct, n_ff)
    macro = (name or f"feedlab_{geo.kind}_{geo.f_ghz:g}GHz".replace(".", "p")) + ".bas"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(macro, cst_macro(geo, band_pct, cells_per_lambda, n_ff, end_db).encode("ascii", "replace"))
        z.writestr("LEGGIMI_README.txt", _CST_README.format(
            title=_title(geo), macro=macro, f_lo=f_lo, f_hi=f_hi, cells=int(cells_per_lambda),
            ffs=", ".join(f"{x:.4g}" for x in ffs)))
        z.writestr("feed.json", json.dumps({"format": "feedlab-feed", "geometry": openems_sim.geometry_payload(geo)},
                                           indent=1))
    return buf.getvalue()
