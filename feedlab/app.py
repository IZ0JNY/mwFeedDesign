"""FeedLab GUI — run with:  feedlab-gui   (or: streamlit run feedlab/app.py)"""
from __future__ import annotations

import io
import json
import math
import contextlib
import os
import tempfile
import time
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as _st

import feedlab
from feedlab import credits as _credits_mod
from feedlab import filenames as _filenames
from feedlab import sim_export as _sim_export

from feedlab import i18n


def _T(tpl: str, **kw) -> str:
    """Whole-sentence template: translated as one catalogue entry, then filled in."""
    return i18n.tr(tpl).format(**kw)

st = i18n.wrap(_st)

from feedlab import (app_openems, cad, dishes, drawing, efficiency, explore, materials, plate, geometry, modematch, noise, openems_local, openems_sim, patterns, tolerance,
                     reflector, wizard)
from feedlab.waveguide import HAM_BANDS_GHZ, wavelength_mm

S = st.session_state
if "lang" not in S:
    S.lang = i18n.default_lang()
i18n.set_lang(S.lang)
st.set_page_config(page_title="FeedLab — Laboratorio di Progettazione di feed/illuminatori a microonde", page_icon="📡", layout="wide")
from feedlab import beta as _beta
_bst = _beta.status()
if _bst["expiry"]:                                 # 30-day test builds only (off since 0.4.15)
    if _bst["expired"]:
        st.error(f"⛔ FeedLab {feedlab.__version__} BETA TEST: la versione di prova è scaduta "
                 f"(valida {_beta.VALID_DAYS} giorni dall'installazione). Scarica la versione aggiornata.")
        st.link_button("⬇️ Scarica l'ultima versione", _beta.RELEASES_URL)
        st.stop()
    if not S.get("beta_seen"):                     # pop-up once per launch (new session = new launch)
        S["beta_seen"] = True

        @_st.dialog("🧪 BETA TEST")
        def _beta_popup():
            st.markdown(f"**FeedLab {feedlab.__version__} BETA TEST**")
            st.write(_T("Versione di prova valida {n} giorni dall'installazione.", n=_beta.VALID_DAYS))
            _c1, _c2 = st.columns(2)
            _c1.metric("Giorni rimasti", _bst["days_left"])
            _c2.metric("Scadenza", f"{_bst['expires']:%d/%m/%Y}")
            st.write("Alla scadenza il programma si disattiva: scarica la versione aggiornata da GitHub.")
            st.markdown("<div style='text-align:center;font-weight:600;margin-top:0.8em'>"
                        + i18n.tr("Chiudere questa finestra per continuare (✕ in alto a destra).") + "</div>",
                        unsafe_allow_html=True)

        _beta_popup()
if "update_info" not in S:                         # new version on GitHub: checked once per launch
    from feedlab import updates as _updates
    S["update_info"] = _updates.check(feedlab.__version__, i18n.get_lang())
    if S["update_info"]:
        _upd = S["update_info"]

        @_st.dialog(i18n.tr("🆕 Nuova versione disponibile"), width="large")
        def _update_popup():
            st.markdown(_T("**FeedLab {new}** è disponibile (stai usando la {cur}).", new=_upd["version"],
                           cur=feedlab.__version__))
            st.markdown(f"**{i18n.tr('Cosa c’è di nuovo')}**")
            _st.markdown(_upd["notes"] or i18n.tr("Vedi le note di rilascio su GitHub."))   # already in the right language
            st.link_button("⬇️ Scarica la nuova versione", _upd["url"])

        _update_popup()
WORK = Path(tempfile.gettempdir()) / "feedlab_work"
WORK.mkdir(exist_ok=True)

BANDS = {f"{v:g} GHz ({k})": v for k, v in HAM_BANDS_GHZ.items() if v <= 140}


# ---------------------------------------------------------------- helpers
def _defaults():
    S.setdefault("f_ghz", None)                       # start blank: the user picks frequency, dish, feed, material
    S.setdefault("dish", None)
    S.setdefault("feed_kind", None)
    S.setdefault("material", None)
    S.setdefault("overrides", {})
    S.setdefault("wall", None)
    S.setdefault("cands", None)
    S.setdefault("fullwave", None)


_defaults()


class _Skip(Exception):
    """raised inside a tab when frequency, dish, feed type or material are not chosen yet"""


def _missing():
    return [t for t, ok in (("frequenza", S.f_ghz), ("parabola", S.dish), ("tipo di feed", S.feed_kind),
                            ("materiale", S.material)) if not ok]


def _need():
    """stop the current tab (not the whole page) until the start-up choices are made"""
    miss = _missing()
    if miss:
        st.info(_T("Per iniziare seleziona: {what}. Frequenza e materiale nella barra laterale, la parabola nella "
                   "Procedura guidata, il tipo di feed in Progetto feed.", what=", ".join(_T(m) for m in miss)))
        raise _Skip


_ANGLES = ("alpha", "a1", "a2", "angle", "flare_angle")


def _big_changes(over, base):
    """keys of the RF geometry changed a lot from the starting design (> 5 % on a dimension, > 2° on an angle);
    the input guide length is left out (it does not change the radiation)"""
    out = []
    for k, v in (over or {}).items():
        b = base.get(k)
        if "input_length" in k or not isinstance(v, (int, float)) or not isinstance(b, (int, float)):
            continue
        if (abs(v - b) > 2.0) if (k in _ANGLES or k.endswith("_deg")) else (abs(v - b) > 0.05 * max(abs(b), 1e-6)):
            out.append(k)
    return out


def _start_values(kind):
    """dimensions of the starting design (no user changes) under the names used by the overrides"""
    dish = S.dish or wizard.dish_from_prime(600, 0.6)
    base = {}
    try:
        g0 = geometry.build_rect(S.f_ghz, _fd_design(), S.get("wr_wg") or wizard._wg_for(S.f_ghz), wall=S.wall) \
            if kind == "rect_horn" else geometry.build(kind, S.f_ghz, fD=_fd_design(), wall=S.wall)
        base.update({k: v for k, v in g0.params.items() if isinstance(v, (int, float))})
    except Exception:
        pass
    try:
        base.update(explore.base_values(kind, S.f_ghz, _fd_design(), S.wall))
    except Exception:
        pass
    return base


def _openems_hint(keys):
    """reminder only (never blocks): significant geometry changes are worth a full-wave check"""
    if keys:
        st.info(_T("Geometria modificata in modo significativo rispetto al progetto di partenza ({keys}): il simulatore "
                   "rapido resta indicativo, è consigliabile verificarla con una simulazione openEMS (scheda Full-wave "
                   "openEMS) prima di costruire.", keys=", ".join(keys)), icon="💡")


def _sync_taper(src: str, dst: str):
    """The edge-taper slider exists in the wizard and in the Laboratory: moving one moves the other and switches the
    illumination to the user's taper (the feed is redesigned at once for it)."""
    S[dst] = S[src]
    S["ill_taper"] = S[src]
    S["ill_mode"] = "taper"


def _fd_design() -> float:
    """f/D the feed is designed for: from the illumination chosen in the wizard (edge taper or goal), else the
    dish f/D. Every tab builds the feed with it; the efficiency is always evaluated on the real dish."""
    return float(S.get("fd_design") or (S.dish.fD if S.dish else 0.6))


def current_geometry():
    dish = S.dish or wizard.dish_from_prime(600, 0.6)
    kind = S.feed_kind
    ov = dict(S.overrides.get(kind, {}))
    if kind == "rect_horn":
        return geometry.build_rect(S.f_ghz, _fd_design(), S.get("wr_wg") or wizard._wg_for(S.f_ghz), wall=S.wall, **ov)
    return geometry.build(kind, S.f_ghz, fD=_fd_design(), wall=S.wall, **ov)


@st.cache_data(show_spinner=False)
def run_modematch(sections: tuple, f_list: tuple, n_modes: int):
    r = modematch.simulate(list(sections), np.array(f_list), n_modes=n_modes)
    return r


@st.cache_data(show_spinner=False)
def quick_pattern(kind: str, sections: tuple, f0: float, rect_params: tuple | None):
    if rect_params:
        a, b, AH, AE, L = rect_params
        lam = wavelength_mm(f0)
        RH = math.hypot(L, (AH - a) / 2) * AH / max(AH - a, 1e-6)
        RE = math.hypot(L, (AE - b) / 2) * AE / max(AE - b, 1e-6)
        return patterns.rectangular_aperture_pattern(AH / lam, AE / lam, RH / lam, RE / lam, n=80, n_theta=361), None
    r = modematch.simulate(list(sections), [f0], n_modes=16)
    return modematch.aperture_pattern(r, 0, f0, n_rho=48, n_phi=60, n_theta=361), r.aperture_modes[0]


def angle_at_db(theta_deg, level_db, at=-10.0) -> float | None:
    """Total angle (°) between the two directions where the pattern first falls to `at` dB (linear interpolation)."""
    th = np.asarray(theta_deg, float); v = np.asarray(level_db, float)
    idx = np.where(v <= at)[0]
    if not idx.size or idx[0] == 0:
        return None
    i = idx[0]
    t = th[i - 1] + (at - v[i - 1]) * (th[i] - th[i - 1]) / (v[i] - v[i - 1])
    return 2 * float(t)


def polar_fig(p: patterns.Pattern, title: str, floor: float = -40, dish_fD: float | None = None):
    e, h = p.db()
    fig = go.Figure()
    ang = {}
    for name, v, col, key in (("Piano E (φ=0°)", e, "#d62728", "E"), ("Piano H (φ=90°)", h, "#1f77b4", "H")):
        th = np.concatenate([-p.theta_deg[::-1], p.theta_deg])
        vv = np.clip(np.concatenate([v[::-1], v]), floor, 0) - floor
        fig.add_trace(go.Scatterpolar(theta=th, r=vv, mode="lines", name=name, line=dict(color=col)))
        a = angle_at_db(p.theta_deg, v, -10.0)
        ang[key] = a
        if a:                                  # the two −10 dB points of this plane
            fig.add_trace(go.Scatterpolar(theta=[a / 2, -a / 2], r=[-10 - floor] * 2, mode="markers",
                                          marker=dict(color=col, size=9, symbol="diamond"), showlegend=False,
                                          hovertemplate="−10 dB: %{theta:.1f}°<extra></extra>"))
    sub = []
    if ang.get("E") or ang.get("H"):
        sub.append(_T("−10 dB: {e} (E) / {h} (H)", e=f"{ang['E']:.1f}°" if ang.get("E") else "—",
                      h=f"{ang['H']:.1f}°" if ang.get("H") else "—"))
    if dish_fD:
        psi = reflector.half_angle_from_fD(dish_fD)
        fig.add_trace(go.Scatterpolar(theta=[psi, psi, None, -psi, -psi], r=[0, -floor, None, 0, -floor], mode="lines",
                                      line=dict(color="green", dash="dot"), name=i18n.tr("bordo parabola")))
        sub.append(_T("parabola: {a:.1f}°", a=2 * psi))
    if sub:
        title = f"{title}<br><sup>{' · '.join(sub)}</sup>"
    fig.update_layout(title=title, height=460, polar=dict(
        angularaxis=dict(rotation=90, direction="clockwise", tickmode="array",
                         tickvals=list(range(0, 360, 30))),
        radialaxis=dict(tickvals=[0, 10, 20, 30, 40], ticktext=[f"{floor}", f"{floor + 10}", f"{floor + 20}",
                                                                 f"{floor + 30}", "0 dB"])))
    return fig


def lobe3d_fig(p: patterns.Pattern, floor: float = -35):
    th = np.radians(p.theta_deg)
    ph = np.radians(np.arange(0, 361, 4))
    T, PH = np.meshgrid(th, ph, indexing="ij")
    n = p.normalized()
    P = np.abs(n.E)[:, None] ** 2 * np.cos(PH) ** 2 + np.abs(n.H)[:, None] ** 2 * np.sin(PH) ** 2
    db = 10 * np.log10(P + 1e-12)
    R = np.clip(db - floor, 0, None) / -floor
    X, Y, Z = R * np.sin(T) * np.cos(PH), R * np.sin(T) * np.sin(PH), R * np.cos(T)
    fig = go.Figure(go.Surface(x=X, y=Y, z=Z, surfacecolor=np.clip(db, floor, 0), colorscale="Turbo",
                               cmin=floor, cmax=0, colorbar=dict(title="dB")))
    fig.update_layout(height=560, scene=dict(aspectmode="data", xaxis_title="x (piano E)", yaxis_title="y (piano H)",
                                             zaxis_title="z (verso il riflettore)"),
                      title="Lobo di irradiazione 3D del feed (normalizzato)")
    return fig


def model3d_fig(geo, cut: bool):
    detailed = isinstance(geo, geometry.RectHornGeometry) or getattr(geo, "mount", None) is not None or \
        bool(geo.params.get("base_square"))
    v = None
    if detailed:                                  # real solid (OpenCascade): holes, counterbores, square base
        try:
            v, f = cad.mesh(geo, cut=cut and not isinstance(geo, geometry.RectHornGeometry))
        except Exception:
            v = None
    if v is None:
        v, f = cad.profile_mesh(geo, n_phi=64, cut_deg=90 if cut else 0)
    fig = go.Figure(go.Mesh3d(x=v[:, 0], y=v[:, 1], z=v[:, 2], i=f[:, 0], j=f[:, 1], k=f[:, 2],
                              color=materials.color(S.get("material", "")), flatshading=False, lighting=dict(ambient=0.45, diffuse=0.8, specular=0.6, facenormalsepsilon=0, vertexnormalsepsilon=0),
                              opacity=1.0))
    fig.update_layout(height=900, margin=dict(l=0, r=0, t=40, b=0),
                      scene=dict(aspectmode="data", xaxis_title="x mm", yaxis_title="y mm", zaxis_title="z mm",
                                 camera=dict(eye=dict(x=1.25, y=1.25, z=0.9))),
                      title=f"Modello 3D ({S.get('material', 'Ottone CuZn39Pb3')}) — z = 0 flangia d'ingresso")
    return fig


def section_fig(geo):
    fig = go.Figure()
    if isinstance(geo, geometry.RectHornGeometry):
        return None
    for poly in geo.polygons:
        for s in (1, -1):
            P = np.vstack([poly, poly[:1]])
            fig.add_trace(go.Scatter(x=P[:, 1], y=s * P[:, 0], fill="toself", mode="lines",
                                     line=dict(color="black", width=1), fillcolor=materials.rgba(S.get("material", ""), 0.75),
                                     showlegend=False))
    fig.add_hline(y=0, line_dash="dashdot", line_color="gray")
    t = float(geo.params.get("wall", 0) or 0)
    feats = geometry.wall_features(geo.profile)
    if geo.kind in geometry.CORRUGATED_KINDS:      # slots: no smooth-horn step/flare labels
        feats = {**feats, "steps": [], "flares": []}
    ann = dict(showarrow=True, arrowhead=0, arrowwidth=1, ax=0, ay=-28, font=dict(size=11), bgcolor="rgba(255,255,255,0.8)")
    for z, ra, rb in feats["steps"]:
        z0 = z - t if rb > ra else z
        fig.add_annotation(x=z0 + t / 2, y=(min(ra, rb) + t + max(ra, rb)) / 2, text=f"gradino {t:.2f} mm", **ann)
    for z0, r0, z1, r1, a in feats["flares"]:
        fig.add_annotation(x=(z0 + z1) / 2, y=-(r0 + r1) / 2, text=f"flare α = {abs(a):.2f}°",
                           **{**ann, "ay": 28, "font": dict(size=11, color="red"), "arrowcolor": "red"})
    # names of the design dimensions (as in the PDF drawing): axial lengths above, diameters on the part
    if geo.kind not in geometry.CORRUGATED_KINDS:
        prof = geo.profile
        Rmax = max(geo.outer_radius, max(r for _, r in prof))
        zs = sorted({round(z, 4) for z, _ in prof})
        named, lev = set(), 0
        for z0, z1 in zip(zs[:-1], zs[1:]):
            k = drawing._param_for(geo, z1 - z0, False)
            if not k or k in named:
                continue
            named.add(k)
            y = Rmax * (1.18 + 0.16 * (lev % 2)); lev += 1
            fig.add_shape(type="line", x0=z0, x1=z1, y0=y, y1=y, line=dict(color="royalblue", width=1))
            for zz in (z0, z1):
                fig.add_shape(type="line", x0=zz, x1=zz, y0=y - 0.04 * Rmax, y1=y + 0.04 * Rmax,
                              line=dict(color="royalblue", width=1))
            fig.add_annotation(x=(z0 + z1) / 2, y=y, text=f"{k} {z1 - z0:.2f}", showarrow=False, yshift=9,
                               font=dict(size=10, color="royalblue"), bgcolor="rgba(255,255,255,0.7)")
        seen = set()
        for z, r in prof:
            k = drawing._param_for(geo, 2 * r, True)
            if not k or k in seen:
                continue
            seen.add(k)
            fig.add_shape(type="line", x0=z, x1=z, y0=-r, y1=r, line=dict(color="seagreen", width=1, dash="dot"))
            fig.add_annotation(x=z, y=0, text=f"Ø {k} {2 * r:.2f}", showarrow=False, textangle=-90, xshift=-8,
                               font=dict(size=10, color="seagreen"), bgcolor="rgba(255,255,255,0.7)")
        if geo.kind == "iz0jny":                      # inner step: height and length
            pp = geo.params
            zs, ri, rs, ls = pp["input_length"], pp["Di_input"] / 2, pp["Ds_step"] / 2, pp["Ls"]
            fig.add_shape(type="line", x0=zs + ls / 2, x1=zs + ls / 2, y0=ri, y1=rs, line=dict(color="red", width=2))
            fig.add_annotation(x=zs + ls / 2, y=(ri + rs) / 2, ax=60, ay=40, showarrow=True, arrowcolor="red",
                               text=_T("scalino interno h {h:.2f} · Ls {l:.2f}", h=rs - ri, l=ls),
                               font=dict(size=10, color="red"), bgcolor="rgba(255,255,255,0.8)")
        fig.update_yaxes(range=[-Rmax * 1.25, Rmax * 1.5])
    fig.update_layout(height=380, yaxis=dict(scaleanchor="x"), xaxis_title="z (mm)", yaxis_title="r (mm)",
                      title=f"Sezione assiale · parete {t:.2f} mm", margin=dict(t=40, b=10))
    return fig


