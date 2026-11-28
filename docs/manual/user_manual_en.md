# FeedLab — User Manual

**Microwave feed / illuminator design laboratory, 10–134 GHz**
Version {VERSION} BETA TEST · Software designed by Ivan De Cesaris, IZ0JNY

---

## Contents

1. What FeedLab does — and what it does not
2. Installing, starting and updating
3. The screen at a glance
4. The sidebar, field by field
5. Step 1 — Guided procedure (dish, goal, illumination)
6. Step 2 — Feed design
7. Step 3 — Laboratory (variants, noise, optimisation, tolerances)
8. Step 4 — Simulation & S11
9. 3D pattern and 3D model
10. Step 5 — Feed + matching plate assembly
11. Step 6 — WR plate (λ/4 matching plate)
12. Step 7 — Drawing & STEP (PDF, STEP, STL)
13. Full-wave openEMS (optional)
14. Project outputs (PDF, tables, project file)
15. Reference tables: materials, tolerances, flanges, screws, counterbores
16. Worked example: a 24 GHz EME feed for a 2.4 m offset dish
17. Troubleshooting and FAQ
18. Glossary

---

## 1. What FeedLab does — and what it does not

FeedLab designs **dish feeds** (the "illuminator" at the focus of a parabolic reflector) for the amateur microwave bands from **10 to 134 GHz**, and produces everything the workshop needs to make them.

**FeedLab does:**

- pick the most suitable feed for **your** dish (commercial catalogue or measured dish), your goal (TX gain, RX G/T, EME) and your tools (lathe/CNC or sheet metal);
- design the feed for the **illumination you choose** (edge taper in dB) and compute all inner dimensions from the published design rules (W1GHZ, OE2IGL, Skobelev, IZ0JNY…);
- simulate the feed in seconds with a **mode-matching** solver: S11, aperture modes, radiation pattern with its −10 dB angle, phase centre, dish efficiency, gain, system temperature and G/T;
- let you change any dimension and see immediately whether the result is better or worse (**Laboratory**), optimise automatically and check **machining tolerances**;
- design the **λ/4 matching plate** from the feed's circular waveguide to the rectangular WR waveguide, and **how feed and plate are fixed** to the external waveguide (holes, threads, counterbores, screws, alignment pins);
- produce a **dimensioned PDF drawing**, a **STEP** file for CAD/CAM and an **STL** for 3D printing, for the feed and for the plate;
- prepare and analyse a **full-wave openEMS** simulation (optional) for a reference check.

**FeedLab does not:**

- replace measurements: the results are *design estimates*. Real dishes are typically 12–15 efficiency points below the calculated value (W1GHZ, WD5AGO);
- cover feeds below 10 GHz (e.g. 1296 MHz septum feeds);
- simulate ring/slot feeds (VE4MA, Chaparral, Axial Corrugated) with the fast solver: for those it uses the author's published efficiency and recommends openEMS.

> **Rule of thumb.** Use the fast solver to *choose and tune*, openEMS to *confirm* a new or heavily modified design, and a sun-noise or return-loss measurement to *verify* the real part.

---

## 2. Installing, starting and updating

### 2.1 Windows (recommended)

1. Open the GitHub **Releases** page of the repository **IZ0JNY/FeedLab** and download the latest version.
2. Choose one of the two packages:
   - **Installer** `FeedLab-Setup-x.y.z.exe` — no administrator rights needed; FeedLab appears in the Start menu ("FeedLab" and "FeedLab (in the browser)"). You choose the **language** during installation.
   - **Portable** `FeedLab-x.y.z-portable.zip` — extract to any folder and double-click `FeedLab.bat`. Nothing is installed; the language follows Windows (change it in the sidebar).
3. Optional: check the download against `SHA256SUMS.txt` published with the release.

Until the installer is digitally signed, **Windows SmartScreen** may say "Windows protected your PC": click **More info → Run anyway**.

FeedLab opens in its own window (Microsoft Edge WebView2, part of Windows 11). If WebView2 is missing it opens in your browser.

**Installing a new version over an old one** updates the existing installation in place: same folder, same Start-menu entries. Your simulations and settings (in *Documents\FeedLab* and the openEMS folder) are kept.

### 2.2 Linux / macOS (from source)

```
pip install -e .
feedlab-gui
```

### 2.3 New versions

At every start FeedLab asks GitHub for the latest release. If a newer version exists, a **window opens** with **what's new** (in your language) and a **Download** button. You can also press **🔄 Check for updates** in the sidebar at any time: it shows the new version, "You already have the latest version", or the exact reason why GitHub could not be reached.

The certificate of GitHub is checked by **Windows itself**, like the browser does, so the check also works when an antivirus inspects HTTPS connections. No personal data is sent.

> Versions **0.4.17 and 0.4.18** could not always reach GitHub: if you have one of them, install the current version by hand once.

---

## 3. The screen at a glance

![FeedLab at start-up: nothing is preselected]({IMG}/m01_start.jpg)

The window has two parts:

- the **sidebar** on the left: band, material, waveguide, feed base, and the buttons for language, credits, updates, manual and bug reports;
- the **tabs** at the top, used from left to right:

| Tab | What you do there |
|---|---|
| 🧭 **Guided procedure** | choose dish, goal, tools and illumination; FeedLab ranks the suitable feeds |
| 📐 **Feed design** | see and edit all dimensions of the chosen feed; wall and base thickness; CNC outer profile |
| 🎛️ **Laboratory** | try variants, see the change in S/N, the system-noise budget, sensitivity, optimisation, tolerances |
| 📈 **Simulation & S11** | S11 over the band, aperture modes, pattern with −10 dB angle, dish efficiency, phase centre, G/T |
| 🌐 **3D pattern** | 3D radiation pattern of the feed |
| 🧊 **3D model** | 3D model of the feed with its drilled base |
| 🔩 **Feed + matching plate assembly** | how feed and plate are fixed to the external waveguide: scheme, section, holes, screws, live 3D |
| 🔲 **WR plate** | λ/4 matching plate to the WR waveguide: aperture, thickness, views, PDF and STEP |
| 📄 **Drawing & STEP** | PDF drawing, STEP, STL, general tolerance |
| 🖥️ **Full-wave openEMS** | optional full-wave check (install, run, results, space mapping) |
| ℹ️ **Credits** | author, licence, contributors and all technical sources |

