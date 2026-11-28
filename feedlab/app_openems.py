"""Tab "Full-wave openEMS" of the FeedLab app: optional deep analysis with openEMS on this PC.

Four parts: guided installation of openEMS, new analysis (single run, mesh convergence, parameter sweep),
background simulations with progress, results (deep analysis, comparisons, report and exports).
"""
from __future__ import annotations

import io
import json
import time
import zipfile
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as _st

from feedlab import filenames as _filenames
from feedlab import i18n
from feedlab import deep_analysis, explore, geometry, materials, openems_local, openems_sim, spacemap, wizard
from feedlab.waveguide import wavelength_mm

st = i18n.wrap(_st)

STATE_IT = {"done": "✅ completata", "running": "⏳ in corso", "queued": "🕒 in coda", "error": "❌ errore",
            "stopped": "⏹️ fermata", "interrotto": "⚠️ interrotta", "nuovo": "📝 solo script"}

_fragment = getattr(_st, "fragment", None)


def _auto(run_every):
    """st.fragment(run_every=...) when available (auto refresh of a part of the page)."""
    def deco(fn):
        if _fragment is None:
            return fn
        return _fragment(run_every=run_every)(fn)
    return deco


def _key(path):
    p = Path(path)
    p = p / "results.json" if p.is_dir() else p
    return str(p), p.stat().st_mtime


@_st.cache_data(show_spinner="Analisi dei risultati…", max_entries=64)
def _analyze_cached(path: str, mtime: float, spec: tuple):
    return deep_analysis.analyze(deep_analysis.load(path), deep_analysis.DishSpec(*spec))


@_st.cache_data(show_spinner=False, max_entries=64)
def _fast_cached(path: str, mtime: float):
    return deep_analysis.compare_fast_model(deep_analysis.load(path))


@_st.cache_data(show_spinner=False, max_entries=256)
def _dish_cached(path: str, mtime: float, f_ghz: float, spec: tuple):
    r = deep_analysis.load(path)
    return deep_analysis.dish_performance(r.ff_at(f_ghz).pattern(), f_ghz, deep_analysis.DishSpec(*spec))


@_st.cache_data(show_spinner="Confronto delle simulazioni…", max_entries=32)
def _compare_cached(items: tuple, spec: tuple):
    return deep_analysis.compare([(lab, deep_analysis.load(p)) for lab, p, _ in items], deep_analysis.DishSpec(*spec))


def _spec_tuple(spec):
    from dataclasses import astuple
    return astuple(spec)


def _fmt_time(s):
    if s is None:
        return "—"
    s = float(s)
    return f"{s / 3600:.1f} h" if s > 5400 else f"{s / 60:.0f} min" if s > 90 else f"{s:.0f} s"


def _env_state(S, refresh=False):
    if refresh or "oems_env" not in S:
        inst = openems_local.find_install()
        py = openems_local.find_working_python(inst) if inst.found else None
        own = openems_local.own_python()
        S["oems_env"] = {"inst": inst, "py": py, "own_tag": openems_local.py_tag(own) if own else ""}
    return S["oems_env"]


# ================================================================== 1. installation
def _install_section(S):
    env = _env_state(S)
    inst, py = env["inst"], env["py"]
    c = st.columns([3, 1])
    with c[0]:
        if inst.found:
            st.success(f"openEMS trovato in `{inst.root}`" + (f" (versione {inst.version})" if inst.version else "")
                       + f" — {inst.source}")
        else:
            st.warning("openEMS non è installato su questo PC.")
        if py:
            st.success(f"Binding Python funzionanti: openEMS {py['openems']}, CSXCAD {py['csxcad']} · Python `{py['python']}`")
        elif inst.found:
            st.warning("I binding Python di openEMS non si importano ancora.")
    if c[1].button("🔄 Verifica di nuovo", key="oems_recheck"):
        _env_state(S, refresh=True)
        st.rerun()

    if S.get("oems_install_status"):
        _install_progress(S)
        return

    if inst.found and py:
        with st.expander("Reinstalla o aggiorna openEMS"):
            _install_form(S, inst)
        return

    if inst.found and not py:
        st.markdown(f"Wheel Python incluse in openEMS: **{', '.join(inst.wheel_tags()) or 'nessuna'}** · "
                    f"Python di FeedLab: **{env['own_tag'] or '—'}**")
        if st.button("Installa i binding Python in FeedLab", type="primary"):
            log = []
            with st.spinner("pip install delle wheel di openEMS…"):
                ok = openems_local.install_bindings(openems_local.own_python(), inst, log.append)
            st.code("\n".join(log)[-3000:])
            if ok:
                _env_state(S, refresh=True)
                st.rerun()
            else:
                st.error("Installazione non riuscita: aggiorna openEMS con la procedura qui sotto (le versioni recenti "
                         "includono le wheel per Python 3.13).")
    _install_form(S, inst)


