"""Catalogue of commercial / well-documented dishes.

Every entry states where each number comes from. Manufacturer datasheets of TV offset dishes usually
give size, offset angle and an "F/D" in the *offset* convention (f / reflector width) plus, sometimes,
the required feed illumination angle — that angle is what the feed must be designed for (OE2IGL:
"use the opening angle, not f/D"). Focal lengths are rarely published: where absent they are estimated
as f ≈ F/D × outer width (checked against OE2IGL's measurement of the OP65: 0.66 × 670 ≈ 445 mm
measured) and flagged as estimates — measure your own dish (depth + string method) before final setup.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import reflector


@dataclass
class DishModel:
    maker: str
    model: str
    kind: str                       # offset | prime
    width_mm: float                 # outer width (offset: horizontal / short axis)
    height_mm: float                # outer height (offset: long axis)
    active_w_mm: float | None = None
    active_h_mm: float | None = None
    fD_maker: float | None = None   # as printed by the maker (offset convention for offset dishes)
    focal_mm: float | None = None   # published or measured focal length
    focal_source: str = ""          # "datasheet" | "measured (…)" | "estimated"
    offset_deg: float | None = None
    illum_deg: float | None = None  # required feed illumination (full angle)
    efficiency_pct: float | None = None
    gain: dict = field(default_factory=dict)   # GHz -> dBi
    collar_mm: str = ""
    material: str = ""
    source: str = ""
    notes: str = ""

    @property
    def label(self) -> str:
        return f"{self.maker} {self.model} ({self.kind}, {self.width_mm / 10:.0f}×{self.height_mm / 10:.0f} cm)"

    @property
    def D_mm(self) -> float:
        """Aperture diameter used for gain: projected (≈ active width) for offset, diameter for prime."""
        return self.active_w_mm or self.width_mm

    def focal(self) -> tuple[float | None, str]:
        if self.focal_mm:
            return self.focal_mm, self.focal_source
        if self.fD_maker and self.kind == "offset":
            return self.fD_maker * self.width_mm, "stimata (F/D × larghezza)"
        if self.fD_maker and self.kind == "prime":
            return self.fD_maker * self.width_mm, "datasheet (f/D)"
        return None, "non pubblicata: misura profondità e stringhe"

    def opening_deg(self) -> float | None:
        """Full illumination angle the feed must cover."""
        if self.illum_deg:
            return self.illum_deg
        f, _ = self.focal()
        if f is None:
            return None
        if self.kind == "prime":
            return 2 * reflector.half_angle_from_fD(f / self.width_mm)
        g = reflector.offset_geometry(f, self.D_mm, 0.0)
        return 2 * g.psi_S

    def fD_equiv(self) -> float | None:
        o = self.opening_deg()
        return None if o is None else reflector.fD_from_half_angle(o / 2)


GIB_SRC = "Gibertini datasheet serie XP (GB-TS-GR-001, 2010) — via conrad.com"
GIB_LN = "Gibertini OP LN datasheet — via telmor.pl"

CATALOG: list[DishModel] = [
    # --- Gibertini (datasheet: active area, F/D, offset, required feed illumination) ---
    DishModel("Gibertini", "OP 65 XP", "offset", 670, 715, 630, 675, 0.66, None, "", 21.3, 70, 69,
              {10.7: 35.38, 11.7: 36.20, 12.75: 36.90}, "40/23", "Alu 1.0 mm", GIB_SRC,
              "OE2IGL ha misurato 676×630, profondità 52 mm → f ≈ 445 mm"),
    DishModel("Gibertini", "OP 75 XP", "offset", 750, 800, 720, 770, 0.66, None, "", 21.0, 70, 69,
              {10.7: 36.54, 11.7: 37.32, 12.75: 38.10}, "40/23", "Alu", GIB_SRC),
    DishModel("Gibertini", "OP 85 XP", "offset", 850, 905, 815, 870, 0.67, None, "", 21.1, 69, 69,
              {10.7: 37.62, 11.7: 38.40, 12.75: 39.15}, "40/23", "Alu 1.2 mm", GIB_SRC),
    DishModel("Gibertini", "OP 100 XP", "offset", 970, 1040, 940, 1010, 0.66, None, "", 21.0, 70, 70,
              {10.7: 38.90, 11.7: 39.70, 12.75: 40.44}, "40/23", "Alu 1.3 mm", GIB_SRC),
    DishModel("Gibertini", "OP 75 LN", "offset", 750, 800, 720, 770, 0.67, None, "", 21.0, 70, 69,
              {10.7: 36.6, 11.7: 37.4, 12.75: 38.2}, "40/23", "acciaio zincato", GIB_LN),
    DishModel("Gibertini", "OP 85 LN", "offset", 850, 905, 815, 870, 0.67, None, "", 21.1, 69, 70,
              {10.7: 37.8, 11.7: 38.5, 12.75: 39.2}, "40/23", "acciaio zincato", GIB_LN),
    DishModel("Gibertini", "OP 125 L", "offset", 1245, 1335, 1210, 1300, 0.66, None, "", 21.3, None, None,
              {}, "", "Alu", "Gibertini OP125L installation guide (kosmosat.gr) + listini",
              "datasheet: F/D 0.66, fascio 1.32° a 11.7 GHz"),
    DishModel("Gibertini", "OP 150 S", "offset", 1550, 1660, 1500, 1610, 0.66, None, "", 21.3, 70, 70,
              {10.7: 43.0, 11.7: 43.7, 12.75: 44.5}, "40", "spessore 2.0 mm",
              "Gibertini OP 150 S datasheet (fornito da IZ0JNY)",
              "fascio −3 dB 1.07° a 11.7 GHz; temperatura di rumore 31 K a 12 GHz e 30° di elevazione"),
    DishModel("Gibertini", "OP 150 L", "offset", 1550, 1660, 1500, 1610, 0.66, None, "", 21.3, 70, 72,
              {10.95: 43.3}, "", "", "dati Gibertini forniti da IZ0JNY (155 × 166 cm, F/D 0.66, 43.3 dBi a 10.95 GHz); "
              "area attiva, offset e illuminazione dal datasheet OP 150 S (stesse dimensioni esterne e F/D)",
              "η ≈ 72% calcolata dal guadagno sull'area attiva di 1500 mm"),
    # --- Fracarro ---
    DishModel("Fracarro", "RO125AP", "offset", 1240, 1345, None, None, None, None, "", 23.0, None, 74,
              {10.7: 41.0, 11.7: 41.6, 12.7: 42.4}, "", "Alu", "Fracarro RO125AP datasheet",
              "il datasheet riporta '0.66' nella riga 'front back ratio': probabile F/D — non usato"),
    # --- Triax ---
    DishModel("Triax", "TDS 80LG (120509)", "offset", 710, 790, None, None, 0.62, None, "", 25.6, None, None,
              {11.7: 37.5}, "40", "acciaio", "Triax datasheet art. 120509 (av-connection)"),
    DishModel("Triax", "TDS 80A (126508)", "offset", 745, 845, None, None, 0.60, None, "", 25.0, None, None,
              {10.75: 37.0, 11.75: 38.1, 12.75: 39.1}, "40", "acciaio", "Triax datasheet art. 126508 (alltrade)"),
    DishModel("Triax", "TDS PRO 65", "offset", 620, 680, 600, 660, 0.60, None, "", None, None, None,
              {}, "40", "acciaio 0.6 mm", "Triax TDS PRO leaflet (alltrade)"),
    DishModel("Triax", "TDS PRO 80", "offset", 790, 850, 750, 830, 0.60, None, "", None, None, None,
              {}, "40", "acciaio 0.7 mm", "Triax TDS PRO leaflet (alltrade)"),
    DishModel("Triax", "TDA 64", "offset", 600, 650, None, None, None, None, "", 26.0, None, None,
              {11.7: 35.8}, "40", "Alu", "Triax TDA 64 datasheet (zajadacz.de)", "F/D non pubblicato"),
    # --- Kathrein (focale/f/D non pubblicati nei datasheet: misurare) ---
    DishModel("Kathrein", "CAS 60 (20010006)", "offset", 570, 570, None, None, None, None, "", None, None, None,
              {11.2: 34.9, 12.1: 35.5, 12.625: 35.9}, "", "Alu verniciato a polvere",
              "Kathrein CAS 60 Produktinformation, Art.-Nr. 20010006 (PDF fornito dall'utente)",
              "diametro 57 cm; HPBW < 2.8° a centro banda; G/T 14.7/15.7 dB/K (UAS 571/572/584/585, feed centrale) "
              "a 11.3/12.5 GHz; elevazione 5–45°; ingombro 599 × 759 × 528 mm con supporto (altezza riflettore non "
              "data). Focale, f/D e angolo di offset non pubblicati: misura assi e profondità"),
    DishModel("Kathrein", "CAS 90", "offset", 900, 900, None, None, None, None, "", None, None, None,
              {}, "", "Alu", "Kathrein CAS 90 datasheet (diametro e banda)", "F/D/focale non pubblicati: misurare"),
    DishModel("Kathrein", "CAS 120", "offset", 1200, 1200, None, None, None, None, "", None, None, None,
              {11.2: 41.5, 12.1: 42.15, 12.6: 42.5}, "", "Alu", "Kathrein CAS 120/G datasheet (radiomuseum/zajadacz)",
              "HPBW < 1.43°; F/D/focale non pubblicati: misurare"),
    DishModel("Kathrein", "CAS 180 (216235)", "offset", 1800, 1800, None, None, None, None, "", None, None, None,
              {11.2: 44.5, 12.1: 45.15, 12.625: 45.5}, "", "Alu verniciato a polvere, riscaldabile",
              "Kathrein CAS 180 product information, order no. 216235 (PDF fornito dall'utente)",
              "diametro 1.8 m; HPBW 0.9°; cross-pol > 30 dB; elevazione 5–50°; ingombri 1980 mm larghezza, 1511 mm "
              "altezza, 1900 mm sporgenza; supporto feed ZAS 181C. Focale, f/D e angolo di offset non pubblicati: "
              "misura assi e profondità"),
    # --- Fuba (fuba.de). La DAA 850 pubblica f/D 0.63 e fuoco 531.3 mm: con offset 21.5° corrisponde alla
    #     paraboloide col bordo inferiore sull'asse (atan(1/(4·0.63)) = 21.6°); stessa regola usata per stimare
    #     la focale di DAA 650 e DAA 780 dal loro angolo di offset. ---
    DishModel("Fuba", "DAA 650", "offset", 600, 650, None, None, None, 368, "stimata dall'offset 22.1° (f = D/(4·tan θ))",
              22.1, None, None, {10.75: 35.2, 12.75: 36.7}, "40", "Alu 0.8 mm", "Fuba, scheda tecnica su fuba.de + 'DAA/DAL-Sortiment Folder' (fuba_daa_dal_sortiment_folderv2.pdf)",
              "HPBW < 2.7° a 12.75 GHz; cross-pol ≥ 27 dB; braccio LNB 49 cm; focale stimata: verifica misurando la profondità"),
    DishModel("Fuba", "DAA 780", "offset", 740, 840, None, None, None, 397, "stimata dall'offset 25° (f = D/(4·tan θ))",
              25.0, None, None, {10.75: 36.8, 12.75: 38.5}, "40", "Alu 1.0 mm", "Fuba, scheda tecnica su fuba.de + 'DAA/DAL-Sortiment Folder' (fuba_daa_dal_sortiment_folderv2.pdf)",
              "cross-pol ≥ 27 dB; braccio LNB 61 cm; focale stimata: verifica misurando la profondità"),
    DishModel("Fuba", "DAA 850", "offset", 850, 850, None, None, 0.63, 531.3, "datasheet Fuba (fuoco 53.13 cm)",
              21.5, None, None, {10.75: 38.12, 12.75: 39.53}, "40", "Alu 1.1 mm", "Fuba, scheda tecnica su fuba.de + 'DAA/DAL-Sortiment Folder' (fuba_daa_dal_sortiment_folderv2.pdf)",
              "f/D 0.63; HPBW < 2.2° a 12.75 GHz; cross-pol ≥ 27 dB; braccio LNB 65 cm"),
    DishModel("Fuba", "DAA 110", "offset", 991, 1099, None, None, None, None, "", None, None, None,
              {10.75: 39.8, 12.75: 40.9}, "40", "Alu, retro in pressofusione", "Fuba DAA/DAL-Sortiment Folder (fuba_daa_dal_sortiment_folderv2.pdf)",
              "riflettore 1099 × 991 mm (assegnato 991 orizzontale, 1099 verticale); focale e offset non pubblicati: misura"),
    DishModel("Fuba", "DAL 800", "offset", 740, 840, None, None, None, None, "", None, None, None,
              {10.75: 36.8, 12.75: 38.5}, "40", "Alu, retro in pressofusione", "Fuba DAA/DAL-Sortiment Folder (fuba_daa_dal_sortiment_folderv2.pdf)",
              "antenna portatile con braccio pieghevole; stesse misure e guadagno della DAA 780 (forse stesso riflettore, "
              "non confermato); focale e offset non pubblicati: misura"),
    # --- Channel Master / Andrew / Skyware ---
    DishModel("Channel Master", "Type 123 1.2 m (Andrew / Skyware)", "offset", 1200, 1300, 1200, None, None, None, "",
              16.97, None, None, {12.0: 41.8, 14.3: 43.3}, "", "SMC/acciaio",
              "Skyware Global Type 123 Class II datasheet; offset 16.97° da manuale Andrew (citato su satsig)",
              "'long focal length optics'; focale non pubblicata"),
    DishModel("Channel Master", "Type 243 2.4 m (Andrew / Skyware)", "offset", 2460, 2664, 2400, None, 0.6, 1440,
              "derivata dal manuale (bordo inclinato 22.62°, bordo inferiore sull'asse)",
              22.62, None, 60, {3.9: 38.0, 6.1: 42.0, 12.0: 47.4, 14.3: 48.9}, "", "SMC / vetroresina, 2 pezzi",
              "Channel Master 2.4 m Offset Tx/Rx manual (outline drawing App. A, purplesat.com) + Skyware Global "
              "Type 243 datasheet Ku Class III (REV 11/14) e C-band Linear (REV 03/15)",
              "riflettore 96.87\" × 104.87\" (2460 × 2664 mm), apertura efficace 2.4 m, offset 22.62° tra asse "
              "meccanico e asse del fascio (manuale); HPBW 0.71° @12 GHz, 0.59° @14.3 GHz; η ≈ 60% calcolata dal "
              "guadagno; feed originale WR75 (Ku) / CPR-229 (C). Focale non pubblicata dal costruttore: f = 1440 mm "
              "(f/D 0.6 su 2.4 m) è la paraboloide madre con bordo inferiore sull'asse, che riproduce esattamente "
              "l'inclinazione del bordo 22.62° del manuale (atan(D/4f)); bracci superiori 198 cm, inferiore 141 cm "
              "(satellites.co.uk). Per conferma misura la profondità ('Ho misurato la mia parabola': asse lungo 2664, "
              "corto 2460)"),
    # --- Prodelin (General Dynamics SATCOM): datasheet gains; focal length not published ---
    DishModel("Prodelin", "1.2 m Ku Series 1123/1125 (1132)", "offset", 1200, 1300, None, None, None, None, "", 22.6, None, None,
              {11.85: 41.7, 14.25: 43.2}, "", "SMC (poliestere/fibra di vetro)",
              "Prodelin 1.2M Ku-Band Rx/Tx Series 1123 & 1125 datasheet (tvcinc.com); offset 22.6° da satelliteguys.us "
              "(non verificato su documento Prodelin); G8RWG (g8rwg.uk) sul modello 1132",
              "focale non pubblicata: G8RWG ha trovato il fuoco con la prova delle stringhe a ~1200 mm dal riflettore "
              "(braccio di serie troppo corto) e ottimizzato col rumore solare (Tsky/Tsun 9.13 dB a 10 GHz); asse lungo "
              "1300 mm stimato (1200/cos 22.6°): misura assi e profondità"),
    DishModel("Prodelin", "1.8 m C/Ku Series 1183/1184", "offset", 1800, 1950, None, None, None, None, "", None, None, None,
              {3.9125: 35.5, 6.1375: 39.5, 11.85: 45.0, 14.25: 46.5}, "", "SMC (poliestere/fibra di vetro), un pezzo",
              "Prodelin 1.8M C & Ku-Band Rx/Tx Series 1183 datasheet (newerasystems.net)",
              "focale, f/D e angolo di offset non pubblicati; asse lungo 1950 mm stimato: misura assi e profondità"),
    DishModel("Prodelin", "2.4 m C/Ku Series 1250/1251", "offset", 2400, 2594, None, None, None, None, "", 22.3, None, None,
              {3.9125: 38.0, 6.1375: 42.0, 11.85: 47.6, 14.125: 49.2}, "", "SMC, due petali divisi lungo l'asse maggiore",
              "Prodelin 2.4M Series 1251 datasheet (kusat.com); manuale Series 1250 (4096-663 rev. A, 2005): "
              "'22.3° elevation offset angle'",
              "focale e f/D non pubblicati; asse lungo 2594 mm stimato (2400/cos 22.3°): misura assi e profondità al centro"),
    DishModel("Channel Master", "1 m", "offset", 997, 1083, None, None, None, 604, "misurata", None,
              None, None, {}, "", "", "W1GHZ Antenna Book App. 5A", "tilt 67.5° dall'orizzontale, stringa sup. 1018 mm, f/D eq. 0.68"),
    # --- dishes measured in the W1GHZ Antenna Book (App. 5A) ---
    DishModel("RCA", "DSS 18\" (SMC)", "offset", 457, 495, None, None, None, 278, "misurata", None, None, 63, {}, "", "SMC",
              "W1GHZ App. 5A / cap. 5", "63% misurato a 10 GHz con tromba rettangolare"),
    DishModel("Dish Network", "18\"", "offset", 460, 504, None, None, None, 287, "misurata", None, None, None, {}, "", "",
              "W1GHZ App. 5A"),
    # --- prime focus ---
    DishModel("Edmund Optics", "parabolic 12\" (305 mm)", "prime", 305, 305, None, None, 0.25, None, "", None, None, None,
              {}, "", "Alu quasi ottico", "Edmund Optics / W1GHZ MUD 2023", "ideale per Cassegrain 47-122 GHz"),
    DishModel("Edmund Optics", "parabolic 18\" (457 mm)", "prime", 457, 457, None, None, 0.25, None, "", None, None, None,
              {}, "", "Alu", "Edmund Optics / W1GHZ"),
    DishModel("Edmund Optics", "parabolic 24\" (609 mm)", "prime", 609, 609, None, None, 0.25, None, "", None, None, None,
              {}, "", "Alu", "Edmund Optics / W1GHZ / VE2UG 47 GHz Cassegrain"),
    DishModel("SHF Microwave", "300 mm f/D 0.6", "prime", 300, 300, None, None, 0.6, None, "", None, None, None,
              {}, "", "Alu", "W1GHZ 'Optimized Cassegrain' 2023 (47 GHz)"),

]


def by_label() -> dict[str, DishModel]:
    return {d.label: d for d in CATALOG}