**At start-up nothing is preselected.** Until you choose **frequency**, **material**, **dish** and **feed type**, the tabs show a short message telling you what is missing and where to choose it.

---

## 4. The sidebar, field by field

![Sidebar at start-up]({IMG}/m02_sidebar_blank.jpg)

![Sidebar after choosing band and material]({IMG}/m03_sidebar.jpg)

| Field | What it is | Notes |
|---|---|---|
| **Band** | operating frequency | amateur bands 10.368, 24.048, 47.088, 76.032, 122.25, 134.928 GHz, or **Other frequency…** (10–140 GHz) |
| **λ** | free-space wavelength | all "λ" values in FeedLab refer to it |
| **Dish / Feed** | summary of the dish and feed you chose | appears once chosen |
| **ℹ️ About materials** | button above the material choice | opens a comparison table: conductivity, roughness, density, losses relative to copper, and coloured-dot ratings (red = poor … green = excellent) for machinability, price, availability, weather resistance and treatments, with the pros and cons of each material. The chosen material is highlighted in yellow |
| **Feed material** | metal (or coating) of the feed | sets conductivity σ and roughness → ohmic loss and the noise the feed adds; below: σ, **skin depth δ** at your frequency and a practical note (§15.1) |
| **Rectangular waveguide** | the WR guide the feed is fixed to through the λ/4 plate | only the guides of the band: 10 GHz **WR-90** or **WR-75**, 24 GHz **WR-42**, 47 GHz **WR-22** or **WR-19**… It sizes plate, drilling and square base |
| **Feed base** | **Circular** or **Square** | square (default at 10 and 24 GHz) only for square standard flanges (WR-90 41.40 mm, WR-75 38.30 mm, WR-42 22.41 mm); it grows by itself if holes or counterbores need it |
| **Language** | Italiano / English | chosen in the installer; here mainly for the portable version |
| **ℹ️ Credits · 🔄 Check for updates · 📖 Manual · 🐞 Report a problem** | author and sources · new versions · this manual · pre-filled GitHub issue | |


![About materials]({IMG}/m34_materials.jpg)

---

## 5. Step 1 — Guided procedure

![Guided procedure with a catalogue dish]({IMG}/m04_wizard.jpg)

Three columns: **dish** (left), **options** (centre), **dish summary** (right: equivalent f/D, opening angle, diameter in λ, HPBW, gain at 60 %, Ruze loss for the surface accuracy you enter).

### 5.1 Dish

**Commercial catalogue (datasheets)** — choose **Manufacturer** and **Model** (alphabetical). Under the model you see the **source** of every figure and a table: type (offset/prime), outer size, active area, maker's f/D, focal length (and where it comes from), offset angle, required illumination, declared efficiency, gains, LNB collar, material. Tick **I measured my dish** to enter long axis, short axis and depth at the centre: measurements are more accurate than many datasheets. If the **focal length is not published**, the table says so: stretch a string across the rim along the long axis and measure the maximum depth.

**Custom dish**

![Custom dish]({IMG}/m09_custom.jpg)

| Dish type | Data you can give |
|---|---|
| **Offset (TV/sat)** | diameter + f/D · reflector measurements (long axis, short axis, depth) · diameter + focal length · diameter + required illumination angle |
| **Prime focus** | diameter and f/D, or diameter and depth at the centre |

### 5.2 Options

![Options and dish illumination]({IMG}/m05_wizard_options.jpg)

| Field | Choices | What it changes |
|---|---|---|
| **Polarisation** | Linear / Circular | circular adds a polariser (septum or dielectric) to the advice; the rectangular horn is excluded |
| **Goal** | Maximum gain (TX/terrestrial) · **Maximum G/T (RX, EME, sun)** — default · Maximum RX performance (minimum noise) | G/T and RX design the feed for a slightly larger f/D (softer edge illumination: less spillover and ground noise); RX also favours feeds with low side and back lobes |
| **Workshop tools** | Lathe/CNC · Sheet metal and soldering only | sheet metal favours open waveguide, rectangular horn and W2IMU |
| **Estimate with the fast simulation** | on/off | runs the mode-matching solver on every candidate (~20 s) |
| **Dish illumination** | **Automatic (recommended)** · Edge taper chosen by me | see 5.3 |
| **Edge taper (dB)** | 6–25 dB, default **10 dB** | active with "Edge taper chosen by me" |

### 5.3 Dish illumination

![Automatic illumination]({IMG}/m06_illum_auto.jpg)

The **edge taper** is how much weaker the signal is at the rim of the dish than at the centre (feed pattern + extra path from focus to rim).

- **Automatic**: the feed is designed for the chosen goal; the panel shows the resulting taper (e.g. about 12.8 dB on an f/D 0.69 dish for G/T).
- **Edge taper chosen by me**: you set the taper; FeedLab designs the feed for the f/D that gives it.

**The illumination really changes the feed:** every tab builds the feed for the resulting *design f/D*, updated at once when you move the taper. Feed design shows it: "Designed for f/D 0.65: edge taper 10.0 dB on the dish (f/D 0.69)".

![Edge taper chosen by the user]({IMG}/m07_illum_taper.jpg)