def _install_form(S, inst):
    st.markdown("#### Procedura guidata di installazione")
    st.markdown(
        "1. **Scarico** l'ultima versione ufficiale per Windows dal repository di openEMS su GitHub (~100 MB).\n"
        "2. **Estraggo** i file in una cartella dell'utente (non servono permessi di amministratore).\n"
        "3. **Imposto** la variabile `OPENEMS_INSTALL_PATH`.\n"
        "4. **Installo i binding Python** di openEMS nel Python di FeedLab (più `h5py`).\n"
        "5. **Verifico** l'importazione e lancio una **simulazione di prova** di pochi secondi.")
    if not openems_local.IS_WIN:
        st.info("Il download automatico riguarda Windows. Su Linux/macOS installa openEMS dal gestore di pacchetti o "
                "compilalo (https://docs.openems.de/install/), poi indica qui sotto la cartella.")
    c = st.columns([3, 2])
    target = c[0].text_input("Cartella di installazione", str(openems_local.default_install_dir()), key="oems_target")
    mode = c[1].radio("Sorgente", ["Scarica da GitHub", "Zip già scaricato", "Già installato in una cartella"],
                      key="oems_src", horizontal=False)
    zip_path = None
    if mode == "Zip già scaricato":
        zip_path = st.text_input("Percorso dello zip openEMS_win…zip", key="oems_zip")
    if mode == "Già installato in una cartella":
        folder = st.text_input("Cartella che contiene openEMS.exe", inst.root or "", key="oems_existing")
        if st.button("Usa questa cartella"):
            i2 = openems_local.find_install(folder)
            if i2.found:
                openems_local.save_settings(openems_root=i2.root)
                openems_local.set_user_env("OPENEMS_INSTALL_PATH", i2.root)
                _env_state(S, refresh=True)
                st.rerun()
            else:
                st.error("openEMS.exe non trovato in quella cartella.")
        return
    test = st.checkbox("Esegui la simulazione di prova al termine", True, key="oems_test")
    if mode == "Scarica da GitHub" and st.button("🔎 Mostra l'ultima versione disponibile"):
        try:
            rel = openems_local.latest_release()
            st.info(f"**{rel['tag']}** — `{rel['name']}` ({rel['size'] / 1e6:.0f} MB), pubblicata {rel['published'][:10]}")
        except Exception as e:
            st.error(f"GitHub non raggiungibile: {e}. Scarica lo zip a mano da {openems_local.RELEASES_PAGE}")
    if st.button("⬇️ Installa openEMS", type="primary", disabled=bool(mode == "Zip già scaricato" and not zip_path)):
        S["oems_install_status"] = str(openems_local.start_guided_install(target, zip_path or None, test))
        st.rerun()
    st.caption(f"Pagina ufficiale delle release: {openems_local.RELEASES_PAGE} · documentazione: https://docs.openems.de")


@_auto("2s")
def _install_progress(S):
    d = openems_local.read_status(S["oems_install_status"]) or {"state": "running", "step": "avvio", "progress": 0.0,
                                                               "log": [], "steps_done": []}
    st.progress(min(1.0, float(d.get("progress", 0))), text=openems_local.STEP_LABELS.get(d.get("step"), d.get("step", "")))
    lines = []
    for s in openems_local.INSTALL_STEPS:
        mark = "✅" if s in d.get("steps_done", []) else ("⏳" if s == d.get("step") and d["state"] == "running" else "▫️")
        lines.append(f"{mark} {openems_local.STEP_LABELS[s]}")
    st.markdown("  \n".join(lines))
    if d.get("total_mb"):
        st.caption(f"Scaricati {d.get('downloaded_mb', 0):.0f} / {d['total_mb']:.0f} MB")
    with st.expander("Dettagli", expanded=d["state"] == "error"):
        st.code("\n".join(d.get("log", []))[-4000:] or "…")
    if d["state"] == "done":
        st.success("openEMS è installato e funzionante. Passa a **Nuova analisi**.")
        if st.button("Chiudi", key="oems_inst_close"):
            S.pop("oems_install_status", None)
            _env_state(S, refresh=True)
            st.rerun()
    elif d["state"] == "error":
        st.error(d.get("error", "errore"))
        if st.button("Riprova", key="oems_inst_retry"):
            S.pop("oems_install_status", None)
            st.rerun()