# readable name of each feed dimension (the code next to it is the label on the section drawing)
PARAM_NAMES = {
    'A_input': "diametro della guida d'ingresso",
    'B_aperture': "diametro dell'apertura",
    'C_phasing': 'lunghezza della sezione di fase',
    'D_aperture': "diametro dell'apertura",
    'Di': "diametro d'ingresso",
    'Di_input': "diametro d'ingresso",
    'Ds': 'diametro dopo il gradino',
    'Ds_step': 'diametro dopo il gradino',
    'Dm': 'diametro del cilindro di fase',
    'Ls': 'lunghezza del gradino',
    'L1': 'lunghezza del 1° cono',
    'Lp': 'lunghezza della sezione di fase',
    'L2': 'lunghezza del 2° cono',
    'L_guide': "lunghezza della guida d'ingresso",
    'input_length': "lunghezza della guida d'ingresso",
    'las': "lunghezza della guida d'ingresso",
    'length': 'lunghezza',
    'diam': 'diametro',
    'flare_length': 'lunghezza del cono',
    'flare_half_deg': 'semi-angolo del cono',
    'cone1_half_deg': 'semi-angolo del 1° cono',
    'cone2_half_deg': 'semi-angolo del 2° cono',
    'horn_diam': 'diametro della tromba',
    'ring_width': "larghezza dell'anello (choke)",
    'ring_depth': "profondità dell'anello (choke)",
    'ring_setback': "arretramento dell'anello (choke)",
    'ring_wall': "spessore della parete dell'anello",
    'aperture_H': 'apertura sul piano H',
    'aperture_E': 'apertura sul piano E',
    'axial_length': 'lunghezza della tromba',
    'pitch': 'passo radiale delle scanalature',
    'w': 'larghezza delle scanalature',
    'axi': 'passo assiale delle scanalature',
    'delta': 'labbro prima della 1ª scanalatura',
    'd1': 'profondità della scanalatura 1',
    'd2': 'profondità della scanalatura 2',
    'd3': 'profondità della scanalatura 3',
    'd4': 'profondità della scanalatura 4',
    'd5': 'profondità della scanalatura 5',
    'd6': 'profondità della scanalatura 6',
    'd7': 'profondità della scanalatura 7',
    'd8': 'profondità della scanalatura 8',
}


# ---------------------------------------------------------------- sidebar
def _set_lang():
    i18n.set_lang(S.lang)
    try:
        openems_local.save_settings(language=S.lang)
    except Exception:
        pass


@_st.dialog("ℹ️ Credits", width="large")
def _credits_dialog():
    from feedlab import credits as _cr
    _cr.render(st, header=False)