The panel shows the **illumination across the diameter** (with the −3 dB and −10 dB lines), the **illuminated dish** in 3D (light = more signal, −3/−10 dB rings, feed at the focus and illumination cone), **spillover**, **illumination (taper) efficiency**, their product, the **surface within −3 and −10 dB** and the **design f/D**.

| Edge taper | Typical use |
|---|---|
| 8–10 dB | maximum gain, terrestrial TX; more spillover |
| 10–12 dB | classic optimum: about 81–82 % (spillover × taper) |
| 12–16 dB | more G/T: EME and RX, less ground noise, slightly less gain |
| > 16 dB | very soft: much of the surface is wasted |

(Model: cos^q feed pattern, Balanis/Kildal; offset dishes as the equivalent circular aperture; blockage, phase errors and losses are in the Simulation tab.)

### 5.4 Find the best feed

Press **🔎 Find the best feed**: FeedLab ranks the feeds that suit dish, goal, tools and illumination.

![Ranking of the candidate feeds]({IMG}/m08_results.jpg)

| Column | Meaning |
|---|---|
| **η estimated %** | efficiency on your dish (illumination × spillover × phase × cross-pol × blockage) |
| **Feed's optimum f/D** | where this feed would be best |
| **Size Ø mm** | blockage diameter (prime focus) |
| **Why / Warning** | reasons for the choice, limits (e.g. "check with openEMS") |

Choose the feed in **Feed to design** and press **➡️ Use this feed**. You can also choose any feed directly in Feed design.

### 5.5 Feed types

| Feed | Range of use | Notes |
|---|---|---|
| **Axial Corrugated Feedhorn CT1DMK**, parametric calculation OE2IGL | 10–76 GHz, f/D 0.33–0.9 (offset ≤ 0.8) | 81–86 %; 8 axial steps (OE2IGL v1.4); openEMS for verification |
| **Chaparral 3 rings** | prime focus f/D < 0.33 | 78 % at f/D 0.35; openEMS |
| **Conical horn** | general purpose | simple, wide band |
| **Dual-Flare, IZ0JNY** | f/D 0.6–0.9, EME | step + cone + phasing cylinder + second cone; low antenna temperature, very low S11; checked with openEMS at 24 GHz |
| **Dual-mode "optimum" Skobelev** | f/D > 0.9 | verify full-wave before building |
| **Large W2IMU flare 30°** | offset f/D 0.65–0.85, 47–241 GHz | +1.6…2.3 dB of sun noise on offset dishes (W1GHZ 2024) |
| **Open circular waveguide** | small deep dishes | minimal blockage, poor F/B |
| **Pickett-Potter** | f/D 0.5–0.95, also above 76 GHz | ~80 % (OE2IGL) |
| **Rectangular horn** | linear polarisation, < 40 GHz | sheet metal, directly from WR |
| **VE4MA / Super-VE4MA** | prime focus f/D 0.35–0.45 | choke ring; openEMS |
| **W2IMU dual-mode / W2IMU Dual-Mode Feedhorn**, parametric calculation OE2IGL | offset / f/D 0.5–0.95 | W1GHZ rules / OE2IGL parametric calculation from the opening angle |

Feeds optimised with openEMS for one specific f/D are not in the list: they are **project files** in `fdtd/results/feedlab/` (for f/D 0.4 at 10 and 24 GHz, 3 and 3.7 m dishes: corrugated 83.5 %, Chaparral 80.1 %, VE4MA 80.3 %, W2IMU 73.5 %). Open them with **📂 Open project**: feed, dish and dimensions are already set. A 0.4.28 project saved with "Feed 0.4 f/D" opens as an Axial Corrugated with its dimensions.

---

## 6. Step 2 — Feed design

![Feed design]({IMG}/m10_design.jpg)

| Field | Meaning |
|---|---|
| **Feed type** | all feeds, alphabetical |
| **Wall thickness (mm)** | metal wall of the horn |
| **Feed base thickness (mm)** | empty = **automatic** (what holes and threads need); minimum 1 mm; thread and screw lengths follow it |
| **Inner dimensions** | depend on the feed; each field shows the name of the dimension in your language and the code used on the section (e.g. «cone length · flare_length»); **lengths blue, diameters green, flare angles red** |
| **input_length** | lengthens the straight input guide (longer feed, same performance) |
| **Flare angles** | changing an angle recomputes the cone length; diameters stay |
| **Apply changes / Reset design** | **every** change — wall and base thickness included — is applied only with **Apply changes**; Reset goes back to the rule's dimensions |

On the right: the **axial section** with every dimension, total length, overall diameter, **recommended tolerance**, the design-rule notes and the line **"Designed for f/D …"** (from the illumination, §5.3). The holes of the base are chosen in the **🔩 Assembly** tab (§10).

![Dimensions and buttons]({IMG}/m12_dims.jpg)

> **openEMS reminder.** If you change a dimension by more than 5 % or an angle by more than 2°, a note suggests checking the feed with openEMS. It is only advice.

### 6.1 CNC machining of the outside (optional)

![CNC options]({IMG}/m11_cnc.jpg)

| Field | Choices | Effect |
|---|---|---|
| **Outer profile** | Constant wall · Option 1: solid up to the end of the 1st cone · Option 2: outside without recesses | simpler and cheaper to turn/mill; only outside metal is added |
| **Outer fillet radius (mm)** | 0 = sharp | rounds outer edges; reduced where the wall would get too thin. The **inside never changes** |

---

## 7. Step 3 — Laboratory

![Laboratory]({IMG}/m13_lab.jpg)

### 7.1 Use case