# ================================================================== 2. new analysis
def _new_section(S, geo, dish):
    env = _env_state(S)
    if isinstance(geo, geometry.RectHornGeometry):
        st.warning("L'analisi full-wave automatica copre i feed a simmetria di rotazione (non la tromba rettangolare).")
        return
    f0 = geo.f_ghz
    st.markdown(f"**Feed:** {geometry.FEED_TYPES[geo.kind]} a {f0:g} GHz · apertura Ø{2 * geo.r_aperture:.2f} mm · "
                f"lunghezza {geo.z_aperture:.1f} mm — quote dalla scheda *Progetto feed* / *Laboratorio*.")
    mode = st.radio("Tipo di analisi", ["Singola simulazione", "Convergenza della mesh", "Sweep di un parametro"],
                    horizontal=True, key="oems_mode")
    c = st.columns(4)
    bw = c[0].slider("Banda ± %", 2, 25, 10, key="oems_bw2")
    nff = c[1].select_slider("Frequenze del lobo", [1, 3, 5, 7], 3, key="oems_nff")
    end_db = c[2].select_slider("Fine simulazione (energia −dB)", [30, 40, 50, 60], 40, key="oems_end")
    threads = c[3].number_input("Thread CPU (0 = tutti)", 0, 128, 0, key="oems_thr")
    c = st.columns(4)
    if mode == "Convergenza della mesh":
        cells_list = c[0].multiselect("Celle per λ", [12, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120], [60, 80, 100], key="oems_cl")
    else:
        cells_list = [c[0].select_slider("Celle per λ", [12, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120], 100, key="oems_cells",
                                         help="nel feed: 100 consigliato (quote entro ~λ/200); 20–40 solo come bozza")]
    sphere = c[1].checkbox("Sfera completa a f0", True, help="direttività vera, potenza irradiata, verifica BOR1", key="oems_sph")
    dump = c[2].checkbox("Salva il campo E (ParaView)", False, key="oems_dump")
    pad = c[3].select_slider("Aria attorno al feed (λ)", [0.25, 0.5, 0.75, 1.0], 0.5, key="oems_pad")
    c = st.columns(3)
    air = c[0].select_slider("Celle per λ in aria", [10, 15, 20, 30, 40, 60, "come nel feed"], 20, key="oems_air",
                             help="fuori dal feed la mesh si allarga gradualmente fino a questo valore: "
                                  "le quote del feed restano a piena risoluzione, RAM e tempo scendono molto")
    grading = c[1].select_slider("Gradazione mesh (rapporto tra celle vicine)", [1.2, 1.3, 1.4, 1.5], 1.4,
                                 key="oems_grad", help="più basso = transizione più dolce, più celle")
    sym = c[2].selectbox("Simmetria", [1, 2, 4], 0, key="oems_sym",
                         format_func={1: "modello intero", 2: "mezzo modello (parete PEC x = 0)",
                                      4: "quarto di modello (PEC + PMC, approssimato)"}.get,
                         help="feed a simmetria di rotazione eccitati in TE11: il mezzo modello dimezza RAM e tempo "
                              "con lo stesso risultato (entro 0.1 punti di efficienza); il quarto li divide per 4 ma "
                              "la parete PMC sposta il risultato di circa mezzo punto")
    sweep = None
    if mode == "Sweep di un parametro":
        tun = explore.TUNABLE.get(geo.kind)
        if not tun:
            st.info("Per questo feed lo sweep parametrico non è disponibile.")
            return
        labels = {k: lab for k, lab, _ in tun}
        key = st.selectbox("Parametro", list(labels), format_func=lambda k: labels[k], key="oems_par")
        base = float(geo.params[explore.PARAM_FROM_GEOM[key]])
        span = dict((k, s) for k, _, s in tun)[key]
        c = st.columns(3)
        lo = c[0].number_input("Da", value=round(base * (1 - span / 2), 3), key="oems_lo")
        hi = c[1].number_input("A", value=round(base * (1 + span / 2), 3), key="oems_hi")
        n = c[2].number_input("Valori", 2, 15, 5, key="oems_n")
        sweep = (key, labels[key], list(np.linspace(lo, hi, int(n))))
    f_lo, f_hi = f0 * (1 - bw / 100), f0 * (1 + bw / 100)
    ffs = list(np.linspace(f_lo, f_hi, nff)) if nff > 1 else [f0]

    def cfg_for(cells):
        return openems_sim.DeepConfig(f_lo=f_lo, f_hi=f_hi, cells_per_lambda=int(cells), end_db=float(end_db),
                                      ff_freqs=[float(x) for x in ffs], sphere=sphere, dump_fields=dump,
                                      threads=int(threads), pad_lambda=float(pad),
                                      air_cells_per_lambda=0 if air == "come nel feed" else int(air),
                                      grading=float(grading), symmetry=int(sym))

    plan = []                     # (label, geometry, config)
    if mode == "Sweep di un parametro" and sweep:
        k, lab, vals = sweep
        ov = dict(S.overrides.get(geo.kind, {}))
        for v in vals:
            g = geometry.build(geo.kind, f0, fD=float(S.get("fd_design") or dish.fD), wall=S.wall, **{**ov, k: float(v)})
            plan.append((f"{k}={v:.3f}", g, cfg_for(cells_list[0])))
    else:
        for cl in sorted(cells_list):
            plan.append((f"{cl} celle/λ" if mode != "Singola simulazione" else "", geo, cfg_for(cl)))
    if not plan:
        return
    est = [openems_sim.mesh_estimate(g, cf) for _, g, cf in plan]
    rows = [{"Simulazione": lab or "singola", "Celle (M)": f"{e['cells'] / 1e6:.2f}", "RAM ~": f"{e['ram_mb']:.0f} MB",
             "Durata stimata": _fmt_time(e["time_min"] * 60)} for (lab, _, _), e in zip(plan, est)]
    st.dataframe(rows, hide_index=True, width="stretch")
    tot = sum(e["time_min"] for e in est) * 60
    st.caption(f"Totale stimato ≈ {_fmt_time(tot)} su un PC desktop tipico (stima indicativa: dipende da CPU e memoria). "
               "Le simulazioni girano una dopo l'altra in background: puoi continuare a usare FeedLab o chiuderlo.")
    study = {"Singola simulazione": "", "Convergenza della mesh": "convergenza",
             "Sweep di un parametro": f"sweep {sweep[0] if sweep else ''}"}[mode]
    project = {"dish": {"kind": dish.kind, "D_mm": dish.D_mm, "fD": dish.fD}, "material": S.get("material")}
    c = st.columns(3)
    can_run = bool(env["py"])
    if c[0].button("▶️ Avvia in background", type="primary", disabled=not can_run, key="oems_go"):
        jobs = [openems_local.create_job(g, cf, label=lab, study=study, project=project) for lab, g, cf in plan]
        openems_local.start_batch(jobs, env["py"]["python"], env["inst"])
        st.success(f"Avviate {len(jobs)} simulazioni. Seguile in **Simulazioni**.")
    if not can_run:
        c[0].caption("Prima installa openEMS (sezione ①).")
    if c[1].button("📦 Solo script (per un altro PC)", key="oems_scripts"):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for i, (lab, g, cf) in enumerate(plan):
                jd = openems_local.create_job(g, cf, label=lab, study=study, project=project)
                for f in ("feed.json", "job.json", json.loads((jd / "job.json").read_text())["script"]):
                    z.write(jd / f, f"{jd.name}/{f}")
            z.writestr("LEGGIMI.txt", "Per ogni cartella: python -u sim_<feed>.py  (serve openEMS con i binding Python).\n"
                                      "Poi carica results.json in FeedLab, scheda Full-wave openEMS > Risultati.\n")
        S["oems_zip"] = buf.getvalue()
    if S.get("oems_zip"):
        with c[1]:
            _zn = _filenames.pick(st, f"openems_{geo.kind}_{f0:g}GHz", "oems_zip")
        c[1].download_button("Scarica gli script (.zip)", S["oems_zip"], file_name=f"{_zn}.zip")
    if can_run and c[2].button("🧊 Anteprima geometria (AppCSXCAD)", key="oems_prev"):
        d = openems_local.work_dir() / "_preview"
        p = openems_sim.make_deep_script(geo, d, plan[0][2])
        openems_local.preview_geometry(p, env["py"]["python"], env["inst"])
        st.info("Si apre AppCSXCAD con il modello (nessuna simulazione).")