@_st.dialog(i18n.tr("ℹ️ Informazioni sui materiali"), width="large")
def _materials_dialog():
    """Table that helps choosing the feed material: conductivity, roughness, density, losses and pros / cons."""
    import html as _h
    tr = i18n.tr
    _col = {1: "#d64545", 2: "#e8833a", 3: "#e0b416", 4: "#8bc34a", 5: "#2e9e4f"}   # red (poor) … green (excellent)
    dots = lambda n: "".join(f'<i style="background:{_col[n]}"></i>' if i < n else "<i></i>" for i in range(5))
    st.markdown("Voti da 1 pallino 🔴 (scarso) a 5 pallini 🟢 (ottimo); **Prezzo**: 5 pallini = il più economico. "
                "**Perdite**: perdite ohmiche di una parete liscia rispetto al rame (1.0×); la rugosità le aumenta "
                "ancora, soprattutto sopra 24 GHz.")
    st.markdown("💡 **Per iniziare:** alluminio 6061/6082 (economico, leggero) con l'interno lucidato; per le "
                "perdite più basse ottone argentato o rame argentato; all'aperto proteggi il feed (vernice, "
                "radome o coperchio).")
    head = ["Materiale", "σ (10⁷ S/m)", "Rq (µm)", "Densità (g/cm³)", "Perdite × rame", "Lavorabilità", "Prezzo",
            "Reperibilità", "Agenti atmosferici", "Trattamenti (argentatura, doratura…)", "Pro", "Contro"]
    rows = []
    for m in sorted(materials.MATERIALS.values(), key=lambda m_: -m_.sigma):
        g = materials.GUIDE.get(m.name)
        if not g:
            continue
        sel = ' class="sel"' if m.name == S.get("material") else ""
        cells = [f"<b>{_h.escape(tr(m.name))}</b>", f"{m.sigma / 1e7:.2f}", f"{m.rq_um:g}", f"{m.density:.2f}",
                 f"{materials.loss_vs_copper(m):.1f}×"] + [f'<span class="st">{dots(v)}</span>' for v in g[:5]] + \
                [_h.escape(tr(g[5])), _h.escape(tr(g[6]))]
        rows.append(f"<tr{sel}>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    _st.html("""<style>
      .mt {max-height:60vh; overflow-y:scroll; overflow-x:auto; border:1px solid #ccc4; border-radius:6px;
           scrollbar-width:auto; scrollbar-color:#2e5c8a #dde4ec}
      .mt::-webkit-scrollbar {width:14px; height:14px}
      .mt::-webkit-scrollbar-track {background:#dde4ec; border-radius:7px}
      .mt::-webkit-scrollbar-thumb {background:#2e5c8a; border-radius:7px; border:2px solid #dde4ec}
      .mt::-webkit-scrollbar-thumb:hover {background:#1d4166}
      .hint {font-size:13px; margin:2px 0 6px; color:#2e5c8a; font-weight:600}
      .mt table {border-collapse:collapse; font-size:12px; min-width:1100px}
      .mt th {position:sticky; top:0; background:#2e5c8a; color:#fff; padding:5px 6px; text-align:left; z-index:1}
      .mt td {padding:4px 6px; border-top:1px solid #ccc5; vertical-align:top}
      .mt td:first-child {min-width:170px}
      .mt tr:nth-child(even) td {background:#8881}
      .mt tr.sel td {background:#ffe9a8 !important; color:#000}
      .mt .st {white-space:nowrap}
      .mt .st i {display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:3px;
                 background:transparent; border:1px solid #9995; box-sizing:border-box}
      .mt .st i[style] {border-color:#0002}
      .mt td:nth-child(11), .mt td:nth-child(12) {min-width:200px}
    </style><div class="hint">""" + _h.escape(tr("↕ Scorri la tabella con la barra a destra per vedere tutti i {n} materiali").replace("{n}", str(len(rows)))) + """</div><div class="mt"><table><tr>""" + "".join(f"<th>{_h.escape(tr(h))}</th>" for h in head) + "</tr>"
             + "".join(rows) + "</table></div>")
    st.caption("Conducibilità: valori tipici della lega. Rugosità: finitura di serie dei servizi CNC (Ra 1.6–3.2 µm) "
               "o di un interno lucidato; ordinando chiedi Ra ≤ 0.8 µm all'interno del feed.")


with st.sidebar:
    st.title("📡 FeedLab")
    st.subheader("Laboratorio di Progettazione di feed/illuminatori a microonde")
    st.caption("10–134 GHz · Software progettato da Ivan IZ0JNY")
    _bands = list(BANDS) + ["Altra frequenza…"]
    band = st.selectbox("Banda", _bands, index=None, placeholder="Seleziona frequenza", key="band_sel")
    if band is None:
        S.f_ghz = None
    elif band == "Altra frequenza…":
        S.f_ghz = st.number_input("Frequenza (GHz)", 10.0, 140.0, float(S.get("f_other") or 10.368), 0.001,
                                  format="%.3f", key="f_other")
    else:
        S.f_ghz = BANDS[band]
    if S.f_ghz:
        st.metric("λ", f"{wavelength_mm(S.f_ghz):.3f} mm")
    if S.dish:
        d = S.dish
        st.markdown(f"**Parabola:** {'offset' if d.kind == 'offset' else 'prime focus'} · D {d.D_mm:.0f} mm · "
                    f"f/D{' eq.' if d.kind == 'offset' else ''} {d.fD:.3f} · apertura {d.opening_deg:.1f}°")
    if S.feed_kind:
        st.markdown(f"**Feed:** {geometry.FEED_TYPES[S.feed_kind]}")
    if st.button("ℹ️ Informazioni sui materiali", key="mat_info_btn", width="stretch",
                 help="tabella per scegliere il materiale: conducibilità, rugosità, peso, lavorabilità, prezzo, "
                      "reperibilità, resistenza agli agenti atmosferici, pro e contro"):
        _materials_dialog()
    mats = sorted(materials.MATERIALS, key=lambda m_: i18n.tr(m_).lower())   # alphabetical in the chosen language
    S.material = st.selectbox("Materiale del feed", mats, index=None, placeholder="Seleziona materiale",
                              key="material_sel", help="conducibilità e rugosità → perdite ohmiche e rumore del feed")
    if S.material:
        m_ = materials.MATERIALS[S.material]
        st.caption(f"σ = {m_.sigma / 1e7:.2f}·10⁷ S/m" +
                   (f" · δ = {materials.skin_depth_um(m_.sigma, S.f_ghz):.3f} µm" if S.f_ghz else "") + f" · {m_.notes}")
    geometry.COLLAR["diam"] = None                   # LNB collar option removed from the interface (0.4.9)
    geometry.MOUNT.update(S.get("mount_cfg") or {"wg": None})
    # base of the feed: round disc or square like the waveguide flange (WR-90, WR-75, WR-42… have square flanges)
    from feedlab import flanges as _fl
    from feedlab.waveguide import suggest_rect_wg as _sug
    # rectangular waveguide the feed is screwed to (through the λ/4 plate): the usual ones for the band
    # (10 GHz WR-90 or WR-75, 24 GHz WR-42, 47 GHz WR-22 or WR-19 …). It drives the matching plate, the flange
    # drilling and the square base.
    _wgs = _sug(S.f_ghz) if S.f_ghz else []
    _wr = st.selectbox("Guida d'onda rettangolare", _wgs, key=f"wr_wg_{'_'.join(_wgs)}",
                       help="guida WR che si avvita al feed tramite la piastrina di adattamento circolare → WR: "
                            "dimensiona la piastrina, la foratura e la base quadrata") if _wgs else None
    S["wr_wg"] = _wr
    _mc = S.get("mount_cfg") or {}
    if _wr and _mc.get("wg") and _mc["wg"] != _wr:   # holes drilled for the guide chosen here
        S["mount_cfg"] = {**_mc, "wg": _wr}
        geometry.MOUNT.update(S["mount_cfg"])
    _bwg = None
    _fl_wr = _fl.FLANGES.get(_wr) if _wr else None
    if _fl_wr is not None and _fl_wr.shape == "square":
        if S.get("base_shape_band") != S.f_ghz:       # new band: square like the flange (10, 24 GHz); round from 47 GHz
            S["base_shape"] = "square"
            S["base_shape_band"] = S.f_ghz
        _shape = st.radio("Base del feed", ["round", "square"], horizontal=True, key="base_shape",
                          format_func=lambda x: {"round": "Circolare", "square": "Quadrata"}[x],
                          help="quadrata: lato uguale alla flangia quadrata della guida rettangolare che si avvita "
                               "(WR-90 41.40 mm, WR-75 38.30 mm, WR-42 22.41 mm)")
        if _shape == "square":
            _bwg = _wr
            st.caption(_T("Base quadrata {a:.2f} × {a:.2f} mm come la flangia {wg}", a=_fl_wr.A, wg=_wr) +
                       (" " + i18n.tr("(più larga se fori e lamature non ci stanno)") if (S.get("mount_cfg") or {}).get("wg") else ""))
    else:
        _shape = "round"
        if _fl_wr is not None:
            st.caption(_T("Flangia {wg} rotonda ({name}): base del feed circolare", wg=_wr, name=_fl_wr.name))
    _bt = S.get("base_t")                            # set in the Feed design tab (spessore della base)
    geometry.BASE.update({"shape": _shape, "wg": _bwg, "thickness": _bt})
    geometry.OUTER_PROFILE.update(mode=S.get("outer_mode", "wall"),          # options in the Feed design tab
                                  fillet=float(S.get("outer_fillet") or 0.0))
    _outer = (S.get("outer_mode", "wall"), S.get("outer_fillet"))
    if S.get("base_prev") != (_shape, _bwg, _bt, _outer):                      # stale drawings/models
        S["base_prev"] = (_shape, _bwg, _bt, _outer)
        for k in ("pdf", "step", "stl"):
            S.pop(k, None)
    st.divider()
    if os.environ.get("FEEDLAB_DESKTOP") == "browser":
        if st.button("⏻ Chiudi FeedLab", help="ferma il programma (le simulazioni openEMS in corso continuano)"):
            st.write("FeedLab chiuso: puoi chiudere questa scheda del browser.")
            os._exit(0)
    st.caption(f"Versione {feedlab.__version__}{' BETA TEST' if _bst['beta'] else ''} · © Ivan De Cesaris IZ0JNY")
    st.selectbox("Lingua / Language", list(i18n.LANGS), key="lang", format_func=lambda k: i18n.LANGS[k],
                 on_change=_set_lang)       # chosen in the installer; here for the portable version
    if st.button("ℹ️ Credits", key="credits_btn", help="Autore, versione e tutte le fonti"):
        _credits_dialog()
    if st.button("🔄 Controlla aggiornamenti", key="upd_btn", help="chiede a GitHub se c'è una versione più nuova"):
        from feedlab import updates as _updates
        _u = _updates.check(feedlab.__version__, i18n.get_lang())
        if _u:
            st.markdown(_T("**FeedLab {new}** è disponibile (stai usando la {cur}).", new=_u["version"],
                           cur=feedlab.__version__))
            st.link_button("⬇️ Scarica la nuova versione", _u["url"])
        elif _updates.LAST_ERROR:
            st.warning(_T("Impossibile contattare GitHub ({e}). Controlla la connessione o scarica da {url}",
                          e=_updates.LAST_ERROR, url=_updates.RELEASES_URL))
        else:
            st.success("Hai già l'ultima versione.")
    _mdir = Path(feedlab.__file__).resolve().parent.parent / "docs" / "manual"
    _man = _mdir / i18n.MANUALS.get(i18n.get_lang(), i18n.MANUALS["en"])
    if not _man.exists():
        _man = _mdir / i18n.MANUALS["en"]
    if _man.exists():
        st.download_button("📖 Manuale", _man.read_bytes(), file_name=_man.name, mime="application/pdf",
                           help="manuale d'uso in PDF nella lingua scelta")
    st.link_button("🐞 Segnala un problema", _credits_mod.issue_url(S.get("feed_kind", ""), S.get("f_ghz")),
                   help="apre la pagina GitHub delle segnalazioni (issue) con versione e progetto già compilati")
    st.caption("openEMS (opzionale): " + ("✅ pronto" if (S.get("oems_env") or {}).get("py") else
                                         "vedi scheda Full-wave openEMS"))

# whoever plays with the settings is invited, every few changes, to validate the design with openEMS
if not _missing():
    _sig = repr((S.feed_kind, S.f_ghz, S.dish, S.material, S.get("overrides", {}).get(S.feed_kind),
                 S.get("ill_taper"), S.get("ill_mode"), S.get("fd_design"), S.get("wall"), S.get("base_t"),
                 S.get("base_shape"), S.get("wr_wg"), S.get("mount_cfg")))
    if S.get("tweak_sig") not in (None, _sig):
        S["tweaks"] = S.get("tweaks", 0) + 1
        if S["tweaks"] % 5 == 0:
            _st.toast(i18n.tr("Hai cambiato parecchie impostazioni: è il momento di una validazione con openEMS. Lancia una simulazione full-wave nella scheda 🖥️ Full-wave openEMS: è più lenta ma più precisa del simulatore veloce, valida i dati e verifica che i due risultati convergano."), icon="🖥️", duration=12)
    S["tweak_sig"] = _sig

# Barra dei tab su più righe: tutti i tab visibili senza scroll orizzontale.
_st.markdown("""<style>
[data-testid="stTabs"] [role="tablist"] {flex-wrap:wrap !important; overflow:visible !important; row-gap:2px}
[data-testid="stTabs"] [role="tablist"] ~ button {display:none}
div[data-baseweb="tab-highlight"] {display:none}
button[data-baseweb="tab"][aria-selected="true"] {box-shadow:inset 0 -3px 0 currentColor}
</style>""", unsafe_allow_html=True)

tabs = st.tabs(["🧭 Procedura guidata", "📐 Progetto feed", "🎛️ Laboratorio", "📈 Simulazione & S11", "🌐 Lobo 3D",
                "🧊 Modello 3D", "🔩 Montaggio feed + piastrina", "🔲 Piastrina WR", "📄 Disegno & STEP",
                "🖥️ Full-wave openEMS", "📦 Output di progetto", "ℹ️ Credits"])


def _project_snapshot():
    """Plain copy of what the project file needs (the build runs in a background thread)."""
    keys = ["f_ghz", "dish", "feed_kind", "material", "overrides", "wall", "base_t", "base_shape", "wr_wg", "mount_cfg",
            "mount_ui", "plate_rf", "fd_design", "ill_mode", "ill_taper", "ill_goal", "outer_mode", "outer_fillet",
            "lab_scenario"]
    return {k: S.get(k) for k in keys}


def _autosave_project():
    """Keep the open design as a project file for EMELab (it reads it: 📥 Prendi da FeedLab), without slowing
    the interface: rebuilt in the background only when the inputs change."""
    if _missing():
        return
    snap = _project_snapshot()
    key = repr({k: v for k, v in snap.items()})
    if S.get("_proj_auto_key") == key:
        return
    S["_proj_auto_key"] = key
    import threading
    from feedlab import project as _project
    try:
        geo = current_geometry()
        fdd = _fd_design()
    except Exception:
        return

    def work():
        try:
            _project.save_auto(_project.build(snap, geo, fdd, with_sweep=False))
        except Exception:
            pass
    threading.Thread(target=work, daemon=True).start()


_autosave_project()


def _apply_project(p: dict):
    """Open a project file: restore dish, band, feed, dimensions, material, illumination and mounting."""
    from feedlab import project as _project
    from feedlab.waveguide import suggest_rect_wg as _sug
    i = p["inputs"]
    f = float(i["f_ghz"])
    lab = next((k for k, v in BANDS.items() if abs(v - f) < 1e-6), None)
    S["band_sel"] = lab or "Altra frequenza…"
    if lab is None:
        S["f_other"] = f
    S["material_sel"] = i.get("material")
    if i.get("wr_wg"):
        S[f"wr_wg_{'_'.join(_sug(f))}"] = i["wr_wg"]
    if i.get("base_shape"):
        S["base_shape"] = i["base_shape"]
        S["base_shape_band"] = f
    _project.apply(S, p)             # also maps a feed type no longer in the list to its base type
    S["cands"] = None

# ---------------------------------------------------------------- 1 wizard
with tabs[0]:
    st.header("Scegli il feed migliore per la tua parabola")
    c1, c2, c3 = st.columns(3)
    with c1:
        src = st.radio("Parabola", ["Catalogo commerciale (datasheet)", "Parabola custom"], horizontal=True)
        dish = None
        if src.startswith("Catalogo"):
            cat = dishes.by_label()
            makers = sorted({d.maker for d in dishes.CATALOG}, key=str.lower)
            mk = st.selectbox("Costruttore", makers, index=None, placeholder="Seleziona parabola", key="dish_maker")
            labs = [l for l, d in cat.items() if d.maker == mk]
            _ml = st.selectbox("Modello", labs, index=None, placeholder="Seleziona parabola",
                               key=f"dish_model_{mk}", disabled=mk is None)
            dm = cat[_ml] if _ml else None
            if dm is not None:
                f_cat, f_src = dm.focal()
                st.caption(f"Fonte: {dm.source}" + (f" — {dm.notes}" if dm.notes else ""))
                info = {"Tipo": dm.kind, "Dimensioni esterne (mm)": f"{dm.width_mm:.0f} × {dm.height_mm:.0f}",
                        "Area attiva (mm)": f"{dm.active_w_mm:.0f} × {dm.active_h_mm:.0f}" if dm.active_w_mm and dm.active_h_mm else "—",
                        "F/D costruttore": dm.fD_maker or "—", "Focale (mm)": f"{f_cat:.0f} ({f_src})" if f_cat else f_src,
                        "Angolo offset": f"{dm.offset_deg}°" if dm.offset_deg else "—",
                        "Illuminazione richiesta": f"{dm.illum_deg}°" if dm.illum_deg else "—",
                        "Efficienza dichiarata": f"{dm.efficiency_pct}%" if dm.efficiency_pct else "—",
                        "Guadagni": ", ".join(f"{g} dBi @{f:g} GHz" for f, g in dm.gain.items()) or "—",
                        "Collare LNB": dm.collar_mm or "—", "Materiale": dm.material or "—"}
                st.table({"Dato": list(info), "Valore": [str(v) for v in info.values()]})
                if dm.opening_deg() is None or st.checkbox("Ho misurato la mia parabola (più preciso del datasheet)"):
                    st.info("Misura: assi del bordo e profondità massima (righello teso sul bordo lungo l'asse lungo).")
                    la = st.number_input("Asse lungo (mm)", 100.0, 13000.0, float(dm.height_mm))
                    sa = st.number_input("Asse corto (mm)", 100.0, 12000.0, float(dm.width_mm))
                    dp = st.number_input("Profondità massima (mm)", 1.0, 3000.0, float(round(sa * sa / (16 * (f_cat or 0.6 * sa)) * sa / la, 1)))
                    dish = wizard.dish_from_offset_tv(la, sa, dp) if dm.kind == "offset" else wizard.dish_from_prime(sa, depth=dp)
                else:
                    dish = wizard.dish_from_catalog(dm)
        else:
            dk = st.radio("Tipo di parabola", ["Offset (TV/sat)", "Prime focus"], horizontal=True)
            if dk.startswith("Offset"):
                mode = st.radio("Dati disponibili", ["Diametro + f/D (come nei datasheet)", "Misure del riflettore (assi + profondità)",
                                                     "Diametro + focale", "Diametro + angolo di illuminazione"])
                if mode.startswith("Diametro + f/D"):
                    D = st.number_input("Diametro / larghezza (mm)", 100.0, 12000.0, 800.0)
                    fdo = st.number_input("f/D offset (f / larghezza)", 0.3, 2.0, 0.66, 0.01,
                                          help="convenzione dei costruttori di parabole TV (es. Gibertini 0.66, Triax 0.6)")
                    dish = wizard.dish_from_offset_fD(D, fdo * D, 0.0)
                elif mode.endswith("illuminazione"):
                    D = st.number_input("Diametro proiettato (mm)", 100.0, 12000.0, 800.0)
                    ang = st.number_input("Angolo di illuminazione richiesto (° totali)", 20.0, 170.0, 70.0, 0.5)
                    dish = wizard.Dish("offset", D, reflector.fD_from_half_angle(ang / 2), None,
                                       note="parabola custom definita dall'angolo di illuminazione")
                elif mode.startswith("Misure"):
                    la = st.number_input("Asse lungo (mm)", 100.0, 13000.0, 676.0)
                    sa = st.number_input("Asse corto (mm)", 100.0, 12000.0, 630.0)
                    dp = st.number_input("Profondità massima (mm)", 1.0, 3000.0, 52.0)
                    dish = wizard.dish_from_offset_tv(la, sa, dp)
                else:
                    D = st.number_input("Diametro proiettato (mm)", 100.0, 12000.0, 600.0)
                    f = st.number_input("Focale del paraboloide madre (mm)", 50.0, 24000.0, 390.0)
                    h = st.number_input("Distanza asse → bordo inferiore (mm)", 0.0, 6000.0, 0.0)
                    dish = wizard.dish_from_offset_fD(D, f, h)
            else:
                D = st.number_input("Diametro (mm)", 100.0, 20000.0, 1200.0)
                mode = st.radio("Conosco", ["f/D", "Profondità al centro"], horizontal=True)
                if mode == "f/D":
                    fD = st.number_input("f/D", 0.2, 2.0, 0.38, 0.01)
                    dish = wizard.dish_from_prime(D, fD)
                else:
                    dp = st.number_input("Profondità (mm)", 1.0, 5000.0, 197.0)
                    dish = wizard.dish_from_prime(D, depth=dp)
    with c2:
        pol = st.radio("Polarizzazione", ["Lineare", "Circolare"], horizontal=True)
        prio = st.radio("Obiettivo", ["Massimo guadagno (TX/terrestre)", "Massimo G/T (RX, EME, sole)",
                                      "Massime prestazioni RX (minimo rumore)"], index=1,
                        help="G/T: equilibrio fra guadagno e rumore. Prestazioni RX: illuminazione più morbida e feed "
                             "con lobi laterali/posteriori più bassi → meno rumore dal terreno, a costo di un po' di guadagno")
        tools = st.radio("Mezzi di costruzione", ["Tornio / CNC", "Solo lamiera e saldatura"])
        quick = st.checkbox("Stima con simulazione rapida (mode matching, ~20 s)", True)
        ill_mode = st.radio("Illuminazione della parabola", ["auto", "taper"], horizontal=True, key="ill_mode",
                            format_func=lambda k: {"auto": i18n.tr("Automatica (consigliata)"),
                                                   "taper": i18n.tr("Taper al bordo scelto da me")}[k],
                            help="automatica: il feed è progettato come oggi per l'obiettivo scelto; taper al bordo: "
                                 "quanto è più debole il segnale sul bordo della parabola rispetto al centro (dB). "
                                 "Più taper = meno spillover e meno rumore dal terreno, ma meno superficie sfruttata")
        if "ill_taper" not in S:
            S["ill_taper"] = 10.0
        ill_taper = st.slider("Taper al bordo (dB)", 6.0, 25.0, step=0.5, key="ill_taper",
                              disabled=ill_mode != "taper", on_change=_sync_taper, args=("ill_taper", "lab_ill_taper"),
                              help="10–12 dB: massimo guadagno (classico); 12–16 dB: più G/T (EME, RX); < 10 dB: parabola "
                                   "molto illuminata, più spillover")
    if dish is not None:
        S.dish = dish                            # the dish chosen here drives every other tab
    with c3:
        st.subheader("Parabola")
        if dish is None or not S.f_ghz:
            st.info("Seleziona la frequenza (barra laterale) e la parabola.")
        else:
            st.write(f"f/D {'equivalente vista dal feed' if dish.kind == 'offset' else ''}: **{dish.fD:.3f}**")
            st.write(f"Angolo di apertura (centro→bordo ×2): **{dish.opening_deg:.1f}°**")
            lam = wavelength_mm(S.f_ghz)
            st.write(f"Diametro: **{dish.D_mm / lam:.0f} λ** — HPBW ≈ **{reflector.hpbw_deg(dish.D_mm, lam, 10):.2f}°** "
                     f"(taper al bordo 10 dB; {reflector.hpbw_deg(dish.D_mm, lam, 0):.2f}° con illuminazione uniforme)")
            st.caption("L'HPBW reale dipende dall'illuminazione del feed: dopo la scelta del feed è calcolato dal suo lobo "
                       "nella scheda Simulazione & S11.")
            st.write(f"Guadagno a 60%: **{reflector.gain_dbi(dish.D_mm, lam, 0.6):.1f} dBi**")
            rms = st.number_input("Precisione superficie RMS (mm)", 0.0, 5.0, 0.2, 0.01)
            st.write(f"Perdita Ruze: **{reflector.ruze_loss_db(rms, lam):.2f} dB**")
            if dish.note:
                st.info(dish.note)
    _prio_k = "gt" if "G/T" in prio else "rx" if "RX" in prio else "gain"
    if dish is not None:
        from feedlab import illumination as _illum
        _ill = _illum.setting(dish.fD, _prio_k, ill_taper if ill_mode == "taper" else None)
        # the feed follows the illumination at once: every tab builds it for this f/D
        if abs(float(S.get("fd_design") or 0) - _ill["fD_design"]) > 1e-6:
            S["fd_design"] = _ill["fD_design"]
            for _k in ("pdf", "step", "stl", "plate_pdf", "plate_step"):
                S.pop(_k, None)
        S["ill_info"] = (_ill["fD_design"], _ill["edge_db"], dish.fD, ill_mode)
        with st.expander(_T("☀️ Illuminazione della parabola: taper al bordo {t:.1f} dB, efficienza {e:.0f}%",
                            t=_ill["edge_db"], e=100 * _ill["total"]), expanded=True):
            g1, g2 = st.columns(2)
            _rho, _lev = _illum.profile_db(dish.fD, _ill["q"])
            fi = go.Figure()
            fi.add_trace(go.Scatter(x=np.concatenate([-_rho[::-1], _rho]), y=np.concatenate([_lev[::-1], _lev]),
                                    mode="lines", line=dict(color="#d4a017", width=3), fill="tozeroy",
                                    fillcolor="rgba(212,160,23,0.25)", name=i18n.tr("illuminazione")))
            for lv, col in ((-3, "green"), (-10, "red")):
                fi.add_hline(y=lv, line_dash="dot", line_color=col, annotation_text=f"{lv} dB")
            fi.update_layout(height=330, margin=dict(l=10, r=10, t=40, b=10), showlegend=False,
                             title=i18n.tr("Illuminazione lungo il diametro della parabola"),
                             xaxis_title=i18n.tr("posizione sul diametro (bordo = ±1)"), yaxis_title="dB",
                             yaxis_range=[min(-30.0, float(_lev.min()) - 2), 1])
            g1.plotly_chart(fi, width="stretch")
            g1.caption(_T("Spillover {s:.0f}% · illuminazione (taper) {t:.0f}% · totale {e:.0f}% (modello cos^q, senza "
                          "blocking e perdite). Superficie entro −3 dB: {a3:.0f}% · entro −10 dB: {a10:.0f}%. "
                          "Feed progettato per f/D {fd:.2f} (parabola {f0:.2f}).",
                          s=100 * _ill["spillover"], t=100 * _ill["taper"], e=100 * _ill["total"],
                          a3=100 * _ill["area3"], a10=100 * _ill["area10"], fd=_ill["fD_design"], f0=dish.fD))
            # 3D disc of the dish, shaded by the illumination
            _R = dish.D_mm / 2
            _f = dish.fD * dish.D_mm
            rr = np.linspace(0, 1, 40)
            pp = np.linspace(0, 2 * np.pi, 73)
            RR, PP = np.meshgrid(rr, pp)
            X, Y = _R * RR * np.cos(PP), _R * RR * np.sin(PP)
            Z = (X ** 2 + Y ** 2) / (4 * _f)
            C = np.interp(RR, _rho, _lev)
            fd3 = go.Figure(go.Surface(x=X / 1000, y=Y / 1000, z=Z / 1000, surfacecolor=C, cmin=-20, cmax=0,
                                       colorscale=[[0, "#14143c"], [0.35, "#3b4cc0"], [0.6, "#d4a017"], [1, "#fff6b0"]],
                                       colorbar=dict(title="dB", len=0.7), showscale=True,
                                       lighting=dict(ambient=0.75, diffuse=0.5), hoverinfo="skip"))
            _psi = np.radians(_ill["half_angle"])
            for lv, col, nm in ((-3, "#00a000", "−3 dB"), (-10, "#d00000", "−10 dB")):       # rings on the dish
                below = np.where(_lev <= lv)[0]
                if below.size:
                    r_lv = _rho[below[0]] * _R
                    ph = np.linspace(0, 2 * np.pi, 121)
                    fd3.add_trace(go.Scatter3d(x=r_lv * np.cos(ph) / 1000, y=r_lv * np.sin(ph) / 1000,
                                               z=np.full_like(ph, r_lv ** 2 / (4 * _f) / 1000 + 0.002),
                                               mode="lines", line=dict(color=col, width=6), name=nm))
            # feed at the focus and the illumination cone to the rim
            zr = _R ** 2 / (4 * _f)
            for a_ in np.linspace(0, 2 * np.pi, 9)[:-1]:
                fd3.add_trace(go.Scatter3d(x=[0, _R * np.cos(a_) / 1000], y=[0, _R * np.sin(a_) / 1000],
                                           z=[_f / 1000, zr / 1000], mode="lines", showlegend=False,
                                           line=dict(color="rgba(212,160,23,0.55)", width=2)))
            fd3.add_trace(go.Scatter3d(x=[0], y=[0], z=[_f / 1000], mode="markers+text", text=["feed"],
                                       textposition="top center", marker=dict(size=6, color="black"), showlegend=False))
            fd3.update_layout(height=430, margin=dict(l=0, r=0, t=40, b=0), legend=dict(x=0, y=1),
                              title=i18n.tr("Parabola illuminata (chiaro = più segnale)"),
                              scene=dict(aspectmode="data", xaxis_title="m", yaxis_title="m", zaxis_title="m",
                                         camera=dict(eye=dict(x=1.35, y=-1.35, z=0.75))))
            g2.plotly_chart(fd3, width="stretch")
            if dish.kind == "offset":
                g2.caption(i18n.tr("Parabola offset: mostrata come apertura circolare equivalente (f/D visto dal feed)."))
    if st.button("🔎 Trova il feed migliore", type="primary", disabled=dish is None or not S.f_ghz):
        S.dish = dish
        with st.spinner("Valuto i candidati…"):
            S.cands = wizard.recommend(dish, S.f_ghz, "circular" if pol == "Circolare" else "linear",
                                       _prio_k, "sheet" if "lamiera" in tools else "lathe", quick,
                                       fd_factor=_ill["factor"])
    if S.cands:
        rows = []
        for i, c in enumerate(S.cands):
            rows.append({"#": i + 1, "Feed": c.label, "η stimata %": round(100 * c.eta_est, 1) if c.eta_est else "—",
                         "f/D ottimo del feed": round(c.best_fD, 2) if c.best_fD else "—",
                         "Ingombro Ø mm": round(c.blockage_diam_mm, 1) if c.blockage_diam_mm else "— (offset)",
                         "Perché": "; ".join(c.reasons), "Attenzione": "; ".join(c.warnings)})
        st.dataframe(rows, width="stretch", hide_index=True)
        st.caption("η = illuminazione × spillover × fase × cross-pol × blocking, calcolata (modello d'apertura o "
                   "design guide). Su parabole reali aspettarsi 12–15 punti in meno (W1GHZ, WD5AGO).")
        pick = st.selectbox("Feed da progettare", [c.label for c in S.cands])
        if st.button("➡️ Usa questo feed"):
            S.feed_kind = next(c.kind for c in S.cands if c.label == pick)
            S.overrides = {}
            st.success("Feed selezionato: apri la scheda 'Progetto feed'.")

# ---------------------------------------------------------------- 2 design
with tabs[1], contextlib.suppress(_Skip):
    st.header("Progetto del feed")
    kinds = sorted(geometry.FEED_TYPES, key=lambda k: i18n.tr(geometry.FEED_TYPES[k]).lower())   # alphabetical
    _kind = st.selectbox("Tipo di feed", kinds, index=kinds.index(S.feed_kind) if S.feed_kind in kinds else None,
                         placeholder="Seleziona tipo di feed", format_func=lambda k: geometry.FEED_TYPES[k])
    if _kind is not None and _kind != S.feed_kind:   # rerun so the sidebar summary shows the new feed at once
        S.feed_kind = _kind
        st.rerun()
    _need()
    if S.feed_kind in ("rect_horn", *geometry.CORRUGATED_KINDS):
        st.caption("Opzioni di lavorazione CNC dell'esterno (profilo semplificato, raccordi) non disponibili per questo feed.")
    else:
        with st.expander("🛠️ Lavorazione CNC dell'esterno (facoltativa, l'interno non cambia)", expanded=False):
            st.radio("Profilo esterno", ["wall", "cone1", "hull"], key="outer_mode", horizontal=True,
                     format_func=lambda m: {"wall": "Parete costante", "cone1": "Proposta 1: pieno fino alla fine del 1° cono",
                                            "hull": "Proposta 2: esterno senza rientranze"}[m],
                     help="proposte 1 e 2: esterno più semplice ed economico da fare al tornio/CNC, senza lo scalino "
                          "vicino alla base; si aggiunge solo materiale all'esterno")
            st.number_input("Raggio dei raccordi esterni (mm)", min_value=0.0, max_value=10.0, step=0.25,
                            key="outer_fillet",
                            help="0 = spigoli vivi. Con R > 0 gli spigoli esterni (bordo dell'apertura, scalini, attacco "
                                 "alla base) diventano raccordi: niente spigoli taglienti, lavorazione con utensile a "
                                 "raggio. L'interno resta a spigolo vivo, quindi le prestazioni RF non cambiano. Dove "
                                 "la parete resterebbe troppo sottile il raggio si riduce da solo.")
            st.caption("Le scelte si applicano al disegno PDF, al modello 3D e ai file STEP/STL.")
    geometry.OUTER_PROFILE.update(mode=S.get("outer_mode", "wall"), fillet=float(S.get("outer_fillet") or 0.0))
    geo = current_geometry()
    if not isinstance(geo, geometry.RectHornGeometry):
        st.caption(i18n.tr("I fori della base del feed e della piastrina si scelgono nella scheda 🔩 Montaggio feed + piastrina."))
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Quote (modificabili)")
        # like every other dimension, wall and base thickness change the feed only when "Applica modifiche" is pressed
        if "wall_in" not in S:
            S["wall_in"] = float(geo.params.get("wall", 1.0))
        if "base_t_in" not in S:
            S["base_t_in"] = S.get("base_t")
        st.number_input("Spessore parete (mm)", 0.2, 10.0, step=0.05, key="wall_in")
        if not isinstance(geo, geometry.RectHornGeometry):
            st.number_input("Spessore base del feed (mm)", min_value=1.0, max_value=30.0, step=0.5,
                            key="base_t_in", placeholder=i18n.tr("automatico") + f" ({geo.params.get('flange_thickness', 0):.2f})",
                            help="vuoto = automatico (quanto serve ai fori filettati della flangia); minimo 1 mm. "
                                 "Più sottile: i fori filettati diventano passanti e il filetto utile è lo spessore")
        editable = {k: v for k, v in geo.params.items() if isinstance(v, (int, float)) and k not in ("wall", "rings", "flange_diam", "flange_thickness", "outer_fillet_R")}
        newv = {}
        map_keys = {"A_input": "A", "B_aperture": "B", "flare_half_deg": "alpha", "C_phasing": "C",
                    "Di_input": "Di", "Ds_step": "Ds", "D_aperture": "Dap" if S.feed_kind in ("skobelev", "pickett_potter", "iz0jny") else "D",
                    "d_input": "d_in", "diam": "diam", "length": "length", "input_length": "input_length",
                    "flare_length": "flare_length", "horn_diam": "horn_diam", "ring_width": "ring_width",
                    "ring_depth": "ring_depth", "ring_setback": "ring_setback", "ring_wall": "ring_wall",
                    "aperture_H": "aperture_H", "aperture_E": "aperture_E", "axial_length": "axial_length",
                    "Ls": "Ls", "Dm": "Dm", "L1": "L1", "Lp": "Lp", "L2": "L2",
                    "cone1_half_deg": "a1", "cone2_half_deg": "a2"}
        if S.feed_kind in geometry.CORRUGATED_KINDS:           # OE2IGL design-guide dimensions, edited one by one
            map_keys = {k: k for k in ("pitch", "w", "axi", "delta", "Di", "Ds", "L_guide", *[f"d{i}" for i in range(1, 9)])}
        for k, v in editable.items():
            if k not in map_keys:
                continue
            if S.feed_kind in geometry.W2IMU_KINDS and k == "flare_length":
                st.text(f"{i18n.tr('lunghezza del cono')} · flare_length ({i18n.tr('calcolata')}) {v:.3f}")
                continue
            if S.feed_kind == "conical" and k == "flare_length":
                continue
            # same colours as the dimensions on the section: blue lengths, green diameters, red angles
            _nm = f"{i18n.tr(PARAM_NAMES[k])} · {k}" if k in PARAM_NAMES else k
            if k.endswith("_deg"):
                lab = f":red[{_nm} (°)]"
            elif k.startswith(("D", "d_", "A_", "B_")) or "diam" in k:
                lab = f":green[{_nm} (mm)]"
            else:
                lab = f":blue[{_nm} (mm)]"
            _guide = k in ("input_length", "L_guide") or (k == "length" and S.feed_kind in ("open_circular", *geometry.CHOKE_KINDS))
            nv = st.number_input(lab, value=float(round(v, 4)), format="%.4f", key=f"in_{S.feed_kind}_{k}",
                                 help="angolo del cono: cambiandolo FeedLab ricalcola la lunghezza del cono "
                                      "(i diametri restano)" if k.endswith("_deg") else
                                 ("lunghezza della guida circolare d'ingresso: allungala se vuoi un feed più lungo; "
                                  "nella guida circolare viaggia solo il TE11, le prestazioni non cambiano"
                                  if _guide else None))
            if abs(nv - round(v, 4)) > 5e-5:          # edited by the user (the field shows 4 decimals)
                newv[map_keys[k]] = nv
        def _fresh_inputs():                      # the fields show the rebuilt geometry at the next run
            for _k in [k_ for k_ in list(S.keys()) if str(k_).startswith(f"in_{S.feed_kind}_")]:
                del S[_k]
        cc1, cc2 = st.columns(2)
        if cc1.button("Applica modifiche"):
            S.wall = float(S["wall_in"])
            S["base_t"] = S.get("base_t_in")
            ov = S.overrides.setdefault(S.feed_kind, {})
            # flare: angle and length are the same quantity seen two ways -> the one just edited wins
            if "alpha" in newv and "flare_length" in newv:
                newv.pop("flare_length")
            if "alpha" in newv:
                ov.pop("flare_length", None)
            if "flare_length" in newv:
                ov.pop("alpha", None)
            for ang, ln in (("a1", "L1"), ("a2", "L2")):     # IZ0JNY cones: the value just edited wins
                if ang in newv and ln in newv:
                    newv.pop(ln)
                if ang in newv:
                    ov.pop(ln, None)
                if ln in newv:
                    ov.pop(ang, None)
            ov.update(newv)
            for k_ in ("pdf", "step", "stl"):
                S.pop(k_, None)
            _fresh_inputs()
            st.rerun()
        if cc2.button("Ripristina progetto"):
            S.overrides[S.feed_kind] = {}
            S.wall, S["base_t"] = None, None
            for _k in ("wall_in", "base_t_in"):
                S.pop(_k, None)
            _fresh_inputs()
            st.rerun()
    with c2:
        fig = section_fig(geo)
        if fig:
            st.plotly_chart(fig, width="stretch")
        _ii = S.get("ill_info")
        if _ii:
            st.caption(_T("Progettato per f/D {fd:.3f}: taper al bordo {t:.1f} dB sulla parabola (f/D {f0:.3f}) — "
                          "si cambia con l'illuminazione nella Procedura guidata.", fd=_ii[0], t=_ii[1], f0=_ii[2]))
        if S.overrides.get(S.feed_kind):
            _openems_hint(_big_changes(S.overrides[S.feed_kind], _start_values(S.feed_kind)))
        lam = geo.lam
        st.write(f"Lunghezza totale **{geo.length:.2f} mm** ({geo.length / lam:.2f} λ) · "
                 f"Ø ingombro **{geo.blockage_diameter():.2f} mm** ({geo.blockage_diameter() / lam:.2f} λ) · "
                 f"tolleranza consigliata **±{drawing.tolerance_mm(S.f_ghz)} mm**")
        for n in getattr(geo, "notes", []) or []:
            st.caption("• " + n)
        if getattr(geo, "design", None) is not None:
            with st.expander("Dati della regola di progetto"):
                st.text(str(geo.design))

# ---------------------------------------------------------------- 3 simulation
with tabs[3], contextlib.suppress(_Skip):
    _need()
    st.header("Simulazione rapida: S11, contenuto modale, lobo, efficienza")
    geo = current_geometry()
    is_rect = isinstance(geo, geometry.RectHornGeometry)
    if not is_rect and geo.kind not in geometry.MODEMATCH_OK:
        st.warning("Per i feed con anelli/choke la simulazione rapida non è disponibile (regioni coassiali): "
                   "usa la scheda **Full-wave openEMS**. Sotto: efficienza attesa dalle simulazioni W1GHZ/WD5AGO.")
        st.text(str(geo.design))
    else:
        c1, c2, c3 = st.columns(3)
        bw = c1.slider("Banda di analisi ± %", 1, 20, 6)
        npts = c2.slider("Punti in frequenza", 5, 41, 15)
        nm = c3.select_slider("Modi (precisione)", [8, 12, 16, 24], 16)
        if not is_rect:
            secs = tuple(geo.staircase())
            fl = tuple(np.linspace(S.f_ghz * (1 - bw / 100), S.f_ghz * (1 + bw / 100), npts))
            with st.spinner("Mode matching…"):
                t0 = time.time()
                mm = run_modematch(secs, fl, nm)
            fig = go.Figure(go.Scatter(x=mm.f_ghz, y=mm.s11_db, mode="lines+markers", name="S11"))
            fig.add_vline(x=S.f_ghz, line_dash="dot")
            fig.update_layout(title="S11 ingresso TE11 (stima mode-matching)", xaxis_title="GHz", yaxis_title="dB",
                              height=330, yaxis_range=[min(-40, float(mm.s11_db.min()) - 3), 0])
            st.plotly_chart(fig, width="stretch")
            i0 = int(np.argmin(np.abs(mm.f_ghz - S.f_ghz)))
            st.caption(f"S11 @ {S.f_ghz:g} GHz: **{mm.s11_db[i0]:.1f} dB** (RL {-mm.s11_db[i0]:.1f} dB) · "
                       f"bilancio di potenza {mm.power_balance[i0]:.4f} · {time.time() - t0:.1f} s. "
                       "Apertura modellata come flangia (stima ottimistica per aperture < 1λ); "
                       "transizione dalla guida WR esclusa. Per S11 di riferimento usa openEMS.")
            modes = mm.aperture_modes[i0]
            if "TE11" in modes:
                te = modes["TE11"]
                st.write("Contenuto modale all'apertura (rispetto a TE11): " + ", ".join(
                    f"{k}: {abs(v / te):.3f} ∠{math.degrees(np.angle(v / te)):.0f}°" for k, v in modes.items()))
                q_ = explore.tm11_power_ratio(modes)
                if geo.kind in explore.STEP_HORNS and q_ is not None:
                    st.caption(_T("TM11/TE11 in potenza: {q}% — Jeff WA6KBL indica circa il 15% per un Pickett-Potter ({stato}).",
                                  q=f"{100 * q_:.1f}",
                                  stato=i18n.tr("nella norma" if explore.TM11_TARGET[0] <= q_ <= explore.TM11_TARGET[1]
                                                else "da correggere")))
        pat, _ = quick_pattern(geo.kind, tuple(geo.staircase()) if not is_rect else (), S.f_ghz,
                               (geo.params["a"], geo.params["b"], geo.params["aperture_H"], geo.params["aperture_E"],
                                geo.params["axial_length"]) if is_rect else None)
        if S.fullwave is not None and st.checkbox("Usa il pattern full-wave openEMS caricato", True):
            pat = S.fullwave["pattern"]
        S["last_pattern"] = pat
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(polar_fig(pat, f"Lobo del feed @ {S.f_ghz:g} GHz",
                                      dish_fD=(S.dish or wizard.dish_from_prime(600, 0.6)).fD), width="stretch")
        with c2:
            e, h = pat.db()
            fig = go.Figure([go.Scatter(x=pat.theta_deg, y=e, name="E"), go.Scatter(x=pat.theta_deg, y=h, name="H")])
            ph_e = np.degrees(np.unwrap(np.angle(pat.E)) - np.angle(pat.E[0]))
            fig.add_trace(go.Scatter(x=pat.theta_deg, y=ph_e, name="fase E (°)", yaxis="y2", line=dict(dash="dot")))
            fig.update_layout(height=460, xaxis_title="θ (°)", yaxis_title="dB", yaxis_range=[-40, 1], xaxis_range=[0, 180],
                              yaxis2=dict(overlaying="y", side="right", title="fase °"), title="Pattern cartesiano")
            st.plotly_chart(fig, width="stretch")
        dish = S.dish or wizard.dish_from_prime(600, 0.6)
        blk = geo.blockage_diameter() / dish.D_mm if dish.kind == "prime" else 0.0
        fds = np.arange(0.25, 1.6, 0.01)
        effs = efficiency.efficiency_vs_fD(pat, fds, blk)
        fig = go.Figure()
        for key, name in (("total", "Totale"), ("spillover", "Spillover"), ("illumination", "Illuminazione"),
                          ("phase", "Fase"), ("polarization", "Cross-pol")):
            fig.add_trace(go.Scatter(x=fds, y=[100 * getattr(x, key) for x in effs], name=name,
                                     line=dict(width=3 if key == "total" else 1.5)))
        fig.add_vline(x=dish.fD, line_dash="dot", annotation_text="tua parabola")
        fig.update_layout(height=400, title="Efficienza della parabola vs f/D (prime focus o equivalente offset)",
                          xaxis_title="f/D", yaxis_title="%", yaxis_range=[0, 101], xaxis=dict(dtick=0.1))
        st.plotly_chart(fig, width="stretch")
        here = efficiency.dish_efficiency(pat, dish.fD, blk)
        best = max(effs, key=lambda x: x.total)
        pc, _ = efficiency.phase_center_by_efficiency(pat, dish.fD, span_lambda=1.5, step=0.01, block_diam_ratio=blk)
        lam = wavelength_mm(S.f_ghz)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("η sulla tua parabola", f"{100 * here.total:.1f} %")
        m2.metric("Taper al bordo", f"{here.edge_taper_db:.1f} dB")
        m3.metric("f/D ottimo del feed", f"{best.fD:.2f}", f"{100 * best.total:.1f} %")
        m4.metric("Centro di fase", f"{pc * lam:+.2f} mm", "davanti all'apertura" if pc > 0 else "dentro la tromba")
        beam = efficiency.dish_beam(pat.shifted(pc), dish.fD, dish.D_mm, lam, blk)
        b1, b2, b3 = st.columns(3)
        b1.metric("HPBW della parabola", f"{beam.hpbw_deg:.3f}°",
                  help="dal lobo reale del feed (integrazione sull'apertura, feed nel centro di fase)")
        b2.metric("HPBW piano E / H", f"{beam.hpbw_E_deg:.3f}° / {beam.hpbw_H_deg:.3f}°")
        b3.metric("Primo lobo laterale", f"{beam.first_sidelobe_db:.1f} dB",
                  f"taper al bordo {beam.edge_taper_db:.1f} dB", delta_color="off")
        G = reflector.gain_dbi(dish.D_mm, lam, max(here.total, 1e-3))
        st.write(f"Guadagno teorico con questo feed: **{G:.1f} dBi** (reale ≈ {reflector.gain_dbi(dish.D_mm, lam, max(here.total - 0.13, 0.01)):.1f} dBi, −13 punti)")
        with st.expander("G/T (prime focus, modello W1GHZ 2014)"):
            el = st.slider("Elevazione (°)", 5, 90, 30)
            nf = st.number_input("NF ricevitore (dB)", 0.2, 15.0, 1.0)
            azen = st.number_input("Attenuazione zenitale atmosfera (dB)", 0.0, 5.0, 0.3 if S.f_ghz < 60 else 1.0)
            tsky = noise.sky_temp(el, azen, f_ghz=S.f_ghz)
            ta = noise.antenna_temp_prime_focus(pat, dish.fD, el, tsky)
            st.write(f"T_cielo {tsky:.1f} K · T_antenna {ta:.1f} K · T_rx {noise.receiver_temp(nf):.0f} K → "
                     f"**G/T = {noise.g_over_t_db(G, ta, noise.receiver_temp(nf)):.1f} dB/K**")
            st.caption(_T("Tsys = T antenna {a:.1f} K + preamplificatore {r:.1f} K (NF {nf:.2f} dB) = {s:.1f} K. Con 1 dB di "
                          "NF in più: {s2:.1f} K → G/T {d:+.2f} dB.", a=ta, r=noise.receiver_temp(nf), nf=nf,
                          s=ta + noise.receiver_temp(nf), s2=ta + noise.receiver_temp(nf + 1),
                          d=-10 * math.log10((ta + noise.receiver_temp(nf + 1)) / (ta + noise.receiver_temp(nf)))))

# ---------------------------------------------------------------- 4 lobe 3D
with tabs[4], contextlib.suppress(_Skip):
    _need()
    st.header("Lobo di irradiazione 3D")
    pat = S.get("last_pattern")
    if pat is None:
        st.info("Esegui prima la simulazione nella scheda 'Simulazione & S11'.")
    else:
        floor = st.slider("Dinamica (dB)", -60, -15, -35)
        st.plotly_chart(lobe3d_fig(pat, floor), width="stretch")

# ---------------------------------------------------------------- 5 model 3D
with tabs[5], contextlib.suppress(_Skip):
    _need()
    st.header("Modello 3D del feed")
    geo = current_geometry()
    cut = st.checkbox("Sezione a quarto (vedi l'interno)", True)
    st.plotly_chart(model3d_fig(geo, cut), width="stretch")

# ---------------------------------------------------------------- 6 export
def _sim_export_section(geo, fname):
    """Scripts for other full-wave programs: openEMS (Python) and CST Studio Suite (VBA macro)."""
    st.subheader("🧪 Script per simulatori full-wave (openEMS, CST)")
    if not _sim_export.supported(geo):
        st.info("Gli script per i simulatori coprono i feed a simmetria di rotazione (non la tromba rettangolare).")
        return
    st.caption("Per chi ha openEMS o CST Studio Suite: il feed progettato, con porta guida d'onda TE11, contorni "
               "aperti e monitor del campo lontano, pronto da simulare. Ogni ZIP contiene le istruzioni (LEGGIMI).")
    c = st.columns(3)
    bw = c[0].slider("Banda ± %", 2, 25, 10, key="simx_bw")
    cells = c[1].select_slider("Celle per λ", [12, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120], 100, key="simx_cells",
                               help="nel feed: 100 consigliato (quote entro ~λ/200); 20–40 solo come bozza")
    nff = c[2].select_slider("Frequenze del lobo", [1, 3, 5, 7], 3, key="simx_nff")
    _est = openems_sim.mesh_estimate(geo, openems_sim.DeepConfig(f_lo=S.f_ghz * (1 - bw / 100), f_hi=S.f_ghz * (1 + bw / 100),
                                                              cells_per_lambda=int(cells)))
    st.caption(_T("Stima openEMS: {m:.1f} M celle, RAM ≈ {r:.1f} GB, durata ≈ {t} su un PC desktop tipico "
                  "(feed a {c} celle/λ, aria graduata a 20 celle/λ).", m=_est["cells"] / 1e6, r=_est["ram_mb"] / 1024,
                  t=app_openems._fmt_time(_est["time_min"] * 60), c=int(cells)))
    c = st.columns(2)
    c[0].download_button("⬇️ Script openEMS (.zip)", _sim_export.openems_zip(geo, bw, cells, nff),
                         file_name=f"{fname}_openems.zip", mime="application/zip", key="simx_oems",
                         help="script Python autonomo (non serve FeedLab): python -u sim_<feed>.py, poi carica "
                              "results.json nella scheda 🖥️ Full-wave openEMS")
    c[1].download_button("⬇️ Macro CST (.zip)", _sim_export.cst_zip(geo, bw, cells, nff, name=fname),
                         file_name=f"{fname}_cst.zip", mime="application/zip", key="simx_cst",
                         help="macro VBA: in un progetto vuoto CST, Home > Macros > Run Macro. Costruisce il modello "
                              "nella History List; il solutore lo avvii tu")


with tabs[8], contextlib.suppress(_Skip):
    _need()
    st.header("Disegno meccanico (PDF) e file per la produzione")
    geo = current_geometry()
    mat = st.text_input("Materiale", f"{S.material}, interno lucidato Ra ≤ {materials.MATERIALS[S.material].rq_um} µm")
    name = st.text_input("Titolo", geometry.short_title(geometry.FEED_TYPES[geo.kind], S.f_ghz))
    _tol_rec = drawing.tolerance_mm(S.f_ghz)
    _tol = st.number_input(_T("Tolleranza generale di lavorazione ± (mm, consigliata {t:g} per {f:g} GHz)", t=_tol_rec, f=S.f_ghz),
                           min_value=0.005, max_value=1.0, value=float(_tol_rec), step=0.005, format="%.3f",
                           key=f"tol_general_{_tol_rec}",
                           help="scritta nel cartiglio del PDF del feed e della piastrina; i fori hanno le loro "
                                "tolleranze (filetti 6H, spine H7, passanti +0.1/0). Consigliata OE2IGL: ±0.1 mm sotto "
                                "30 GHz, ±0.05 sotto 55 GHz, ±0.02 sotto 80 GHz, ±0.01 oltre")
    if drawing.TOLERANCE.get("general") != _tol:
        drawing.TOLERANCE["general"] = _tol
        for _k in ("pdf", "plate_pdf"):
            S.pop(_k, None)
    base = WORK / f"{geo.kind}_{S.f_ghz:g}GHz".replace(".", "p")
    if getattr(geo, "mount", None) is not None:
        _m = geo.mount
        st.success(_T("Foratura della base attiva per la flangia {wg} {name}: {n} fori nel PDF (foglio della flangia), "
                      "nello STEP e nell'STL.", wg=_m.flange.wg, name=_m.flange.name, n=len(_m.feed_holes)))
    elif not isinstance(geo, geometry.RectHornGeometry):
        st.info(i18n.tr("Base del feed senza fori: scegli lo schema di montaggio nella scheda 🔩 Montaggio feed + "
                        "piastrina, poi rigenera STEP/STL."))
    fname = _filenames.pick(st, base.name, "feed")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📄 Genera PDF"):
        tt = S.get("tol_table")
        pth = drawing.drawing_pdf(geo, base.with_suffix(".pdf"), mat, name,
                                  tolerances=tt[1] if tt and tt[0] == geo.kind else None)
        S["pdf"] = pth.read_bytes()
    if S.get("pdf"):
        c1.download_button("Scarica disegno PDF", S["pdf"], file_name=fname + ".pdf", mime="application/pdf")
    if c2.button("🧊 Genera STEP"):
        with st.spinner("OpenCascade…"):
            S["step"] = cad.export_step(geo, base.with_suffix(".step")).read_bytes()
    if S.get("step"):
        c2.download_button("Scarica .stp", S["step"], file_name=fname + ".stp", mime="model/step")
    if c3.button("🖨️ Genera STL"):
        S["stl"] = cad.export_stl(geo, base.with_suffix(".stl")).read_bytes()
    if S.get("stl"):
        c3.download_button("Scarica .stl", S["stl"], file_name=fname + ".stl", mime="model/stl")
    rep = {"feed": geo.kind, "f_ghz": S.f_ghz, "params_mm": geo.params,
           "dish": None if S.dish is None else S.dish.__dict__}
    c4.download_button("🧾 Parametri JSON", json.dumps(rep, indent=2, default=float), file_name=fname + ".json", mime="application/json")
    _sim_export_section(geo, fname)
    if S.get("pdf"):
        import base64
        b64 = base64.b64encode(S["pdf"]).decode()
        st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="620"></iframe>',
                    unsafe_allow_html=True)

# ---------------------------------------------------------------- 7 openEMS (optional deep analysis)
with tabs[9], contextlib.suppress(_Skip):
    _need()
    app_openems.render(S, current_geometry(), polar_fig)


# ---------------------------------------------------------------- 3 laboratory
@st.cache_data(show_spinner=False, max_entries=500)
def lab_eval(kind, f, sc_tuple, over_tuple, wall, fd_design=None):
    sc = explore.Scenario(*sc_tuple)
    return explore.evaluate(kind, f, sc, dict(over_tuple), wall, fd_design)


def _apply_lab_overrides(kind, over, base_vals):
    """on_click of «Applica l'ottimo / il progetto robusto»: runs before the widgets are drawn, the only moment
    Streamlit lets us move the lab sliders (assigning their keys afterwards raises and the optimum was lost)."""
    over = {k: float(v) for k, v in over.items() if k in base_vals}
    S.overrides[kind] = dict(over)
    for k, _, _ in explore.TUNABLE.get(kind, []):
        S[f"lab_{kind}_{k}"] = float(over.get(k, base_vals[k]))
    for k in [k for k in list(S.keys()) if str(k).startswith(f"in_{kind}_")]:   # Progetto feed shows the new values
        del S[k]
    for k in ("pdf", "step", "stl"):
        S.pop(k, None)


with tabs[2], contextlib.suppress(_Skip):
    _need()
    st.header("Laboratorio: varia le quote e guarda cosa cambia")
    if "lab_ill_taper" not in S:
        S["lab_ill_taper"] = float(S.get("ill_taper", 10.0))
    _lt1, _lt2 = st.columns([2, 3])
    _lt1.slider("Taper al bordo (dB) — come nella Procedura guidata", 6.0, 25.0, step=0.5, key="lab_ill_taper",
                on_change=_sync_taper, args=("lab_ill_taper", "ill_taper"),
                help="lo stesso cursore della Procedura guidata: spostandolo il feed viene riprogettato per il nuovo "
                     "taper e tutte le simulazioni si aggiornano (l'illuminazione passa a 'Taper al bordo scelto da me')")
    _ii = S.get("ill_info")
    if _ii:
        _lt2.caption(_T("Illuminazione: {m} · taper al bordo {t:.1f} dB · feed progettato per f/D {fd:.3f} (parabola {f0:.3f})",
                        m=i18n.tr("taper scelto" if _ii[3] == "taper" else "automatica"), t=_ii[1], fd=_ii[0], f0=_ii[2]))
    kind = S.feed_kind
    if kind not in explore.TUNABLE:
        st.warning("Il laboratorio interattivo usa il simulatore rapido: disponibile per guida aperta, W2IMU, "
                   "Large W2IMU, Skobelev, Pickett-Potter, conico e tromba rettangolare. Per VE4MA/Chaparral usa openEMS.")
    else:
        dish = S.dish or wizard.dish_from_prime(600, 0.6)
        lam = wavelength_mm(S.f_ghz)
        with st.expander("Scenario d'uso (parabola, ricevitore, cielo)", expanded=True):
            c = st.columns(6)
            objective = c[0].selectbox("Obiettivo", list(explore.OBJECTIVES), format_func=lambda k: explore.OBJECTIVES[k],
                                       index=1)
            elev = c[1].slider("Elevazione °", 0, 90, 30 if objective != "tx" else 5)
            nf = c[2].number_input("NF LNA (dB)", 0.1, 20.0, 1.0 if S.f_ghz < 30 else 3.0 if S.f_ghz < 80 else 8.0, 0.1)
            line = c[3].number_input("Perdita linea feed→LNA/PA (dB)", 0.0, 10.0, 0.1, 0.05)
            rms = c[4].number_input("RMS superficie (mm)", 0.0, 3.0, 0.1, 0.01)
            azen = c[5].number_input("Att. zenitale (dB)", 0.0, 10.0, 0.1 if S.f_ghz < 20 else 0.3 if S.f_ghz < 60 else 1.0, 0.05)
        sc = explore.Scenario(dish.kind, dish.D_mm, dish.fD, max(elev, 1), noise.receiver_temp(nf), azen, 290.0, rms, line,
                              material=S.material)
        S["lab_scenario"] = {"elev_deg": float(max(elev, 1)), "nf_db": float(nf), "line_loss_db": float(line),
                             "rms_mm": float(rms), "zenith_db": float(azen)}
        sc_t = tuple(sc.__dict__.values())
        _fdd = _fd_design()
        base_vals = explore.base_values(kind, S.f_ghz, _fdd, S.wall)
        cur_over = dict(S.overrides.get(kind, {}))
        start = {**base_vals, **cur_over}
        st.subheader("Quote del feed")
        cols = st.columns(len(explore.TUNABLE[kind]))
        lab_over = {}
        for col, (key, label, span) in zip(cols, explore.TUNABLE[kind]):
            x0 = base_vals[key]
            unit = "°" if key in ("alpha", "a1", "a2") else "mm"
            v = col.slider(f"{label} ({unit})", float(x0 * (1 - span)), float(x0 * (1 + span)),
                           float(np.clip(start[key], x0 * (1 - span), x0 * (1 + span))), float(x0 * span / 50),
                           format="%.3f", key=f"lab_{kind}_{key}",
                           help=f"progetto: {x0:.3f} {unit} = {x0 / lam:.3f} λ" if unit == "mm" else f"progetto: {x0:.2f}°")
            col.caption(f"{v / lam:.3f} λ · {100 * (v / x0 - 1):+.1f}%" if unit == "mm" else f"{100 * (v / x0 - 1):+.1f}%")
            if abs(v - x0) > 1e-9:
                lab_over[key] = v
        if kind == "iz0jny":
            g_lab = geometry.build(kind, S.f_ghz, fD=_fdd, wall=S.wall, **lab_over)
            p_lab = g_lab.params
            st.caption(_T("Coni: semiangolo 1 {a1:.2f}° → L1 {l1:.3f} mm · semiangolo 2 {a2:.2f}° → L2 {l2:.3f} mm "
                          "· lunghezza totale {L:.2f} mm (se cambi l'angolo, la lunghezza del cono segue; "
                          "l'angolo prevale sulla lunghezza)", a1=p_lab["cone1_half_deg"], l1=p_lab["L1"],
                          a2=p_lab["cone2_half_deg"], l2=p_lab["L2"], L=g_lab.z_aperture))
        elif any(k == "alpha" for k, _, _ in explore.TUNABLE[kind]):
            g_lab = geometry.build(kind, S.f_ghz, fD=_fdd, wall=S.wall, **lab_over)
            p_lab = g_lab.params
            st.caption(f"Flare: semiangolo {p_lab['flare_half_deg']:.2f}° → lunghezza flare {p_lab['flare_length']:.3f} mm "
                       f"({p_lab['flare_length'] / lam:.3f} λ), lunghezza totale {g_lab.z_aperture:.2f} mm")
        with st.spinner("Calcolo…"):
            base = lab_eval(kind, S.f_ghz, sc_t, tuple(sorted({}.items())), S.wall, _fdd)
            cur = lab_eval(kind, S.f_ghz, sc_t, tuple(sorted(lab_over.items())), S.wall, _fdd)
        st.subheader("Risultato rispetto al progetto di partenza")
        m = st.columns(7)
        def met(col, lab, v, b, fmt, unit, better_up=True):
            d = v - b
            col.metric(lab, f"{fmt.format(v)} {unit}", None if abs(d) < 1e-9 else f"{d:+.2f}",
                       delta_color="normal" if better_up else "inverse")
        snr = cur.snr_delta(base, objective)
        st.caption(f"Perdita ohmica del feed ({S.material}): {cur.ohmic_db:.3f} dB → +{materials.noise_from_loss(cur.ohmic_db):.1f} K di rumore")
        if cur.tsys:
            _ts = cur.tsys
            st.caption(_T("**Tsys {s:.1f} K** = antenna {a0:.1f} K attenuata dalle perdite ({l:.2f} dB) → {a:.1f} K + rumore "
                          "delle perdite (feed + linea) {ln:.1f} K + preamplificatore {r:.1f} K (NF {nf:.2f} dB). "
                          "G/T = G − 10·log10(Tsys).", s=_ts["sys"], a0=_ts["t_ant"], l=_ts["loss_db"], a=_ts["ant"],
                          ln=_ts["line"], r=_ts["rx"], nf=nf))
        m[0].metric("Δ S/N", f"{snr:+.2f} dB", help="TX: ΔG · RX: Δ(G/T) · EME: ΔG+Δ(G/T)")
        met(m[1], "Efficienza", 100 * cur.eta, 100 * base.eta, "{:.1f}", "%")
        met(m[2], "Guadagno", cur.gain_dbi, base.gain_dbi, "{:.2f}", "dBi")
        met(m[3], "G/T", cur.g_over_t, base.g_over_t, "{:.2f}", "dB/K")
        met(m[4], "T antenna", cur.t_ant, base.t_ant, "{:.1f}", "K", better_up=False)
        if cur.s11_db is not None:
            met(m[5], "S11", cur.s11_db, base.s11_db, "{:.1f}", "dB", better_up=False)
        met(m[6], "Taper bordo", cur.edge_taper_db, base.edge_taper_db, "{:.1f}", "dB")
        st.caption(f"Spillover {100 * cur.spill:.1f}% · illuminazione {100 * cur.illum:.1f}% · fase {100 * cur.phase:.1f}% · "
                   f"pol {100 * cur.pol:.1f}% · blocking {100 * cur.block:.1f}% · centro di fase {cur.pc_mm:+.2f} mm "
                   f"({'davanti' if cur.pc_mm > 0 else 'dentro'} all'apertura). Valori calcolati: sulla parabola reale "
                   "aspettarsi 12–15 punti di efficienza in meno, ma le DIFFERENZE tra varianti sono significative.")
        c1, c2 = st.columns(2)
        with c1:
            fig = polar_fig(cur.pattern, "Lobo: variante (pieno) vs progetto (tratteggio)", dish_fD=dish.fD)
            eb, hb = base.pattern.db()
            for v, col in ((eb, "#d62728"), (hb, "#1f77b4")):
                th = np.concatenate([-base.pattern.theta_deg[::-1], base.pattern.theta_deg])
                fig.add_trace(go.Scatterpolar(theta=th, r=np.clip(np.concatenate([v[::-1], v]), -40, 0) + 40,
                                              mode="lines", line=dict(color=col, dash="dash", width=1), showlegend=False))
            st.plotly_chart(fig, width="stretch")
        with c2:
            fds = np.arange(0.3, 1.4, 0.02)
            blk = 0.0
            fig = go.Figure()
            for res, name, dash in ((base, "progetto", "dash"), (cur, "variante", "solid")):
                ef = efficiency.efficiency_vs_fD(res.pattern, fds, blk)
                fig.add_trace(go.Scatter(x=fds, y=[100 * e.total for e in ef], name=f"η {name}", line=dict(dash=dash, width=3)))
                fig.add_trace(go.Scatter(x=fds, y=[100 * e.spillover for e in ef], name=f"spillover {name}",
                                         line=dict(dash=dash, width=1)))
            fig.add_vline(x=dish.fD, line_dash="dot", annotation_text="tua parabola")
            fig.update_layout(height=460, title="Efficienza vs f/D", xaxis_title="f/D", yaxis_title="%", yaxis_range=[30, 101],
                              xaxis=dict(dtick=0.1))
            st.plotly_chart(fig, width="stretch")
        st.subheader("💡 Consigli")
        for t in explore.advice(cur, base, sc, objective, kind, S.f_ghz):
            st.markdown("- " + t)
        _openems_hint(_big_changes(lab_over, base_vals))
        b1, b2, b3 = st.columns(3)
        if b1.button("✅ Applica queste quote al progetto", type="primary"):
            S.overrides[kind] = {**lab_over}
            st.success("Quote applicate: disegno, STEP e openEMS useranno la variante.")
        st.divider()
        st.subheader("🔬 Sensibilità: cosa succede variando ogni quota")
        if st.button("Calcola sensibilità (≈ 7 punti per quota)"):
            with st.spinner("Scansione…"):
                S["sens"] = (objective, explore.sensitivity(kind, S.f_ghz, sc, lab_over, objective, 7, S.wall, _fdd))
        if S.get("sens") and S["sens"][0] == objective:
            sens = S["sens"][1]
            cols = st.columns(len(sens))
            for col, (key, d) in zip(cols, sens.items()):
                R = d["rows"]
                fig = go.Figure()
                ylab = {"tx": "G (dBi)", "rx": "G/T (dB/K)", "eme": "G + G/T"}[objective]
                fig.add_trace(go.Scatter(x=R[:, 0], y=R[:, 1] - np.nanmax(R[:, 1]), name=ylab, mode="lines+markers"))
                if not np.all(np.isnan(R[:, 5])):
                    fig.add_trace(go.Scatter(x=R[:, 0], y=R[:, 5], name="S11 dB", yaxis="y2", line=dict(dash="dot")))
                fig.add_vline(x=d["x0"], line_dash="dot")
                fig.update_layout(height=300, title=d["label"], xaxis_title="mm" if key != "alpha" else "°",
                                  yaxis_title="dB dal max", yaxis2=dict(overlaying="y", side="right", title="S11"),
                                  showlegend=False, margin=dict(t=40, b=30))
                col.plotly_chart(fig, width="stretch")
                ib = int(np.nanargmax(R[:, 1]))
                gain = R[ib, 1] - R[len(R) // 2, 1]
                col.caption(f"Migliore a {R[ib, 0]:.3f} ({100 * (R[ib, 0] / d['x0'] - 1):+.0f}%): {gain:+.2f} dB. "
                            f"Pendenza ≈ {np.nanmax(np.abs(np.diff(R[:, 1]) / np.diff(R[:, 0]))):.2f} dB/{'mm' if key != 'alpha' else '°'} "
                            f"→ tolleranza utile.")
        st.divider()
        st.subheader("🤖 Ottimizzazione automatica")
        keys = st.multiselect("Quote da ottimizzare", [k for k, _, _ in explore.TUNABLE[kind]],
                              default=[k for k, _, _ in explore.TUNABLE[kind]][:2],
                              format_func=lambda k: dict((a, b) for a, b, _ in explore.TUNABLE[kind])[k])
        c1, c2 = st.columns(2)
        nev = c1.slider("Valutazioni massime", 10, 120, 40)
        s11lim = c2.slider("S11 massimo accettato (dB)", -30, -10, -18)
        if st.button(f"Ottimizza per: {explore.OBJECTIVES[objective]}") and keys:
            bar = st.progress(0.0, "ottimizzazione…")
            over, res = explore.optimize(kind, S.f_ghz, sc, lab_over, objective, keys, nev, S.wall, _fdd,
                                         s11_limit_db=s11lim,
                                         progress=lambda i, n, v: bar.progress(min(i / n, 1.0), f"valutazione {i}/{n}"))
            S["opt"] = (over, res)
        if S.get("opt"):
            over, res = S["opt"]
            st.success(f"Ottimo trovato: Δ S/N {res.snr_delta(base, objective):+.2f} dB · η {100 * res.eta:.1f}% · "
                       f"G {res.gain_dbi:.2f} dBi · G/T {res.g_over_t:.2f} dB/K · S11 {res.s11_db if res.s11_db is None else round(res.s11_db, 1)} dB")
            st.write({k: f"{v:.3f} ({100 * (v / base_vals[k] - 1):+.1f}%)" for k, v in over.items()})
            st.button("Applica l'ottimo al progetto", on_click=_apply_lab_overrides, args=(kind, over, base_vals))

        # ------------------------------------------------ fabrication tolerances
        st.divider()
        st.subheader("🎯 Tolleranze di lavorazione e resa")
        if kind not in tolerance.TOL_KEYS:
            st.info("L'analisi di tolleranza usa il simulatore rapido a guida circolare: non disponibile per la tromba rettangolare.")
        else:
            st.caption("Ogni quota lavorata varia dentro la sua tolleranza: FeedLab stima come si distribuiscono efficienza, "
                       "guadagno, G/T e S11 dei pezzi prodotti (Monte Carlo), quali quote sono critiche e quale tolleranza "
                       "serve davvero a ciascuna. Si analizza il progetto con le quote attuali del laboratorio.")
            c = st.columns(4)
            tol_in = c[0].number_input("Tolleranza di lavorazione ± (mm)", 0.001, 0.5, float(drawing.tolerance_mm(S.f_ghz)),
                                       0.005, format="%.3f", key="tol_mm")
            dist = c[1].selectbox("Distribuzione delle quote", ["uniform", "normal"], key="tol_dist",
                                  format_func=lambda d: {"uniform": "Uniforme in ±t (prudente)",
                                                         "normal": "Normale, ±t = 3σ (CNC capace)"}[d])
            budget = c[2].number_input("Perdita ammessa (dB)", 0.01, 1.0, 0.1, 0.01, key="tol_budget",
                                       help="un pezzo è 'buono' se perde al massimo questo rispetto al nominale")
            s11t = c[3].slider("S11 massimo (dB)", -30, -10, -18, key="tol_s11")
            if st.button("🎲 Analizza tolleranze (≈ 20 simulazioni rapide)", key="tol_go"):
                bar = st.progress(0.0, "modello delle tolleranze…")
                rep = tolerance.analyse(kind, S.f_ghz, sc, lab_over, objective, tol_in, dist, 5000, 6, budget, s11t, S.wall, _fdd,
                                        progress=lambda i, n: bar.progress(min(i / n, 1.0), f"simulazione {i}/{n}"))
                bar.empty()
                S["tol"] = (kind, objective, rep)
            if S.get("tol") and S["tol"][0] == kind:
                rep = S["tol"][2]
                ylab = {"tx": "G", "rx": "G/T", "eme": "G + G/T"}[S["tol"][1]]
                so, se, ss = rep.stats["objective"], rep.stats["eta"], rep.stats["s11_db"]
                m = st.columns(4)
                m[0].metric("Resa", f"{100 * rep.yield_frac:.1f} %",
                            help=_T("pezzi con perdita ≤ {a} dB e S11 ≤ {b} dB", a=rep.spec['loss_budget_db'],
                                    b=rep.spec['s11_limit_db']))
                m[1].metric(_T("Perdita media di {y}", y=ylab), f"{rep.nominal['objective'] - so['mean']:.3f} dB",
                            help=_T("dispersione σ = {s} dB", s=f"{so['std']:.3f}"))
                m[2].metric("Efficienza (5–95%)", f"{100 * se['p05']:.1f}–{100 * se['p95']:.1f} %")
                if not math.isnan(ss["p95"]):
                    m[3].metric("S11 peggiore (95%)", f"{ss['p95']:.1f} dB")
                fig = go.Figure()
                fig.add_trace(go.Histogram(x=rep.samples["objective"] - rep.nominal["objective"], nbinsx=60,
                                           name=f"Δ {ylab} (dB)"))
                fig.add_vline(x=-rep.spec["loss_budget_db"], line_dash="dot")
                fig.update_layout(height=260, xaxis_title=_T("Δ {y} rispetto al nominale (dB)", y=ylab), yaxis_title=i18n.tr("pezzi"),
                                  margin=dict(t=20, b=30), showlegend=False)
                st.plotly_chart(fig, width="stretch")
                st.markdown("**Quote critiche** (in ordine di importanza)")
                st.dataframe([{"Quota": cr["label"], "Nominale": f"{cr['nominal']:.3f} {cr['unit']}",
                               "Tolleranza analizzata": f"±{cr['tol_now']:.3f} {cr['unit']}",
                               "Quota di varianza": f"{100 * cr['share']:.0f} %",
                               f"Perdita a ±t (dB)": f"{cr['d_obj']:.3f}",
                               "ΔS11 a ±t (dB)": "" if math.isnan(cr["d_s11"]) else f"{cr['d_s11']:+.2f}",
                               "Tolleranza consigliata": f"±{cr['tol_ok']:g} {cr['unit']}"} for cr in rep.critical],
                             hide_index=True, width="stretch")
                ver = ", ".join(f"{m_} {v:.3g}" for m_, v in rep.verify)
                st.caption(f"{rep.n_runs} simulazioni rapide (modello quadratico + verifica diretta: scarto massimo {ver}). "
                           "Tolleranza consigliata: la più larga classe d'officina che mantiene la perdita di quella quota "
                           f"entro la sua parte del budget di {rep.spec['loss_budget_db']} dB. Il modello rapido non vede "
                           "parete esterna e bordo: per le quote critiche verifica con openEMS.")
                if st.button("📄 Usa queste tolleranze nel disegno PDF", key="tol_pdf"):
                    S["tol_table"] = (kind, rep.critical)
                    st.success("Le trovi nella tabella delle tolleranze del disegno (scheda Disegno & STEP).")
            st.markdown("**Ottimizzazione robusta**: cerca le quote che danno il miglior risultato *medio meno k·σ* dentro "
                        "le tolleranze, invece del picco nominale più stretto.")
            c = st.columns(3)
            rkeys = c[0].multiselect("Quote da ottimizzare", [k for k, _, _ in explore.TUNABLE[kind]],
                                     default=[k for k, _, _ in explore.TUNABLE[kind]][:2], key="rob_keys",
                                     format_func=lambda k: dict((a, b) for a, b, _ in explore.TUNABLE[kind])[k])
            ks = c[1].slider("k (σ)", 0.0, 3.0, 2.0, 0.5, key="rob_k", help="2 ≈ il 97% dei pezzi fa almeno così")
            rnev = c[2].slider("Valutazioni robuste", 6, 40, 16, key="rob_nev",
                               help="ognuna costa 2N+1 simulazioni rapide (≈ 0.5 s l'una)")
            if st.button("🛡️ Ottimizzazione robusta", key="rob_go") and rkeys:
                bar = st.progress(0.0, "ottimo nominale, poi ricerca robusta…")
                over_r, info = tolerance.robust_optimize(kind, S.f_ghz, sc, lab_over, objective, rkeys, tol_in, ks, rnev,
                                                         s11t, S.wall, _fdd,
                                                         progress=lambda i, n, v: bar.progress(min(i / n, 1.0), f"valutazione {i}/{n}"))
                bar.empty()
                S["ropt"] = (kind, over_r, info)
            if S.get("ropt") and S["ropt"][0] == kind:
                _, over_r, info = S["ropt"]
                ylab_r = {"tx": "G", "rx": "G/T", "eme": "G + G/T"}[objective]
                st.success(f"Progetto robusto: {ylab_r} nominale {info['objective']:.2f} · medio {info['mean']:.2f} ± {info['sd']:.3f} dB · "
                           f"garantito (media − k·σ) {info['score']:.2f} · η {100 * info['eta']:.1f}% · S11 {info['s11_db']:.1f} dB")
                st.write({k: f"{v:.3f} ({100 * (v / base_vals[k] - 1):+.1f}%)" for k, v in over_r.items() if k in base_vals})
                st.button("Applica il progetto robusto", key="rob_apply", on_click=_apply_lab_overrides,
                          args=(kind, over_r, base_vals))


# ---------------------------------------------------------------- assembly: feed + matching plate → waveguide
def _mesh_fig(v, f, title, height=430, eye=(1.4, -1.4, 0.9)):
    fig = go.Figure(go.Mesh3d(x=v[:, 0], y=v[:, 1], z=v[:, 2], i=f[:, 0], j=f[:, 1], k=f[:, 2],
                              color=materials.color(S.get("material", "")), flatshading=True,
                              lighting=dict(ambient=0.45, diffuse=0.8, specular=0.5, facenormalsepsilon=0, vertexnormalsepsilon=0)))
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=40, b=0), title=title,
                      scene=dict(aspectmode="data", xaxis_title="x mm", yaxis_title="y mm", zaxis_title="z mm",
                                 camera=dict(eye=dict(x=eye[0], y=eye[1], z=eye[2]))))
    return fig


with tabs[6], contextlib.suppress(_Skip):
    _need()
    st.header("Montaggio feed + piastrina sulla guida d'onda")
    from feedlab import flanges, mounting
    from feedlab.waveguide import RECT_WG as _RWG
    geo = current_geometry()
    wg = S.get("wr_wg")
    if isinstance(geo, geometry.RectHornGeometry):
        st.info("La tromba rettangolare si collega direttamente alla guida WR: piastrina non necessaria.")
    elif wg not in flanges.FLANGES:
        st.info("Scegli la guida d'onda rettangolare nella barra laterale.")
    else:
        fl = flanges.FLANGES[wg]
        st.caption(_T("Come si fissano il feed e la piastrina λ/4 al tronchetto di guida d'onda esterno {wg} (flangia {name}). "
                      "Scegli lo schema: FeedLab imposta da solo i fori della base del feed e della piastrina (stesso "
                      "pattern della flangia); nel menu avanzato puoi cambiare ogni dettaglio.", wg=wg, name=fl.name))
        a1, a2 = st.columns([1, 1])
        with a1:
            system = st.radio("Viti", ["metric", "imperial"], horizontal=True, key="mount_sys",
                              format_func=lambda x: {"metric": "Metriche (M)", "imperial": "Pollici (UNC)"}[x])
            _sch = mounting.schemes_for(wg)
            _prev = (S.get("mount_ui") or {}).get("scheme")
            scheme = st.radio("Schema di montaggio", _sch, key=f"mount_scheme_{fl.shape}",
                              index=_sch.index(_prev) if _prev in _sch else len(_sch) - 1,
                              format_func=lambda k: i18n.tr(mounting.SCHEMES[k][0]))
            st.caption(i18n.tr(mounting.SCHEMES[scheme][1]))
        d = mounting.defaults(scheme, wg, S.f_ghz, system)
        _scr = flanges.screw_for(wg, system)
        _dfl = flanges.flange_hole(wg)
        dcirc_ = (S.get("plate_rf") or (None, 2 * geo.r_input))[1]
        _dmax = flanges.max_hole_dia(wg, dcirc_)
        _dmin = round(flanges.SCREWS[_scr][0] + 0.1, 1)
        k_ = f"{scheme}_{wg}_{system}"                       # every scheme keeps its own advanced settings
        with a1.expander("⚙️ Avanzate: fori, filetti, lamature, viti, piastrina", expanded=False):
            if d["holes"]:
                if d["base_holes"] == "tap":
                    _th = flanges.base_thread_options(wg, S.f_ghz, system)
                    d["thread"] = st.selectbox("Filettatura dei fori nella base", _th, key=f"adv_thread_{k_}")
                else:
                    d["hole_dia"] = st.number_input(_T("Ø fori nella base del feed (mm, da {a:g} a {b:g})", a=_dmin, b=_dmax),
                                                    min_value=float(_dmin), max_value=float(_dmax), value=float(min(_dfl, _dmax)),
                                                    step=0.1, key=f"adv_bdia_{k_}",
                                                    help="il massimo lascia almeno 1 mm di metallo verso il bordo più vicino")
                    d["cbore"] = st.checkbox("Lamatura per la testa della vite (lato tromba della base)", value=d["cbore"],
                                             key=f"adv_cb_{k_}")
                    if d["cbore"] and _scr in flanges.CBORE:
                        _cd, _ck = flanges.CBORE[_scr]
                        d["cb_dia"] = st.number_input(_T("Diametro della lamatura (mm, standard {d:g} per la testa {s})", d=_cd, s=_scr),
                                                      1.0, 30.0, float(_cd), 0.1, key=f"adv_cbd_{k_}")
                        d["cb_depth"] = st.number_input(_T("Profondità della lamatura (mm, standard {d:g} per la testa {s})", d=_ck, s=_scr),
                                                        0.5, 20.0, float(_ck), 0.5, key=f"adv_cbk_{k_}")
                if fl.shape == "square":
                    d["plate_tap"] = st.checkbox(_T("Fori della flangia filettati {s} nella piastrina (la guida si avvita alla piastrina)", s=_scr),
                                                 value=d["plate_tap"], key=f"adv_ptap_{k_}")
                if not d["plate_tap"]:
                    _pdef = d["hole_dia"] or _dfl
                    d["plate_hole_dia"] = st.number_input(_T("Ø fori della flangia nella piastrina (mm, da {a:g} a {b:g})", a=_dmin, b=_dmax),
                                                          min_value=float(_dmin), max_value=float(_dmax),
                                                          value=float(min(_pdef, _dmax)), step=0.1, key=f"adv_pdia_{k_}")
                if fl.shape == "square":
                    _opts = flanges.plate_screw_options(S.f_ghz)
                    if st.checkbox("4 viti piastrina → feed (nei 4 punti liberi)", value=bool(d["plate_screw"]), key=f"adv_ps_{k_}"):
                        d["plate_screw"] = st.selectbox("Viti piastrina → feed", _opts, key=f"adv_psz_{k_}",
                                                        format_func=lambda m_: m_ if system == "metric" else f"{flanges.UNC_FOR_METRIC[m_]} (≈ {m_})")
                        d["plate_head"] = st.radio("Testa delle viti", ["allen", "flat"], key=f"adv_ph_{k_}",
                                                   format_func=lambda k: {"allen": i18n.tr("A brugola con lamatura (ISO 4762)"),
                                                                          "flat": i18n.tr("Testa piana Phillips svasata (ISO 7046)")}[k])
                        if d["plate_head"] == "allen":
                            _psn = flanges.plate_screw_name(d["plate_screw"], system)
                            _pcd, _pck = flanges.CBORE[_psn]
                            d["plate_cb_dia"] = st.number_input(_T("Lamatura delle viti nella piastrina: diametro (mm, standard {d:g})", d=_pcd),
                                                                1.0, 20.0, float(_pcd), 0.1, key=f"adv_pcbd_{k_}_{_psn}")
                            d["plate_cb_depth"] = st.number_input(_T("Lamatura delle viti nella piastrina: profondità (mm, standard {d:g})", d=_pck),
                                                                  0.5, 10.0, float(_pck), 0.1, key=f"adv_pcbk_{k_}_{_psn}")
                    else:
                        d["plate_screw"] = None
                else:
                    d["pins"] = st.checkbox("Fori per i pin di allineamento (piastrina e base del feed)", True, key=f"adv_pins_{k_}")
            d["outer_mm"] = st.number_input("Misura esterna della piastrina (mm, vuoto = automatica)", min_value=5.0,
                                            max_value=200.0, value=None, step=0.1, key=f"adv_outer_{wg}",
                                            placeholder=i18n.tr("automatica"))
            d["outer_r"] = st.number_input("Raggio angoli esterni (mm)", min_value=0.0, max_value=10.0,
                                           value=2.0 if fl.shape == "square" else 0.0, step=0.5, key=f"adv_outr_{wg}",
                                           disabled=fl.shape != "square")
            d["plate_t"] = st.number_input("Spessore della piastrina (mm, vuoto = λ/4 calcolato)", min_value=0.5,
                                           max_value=30.0, value=None, step=0.1, key=f"adv_pt_{wg}",
                                           placeholder=i18n.tr("automatico (λ/4)"))
        with a2:
            _fig = mounting.section_fig(scheme, i18n.tr)
            st.pyplot(_fig, width="stretch")
            import matplotlib.pyplot as _plt
            _plt.close(_fig)
        d.update(scheme=scheme, scheme_title=mounting.SCHEMES[scheme][0], system=system)
        S["mount_ui"] = d
        # drilling applied at once (feed and plate), so the 3D views below follow every change
        pol0, dcirc0, rr0, opt0 = S.get("plate_rf") or ("V", 2 * geo.r_input, round(min(2.0, 0.08 * _RWG[wg].a_mm), 2), True)
        try:
            plv = plate.design_plate(S.f_ghz, wg, dcirc0, pol0, rr0, opt0, holes=system if d["holes"] else None,
                                     plate_screw=d["plate_screw"], base_holes=d["base_holes"], hole_dia=d["hole_dia"],
                                     thread=d["thread"], cbore=d["cbore"], cb_depth=d["cb_depth"], cb_dia=d["cb_dia"],
                                     pins=d["pins"], plate_t=d["plate_t"], plate_head=d["plate_head"], plate_tap=d["plate_tap"],
                                     outer_mm=d["outer_mm"], outer_r=d["outer_r"], plate_hole_dia=d["plate_hole_dia"],
                                     plate_cb_dia=d.get("plate_cb_dia"), plate_cb_depth=d.get("plate_cb_depth"))
            cfg = {"wg": wg if d["holes"] else None, "system": system, "pol": pol0, "plate_screw": d["plate_screw"],
                   "plate_t": plv.body_t if d["holes"] else None, "base_holes": d["base_holes"], "hole_dia": d["hole_dia"],
                   "thread": d["thread"], "cbore": d["cbore"], "cb_depth": d["cb_depth"], "cb_dia": d["cb_dia"],
                   "pins": d["pins"], "plate_head": d["plate_head"], "plate_tap": d["plate_tap"],
                   "plate_hole_dia": d["plate_hole_dia"], "plate_cb_dia": d.get("plate_cb_dia"),
                   "plate_cb_depth": d.get("plate_cb_depth")}
            if cfg != (S.get("mount_cfg") or {"wg": None}):
                S["mount_cfg"] = cfg
                geometry.MOUNT.clear()
                geometry.MOUNT.update(cfg)
                for _k in ("pdf", "step", "stl", "plate_pdf", "plate_step"):
                    S.pop(_k, None)
            gfeed = current_geometry()
            if plv.mount is not None:
                for w_ in plv.mount.warnings:
                    st.warning(w_)
                for _n in getattr(gfeed, "notes", []) or []:
                    if "teste delle viti" in _n or "troppo sottile per la lamatura" in _n or "sovrasta" in _n:
                        st.warning(_n)
                    elif "allargata" in _n:
                        st.info(_n)
            st.markdown(_T("Piastrina **{o:.2f} mm**, spessore **{t:.2f} mm** · base del feed spessa **{b:.2f} mm**",
                           o=plv.outer, t=plv.body_t, b=gfeed.params.get("flange_thickness", 0.0)))
            v1, v2 = st.columns(2)
            try:
                pv, pf = plate.mesh(plv)
                v1.plotly_chart(_mesh_fig(pv, pf, i18n.tr("Piastrina (3D, si aggiorna a ogni modifica)"), 430,
                                          (1.2, -1.4, 1.1)), width="stretch")
            except Exception as ex_:
                v1.caption(_T("Vista 3D non disponibile: {e}", e=ex_))
            try:
                bv, bf = cad.mesh(gfeed)
                v2.plotly_chart(_mesh_fig(bv, bf, i18n.tr("Feed con la base forata (3D, si aggiorna a ogni modifica)"), 430,
                                          (1.6, -1.6, 0.6)), width="stretch")
            except Exception as ex_:
                v2.caption(_T("Vista 3D non disponibile: {e}", e=ex_))
        except ValueError as ex:
            st.error(str(ex))


# ---------------------------------------------------------------- matching plate
with tabs[7], contextlib.suppress(_Skip):
    _need()
    st.header("Piastrina λ/4 di adattamento: guida circolare del feed → guida rettangolare WR")
    st.caption("Il feed a simmetria circolare irradia la polarizzazione lineare imposta dall'orientamento della guida WR: "
               "il campo E è parallelo al lato corto 'b'. Metodo: design guide OE2IGL (openEMS), ottimizzazione HB9PZK.")
    geo = current_geometry()
    from feedlab.waveguide import RECT_WG, suggest_rect_wg
    if isinstance(geo, geometry.RectHornGeometry):
        st.info("La tromba rettangolare si collega direttamente alla guida WR: piastrina non necessaria.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        if S.get("wr_wg"):                       # chosen once, in the sidebar (plate, drilling, square base)
            wg = S["wr_wg"]
            c1.markdown(_T("**Guida rettangolare:** {wg}", wg=wg))
            c1.caption("si cambia nella barra laterale")
        else:
            wg = c1.selectbox("Guida rettangolare", list(RECT_WG))
        pol_ = c2.radio("Polarizzazione", ["Verticale", "Orizzontale"], horizontal=True)
        dcirc = c3.number_input("Ø guida circolare del feed (mm)", 0.5, 100.0, float(round(2 * geo.r_input, 3)), 0.001,
                                format="%.3f")
        rr = c4.number_input("Raggio angoli apertura (mm)", 0.0, 5.0, float(round(min(2.0, 0.08 * RECT_WG[wg].a_mm), 2)), 0.05,
                             help="raggio della fresa: angoli arrotondati compensati sulla larghezza (HB9PZK)")
        opt = st.checkbox("Versione ottimizzata (b e spessore corretti con openEMS)", True)
        from feedlab import flanges
        S["plate_rf"] = ("V" if pol_ == "Verticale" else "H", float(dcirc), float(rr), bool(opt))
        _mu = S.get("mount_ui") or {}
        holes_on, system = bool(_mu.get("holes")), _mu.get("system", "metric")
        base_holes, hole_dia, thread = _mu.get("base_holes", "flange"), _mu.get("hole_dia"), _mu.get("thread")
        _cbore, cb_dia, cb_depth = bool(_mu.get("cbore")), _mu.get("cb_dia"), _mu.get("cb_depth")
        pscrew, pins, plate_head, plate_tap = _mu.get("plate_screw"), bool(_mu.get("pins", True)), \
            _mu.get("plate_head", "allen"), bool(_mu.get("plate_tap"))
        _outer, _outer_r, _pt = _mu.get("outer_mm"), _mu.get("outer_r", 0.0), _mu.get("plate_t")
        _round_fl = wg in flanges.FLANGES and flanges.FLANGES[wg].shape == "round"
        _scr = flanges.screw_for(wg, system) if wg in flanges.FLANGES else None
        if holes_on:
            st.info(_T("Fori di montaggio: schema \"{s}\" (si sceglie nella scheda 🔩 Montaggio feed + piastrina).",
                       s=i18n.tr(_mu.get("scheme_title", ""))))
        else:
            st.caption(i18n.tr("Nessun foro di montaggio: si scelgono nella scheda 🔩 Montaggio feed + piastrina."))
        pol_c = "V" if pol_ == "Verticale" else "H"
        try:
            pl = plate.design_plate(S.f_ghz, wg, dcirc, pol_c, rr, opt, holes=system if holes_on else None,
                                    plate_screw=pscrew, base_holes=base_holes, hole_dia=hole_dia, thread=thread,
                                    cbore=_cbore, cb_depth=cb_depth, cb_dia=cb_dia, pins=pins, plate_t=_pt,
                                    plate_head=plate_head, plate_tap=plate_tap, outer_mm=_outer, outer_r=_outer_r,
                                    plate_hole_dia=_mu.get("plate_hole_dia"), plate_cb_dia=_mu.get("plate_cb_dia"),
                                    plate_cb_depth=_mu.get("plate_cb_depth"))
            new_cfg = {"wg": wg if holes_on else None, "system": system, "pol": pol_c, "plate_screw": pscrew,
                       "plate_t": pl.body_t if holes_on else None, "base_holes": base_holes, "hole_dia": hole_dia,
                       "thread": thread, "cbore": _cbore, "cb_depth": cb_depth, "cb_dia": cb_dia, "pins": pins,
                       "plate_head": plate_head, "plate_tap": plate_tap, "plate_hole_dia": _mu.get("plate_hole_dia"),
                       "plate_cb_dia": _mu.get("plate_cb_dia"), "plate_cb_depth": _mu.get("plate_cb_depth")}
            if new_cfg != (S.get("mount_cfg") or {"wg": None}) and (holes_on or (S.get("mount_cfg") or {}).get("wg")):
                S["mount_cfg"] = new_cfg
                geometry.MOUNT.update(new_cfg)
                for k in ("pdf", "step", "stl", "plate_pdf", "plate_step"):
                    S.pop(k, None)
            _gf = current_geometry()                 # screws follow the feed base thickness (sidebar)
            if pl.mount is not None and getattr(_gf, "mount", None) is not None and \
                    _gf.mount.flange.wg == pl.mount.flange.wg:
                pl.mount.screw_len, pl.mount.screw_len_label = _gf.mount.screw_len, _gf.mount.screw_len_label
                pl.mount.screw_in, pl.mount.guide_in = _gf.mount.screw_in, _gf.mount.guide_in
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Apertura a", f"{pl.a:.3f} mm"); m2.metric("Apertura b", f"{pl.b:.3f} mm")
            m3.metric("Spessore", f"{pl.thickness:.3f} mm", f"± {pl.tolerance:.3f}", delta_color="off")
            m4.metric("Z0 intermedia", f"{pl.z0:.0f} Ω")
            w = RECT_WG[wg]
            st.write(f"{wg}: {w.a_mm} × {w.b_mm} mm (fc TE10 {w.fc_te10_ghz:.2f} GHz) · guida circolare Ø{dcirc:.3f} mm "
                     f"(fc TE11 {299.792458 / (1.706 * dcirc):.2f} GHz)")
            if pl.mount is not None:
                mm_ = pl.mount
                _deep = max(((h.depth or 0.0) for h in mm_.feed_holes if h.kind == 'tap' and h.depth), default=0.0)
                if mm_.base_holes == "tap":
                    _txt = [_T("Flangia {wg} {name}: fori filettati {th} passanti nella base; le viti della guida "
                               "attraversano flangia e piastrina e si avvitano nella base.",
                               wg=mm_.flange.wg, name=mm_.flange.name, th=mm_.thread)]
                elif any(h.kind == "tap" for h in mm_.plate_holes):
                    _txt = [_T("Flangia {wg} {name}: le viti della guida ({screw}) si avvitano nella piastrina (6H); "
                               "nella base del feed fori passanti Ø{d:g}.", wg=mm_.flange.wg, name=mm_.flange.name,
                               screw=mm_.screw, d=max(h.dia for h in mm_.feed_holes if h.kind == "cbore_back"))]
                elif any(h.cb_dia for h in mm_.feed_holes):
                    _txt = [_T("Flangia {wg} {name}: viti {screw} dal lato del feed, con la testa nella lamatura della base; "
                               "attraversano base e piastrina e si avvitano nella flangia della guida.",
                               wg=mm_.flange.wg, name=mm_.flange.name, screw=mm_.screw)]
                else:
                    _txt = [_T("Flangia {wg} {name}: fori passanti nella base e nella piastrina; viti {screw} dal lato del "
                               "feed con la testa appoggiata sulla base, avvitate nella flangia della guida.",
                               wg=mm_.flange.wg, name=mm_.flange.name, screw=mm_.screw)]
                if mm_.plate_screw:
                    _txt += [_T("4 viti piastra→feed {ps} × {ln} a testa piana Phillips, a filo nella svasatura (lato guida).",
                                ps=mm_.plate_screw, ln=mm_.screw_len_label) if mm_.plate_head == "flat" else
                             _T("4 viti piastra→feed {ps} × {ln} a brugola, con la testa nella lamatura (lato guida).",
                                ps=mm_.plate_screw, ln=mm_.screw_len_label),
                             _T("Nel feed la vite entra {a} mm; foro profondo {b} mm, filettato per {c} mm.",
                                a=f"{mm_.screw_in:.1f}", b=f"{_deep:.0f}", c=f"{mm_.tap_depth:.1f}")]
                if any(h.kind == "dowel" for h in mm_.plate_holes):
                    _txt.append(i18n.tr("4 fori per i pin di allineamento della flangia."))
                if any(h.kind == "pin" for h in mm_.plate_holes):
                    _txt.append(i18n.tr("2 spine di centraggio piastra–feed."))
                if pl.pocket_depth > 0.005:
                    _txt.append(_T("Corpo piastrina {t} mm con tasca Ø{d} × {p} mm sul lato feed (prolunga la guida "
                                   "circolare; la parte λ/4 resta invariata).",
                                   t=f"{pl.body_t:.2f}", d=f"{pl.circ_diam:.3f}", p=f"{pl.pocket_depth:.2f}"))
                _txt.append(i18n.tr("La foratura è applicata anche al feed (PDF foglio 2 e STEP nella scheda Disegno & STEP)."))
                st.info(" ".join(_txt))
                for w_ in mm_.warnings:
                    st.warning(w_)
            base = WORK / f"plate_{wg}_{S.f_ghz:g}GHz_{pl.polarization}".replace(".", "p")
            pname = _filenames.pick(st, base.name, "plate")
            b1, b2 = st.columns(2)
            if b1.button("📄 Disegno PDF piastrina"):
                S["plate_pdf"] = Path(plate.drawing_pdf(pl, base.with_suffix(".pdf"), S.material)).read_bytes()
            if S.get("plate_pdf"):
                b1.download_button("Scarica PDF", S["plate_pdf"], file_name=pname + ".pdf", mime="application/pdf")
            if b2.button("🧊 STEP piastrina"):
                S["plate_step"] = Path(plate.export_step(pl, base.with_suffix(".step"))).read_bytes()
            if S.get("plate_step"):
                b2.download_button("Scarica .stp", S["plate_step"], file_name=pname + ".stp", mime="model/step")
            # front view preview
            fig = go.Figure()
            h = pl.outer / 2
            if pl.shape != "round" and pl.outer_r > 0.01:        # square with rounded corners
                rc = pl.outer_r
                fig.add_shape(type="path", line=dict(color="black"), fillcolor="rgba(201,162,39,0.5)",
                              path=(f"M {-h + rc},{-h} L {h - rc},{-h} Q {h},{-h} {h},{-h + rc} L {h},{h - rc} "
                                    f"Q {h},{h} {h - rc},{h} L {-h + rc},{h} Q {-h},{h} {-h},{h - rc} "
                                    f"L {-h},{-h + rc} Q {-h},{-h} {-h + rc},{-h} Z"))
            else:
                fig.add_shape(type="circle" if pl.shape == "round" else "rect", x0=-h, y0=-h, x1=h, y1=h,
                              line=dict(color="black"), fillcolor="rgba(201,162,39,0.5)")
            aa, bb = (pl.a, pl.b) if pl.polarization == "V" else (pl.b, pl.a)
            fig.add_shape(type="rect", x0=-aa / 2, y0=-bb / 2, x1=aa / 2, y1=bb / 2, line=dict(color="black"), fillcolor="white")
            fig.add_shape(type="circle", x0=-dcirc / 2, y0=-dcirc / 2, x1=dcirc / 2, y1=dcirc / 2, line=dict(dash="dash", color="gray"))
            wa, wb = (w.a_mm, w.b_mm) if pl.polarization == "V" else (w.b_mm, w.a_mm)
            fig.add_shape(type="rect", x0=-wa / 2, y0=-wb / 2, x1=wa / 2, y1=wb / 2, line=dict(dash="dot", color="blue"))
            if pl.mount is not None:
                for hl in pl.mount.plate_holes:
                    col_ = {"flange": "black", "plate": "magenta", "pin": "green"}[flanges.hole_role(hl)]
                    fig.add_shape(type="circle", x0=hl.x - hl.dia / 2, y0=hl.y - hl.dia / 2, x1=hl.x + hl.dia / 2,
                                  y1=hl.y + hl.dia / 2, line=dict(color=col_))
                    if hl.kind in ("cbore", "csk"):
                        fig.add_shape(type="circle", x0=hl.x - hl.cb_dia / 2, y0=hl.y - hl.cb_dia / 2, x1=hl.x + hl.cb_dia / 2,
                                      y1=hl.y + hl.cb_dia / 2, line=dict(color="magenta"))
            fig.add_annotation(x=0, y=0, ax=0 if pl.polarization == "V" else -40, ay=40 if pl.polarization == "V" else 0,
                               text="E", showarrow=True, arrowcolor="red", arrowhead=2, arrowwidth=2)
            fig.update_layout(height=420, xaxis=dict(range=[-h - 3, h + 3], title="mm"),
                              yaxis=dict(range=[-h - 3, h + 3], scaleanchor="x"), title="Vista frontale (lato feed)")
            v1, v2 = st.columns(2)
            v1.plotly_chart(fig, width="stretch")
            try:                                      # 3D model of the plate (same solid as the STEP file)
                pv, pf = plate.mesh(pl)
                f3 = go.Figure(go.Mesh3d(x=pv[:, 0], y=pv[:, 1], z=pv[:, 2], i=pf[:, 0], j=pf[:, 1], k=pf[:, 2],
                                         color=materials.color(S.get("material", "")), flatshading=True,
                                         lighting=dict(ambient=0.45, diffuse=0.8, specular=0.5, facenormalsepsilon=0, vertexnormalsepsilon=0)))
                f3.update_layout(height=420, title="Vista 3D della piastrina", margin=dict(l=0, r=0, t=40, b=0),
                                 scene=dict(aspectmode="data", xaxis_title="x mm", yaxis_title="y mm", zaxis_title="z mm",
                                            camera=dict(eye=dict(x=1.2, y=-1.4, z=1.1))))
                v2.plotly_chart(f3, width="stretch")
            except Exception as ex_:
                v2.caption(_T("Vista 3D non disponibile: {e}", e=ex_))
            _gb = current_geometry()                  # the feed base, drilled like the plate: check the counterbores
            if holes_on and getattr(_gb, "mount", None) is not None:
                st.subheader("Feed con la base forata (3D, ruotabile)")
                _cbs = [hh for hh in _gb.mount.feed_holes if hh.kind == "cbore_back"]
                if _cbs and not _cbs[0].cb_depth:
                    st.info(_T("Fori passanti Ø{d:g} mm senza lamatura: la testa della vite si appoggia sulla base "
                               "(lato tromba); base spessa {t:.2f} mm.", d=_cbs[0].dia, t=_gb.params["flange_thickness"]))
                elif _cbs:
                    st.info(_T("Lamature sul lato tromba della base (dove escono le teste delle viti): Ø{d:g} mm, profonde "
                               "{k:g} mm; base spessa {t:.2f} mm, sotto la testa restano {r:.2f} mm.",
                               d=_cbs[0].cb_dia, k=_cbs[0].cb_depth, t=_gb.params["flange_thickness"],
                               r=_gb.params["flange_thickness"] - _cbs[0].cb_depth))
                if _cbs:
                    for _n in getattr(_gb, "notes", []) or []:          # heads under the horn, counterbore past the edge
                        if "teste delle viti" in _n or "troppo sottile per la lamatura" in _n or "sovrasta" in _n:
                            st.warning(_n)
                        elif "allargata" in _n:
                            st.info(_n)
                try:
                    bv, bf = cad.mesh(_gb)                 # whole feed, base drilled like the plate
                    fb = go.Figure(go.Mesh3d(x=bv[:, 0], y=bv[:, 1], z=bv[:, 2], i=bf[:, 0], j=bf[:, 1], k=bf[:, 2],
                                             color=materials.color(S.get("material", "")), flatshading=True,
                                             lighting=dict(ambient=0.45, diffuse=0.8, specular=0.5, facenormalsepsilon=0, vertexnormalsepsilon=0)))
                    fb.update_layout(height=620, margin=dict(l=0, r=0, t=40, b=0),
                                     title=i18n.tr("Feed: in basso la base (faccia verso la piastrina, z = 0) con fori e lamature, in alto l'apertura"),
                                     scene=dict(aspectmode="data", xaxis_title="x mm", yaxis_title="y mm", zaxis_title="z mm",
                                                camera=dict(eye=dict(x=1.6, y=-1.6, z=0.6))))   # whole feed, base visible
                    st.plotly_chart(fb, width="stretch")
                    st.caption("Ruota la vista col mouse e usa la rotellina per avvicinarti alla base. "
                               "STEP/STL e disegno PDF (foglio della flangia) riportano gli stessi fori.")
                except Exception as ex_:
                    st.caption(_T("Vista 3D non disponibile: {e}", e=ex_))
        except ValueError as ex:
            st.error(str(ex))


# ---------------------------------------------------------------- credits
# ---------------------------------------------------------------- project outputs
with tabs[10]:
    st.header("📦 Output di progetto")
    st.caption("Scegli quali documenti generare: PDF delle simulazioni e dei disegni, tabella di tutte le quote e i dati, "
               "risultati openEMS, report completo e il file di progetto (.json), che si può scambiare e riaprire in "
               "FeedLab.")
    if _missing():
        st.info(_T("Per iniziare seleziona: {m}.", m=", ".join(i18n.tr(x) for x in _missing())))
    else:
        from feedlab import project as _project, report as _report
        OUT = [("full", "📄 Report completo di progetto (PDF)", True), ("sims", "📈 Simulazioni veloci (PDF)", False),
               ("feed", "📐 Feed: disegno e simulazioni (PDF)", False), ("dish", "📡 Parabola (PDF)", False),
               ("plate", "🔲 Piastrina λ/4 (PDF)", False), ("assembly", "🔩 Feed + piastrina, montaggio (PDF)", False),
               ("data", "📋 Tabella di tutte le quote e i dati (PDF + CSV)", False),
               ("openems", "🖥️ Simulazioni openEMS (PDF)", False), ("json", "💾 File di progetto (.json)", True),
               ("cad", "🧊 Modelli 3D del feed (STEP + STL)", False),
               ("simx", "🧪 Script per simulatori: openEMS + macro CST", False)]
        cols = st.columns(2)
        pick = {k: cols[n % 2].checkbox(lab, value=dflt, key=f"out_{k}") for n, (k, lab, dflt) in enumerate(OUT)}
        if not S.get("wr_wg") or not S.get("plate_rf"):
            st.caption(i18n.tr("La piastrina si progetta nella scheda 🔲 Piastrina WR: aprila una volta per includerla."))
        base_name = f"FeedLab_{S.feed_kind}_{S.f_ghz:.3f}GHz"
        out_name = _filenames.pick(st, base_name, "outputs")
        if st.button("⚙️ Genera", type="primary", key="out_go"):
            files = {}
            with st.spinner("Calcolo del progetto e generazione dei documenti…"):
                geo_o = current_geometry()
                proj = _project.build(_project_snapshot(), geo_o, _fd_design())
                _project.save_auto(proj)
                wdir = WORK / "outputs"
                wdir.mkdir(exist_ok=True)
                jobs = {"full": lambda: _report.full_pdf(proj, S, geo_o, wdir), "sims": lambda: _report.sims_pdf(proj),
                        "feed": lambda: _report.feed_pdf(proj, geo_o, wdir), "dish": lambda: _report.dish_pdf(proj),
                        "plate": lambda: _report.plate_pdf(S, proj, wdir), "assembly": lambda: _report.assembly_pdf(proj, S),
                        "data": lambda: _report.data_pdf(proj), "openems": lambda: _report.openems_pdf(proj)}
                names = {"full": "report_completo", "sims": "simulazioni", "feed": "feed", "dish": "parabola",
                         "plate": "piastrina", "assembly": "feed_piastrina", "data": "dati", "openems": "openems"}
                for k, fn in jobs.items():
                    if pick.get(k):
                        try:
                            b = fn()
                            if b:
                                files[f"{base_name}_{names[k]}.pdf"] = b
                        except Exception as e:
                            st.warning(f"{i18n.tr(dict((a, b) for a, b, _ in OUT)[k])}: {e}")
                if pick.get("data"):
                    files[f"{base_name}_dati.csv"] = _report.data_csv(proj)
                if pick.get("json"):
                    files[f"{base_name}.feedlab.json"] = _project.to_json(proj)
                if pick.get("cad"):
                    try:
                        files[f"{base_name}.stp"] = cad.export_step(geo_o, wdir / "feed.step").read_bytes()
                        files[f"{base_name}.stl"] = cad.export_stl(geo_o, wdir / "feed.stl").read_bytes()
                    except Exception as e:
                        st.warning(f"STEP/STL: {e}")
                if pick.get("simx") and _sim_export.supported(geo_o):
                    files[f"{base_name}_openems.zip"] = _sim_export.openems_zip(geo_o)
                    files[f"{base_name}_cst.zip"] = _sim_export.cst_zip(geo_o, name=base_name)
            S["outputs"] = files
            S["outputs_base"] = base_name
        if S.get("outputs"):
            _ob = S.get("outputs_base", base_name)
            files = {(out_name + n[len(_ob):] if n.startswith(_ob) else n): d for n, d in S["outputs"].items()}
            st.success(_T("{n} file pronti.", n=len(files)))
            st.download_button("⬇️ Scarica tutto (ZIP)", _report.zip_all(files), file_name=f"{out_name}.zip",
                               mime="application/zip", type="primary")
            for name, data in files.items():
                mime = ("application/pdf" if name.endswith(".pdf") else "application/json" if name.endswith(".json")
                        else "text/csv" if name.endswith(".csv") else "application/zip" if name.endswith(".zip")
                        else "application/octet-stream")
                st.download_button(f"⬇️ {name}", data, file_name=name, mime=mime, key=f"dl_{name}")
    st.divider()
    st.subheader("📂 Apri un file di progetto")
    up = st.file_uploader("File di progetto FeedLab (.json)", type=["json"], key="proj_up")

    def _open_cb():
        """Runs before the widgets are drawn: only here their values (band, material…) may be set."""
        try:
            from feedlab import project as _project
            _apply_project(_project.load(S["proj_up"].getvalue()))
            S["proj_msg"] = ("ok", None)
        except Exception as e:
            S["proj_msg"] = ("err", str(e))
    st.button("📂 Apri progetto", key="proj_open", disabled=up is None, on_click=_open_cb)
    _pm = S.pop("proj_msg", None)
    if _pm and _pm[0] == "ok":
        st.success("Progetto aperto.")
    elif _pm:
        st.error(i18n.tr("File non valido") + f": {_pm[1]}")

with tabs[-1]:
    from feedlab import credits as _credits
    _credits.render(st)