| Field | Meaning |
|---|---|
| **Goal** | TX — maximum gain · RX — maximum G/T · EME — gain + G/T |
| **Elevation** | antenna elevation (ground noise) |
| **NF LNA (dB)** | noise figure of the preamplifier |
| **Feed→LNA/PA line loss (dB)** | waveguide/relay loss before the LNA |
| **Surface RMS (mm)** | dish surface accuracy (Ruze) |
| **Zenith att. (dB)** | atmospheric attenuation at zenith |

### 7.2 Result and noise budget

![Result compared with the starting design, Tsys]({IMG}/m14_lab_result.jpg)

Move the dimension sliders: FeedLab recomputes **Δ S/N**, efficiency, gain, **G/T**, antenna temperature, S11 and edge taper.

| Goal | Δ S/N |
|---|---|
| TX | ΔG |
| RX | Δ(G/T) |
| EME | ΔG + Δ(G/T) |

Under the figures:

- the **ohmic loss** of the feed in the chosen material and the noise it adds;
- the **system temperature**: **Tsys = antenna temperature attenuated by the losses + noise of the losses (feed + line) + preamplifier**, and G/T = G − 10·log10(Tsys). Example at 10 GHz: with NF 1 dB the preamplifier adds 75 K, with 2 dB 170 K; on a cold dish (antenna ~20–40 K) Tsys almost doubles and G/T drops by about 2.5–3 dB — this is why a good LNA matters so much;
- spillover, illumination, phase, polarisation, blockage and phase-centre position.

The **pattern** (variant solid, design dashed) shows the **−10 dB points** of the E and H planes and the **dish rim**, with the angles in the subtitle (e.g. "−10 dB: 66.3° (E) / 71.3° (H) · dish: 79.6°"). The **efficiency vs f/D** chart has ticks every **0.1** and a dotted line at your dish.

### 7.3 Advice, sensitivity, optimisation

![Advice]({IMG}/m15_lab_advice.jpg)

- **💡 Advice** in plain language; **✅ Apply these dimensions to the design** copies the variant to Feed design.
- **🔬 Sensitivity**: how much the result changes when each dimension changes.
- **🤖 Automatic optimisation**: choose dimensions, number of evaluations and maximum S11.

![Optimisation]({IMG}/m16_lab_opt.jpg)

### 7.4 Fabrication tolerances and yield

![Tolerances]({IMG}/m17_lab_tol.jpg)

| Field | Meaning |
|---|---|
| **Machining tolerance ± (mm)** | the workshop tolerance |
| **Distribution** | Uniform within ±t (conservative) · Normal with ±t = 3σ (capable CNC) |
| **Allowed loss (dB) / Maximum S11 (dB)** | what is still acceptable |
| **🎲 Analyse tolerances** | Monte Carlo: **yield**, mean loss, spread, worst S11, **critical dimensions** with the tolerance each needs |
| **📄 Use these tolerances in the PDF drawing** | adds the table to the drawing |
| **🛡️ Robust optimisation** | dimensions that stay good within the tolerances (mean − k·σ) |

---

## 8. Step 4 — Simulation & S11

![Simulation]({IMG}/m18_sim.jpg)

| Control / result | Meaning |
|---|---|
| **Analysis band ± %, frequency points, modes** | sweep and solver accuracy |
| **S11 at the TE11 input** | return loss over the band (the WR transition is not included) |
| **Mode content at the aperture** | TE11, TM11, TE12 relative to TE11 (Pickett-Potter/Skobelev: TM11 ≈ 15 %, WA6KBL) |

![Pattern with the −10 dB angle]({IMG}/m19_sim_pattern.jpg)

The **feed pattern** shows the E and H planes, the **−10 dB points** (diamonds) and the **dish rim** (green dotted), with "−10 dB: …° (E) / …° (H) · dish: …°" under the title. If the −10 dB angle is close to the dish opening, the edge taper is about 10 dB plus the space attenuation.

![Dish efficiency vs f/D]({IMG}/m20_sim_eff.jpg)

| Result | Meaning |
|---|---|
| **Dish efficiency vs f/D** | total, spillover, illumination, phase, cross-pol; ticks every 0.1; dotted line = your dish |
| **η on your dish, edge taper, feed's optimum f/D, phase centre** | the key numbers |
| **Dish HPBW, E/H HPBW, first sidelobe** | from the illumination of this feed |
| **G/T expander** | elevation, receiver NF, zenith attenuation → sky, antenna and receiver temperature, **Tsys** and G/T, with the effect of 1 dB more NF |

---

## 9. 3D pattern and 3D model

![3D pattern]({IMG}/m21_lobe3d.jpg)

![3D model]({IMG}/m22_model3d.jpg)

**3D pattern**: normalised radiation pattern (dynamic range adjustable). **3D model**: the real solid of the STEP/STL, with the drilled base; *Quarter cut* shows the inside.

---

## 10. Step 5 — Feed + matching plate assembly

This tab decides **how the feed and the λ/4 plate are fixed to the external waveguide section** (the WR-90, WR-75 or WR-42 flange of your relay or LNA, or a round MIL flange from 47 GHz). The plate and the feed base always get the **same hole pattern as the standard flange**, at the same positions.

### 10.1 Choose the scheme

| Scheme | How it is assembled | What FeedLab sets |
|---|---|---|
| **Screws from the feed side** | the screws go in from the feed side, head in a counterbore of the base, through base and plate into the waveguide flange | through holes in base and plate (flange Ø rounded up to the tenth: WR-42 3.07 → 3.1), counterbore in the base |
| **Screws from the waveguide side** | the waveguide screws pass through flange and plate and screw into the base | threaded through holes in the base (24 GHz M3, 10 GHz M4…), through holes in the plate |
| **Plate screwed to the feed base with counterbored screws (waveguide screwed into the plate)** | the waveguide screws into the plate; 4 socket-head screws (WR-42: M2.5) in counterbores of the plate fix it to the base | flange holes threaded M3 6H in the plate, 4 plate→feed screws on the axes (WR-42: at 9.00 mm), blind tapped holes in the feed |
| **From 47 GHz: screws from the feed side + pins / waveguide screws threaded in the base + pins** | round MIL flange; the flange dowels align the stack | through or threaded (4-40) holes, alignment-pin holes in plate and base |
| **No holes** | fixing up to you | nothing |