# ================================================================== 3. jobs
def _jobs_section(S):
    jobs = openems_local.list_jobs()
    if any(j["state"] in ("running", "queued") for j in jobs):
        _jobs_live(S)
    else:
        _jobs_list(jobs)


@_auto("3s")
def _jobs_live(S):
    _jobs_list(openems_local.list_jobs())


def _jobs_list(jobs):
    if not jobs:
        st.info("Nessuna simulazione. Avviane una da **Nuova analisi**.")
        return
    st.caption(f"Cartella: `{openems_local.work_dir()}`")
    for j in jobs[:30]:
        c = st.columns([4, 2, 3, 2])
        name = j["label"] or j["kind"]
        c[0].markdown(f"**{j['kind']} {j['f_ghz']:g} GHz** · {name}" + (f" · _{j['study']}_" if j["study"] else "")
                      + f"  \n<small>{time.strftime('%d/%m %H:%M', time.localtime(j['created']))} · "
                        f"{j['cells_per_lambda']} celle/λ</small>", unsafe_allow_html=True)
        c[1].markdown(STATE_IT.get(j["state"], j["state"]))
        if j["state"] == "running":
            extra = f" · {j['energy_db']:.0f} dB" if j["energy_db"] is not None else ""
            c[2].progress(min(1.0, j["progress"]), text=f"{j['stage']}{extra} · resta {_fmt_time(j['eta_s'])}")
        elif j["state"] == "done":
            s = j["summary"]
            c[2].markdown(f"S11 {s.get('s11_f0_db', float('nan')):.1f} dB · D {s.get('Dmax_dbi', float('nan')):.1f} dBi · "
                          f"{_fmt_time(s.get('total_s'))}")
        elif j["state"] == "error":
            c[2].markdown(f"<small>{j['error'][:160]}</small>", unsafe_allow_html=True)
        with c[3].popover("⋯"):
            if j["state"] in ("running", "queued") and st.button("⏹️ Ferma", key="stop" + j["name"]):
                openems_local.stop_job(j["dir"])
            if st.button("📂 Apri cartella", key="open" + j["name"]):
                openems_local.open_folder(j["dir"])
            if j["state"] not in ("running", "queued") and st.button("🗑️ Elimina", key="del" + j["name"]):
                openems_local.delete_job(j["dir"])
            st.code(j["log_tail"][-1500:] or i18n.tr("(nessun log)"))


# ================================================================== 4. results
def _dish_inputs(S, dish, geo):
    with st.expander("Parabola e ricevitore per l'analisi", expanded=False):
        c = st.columns(4)
        kind = c[0].selectbox("Tipo", ["offset", "prime"], index=0 if dish.kind == "offset" else 1, key="da_kind")
        D = c[1].number_input("D (mm)", 50.0, 20000.0, float(dish.D_mm), key="da_D")
        fD = c[2].number_input("f/D (equivalente per offset)", 0.2, 2.0, float(dish.fD), 0.01, key="da_fD")
        elev = c[3].slider("Elevazione °", 1, 90, 30, key="da_el")
        c = st.columns(4)
        f = geo.f_ghz
        nf = c[0].number_input("NF LNA (dB)", 0.1, 20.0, 1.0 if f < 30 else 3.0 if f < 80 else 8.0, 0.1, key="da_nf")
        azen = c[1].number_input("Att. zenitale (dB)", 0.0, 10.0, 0.1 if f < 20 else 0.3 if f < 60 else 1.0, 0.05, key="da_az")
        rms = c[2].number_input("RMS superficie (mm)", 0.0, 3.0, 0.1, 0.01, key="da_rms")
        line = c[3].number_input("Perdita linea (dB)", 0.0, 10.0, 0.1, 0.05, key="da_line")
    ohm = 0.0
    if not isinstance(geo, geometry.RectHornGeometry):
        mat = materials.MATERIALS.get(S.get("material", ""), None)
        if mat:
            ohm = materials.feed_ohmic_loss_db(geo.staircase(wavelength_mm(f) / 10), f, mat)
    blk = geo.blockage_diameter() if kind == "prime" else 0.0
    return deep_analysis.DishSpec(kind, D, fD, elev, nf, azen, rms, line + ohm, block_diam_mm=blk)