![Screws from the feed side]({IMG}/m23_mount_feedside.jpg)

On the right, the **cross-section** of the stack (external waveguide flange | plate | feed base | feed) shows where screws, threads and counterbores are.

![Screws from the waveguide side]({IMG}/m24_mount_guideside.jpg)

![Plate screwed to the feed base with counterbored screws (waveguide screwed into the plate)]({IMG}/m25_mount_plate.jpg)

### 10.2 Advanced: every detail

Open **⚙️ Advanced: holes, threads, counterbores, screws, plate**. Each scheme keeps its own settings.

![Advanced menu]({IMG}/m26_mount_adv.jpg)

| Field | Default | Limits / notes |
|---|---|---|
| **Feed-base hole Ø** | flange hole rounded up (WR-42 3.1) | from screw size + 0.1 to the largest Ø that leaves **1 mm of metal** to the nearest edge |
| **Thread of the base holes** | 10 GHz M4 (or M3), 24 GHz M3 (M2.5, M2); UNC equivalents; MIL 4-40 | threaded through the whole base |
| **Counterbore for the screw head (base)** | on for "screws from the feed side" | Ø and depth editable (M3: 6.5 × 3.1); the base thickens to counterbore + 1.5 mm |
| **Flange holes threaded in the plate** | on for the IZ0JNY scheme | 6H |
| **Plate flange-hole Ø** | as the base | 1 mm rule |
| **4 plate → feed screws** | on for the IZ0JNY scheme | 24 GHz M2.5 or M2, 10 GHz M3 or M4; length = 2 × plate thickness |
| **Screw head** | Socket head in a counterbore (ISO 4762) | or Phillips flat head, countersunk (ISO 7046) |
| **Plate screw counterbore Ø / depth** | standard for the head (M2.5: 5.5 × 2.5) | editable |
| **Holes for the alignment pins** | on (MIL flanges) | through the plate, 3 mm in the base |
| **Plate outer size** | automatic: as the flange, larger if the plate screws need it (WR-42 + M2.5: 25.5 mm) | type your own (e.g. 27.86) |
| **Outer corner radius** | 2 mm (square plates) | |
| **Plate thickness** | the computed λ/4 | changes **only if you set it**; a thicker body gets a feed-side pocket |

![Advanced menu, continued]({IMG}/m27_mount_adv2.jpg)

### 10.3 Live 3D

![Plate and feed in 3D]({IMG}/m28_mount_3d.jpg)

Below, the **plate** and the **feed with its drilled base** in 3D **update at every change**, with the plate size and thickness, the base thickness and the warnings (for example "the screw heads touch the feed body", "the feed flare overhangs the screws: use an L hex key", "square base enlarged to keep holes and counterbores inside").

---

## 11. Step 6 — WR plate

![WR plate]({IMG}/m29_plate.jpg)

The **λ/4 matching plate** joins the circular waveguide of the feed to the rectangular WR guide (OE2IGL design guide, HB9PZK optimisation). The orientation of the WR guide sets the polarisation: the E field is parallel to the short side *b*.

| Field | Meaning |
|---|---|
| **Polarisation** | Vertical / Horizontal (rotates aperture and holes by 90°) |
| **Feed circular waveguide Ø** | input diameter of the feed (proposed from the design) |
| **Aperture corner radius** | cutter radius in the corners (FeedLab compensates the width); with R2.00 on WR-42 the aperture is 9.50 × 6.21 mm |
| **Optimised version** | b and thickness corrected with openEMS (recommended) |
| **Results** | aperture a × b, **thickness λ/4** with its critical tolerance, intermediate Z0 |

The holes come from the **Assembly** tab (a note recalls the scheme).

![Front view and 3D view]({IMG}/m30_plate_views.jpg)

The **front view** colours the holes by function: **black** = waveguide flange holes, **magenta** = plate fixing (counterbore/countersink), **green** = alignment pins. **📄 Plate PDF drawing** gives a dimensioned workshop drawing: outer size and halves, hole positions, aperture, radii, hole callouts grouped by function (**WAVEGUIDE FLANGE**, **PLATE FIXING**, **ALIGNMENT PIN**) and the hole table with coordinates and tolerances. **🧊 Plate STEP** gives the solid.

---

## 12. Step 7 — Drawing & STEP

![Drawing & STEP]({IMG}/m31_drawing.jpg)

| Field / button | Meaning |
|---|---|
| **Material, Title** | printed in the title block |
| **General machining tolerance ±** | default: recommended value for the band (§15.2); printed in feed and plate PDFs with the hole tolerances |
| **📄 Create PDF** | A4 drawing: dimensioned section, dimension table (mm and λ), title block; **sheet 2** = drilled flange; critical tolerance table (from §7.4) |
| **🧊 Create STEP / 🖨️ Create STL** | solid for CAD/CAM (threads at tap-drill Ø) / for 3D printing |
| **JSON parameters** | all dimensions and settings |

**Hole tolerances on the drawings:** threads ISO 6H · dowel holes H7 (pins m6) · through holes +0.1/0 · counterbores +0.2/0.

---

## 13. Full-wave openEMS (optional)

![openEMS]({IMG}/m32_openems.jpg)

| Sub-tab | What it does |
|---|---|
| **① openEMS installation** | guided installation on Windows (official build, user folder, `OPENEMS_INSTALL_PATH`, Python bindings, test run); on Linux/macOS give the folder |
| **② New analysis** | single run, mesh convergence or parameter sweep; or a script to run on another PC |
| **③ Simulations** | running and finished jobs |
| **④ Results** | S11, patterns, efficiency, gain, G/T, phase centre; upload a `results.json` from another PC; compare runs |
| **⑤ Space mapping** | corrects the fast-solver design with the openEMS result |

> **Mesh.** In **② New analysis** you set **Cells per λ** in the feed (100 by default: dimensions stay within about λ/200, ±0.15 mm at 10 GHz), **Cells per λ in air** (20: outside the feed the mesh widens gradually), the **grading** (maximum ratio of neighbouring cells, 1.4) and the **symmetry** (full, half or quarter model). The table below shows the estimated cells, RAM and run time of each simulation and updates on every change. Grid lines always sit on every edge of the feed, so radii and lengths are exact; with few cells per λ the shape of slots and sloped walls is lost.

> **Validation reminder.** Every 5 changes to the design (dimensions, material, illumination, base, mounting…) a notice invites you to run an openEMS simulation: slower but more accurate than the fast simulator, it validates the data and shows whether the two results converge. With **⑤ Space mapping** the openEMS result then corrects the design.

---

## 14. Project outputs (PDF, tables, project file)

![Project outputs]({IMG}/m35_output.jpg)

In the **📦 Project outputs** tab choose which documents to generate, press **⚙️ Generate** and download the files one by one or all together with **⬇️ Download all (ZIP)**. Every document shows feed, band, dish and material at the top, and FeedLab version and UTC date at the bottom.

| Document | Contents |
|---|---|
| **📄 Complete project report (PDF)** | cover with the main results, fast simulations, dish, feed drawing, plate, mounting, openEMS and the table of all data |
| **📈 Fast simulations (PDF)** | gain, G/T, efficiencies, taper, S11, phase centre, Tsys and the scenario used; S11 over ±5 % of the band; E- and H-plane pattern with the dish rim |
| **📐 Feed: drawing and simulations (PDF)** | the dimensioned drawing of the Drawing & STEP tab followed by the simulations |
| **📡 Dish (PDF)** | dish data, opening angle, design f/D of the feed, illumination and efficiency breakdown |
| **🔲 λ/4 plate (PDF)** | the plate drawing (included after opening the 🔲 WR plate tab once) |
| **🔩 Feed + plate, mounting (PDF)** | mounting scheme, screws, thicknesses and section |
| **📋 Table of all dimensions and data (PDF + CSV)** | every value entered or computed: design data, feed dimensions, plate, results, openEMS; the CSV opens in Excel / LibreOffice |
| **🖥️ openEMS simulations (PDF)** | for every finished simulation of this feed and band: gain, G/T, efficiency, phase centre, beam, S11 and full-wave pattern |
| **💾 Project file (.json)** | the whole project: data entered and computed results. Share it with other radio amateurs and open it again in FeedLab |
| **🧊 3D models of the feed (STEP + STL)** | as in the Drawing & STEP tab |

**📂 Open a project file**: upload a `.feedlab.json` and press **Open project** to get back band, dish, feed, edited dimensions, material, illumination, waveguide and mounting.

The simulation scenario (elevation, NF, losses, surface, attenuation) is the one set in the **Laboratory**; if you have not opened it, the Laboratory defaults apply.

---

## 15. Reference tables

### 15.1 Materials