def _results_section(S, geo, dish, polar_fig):
    done = [j for j in openems_local.list_jobs() if j["has_results"]]
    up = st.file_uploader("…oppure carica un results.json (da un altro PC)", type="json", key="oems_up")
    if up is not None:
        d = openems_local.work_dir() / "_uploaded" / time.strftime("%Y%m%d-%H%M%S")
        d.mkdir(parents=True, exist_ok=True)
        (d / "results.json").write_bytes(up.getvalue())
        S["oems_uploaded"] = str(d)
    opts = {j["dir"]: f"{j['kind']} {j['f_ghz']:g} GHz · {j['label']} · {j['study'] or 'singola'} · "
                      f"{time.strftime('%d/%m %H:%M', time.localtime(j['created']))}" for j in done}
    if S.get("oems_uploaded"):
        opts = {S["oems_uploaded"]: "results.json caricato", **opts}
    if not opts:
        st.info("Nessun risultato ancora. Le simulazioni completate compaiono qui.")
        return
    sel = st.multiselect("Simulazioni da analizzare (più di una = confronto)", list(opts), default=list(opts)[:1],
                         format_func=lambda k: opts[k], key="oems_sel")
    if not sel:
        return
    spec = _dish_inputs(S, dish, geo)
    try:
        results = [(opts[k], deep_analysis.load(k)) for k in sel]
    except Exception as e:
        st.error(f"Risultati non leggibili: {e}")
        return
    if len(results) > 1:
        _compare_view(results, spec)
        return
    label, r = results[0]
    rk = _key(r.path)
    st_ = _spec_tuple(spec)
    a = _analyze_cached(*rk, st_)
    for w in a["warnings"]:
        st.warning(w)
    s = a["s11"]
    d0 = a["f0_detail"]
    c = st.columns(3)
    c[0].metric("S11 a f0", f"{s['s11_f0_db']:.1f} dB", help=f"VSWR {s['vswr_f0']:.2f}")
    c[1].metric("Efficienza sulla parabola", f"{100 * d0['eta_total']:.1f} %")
    sph = a.get("sphere") or {}
    c[2].metric("Direttività del feed", f"{sph.get('D_dbi', a['per_freq'][0]['D_bor_dbi']):.2f} dBi")
    c = st.columns(3)
    c[0].metric("Guadagno", f"{d0['gain_dbi']:.2f} dBi")
    c[1].metric("G/T", f"{d0['g_over_t_db']:.2f} dB/K")
    c[2].metric("Centro di fase", f"{d0['phase_center']['d_mm']:+.2f} mm", help="+ = davanti all'apertura (verso il riflettore)")
    c = st.columns(3)
    c[0].metric("HPBW della parabola", f"{d0['hpbw_deg']:.3f}°", help="dal lobo full-wave del feed, per integrazione sull'apertura")
    c[1].metric("HPBW piano E / H", f"{d0['hpbw_E_deg']:.3f}° / {d0['hpbw_H_deg']:.3f}°")
    c[2].metric("Primo lobo laterale", f"{d0['sidelobe_db']:.1f} dB")

    fig = go.Figure(go.Scatter(x=r.freq_ghz, y=r.s11_db, name="openEMS"))
    fm = _fast_cached(*rk)
    if fm:
        fig.add_trace(go.Scatter(x=fm["freq_ghz"], y=fm["s11_db"], name="FeedLab rapido", line=dict(dash="dash")))
    for lvl in (-15, -20):
        fig.add_hline(y=lvl, line_dash="dot", line_color="gray")
    fig.update_layout(title="S11", xaxis_title="GHz", yaxis_title="dB", height=320)
    st.plotly_chart(fig, width="stretch")
    bw = lambda b: "—" if not b else f"{b['f_lo']:.3f}–{b['f_hi']:.3f} GHz ({b['pct']:.1f} %{'+' if b['beyond_sweep'] else ''})"  # noqa: E731
    st.caption(f"Banda S11 < −15 dB: {bw(s['bw15'])} · < −20 dB: {bw(s['bw20'])} · minimo {s['s11_min_db']:.1f} dB a "
               f"{s['f_min_ghz']:.3f} GHz" + (f" · Zin {s['zin_f0'].real:.0f}{s['zin_f0'].imag:+.0f}j Ω" if 'zin_f0' in s else ""))

    freqs = [ff.f_ghz for ff in r.ff]
    fsel = st.select_slider("Frequenza del lobo", freqs, value=min(freqs, key=lambda x: abs(x - r.f0)),
                            format_func=lambda x: f"{x:g} GHz", key="oems_fsel")
    ff = r.ff_at(fsel)
    c = st.columns(2)
    pp = ff.pattern()
    c[0].plotly_chart(polar_fig(pp, f"Lobo co-polare {fsel:g} GHz"), width="stretch")
    fig = go.Figure()
    ref = max(np.abs(pp.E).max(), np.abs(pp.H).max())
    for ph, col in ((0, "#d62728"), (45, "#2ca02c"), (90, "#1f77b4")):
        co, cr = ff.ludwig3(ph)
        fig.add_trace(go.Scatter(x=ff.theta, y=20 * np.log10(np.abs(co) / ref + 1e-12), name=f"co φ={ph}°", line=dict(color=col)))
        fig.add_trace(go.Scatter(x=ff.theta, y=20 * np.log10(np.abs(cr) / ref + 1e-12), name=f"cross φ={ph}°",
                                 line=dict(color=col, dash="dot")))
    fig.update_layout(title="Co/cross-polare (Ludwig-3)", xaxis_title="θ °", yaxis_title="dB", yaxis_range=[-50, 1], height=460)
    c[1].plotly_chart(fig, width="stretch")
    dp = _dish_cached(*rk, float(fsel), st_)
    ps = pp.shifted(dp["phase_center"]["d_lambda"])
    c = st.columns(2)
    fig = go.Figure()
    for v, nm, col in ((ps.E, "piano E", "#d62728"), (ps.H, "piano H", "#1f77b4")):
        fig.add_trace(go.Scatter(x=ps.theta_deg, y=np.degrees(np.angle(v * np.conj(v[0]))), name=nm, line=dict(color=col)))
    fig.update_layout(title=f"Fase riferita al centro di fase ({dp['phase_center']['d_mm']:+.2f} mm)", xaxis_title="θ °",
                      yaxis_title="°", xaxis_range=[0, 120], height=340)
    c[0].plotly_chart(fig, width="stretch")
    cv = dp["curve"]
    fig = go.Figure()
    for k, nm in (("total", "totale"), ("spill", "spillover"), ("illum", "illuminazione"), ("phase", "fase"), ("pol", "polarizz.")):
        fig.add_trace(go.Scatter(x=cv["fD"], y=100 * np.array(cv[k]), name=nm, line=dict(width=3 if k == "total" else 1.5)))
    fig.add_vline(x=spec.fD, line_dash="dash", line_color="gray")
    fig.update_layout(title=f"Efficienza vs f/D (ottimo {dp['best_fD']:.2f})", xaxis_title="f/D", yaxis_title="%",
                      yaxis_range=[40, 101], height=340)
    c[1].plotly_chart(fig, width="stretch")
    rows = [{"GHz": x["f_ghz"], "−10 dB E °": round(x["bw10_E"], 1), "−10 dB H °": round(x["bw10_H"], 1),
             "X-pol dB": round(x["xpol_peak_db"], 1), "F/B dB": round(x["fb_db"], 1), "D dBi": round(x["D_bor_dbi"], 2),
             "C. fase mm": round(x["pc_mm"], 2), "η %": round(100 * x["eta_total"], 1), "taper dB": round(x["edge_taper_db"], 1),
             "G dBi": round(x["gain_dbi"], 2), "G/T dB/K": round(x["g_over_t_db"], 2)} for x in a["per_freq"]]
    st.dataframe(rows, hide_index=True, width="stretch")
    e = d0["eff"]
    st.caption(f"A f0: spillover {100 * e['spillover']:.1f} % · illuminazione {100 * e['illumination']:.1f} % · fase "
               f"{100 * e['phase']:.1f} % · polarizzazione {100 * e['polarization']:.1f} % · bloccaggio {100 * e['blockage']:.1f} % · "
               f"T antenna {d0['t_ant']:.1f} K (cielo {d0['t_sky']:.1f} K) · spostamento del centro di fase in banda "
               f"{a['pc_spread_mm']:.2f} mm" + (f" · P irr./P acc. {sph['rad_eff']:.3f} · scostamento BOR1 {sph['bor_dev_db']:.2f} dB"
                                                if sph else "") + f" · mesh {(r.mesh.get('cells') or 0) / 1e6:.2f} M celle, "
               f"{_fmt_time(r.timing.get('total_s'))}")

    _dd = f"FeedLab_deep_{r.meta.get('kind')}"
    _dn = _filenames.pick(st, _dd, "oems_deep")
    c = st.columns(4)
    jd = Path(r.path).parent
    if c[0].button("📄 Report HTML", key="oems_rep"):
        S["oems_report"] = deep_analysis.html_report(r, a, spec, jd / "report.html").read_bytes()
    if S.get("oems_report"):
        c[0].download_button("Scarica il report", S["oems_report"], file_name=f"{_dn}.html",
                             mime="text/html")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for p in deep_analysis.export_csv(r, jd / "export") + deep_analysis.export_dat(r, jd / "export"):
            z.write(p, p.name)
    c[1].download_button("CSV + .dat W1GHZ", buf.getvalue(), file_name=(f"{_dn}_dati.zip" if _dn != _dd else f"openems_{r.meta.get('kind')}_dati.zip"))
    if c[2].button("↪️ Usa questo lobo nelle altre schede", key="oems_use"):
        S.fullwave = openems_sim.load_results(r.path)
        st.success("Lobo full-wave caricato: la scheda *Simulazione & S11* può usarlo al posto del modello rapido.")
    if c[3].button("📂 Apri cartella", key="oems_open_res"):
        openems_local.open_folder(jd)


def _compare_view(results, spec):
    rows = _compare_cached(tuple((lab, r.path, _key(r.path)[1]) for lab, r in results), _spec_tuple(spec))
    table = [{"Simulazione": r["label"].split(" · ")[1] if " · " in r["label"] else r["label"],
              "celle/λ": r["cells_per_lambda"], "M celle": round(r["cells_M"], 2), "min": round(r["time_min"], 1),
              "S11 f0 dB": round(r["s11_f0_db"], 1), "S11 peggiore dB": round(r["s11_max_band_db"], 1),
              "D dBi": round(r["D_dbi"], 2), "η %": round(100 * r["eta"], 1), "C. fase mm": round(r["pc_mm"], 2),
              "X-pol dB": round(r["xpol_db"], 1), "G dBi": round(r["gain_dbi"], 2), "G/T": round(r["g_over_t_db"], 2)}
             for r in rows]
    st.dataframe(table, hide_index=True, width="stretch")
    if len({r["cells_per_lambda"] for r in rows}) == len(rows):
        conv = deep_analysis.convergence([dict(r) for r in rows])
        if conv["ok"] is True:
            st.success("Mesh convergente: tra le due mesh più fitte D cambia < 0.1 dB, η < 0.5 %, S11 < 2 dB.")
        elif conv["ok"] is False:
            st.warning("Mesh non ancora convergente: aggiungi una simulazione con più celle per λ.")
    fig = go.Figure()
    for label, r in results:
        fig.add_trace(go.Scatter(x=r.freq_ghz, y=r.s11_db, name=label.split(" · ")[1] if " · " in label else label))
    fig.update_layout(title="S11 a confronto", xaxis_title="GHz", yaxis_title="dB", height=360)
    st.plotly_chart(fig, width="stretch")
    best = max(rows, key=lambda r: r["g_over_t_db"])
    st.info(f"G/T migliore: **{best['label']}** ({best['g_over_t_db']:.2f} dB/K, η {100 * best['eta']:.1f} %).")