| Material | σ (10⁷ S/m) | skin depth δ (µm) at 10 / 24 / 47 / 76 GHz | Rq (µm) | Losses × copper | Practical note |
|---|---|---|---|---|---|
| Copper silver-plated (Ag ≥ 3 µm) | 6.10 | 0.63 / 0.42 / 0.30 / 0.23 | 0.3 | 1.0× | silver plating ≥ 3-5 δ; best for RX at mm-waves |
| Brass silver-plated | 6.10 | 0.63 / 0.42 / 0.30 / 0.23 | 0.3 | 1.0× | machinability of brass + losses of silver |
| Copper C101 OFE (Weerg) | 5.85 | 0.65 / 0.42 / 0.30 / 0.24 | 2 | 1.0× | oxygen-free copper; standard finish Ra 1.6–3.2 µm: ask for Ra ≤ 0.8 inside (lower losses) |
| Copper OFHC (Cu-ETP) | 5.80 | 0.65 / 0.43 / 0.30 / 0.24 | 0.4 | 1.0× | excellent conductor; it oxidises: protect it |
| Copper C110 ETP (PCBWay) | 5.80 | 0.65 / 0.43 / 0.30 / 0.24 | 2 | 1.0× | electrolytic copper; standard finish Ra 1.6–3.2 µm: ask for Ra ≤ 0.8 inside (lower losses) |
| Copper T2 (JLCCNC) | 5.70 | 0.65 / 0.43 / 0.31 / 0.24 | 2 | 1.0× | 99.9 % pure copper; standard finish Ra 1.6–3.2 µm: ask for Ra ≤ 0.8 inside (lower losses) |
| 3D print + electroplated copper | 5.00 | 0.70 / 0.46 / 0.33 / 0.26 | 3 | 1.1× | print roughness dominates above 24 GHz |
| Copper gold-plated (Au flash on Ni) | 4.10 | 0.77 / 0.51 / 0.36 / 0.29 | 0.3 | 1.2× | avoid nickel underneath: it is magnetic and lossy |
| Aluminium 1050 (pure) | 3.50 | 0.84 / 0.55 / 0.39 / 0.31 | 0.6 | 1.3× | more conductive but soft |
| Aluminium 6082-T6 Anticorodal (Weerg) | 2.60 | 0.97 / 0.64 / 0.45 / 0.36 | 2 | 1.5× | corrosion resistant; standard finish Ra 1.6–3.2 µm: ask for Ra ≤ 0.8 inside (lower losses) |
| Aluminium 6082/6061 T6 | 2.50 | 0.99 / 0.65 / 0.46 / 0.37 | 0.6 | 1.5× | light; anodise outside only |
| Aluminium 6061-T6 (JLCCNC, PCBWay) | 2.50 | 0.99 / 0.65 / 0.46 / 0.37 | 2 | 1.5× | the most common; standard finish Ra 1.6–3.2 µm: ask for Ra ≤ 0.8 inside (lower losses) |
| Aluminium 2011 (Weerg) | 2.30 | 1.03 / 0.68 / 0.48 / 0.38 | 2 | 1.6× | free-machining, for the lathe; standard finish Ra 1.6–3.2 µm: ask for Ra ≤ 0.8 inside (lower losses) |
| Aluminium 5052 (PCBWay) | 2.00 | 1.11 / 0.73 / 0.52 / 0.41 | 2 | 1.7× | corrosion resistant; standard finish Ra 1.6–3.2 µm: ask for Ra ≤ 0.8 inside (lower losses) |
| Aluminium 7075-T6 Ergal (JLCCNC, PCBWay, Weerg) | 1.90 | 1.13 / 0.74 / 0.53 / 0.42 | 2 | 1.7× | very strong, less conductive than 6061; standard finish Ra 1.6–3.2 µm: ask for Ra ≤ 0.8 inside (lower losses) |
| Aluminium 2A12 / 2024 (PCBWay) | 1.74 | 1.18 / 0.78 / 0.56 / 0.44 | 2 | 1.8× | aerospace grade, low conductivity; standard finish Ra 1.6–3.2 µm: ask for Ra ≤ 0.8 inside (lower losses) |
| Aluminium 5083 (Weerg) | 1.60 | 1.24 / 0.81 / 0.58 / 0.46 | 2 | 1.9× | marine grade, low conductivity; standard finish Ra 1.6–3.2 µm: ask for Ra ≤ 0.8 inside (lower losses) |
| Brass H59 (JLCCNC) | 1.60 | 1.24 / 0.81 / 0.58 / 0.46 | 2 | 1.9× | machining brass; standard finish Ra 1.6–3.2 µm: ask for Ra ≤ 0.8 inside (lower losses) |
| Brass H62 (JLCCNC) | 1.57 | 1.25 / 0.82 / 0.59 / 0.46 | 2 | 1.9× | brass; standard finish Ra 1.6–3.2 µm: ask for Ra ≤ 0.8 inside (lower losses) |
| Brass CuZn39Pb3 | 1.50 | 1.28 / 0.84 / 0.60 / 0.47 | 0.4 | 2.0× | very easy to turn; losses ~2× copper |
| Brass C360 (PCBWay) | 1.50 | 1.28 / 0.84 / 0.60 / 0.47 | 2 | 2.0× | free-cutting brass (like CuZn39Pb3); standard finish Ra 1.6–3.2 µm: ask for Ra ≤ 0.8 inside (lower losses) |
| Brass OT58 CuZn40Pb2 (Weerg) | 1.50 | 1.28 / 0.84 / 0.60 / 0.47 | 2 | 2.0× | free-cutting brass; standard finish Ra 1.6–3.2 µm: ask for Ra ≤ 0.8 inside (lower losses) |
| Bronze CuSn12 (Weerg) | 0.55 | 2.11 / 1.38 / 0.99 / 0.78 | 2 | 3.2× | high losses (about 3× brass): not recommended for the inside |
| Stainless steel AISI 304 | 0.14 | 4.18 / 2.74 / 1.96 / 1.54 | 0.4 | 6.4× | structures only: high losses |
| Stainless steel 316L (JLCCNC, PCBWay, Weerg) | 0.13 | 4.29 / 2.81 / 2.01 / 1.58 | 2 | 6.6× | structures only: high losses |
| 3D print + copper paint | 0.10 | 4.94 / 3.25 / 2.32 / 1.83 | 5 | 7.6× | high losses, prototypes/low bands only |
| Titanium Ti-6Al-4V (PCBWay) | 0.06 | 6.49 / 4.26 / 3.05 / 2.40 | 2 | 10.0× | structures only: very high losses |

Materials named after a service (JLCCNC, PCBWay, Weerg) are those these online CNC services machine; the roughness given (Rq ≈ 2 µm) is their standard finish: asking for a polished inside (Ra ≤ 0.8 µm) lowers the losses. The **ℹ️ About materials** button shows the same table with machinability, price, availability, weather resistance, treatments, pros and cons.

RF current flows in a layer a few δ thick: platings ≥ 3–5 δ; roughness comparable to δ increases the loss. FeedLab turns the ohmic loss into added noise temperature (Laboratory).

### 15.2 General machining tolerance

| Band | Recommended | Notes |
|---|---|---|
| 10, 24 GHz | ±0.1 mm | inner diameters ≈ λ/100 |
| 47 GHz | ±0.05 mm | |
| 76 GHz | ±0.02 mm | |
| 122 / 134 GHz | ±0.01 mm | |

The λ/4 plate thickness has its own tighter tolerance (WR-42: ±0.087 mm). The tolerance analysis (§7.4) tells which dimensions need more.

### 15.3 Standard flanges (Flann; MIL-DTL-3922/67C)