# ================================================================== entry point
def render(S, geo, polar_fig):
    st.header("Deep analysis full-wave con openEMS (opzionale)")
    st.caption("FeedLab funziona anche senza openEMS: le altre schede usano il simulatore rapido (secondi). openEMS (FDTD, "
               "gratuito) serve solo se vuoi un'analisi di riferimento: una simulazione richiede da alcuni minuti a ore, "
               "per questo la avvii tu, quando serve, e gira in background.")
    dish = S.dish or wizard.dish_from_prime(600, 0.6)
    t = st.tabs(["① Installazione openEMS", "② Nuova analisi", "③ Simulazioni", "④ Risultati", "⑤ Space mapping"])
    with t[0]:
        _install_section(S)
    with t[1]:
        _new_section(S, geo, dish)
    with t[2]:
        _jobs_section(S)
    with t[3]:
        _results_section(S, geo, dish, polar_fig)
    with t[4]:
        _spacemap_section(S, geo, dish)


# ================================================================== 5. space mapping
def _sm_cfg(f0, cells):
    return openems_sim.DeepConfig(f_lo=f0 * 0.95, f_hi=f0 * 1.05, cells_per_lambda=int(cells), ff_freqs=[float(f0)],
                                  sphere=False, n_freq=101)


def _sm_launch(study: spacemap.SMStudy, pt: spacemap.SMPoint, env, cells: int):
    g = geometry.build(study.kind, study.f_ghz, fD=study.fD_design or study.sc.fD, wall=study.wall, **pt.over)
    i = study.points.index(pt)
    jd = openems_local.create_job(g, _sm_cfg(study.f_ghz, cells), label=f"SM {study.id} #{i}",
                                  study=f"space mapping {study.id}")
    pt.job = str(jd)
    study.save(openems_local.work_dir())
    openems_local.start_batch([jd], env["py"]["python"], env["inst"])


def _sm_fullwave(study):
    def fw(p):
        if not p.job:
            return None
        js = openems_local.job_state(p.job)
        if js["state"] == "done":
            return spacemap.fullwave_metrics(Path(p.job) / "results.json", study, p.over)
        if js["state"] in ("error", "stopped", "interrotto"):
            raise RuntimeError(f"simulazione {js['state']}: {js['error'][:200]}")
        return None
    return fw


def _sm_advance(study, env, cells):
    try:
        pt = spacemap.step(study, fullwave=_sm_fullwave(study))
    except RuntimeError as ex:
        study.status, study.note = "errore", str(ex)
        study.save(openems_local.work_dir())
        return
    study.save(openems_local.work_dir())
    if pt is not None and env["py"]:
        _sm_launch(study, pt, env, cells)


def _spacemap_section(S, geo, dish):
    st.markdown("Il **modello rapido** esplora, **openEMS** verifica pochi candidati e le differenze **correggono** il "
                "modello rapido, che viene ottimizzato di nuovo. Si ripete finché il risultato full-wave smette di migliorare "
                "(space mapping). Ogni iterazione è una simulazione openEMS in background.")
    env = _env_state(S)
    kind = geo.kind
    if kind not in geometry.MODEMATCH_OK or kind not in explore.TUNABLE or isinstance(geo, geometry.RectHornGeometry):
        st.info("Lo space mapping usa il modello rapido: disponibile per guida aperta, W2IMU, Skobelev, Pickett-Potter, conico.")
    else:
        c = st.columns(4)
        objective = c[0].selectbox("Obiettivo", list(explore.OBJECTIVES), format_func=lambda k: explore.OBJECTIVES[k],
                                   index=1, key="sm_obj")
        keys = c[1].multiselect("Quote da ottimizzare", [k for k, _, _ in explore.TUNABLE[kind]],
                                default=[k for k, _, _ in explore.TUNABLE[kind]][:2], key="sm_keys",
                                format_func=lambda k: dict((a, b) for a, b, _ in explore.TUNABLE[kind])[k])
        cells = c[2].select_slider("Celle per λ", [15, 20, 25, 30, 40, 60, 80, 100], 100, key="sm_cells")
        max_iter = c[3].slider("Simulazioni openEMS massime", 2, 8, 5, key="sm_max")
        c = st.columns(3)
        tol_mm = c[0].number_input("Convergenza: variazione quote < (mm)", 0.001, 0.2, 0.01, 0.005, format="%.3f", key="sm_tol")
        s11_lim = c[1].slider("S11 massimo (dB)", -30, -10, -18, key="sm_s11")
        auto = c[2].checkbox("Avanza da solo a fine simulazione", True, key="sm_auto",
                             help="quando la scheda è aperta, FeedLab controlla ogni 10 s e lancia il candidato successivo")
        est = openems_sim.mesh_estimate(geo, _sm_cfg(geo.f_ghz, cells))
        st.caption(f"Ogni simulazione ≈ {_fmt_time(est['time_min'] * 60)}, RAM ≈ {est['ram_mb']:.0f} MB; "
                   f"in totale al massimo {max_iter} simulazioni.")
        if st.button("▶️ Avvia space mapping", type="primary", disabled=not env["py"] or not keys, key="sm_go"):
            sc = explore.Scenario(dish.kind, dish.D_mm, dish.fD, material=S.get("material", "Ottone CuZn39Pb3"))
            with st.spinner("Punto di partenza…"):
                study = spacemap.new_study(kind, geo.f_ghz, sc, objective, keys, dict(S.overrides.get(kind, {})),
                                           S.wall, None, s11_lim, tol_mm, max_iter)
                study.note = "auto" if auto else ""
                _sm_launch(study, study.points[0], env, cells)
            st.success("Prima simulazione avviata: segui l'avanzamento qui sotto e in **Simulazioni**.")
        if not env["py"]:
            st.caption("Prima installa openEMS (sezione ①).")
    st.divider()
    _sm_studies(S, env)


@_auto("10s")
def _sm_studies(S, env):
    studies = spacemap.list_studies(openems_local.work_dir())
    if not studies:
        st.info("Nessuno studio di space mapping.")
        return
    cells = S.get("sm_cells", 100)
    for study in studies[:10]:
        if study.status == "in corso" and study.note == "auto":
            last = study.points[-1]
            if last.job and openems_local.job_state(last.job)["state"] in ("done", "error", "stopped", "interrotto"):
                _sm_advance(study, env, cells)
        best = spacemap.best_point(study)
        with st.expander(f"{study.kind} {study.f_ghz:g} GHz · {explore.OBJECTIVES[study.objective]} · {study.status} · "
                         f"{sum(1 for p in study.points if p.fw)} simulazioni", expanded=study is studies[0]):
            rows = []
            x0 = study.x0()
            for i, p in enumerate(study.points):
                stt = openems_local.job_state(p.job)["state"] if p.job else "—"
                r = {"#": i}
                for k in study.keys:
                    r[k] = f"{p.over.get(k, x0[k]):.3f}"
                r["Obiettivo rapido"] = f"{p.fast['objective']:.2f}"
                r["Obiettivo openEMS"] = f"{p.fw['objective']:.2f}" if p.fw else STATE_IT.get(stt, stt)
                r["Δ openEMS − rapido"] = f"{p.fw['objective'] - p.fast['objective']:+.2f}" if p.fw else ""
                r["η openEMS"] = f"{100 * p.fw['eta']:.1f} %" if p.fw else ""
                r["S11 openEMS"] = f"{p.fw['s11_db']:.1f} dB" if p.fw else ""
                rows.append(r)
            st.dataframe(rows, hide_index=True, width="stretch")
            if study.note and study.note != "auto":
                st.warning(study.note)
            c = st.columns(3)
            if study.status == "in corso" and study.note != "auto":
                last = study.points[-1]
                ready = last.job and openems_local.job_state(last.job)["state"] == "done"
                if c[0].button("➡️ Iterazione successiva", disabled=not ready, key="smn" + study.id):
                    with st.spinner("Correzione del modello rapido e nuovo candidato…"):
                        _sm_advance(study, env, cells)
            if best is not None and c[1].button("✅ Applica il migliore al progetto", key="sma" + study.id):
                S.overrides[study.kind] = {k: v for k, v in best.over.items()}
                for k, v in best.over.items():
                    S[f"lab_{study.kind}_{k}"] = float(v)
                st.success("Quote applicate: le trovi in Progetto feed e Laboratorio.")
            if best is not None:
                c[2].caption(f"Migliore verificato full-wave: {best.fw['objective']:.2f} "
                             f"(η {100 * best.fw['eta']:.1f}%, S11 {best.fw['s11_db']:.1f} dB)")