| WR | Flange | Shape | Size (mm) | Hole positions (mm) | Hole Ø (published → FeedLab) | Screw |
|---|---|---|---|---|---|---|
| WR-90 | UBR 100 | square | 41.40 | x ±15.49, y ±16.26 | 4.255 → 4.3 | M4 / 8-32 UNC |
| WR-75 | UBR 120 | square | 38.30 | x ±13.21, y ±14.25 | 4.085 → 4.1 | M3 / 6-32 UNC |
| WR-42 | UBR 220 (UG-595/U) | square | 22.41 | x ±8.13, y ±8.51 | 3.07 → 3.1 | M3 / 4-40 UNC |
| WR-22, WR-19 | UG-383/U | round | Ø28.55 | PCD 23.81 (4 holes + 4 dowels) | 3.05 → 3.1 | 4-40 UNC |
| WR-15 … WR-5 | UG-385/387/U | round | Ø19.05 | PCD 14.29 (4 holes + 4 dowels) | 3.05 → 3.1 | 4-40 UNC |

### 15.4 Screws, holes and heads

| Screw | Tap drill | Clearance (normal / medium) | Socket-head counterbore Ø × depth | Flat-head countersink Ø |
|---|---|---|---|---|
| M2 | 1.6 | 2.4 / 2.4 | 4.4 × 2.1 | 4.0 |
| M2.5 | 2.05 | 2.8 / 2.9 | 5.5 × 2.5 | 4.9 |
| M3 | 2.5 | 3.2 / 3.4 | 6.5 × 3.1 | 5.7 |
| M4 | 3.3 | 4.3 / 4.5 | 8.0 × 4.4 | 8.6 |
| 2-56 UNC | 1.78 | 2.6 | 4.2 × 2.3 | 4.6 |
| 4-40 UNC | 2.26 | 3.0 / 3.4 | 5.3 × 3.0 | 5.9 |
| 6-32 UNC | 2.70 | 3.7 / 3.9 | 6.1 × 3.7 | — |
| 8-32 UNC | 3.45 | 4.3 / 4.5 | 7.9 × 4.4 | 8.6 |

Socket heads ISO 4762 / ASME B18.3; flat heads ISO 7046 (90°) / UNC 82°. Blind tapped holes are drilled to an even whole millimetre; the thread reaches the screw end and stops 3 pitches (≥ 1 mm) before the bottom.

---

## 16. Worked example: 24 GHz EME feed for a 2.4 m offset dish

1. **Sidebar:** Band **24.048 GHz**, material **Brass CuZn39Pb3** (or silver-plated brass), waveguide **WR-42**, base **Circular**.
2. **Guided procedure:** catalogue → **Channel Master Type 243 2.4 m**; goal **Maximum G/T**; illumination **Automatic** or e.g. 12 dB; **Find the best feed** → **Dual-Flare, IZ0JNY** → **Use this feed**.
3. **Feed design:** check "Designed for f/D …"; base thickness automatic; **Apply changes** after any edit.
4. **Laboratory:** goal **EME**, LNA NF and line loss; read **Tsys** and Δ S/N; **Analyse tolerances** at ±0.1 mm.
5. **Simulation & S11:** S11 < −20 dB over the band; compare the **−10 dB angle** with the dish opening; η and phase centre.
6. **Assembly:** scheme **Plate screwed to the feed base with counterbored screws (waveguide screwed into the plate)** — M3 6H in the plate, 4 × M2.5 socket screws at 9.00 mm; in Advanced set the outer size (e.g. 27.86 mm, R2) if you want.
7. **WR plate:** aperture corner radius **2.00** (your end mill); **Plate PDF drawing** and **Plate STEP**.
8. **Drawing & STEP:** general tolerance ±0.1 mm; **Create PDF** (feed + drilled flange) and **Create STEP**.
9. **Optional:** openEMS before cutting metal.

---

## 17. Troubleshooting and FAQ

| Problem | What to do |
|---|---|
| "Windows protected your PC" | More info → Run anyway |
| No update window | press **🔄 Check for updates**: it shows the exact error. 0.4.17/0.4.18: install the current version by hand once |
| A tab only shows "To start, select…" | choose band and material (sidebar), dish (Guided procedure), feed type (Feed design) |
| I changed a dimension but nothing happens | press **Apply changes** (Feed design) |
| The base is thicker than expected | blind holes for the plate screws need depth: set the base thickness yourself or use smaller screws / another scheme |
| The plate is larger than the flange | the plate screws need room (1 mm outside the counterbore): M2, flat heads, or set the size in Assembly → Advanced |
| "screw heads touch the feed body" | lengthen the input guide or use the "screws from the waveguide side" scheme |
| Ring/slot feeds show no S11 | use openEMS |
| Results differ from my measurement | real dishes are 12–15 points below; check focal length and feed position (phase centre at the focus) |

---

## 18. Glossary

| Term | Meaning |
|---|---|
| **f/D** | focal length / diameter; offset dishes: equivalent f/D seen by the feed |
| **Design f/D** | the f/D the feed is designed for, from the chosen illumination |
| **Edge taper** | level at the rim relative to the centre (dB) |
| **Spillover** | feed power that misses the dish (lost, picks up ground noise) |
| **Illumination (taper) efficiency** | how uniformly the aperture is used |
| **Tsys** | system noise temperature: antenna + losses + preamplifier |
| **G/T** | gain over system noise temperature, the figure of merit for RX and EME |
| **S11 / return loss** | mismatch at the feed input |
| **Phase centre** | the point the feed seems to radiate from: at the focus |
| **Mode matching** | fast solver for circular-waveguide feeds made of steps and cones |
| **λ/4 plate** | quarter-wave matching section between circular and rectangular waveguide |
| **Counterbore / countersink** | flat-bottom seat for a socket head / conical seat for a flat head |
| **6H, H7, m6** | ISO tolerance classes for internal threads, holes and pins |

---

*FeedLab is free software (GNU GPL v3.0 or later), © 2026 Ivan De Cesaris, IZ0JNY, without any warranty: results are design estimates to be verified with full-wave simulation and measurements. Sources: W1GHZ Online Microwave Antenna Book, OE2IGL design guides, Balanis, Kildal and the works in the Credits tab.*
