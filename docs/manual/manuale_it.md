# FeedLab — Manuale d'uso

**Laboratorio di progettazione di feed / illuminatori a microonde, 10–134 GHz**
Versione {VERSION} BETA TEST · Software progettato da Ivan De Cesaris, IZ0JNY

---

## Indice

1. Cosa fa FeedLab — e cosa non fa
2. Installazione, avvio e aggiornamenti
3. Lo schermo in sintesi
4. La barra laterale, campo per campo
5. Passo 1 — Procedura guidata (parabola, obiettivo, illuminazione)
6. Passo 2 — Progetto feed
7. Passo 3 — Laboratorio (varianti, rumore, ottimizzazione, tolleranze)
8. Passo 4 — Simulazione & S11
9. Lobo 3D e Modello 3D
10. Passo 5 — Montaggio feed + piastrina
11. Passo 6 — Piastrina WR (piastrina λ/4)
12. Passo 7 — Disegno & STEP (PDF, STEP, STL)
13. Full-wave openEMS (facoltativo)
14. Output di progetto (PDF, tabelle, file di progetto)
15. Tabelle di riferimento: materiali, tolleranze, flange, viti, lamature
16. Esempio completo: feed EME a 24 GHz per una offset da 2.4 m
17. Problemi frequenti
18. Glossario

---

## 1. Cosa fa FeedLab — e cosa non fa

FeedLab progetta i **feed delle parabole** (l'illuminatore nel fuoco del riflettore) per le bande radioamatoriali a microonde da **10 a 134 GHz**, e produce tutto quello che serve all'officina per costruirli.

**FeedLab:**

- sceglie il feed più adatto alla **tua** parabola (catalogo commerciale o parabola misurata), al tuo obiettivo (guadagno in TX, G/T in RX, EME) e ai tuoi mezzi (tornio/CNC o lamiera);
- progetta il feed per l'**illuminazione che scegli** (taper al bordo in dB) e calcola tutte le quote interne dalle regole pubblicate (W1GHZ, OE2IGL, Skobelev, IZ0JNY…);
- simula il feed in pochi secondi con un risolutore a **mode matching**: S11, modi all'apertura, lobo con l'angolo a −10 dB, centro di fase, efficienza sulla parabola, guadagno, temperatura di sistema e G/T;
- ti fa cambiare ogni quota e vedere subito se il risultato migliora o peggiora (**Laboratorio**), ottimizzare in automatico e controllare le **tolleranze di lavorazione**;
- progetta la **piastrina λ/4** dalla guida circolare del feed alla guida rettangolare WR, e **come si fissano feed e piastrina** alla guida esterna (fori, filetti, lamature, viti, pin di allineamento);
- produce il **disegno PDF quotato**, il file **STEP** per CAD/CAM e l'**STL** per la stampa 3D, del feed e della piastrina;
- prepara e analizza una simulazione **full-wave openEMS** (facoltativa) come verifica di riferimento.

**FeedLab non:**

- sostituisce le misure: i risultati sono *stime di progetto*. Sulle parabole reali l'efficienza è di solito 12–15 punti sotto il valore calcolato (W1GHZ, WD5AGO);
- copre i feed sotto i 10 GHz (per esempio i septum per 1296 MHz);
- simula con il risolutore rapido i feed ad anelli o scanalature (VE4MA, Chaparral, Axial Corrugated): per questi usa l'efficienza pubblicata dall'autore e consiglia openEMS.

> **Regola pratica.** Usa il risolutore rapido per *scegliere e mettere a punto*, openEMS per *confermare* un progetto nuovo o molto modificato, e una misura di rumore solare o di return loss per *verificare* il pezzo reale.

---

## 2. Installazione, avvio e aggiornamenti

### 2.1 Windows (consigliato)

1. Apri la pagina **Releases** del repository GitHub **IZ0JNY/FeedLab** e scarica l'ultima versione.
2. Scegli uno dei due pacchetti:
   - **Installer** `FeedLab-Setup-x.y.z.exe` — non servono diritti di amministratore; FeedLab compare nel menu Start ("FeedLab" e "FeedLab (nel browser)"). La **lingua** si sceglie durante l'installazione.
   - **Portable** `FeedLab-x.y.z-portable.zip` — estrai in una cartella qualsiasi e fai doppio clic su `FeedLab.bat`. Non installa nulla; la lingua segue Windows (si cambia nella barra laterale).
3. Facoltativo: controlla il file scaricato con `SHA256SUMS.txt` pubblicato con la release.

Finché l'installer non è firmato digitalmente, **Windows SmartScreen** può dire "Windows ha protetto il PC": clicca **Ulteriori informazioni → Esegui comunque**.

FeedLab si apre nella sua finestra (Microsoft Edge WebView2, compreso in Windows 11). Senza WebView2 si apre nel browser.

**Installare una versione nuova sopra quella vecchia** aggiorna l'installazione esistente: stessa cartella, stesse voci nel menu Start. Le simulazioni e le impostazioni (in *Documenti\FeedLab* e nella cartella di openEMS) restano.

### 2.2 Linux / macOS (dai sorgenti)

```
pip install -e .
feedlab-gui
```

### 2.3 Nuove versioni

A ogni avvio FeedLab chiede a GitHub l'ultima release. Se c'è una versione più nuova, **si apre una finestra** con le **novità** (nella tua lingua) e il pulsante per **scaricarla**. In qualunque momento puoi anche premere **🔄 Controlla aggiornamenti** nella barra laterale: mostra la versione nuova, "Hai già l'ultima versione", oppure il motivo preciso per cui GitHub non risponde.

Il certificato di GitHub lo verifica **Windows stesso**, come fa il browser: il controllo funziona anche con gli antivirus che ispezionano le connessioni HTTPS. Non viene inviato nessun dato personale.

> Le versioni **0.4.17 e 0.4.18** non sempre raggiungevano GitHub: se hai una di queste, installa a mano una volta la versione attuale.

---

## 3. Lo schermo in sintesi

![FeedLab all'avvio: nessuna scelta predefinita]({IMG}/m01_start.jpg)

La finestra ha due parti:

- la **barra laterale** a sinistra: banda, materiale, guida d'onda, base del feed, e i pulsanti per lingua, credits, aggiornamenti, manuale e segnalazioni;
- le **schede** in alto, da usare da sinistra a destra:

| Scheda | Cosa ci fai |
|---|---|
| 🧭 **Procedura guidata** | scegli parabola, obiettivo, mezzi e illuminazione; FeedLab ordina i feed adatti |
| 📐 **Progetto feed** | vedi e modifichi tutte le quote del feed; spessore di parete e base; profilo esterno CNC |
| 🎛️ **Laboratorio** | provi varianti, vedi la variazione di S/N, il bilancio di rumore, sensibilità, ottimizzazione, tolleranze |
| 📈 **Simulazione & S11** | S11 sulla banda, modi all'apertura, lobo con angolo a −10 dB, efficienza, centro di fase, G/T |
| 🌐 **Lobo 3D** | lobo di irradiazione 3D del feed |
| 🧊 **Modello 3D** | modello 3D del feed con la base forata |
| 🔩 **Montaggio feed + piastrina** | come si fissano feed e piastrina alla guida esterna: schema, sezione, fori, viti, 3D in tempo reale |
| 🔲 **Piastrina WR** | piastrina λ/4 verso la guida WR: apertura, spessore, viste, PDF e STEP |
| 📄 **Disegno & STEP** | disegno PDF, STEP, STL, tolleranza generale |
| 🖥️ **Full-wave openEMS** | verifica full-wave facoltativa (installazione, simulazione, risultati, space mapping) |
| ℹ️ **Credits** | autore, licenza, collaboratori e tutte le fonti tecniche |

**All'avvio non c'è nessuna scelta predefinita.** Finché non scegli **frequenza**, **materiale**, **parabola** e **tipo di feed**, le schede mostrano un breve messaggio con cosa manca e dove sceglierlo.

---

## 4. La barra laterale, campo per campo

![Barra laterale all'avvio]({IMG}/m02_sidebar_blank.jpg)

![Barra laterale dopo aver scelto banda e materiale]({IMG}/m03_sidebar.jpg)

| Campo | Cos'è | Note |
|---|---|---|
| **Banda** | frequenza di lavoro | bande radioamatoriali 10.368, 24.048, 47.088, 76.032, 122.25, 134.928 GHz, oppure **Altra frequenza…** (10–140 GHz) |
| **λ** | lunghezza d'onda nello spazio libero | tutti i valori "λ" di FeedLab si riferiscono a questa |
| **Parabola / Feed** | riepilogo della parabola e del feed scelti | compare dopo la scelta |
| **ℹ️ Informazioni sui materiali** | pulsante sopra la scelta del materiale | apre una tabella di confronto: conducibilità, rugosità, densità, perdite rispetto al rame, e voti a pallini colorati (rosso = scarso … verde = ottimo) per lavorabilità, prezzo, reperibilità, resistenza agli agenti atmosferici e trattamenti, con pro e contro di ogni materiale. Il materiale scelto è evidenziato in giallo |
| **Materiale del feed** | il metallo (o il rivestimento) del feed | fissa conducibilità σ e rugosità → perdite ohmiche e rumore aggiunto; sotto: σ, **profondità di penetrazione δ** alla tua frequenza e una nota pratica (§15.1) |
| **Guida d'onda rettangolare** | la guida WR a cui si fissa il feed tramite la piastrina λ/4 | solo le guide della banda: 10 GHz **WR-90** o **WR-75**, 24 GHz **WR-42**, 47 GHz **WR-22** o **WR-19**… Dimensiona piastrina, foratura e base quadrata |
| **Base del feed** | **Circolare** o **Quadrata** | quadrata (default a 10 e 24 GHz) solo per le flange standard quadrate (WR-90 41.40 mm, WR-75 38.30 mm, WR-42 22.41 mm); si allarga da sola se fori o lamature lo richiedono |
| **Lingua** | Italiano / English | si sceglie nell'installer; qui serve soprattutto per la versione portable |
| **ℹ️ Credits · 🔄 Controlla aggiornamenti · 📖 Manuale · 🐞 Segnala un problema** | autore e fonti · nuove versioni · questo manuale · segnalazione GitHub precompilata | |


![Informazioni sui materiali]({IMG}/m34_materials.jpg)

---

## 5. Passo 1 — Procedura guidata

![Procedura guidata con una parabola a catalogo]({IMG}/m04_wizard.jpg)

Tre colonne: **parabola** (sinistra), **opzioni** (centro), **riepilogo della parabola** (destra: f/D equivalente, angolo di apertura, diametro in λ, HPBW, guadagno al 60 %, perdita di Ruze per la precisione della superficie che inserisci).

### 5.1 Parabola

**Catalogo commerciale (datasheet)** — scegli **Costruttore** e **Modello** (in ordine alfabetico). Sotto il modello trovi la **fonte** di ogni dato e una tabella: tipo (offset/prime focus), dimensioni esterne, area attiva, f/D del costruttore, focale (e da dove viene), angolo di offset, illuminazione richiesta, efficienza dichiarata, guadagni, collare LNB, materiale. Spunta **Ho misurato la mia parabola** per inserire asse lungo, asse corto e profondità al centro: le misure sono più precise di molti datasheet. Se la **focale non è pubblicata**, la tabella lo dice: tendi un filo sul bordo lungo l'asse lungo e misura la profondità massima.

**Parabola custom**

![Parabola custom]({IMG}/m09_custom.jpg)

| Tipo di parabola | Dati che puoi dare |
|---|---|
| **Offset (TV/sat)** | diametro + f/D · misure del riflettore (asse lungo, asse corto, profondità) · diametro + focale · diametro + angolo di illuminazione richiesto |
| **Prime focus** | diametro e f/D, oppure diametro e profondità al centro |

### 5.2 Opzioni

![Opzioni e illuminazione della parabola]({IMG}/m05_wizard_options.jpg)

| Campo | Scelte | Cosa cambia |
|---|---|---|
| **Polarizzazione** | Lineare / Circolare | la circolare aggiunge un polarizzatore (septum o dielettrico) ai consigli; esclude la tromba rettangolare |
| **Obiettivo** | Massimo guadagno (TX/terrestre) · **Massimo G/T (RX, EME, sole)** — predefinito · Massime prestazioni RX (minimo rumore) | G/T e RX progettano il feed per un f/D un po' più grande (illuminazione più morbida al bordo: meno spillover e meno rumore dal terreno); RX preferisce anche i feed con lobi laterali e posteriori bassi |
| **Mezzi di costruzione** | Tornio / CNC · Solo lamiera e saldatura | con la lamiera vengono preferiti guida aperta, tromba rettangolare e W2IMU |
| **Stima con simulazione rapida** | sì/no | fa girare il mode matching su ogni candidato (~20 s) |
| **Illuminazione della parabola** | **Automatica (consigliata)** · Taper al bordo scelto da me | vedi 5.3 |
| **Taper al bordo (dB)** | 6–25 dB, predefinito **10 dB** | attivo con "Taper al bordo scelto da me" |

### 5.3 Illuminazione della parabola

![Illuminazione automatica]({IMG}/m06_illum_auto.jpg)

Il **taper al bordo** dice quanto il segnale sul bordo della parabola è più debole che al centro (lobo del feed + percorso più lungo dal fuoco al bordo).

- **Automatica**: il feed è progettato per l'obiettivo scelto; il riquadro mostra il taper che ne risulta (per esempio circa 12.8 dB su una parabola f/D 0.69 con obiettivo G/T).
- **Taper al bordo scelto da me**: imposti tu il taper; FeedLab progetta il feed per l'f/D che lo dà.

**L'illuminazione cambia davvero il feed:** tutte le schede costruiscono il feed per l'*f/D di progetto* che ne risulta, aggiornato subito quando muovi il taper. In Progetto feed lo vedi scritto: "Progettato per f/D 0.65: taper al bordo 10.0 dB sulla parabola (f/D 0.69)".

![Taper al bordo scelto dall'utente]({IMG}/m07_illum_taper.jpg)

Il riquadro mostra l'**illuminazione lungo il diametro** (con le linee a −3 e −10 dB), la **parabola illuminata** in 3D (chiaro = più segnale, anelli a −3/−10 dB, feed nel fuoco e cono di illuminazione), lo **spillover**, l'**efficienza di illuminazione (taper)**, il loro prodotto, la **superficie entro −3 e −10 dB** e l'**f/D di progetto**.

| Taper al bordo | Uso tipico |
|---|---|
| 8–10 dB | massimo guadagno, TX terrestre; più spillover |
| 10–12 dB | ottimo classico: circa 81–82 % (spillover × taper) |
| 12–16 dB | più G/T: EME e RX, meno rumore dal terreno, un po' meno guadagno |
| > 16 dB | illuminazione molto morbida: buona parte della superficie è sprecata |

(Modello: lobo del feed cos^q, Balanis/Kildal; parabole offset come apertura circolare equivalente; blocking, errori di fase e perdite sono nella scheda Simulazione.)

### 5.4 Trova il feed migliore

Premi **🔎 Trova il feed migliore**: FeedLab ordina i feed adatti a parabola, obiettivo, mezzi e illuminazione.

![Classifica dei feed candidati]({IMG}/m08_results.jpg)

| Colonna | Significato |
|---|---|
| **η stimata %** | efficienza sulla tua parabola (illuminazione × spillover × fase × cross-pol × blocking) |
| **f/D ottimo del feed** | dove questo feed renderebbe al meglio |
| **Ingombro Ø mm** | diametro di blocking (prime focus) |
| **Perché / Attenzione** | motivi della scelta e limiti (per esempio "verifica con openEMS") |

Scegli il feed in **Feed da progettare** e premi **➡️ Usa questo feed**. Puoi anche scegliere qualsiasi feed direttamente in Progetto feed.

### 5.5 Tipi di feed

| Feed | Campo d'uso | Note |
|---|---|---|
| **Axial Corrugated Feedhorn CT1DMK**, parametric calculation OE2IGL | 10–76 GHz, f/D 0.33–0.9 (offset ≤ 0.8) | 81–86 %; 8 scalini assiali (OE2IGL v1.4); verifica con openEMS |
| **Chaparral 3 anelli** | prime focus f/D < 0.33 | 78 % a f/D 0.35; openEMS |
| **Horn conico** | uso generale | semplice, a larga banda |
| **Dual-Flare, IZ0JNY** | f/D 0.6–0.9, EME | scalino + cono + cilindro di fasatura + secondo cono; temperatura d'antenna bassa, S11 molto basso; verificato con openEMS a 24 GHz |
| **Dual-mode "optimum" Skobelev** | f/D > 0.9 | verificare full-wave prima di costruire |
| **Large W2IMU flare 30°** | offset f/D 0.65–0.85, 47–241 GHz | su offset +1.6…2.3 dB di sun noise (W1GHZ 2024) |
| **Guida circolare aperta** | parabole piccole e profonde | blocking minimo, F/B scarso |
| **Pickett-Potter** | f/D 0.5–0.95, anche oltre 76 GHz | ~80 % (OE2IGL) |
| **Tromba rettangolare** | polarizzazione lineare, < 40 GHz | lamiera, direttamente dalla WR |
| **VE4MA / Super-VE4MA** | prime focus f/D 0.35–0.45 | choke; openEMS |
| **W2IMU dual-mode / W2IMU Dual-Mode Feedhorn**, parametric calculation OE2IGL | offset / f/D 0.5–0.95 | regole W1GHZ / calcolo parametrico OE2IGL dall'angolo di apertura |

I feed ottimizzati con openEMS per una f/D precisa non sono nella lista: sono **file progetto** in `fdtd/results/feedlab/` (per f/D 0.4 a 10 e 24 GHz, parabole da 3 e 3.7 m: corrugato 83.5 %, Chaparral 80.1 %, VE4MA 80.3 %, W2IMU 73.5 %). Si aprono con **📂 Apri progetto** e danno feed, parabola e quote già impostati. Un progetto della 0.4.28 con «Feed 0.4 f/D» si apre come Axial Corrugated con le sue quote.

---

## 6. Passo 2 — Progetto feed

![Progetto feed]({IMG}/m10_design.jpg)

| Campo | Significato |
|---|---|
| **Tipo di feed** | tutti i feed, in ordine alfabetico |
| **Spessore parete (mm)** | parete metallica dell'horn |
| **Spessore base del feed (mm)** | vuoto = **automatico** (quanto serve a fori e filetti); minimo 1 mm; filetti e lunghezze delle viti si adattano |
| **Quote interne** | dipendono dal feed; ogni campo ha il nome della quota nella tua lingua e la sigla che compare sulla sezione (es. «lunghezza del cono · flare_length»); **lunghezze in blu, diametri in verde, angoli dei flare in rosso** |
| **input_length** | allunga la guida d'ingresso diritta (feed più lungo, stesse prestazioni) |
| **Angoli dei flare** | cambiando un angolo si ricalcola la lunghezza del cono; i diametri restano |
| **Applica modifiche / Ripristina progetto** | **ogni** modifica — compresi spessore di parete e base — si applica solo con **Applica modifiche**; Ripristina torna alle quote della regola |

A destra: la **sezione assiale** con tutte le quote, lunghezza totale, ingombro, **tolleranza consigliata**, le note della regola di progetto e la riga **"Progettato per f/D …"** (dall'illuminazione, §5.3). I fori della base si scelgono nella scheda **🔩 Montaggio** (§10).

![Quote e pulsanti]({IMG}/m12_dims.jpg)

> **Promemoria openEMS.** Se cambi una quota di oltre il 5 % o un angolo di oltre 2°, una nota consiglia di verificare il feed con openEMS. È solo un consiglio.

### 6.1 Lavorazione CNC dell'esterno (facoltativa)

![Opzioni CNC]({IMG}/m11_cnc.jpg)

| Campo | Scelte | Effetto |
|---|---|---|
| **Profilo esterno** | Parete costante · Proposta 1: pieno fino alla fine del 1° cono · Proposta 2: esterno senza rientranze | più semplice ed economico al tornio/CNC; si aggiunge solo metallo all'esterno |
| **Raggio dei raccordi esterni (mm)** | 0 = spigoli vivi | arrotonda gli spigoli esterni; si riduce dove la parete diventerebbe troppo sottile. L'**interno non cambia mai** |

---

## 7. Passo 3 — Laboratorio

![Laboratorio]({IMG}/m13_lab.jpg)

### 7.1 Scenario d'uso

| Campo | Significato |
|---|---|
| **Obiettivo** | TX — massimo guadagno · RX — massimo G/T · EME — guadagno + G/T |
| **Elevazione** | elevazione dell'antenna (rumore dal terreno) |
| **NF LNA (dB)** | cifra di rumore del preamplificatore |
| **Perdita linea feed→LNA/PA (dB)** | perdita di guida/relè prima dell'LNA |
| **RMS superficie (mm)** | precisione della superficie (Ruze) |
| **Att. zenitale (dB)** | attenuazione atmosferica allo zenit |

### 7.2 Risultato e bilancio di rumore

![Risultato rispetto al progetto di partenza, Tsys]({IMG}/m14_lab_result.jpg)

Muovi i cursori delle quote: FeedLab ricalcola **Δ S/N**, efficienza, guadagno, **G/T**, temperatura d'antenna, S11 e taper al bordo.

| Obiettivo | Δ S/N |
|---|---|
| TX | ΔG |
| RX | Δ(G/T) |
| EME | ΔG + Δ(G/T) |

Sotto i valori:

- la **perdita ohmica** del feed nel materiale scelto e il rumore che aggiunge;
- la **temperatura di sistema**: **Tsys = temperatura d'antenna attenuata dalle perdite + rumore delle perdite (feed + linea) + preamplificatore**, e G/T = G − 10·log10(Tsys). Esempio a 10 GHz: con NF 1 dB il preamplificatore aggiunge 75 K, con 2 dB 170 K; su una parabola fredda (antenna ~20–40 K) Tsys quasi raddoppia e il G/T scende di circa 2.5–3 dB — ecco perché un buon LNA conta così tanto;
- spillover, illuminazione, fase, polarizzazione, blocking e posizione del centro di fase.

Il **lobo** (variante a tratto pieno, progetto tratteggiato) mostra i **punti a −10 dB** dei piani E e H e il **bordo della parabola**, con gli angoli nel sottotitolo (per esempio "−10 dB: 66.3° (E) / 71.3° (H) · parabola: 79.6°"). Il grafico **efficienza vs f/D** ha le tacche ogni **0.1** e una linea tratteggiata sulla tua parabola.

### 7.3 Consigli, sensibilità, ottimizzazione

![Consigli]({IMG}/m15_lab_advice.jpg)

- **💡 Consigli** in parole semplici; **✅ Applica queste quote al progetto** copia la variante in Progetto feed.
- **🔬 Sensibilità**: quanto cambia il risultato variando ogni quota.
- **🤖 Ottimizzazione automatica**: scegli le quote, il numero di valutazioni e l'S11 massimo.

![Ottimizzazione]({IMG}/m16_lab_opt.jpg)

### 7.4 Tolleranze di lavorazione e resa

![Tolleranze]({IMG}/m17_lab_tol.jpg)

| Campo | Significato |
|---|---|
| **Tolleranza di lavorazione ± (mm)** | la tolleranza dell'officina |
| **Distribuzione** | Uniforme entro ±t (prudente) · Normale con ±t = 3σ (CNC capace) |
| **Perdita ammessa (dB) / S11 massimo (dB)** | cosa è ancora accettabile |
| **🎲 Analizza tolleranze** | Monte Carlo: **resa**, perdita media, dispersione, S11 peggiore, **quote critiche** con la tolleranza che serve a ciascuna |
| **📄 Usa queste tolleranze nel disegno PDF** | aggiunge la tabella al disegno |
| **🛡️ Ottimizzazione robusta** | quote che restano buone entro le tolleranze (media − k·σ) |

---

## 8. Passo 4 — Simulazione & S11

![Simulazione]({IMG}/m18_sim.jpg)

| Comando / risultato | Significato |
|---|---|
| **Banda di analisi ± %, punti in frequenza, modi** | ampiezza della scansione e precisione del risolutore |
| **S11 ingresso TE11** | return loss sulla banda (la transizione dalla WR non è inclusa) |
| **Contenuto modale all'apertura** | TE11, TM11, TE12 rispetto al TE11 (Pickett-Potter/Skobelev: TM11 ≈ 15 %, WA6KBL) |

![Lobo con l'angolo a −10 dB]({IMG}/m19_sim_pattern.jpg)

Il **lobo del feed** mostra i piani E e H, i **punti a −10 dB** (rombi) e il **bordo della parabola** (verde tratteggiato), con "−10 dB: …° (E) / …° (H) · parabola: …°" sotto il titolo. Se l'angolo a −10 dB è vicino all'apertura della parabola, il taper al bordo è circa 10 dB più l'attenuazione di spazio.

![Efficienza della parabola vs f/D]({IMG}/m20_sim_eff.jpg)

| Risultato | Significato |
|---|---|
| **Efficienza della parabola vs f/D** | totale, spillover, illuminazione, fase, cross-pol; tacche ogni 0.1; linea tratteggiata = la tua parabola |
| **η sulla tua parabola, taper al bordo, f/D ottimo del feed, centro di fase** | i numeri principali |
| **HPBW della parabola, HPBW E/H, primo lobo laterale** | dall'illuminazione di questo feed |
| **Riquadro G/T** | elevazione, NF del ricevitore, attenuazione zenitale → temperatura di cielo, d'antenna e del ricevitore, **Tsys** e G/T, con l'effetto di 1 dB di NF in più |

---

## 9. Lobo 3D e Modello 3D

![Lobo 3D]({IMG}/m21_lobe3d.jpg)

![Modello 3D]({IMG}/m22_model3d.jpg)

**Lobo 3D**: lobo di irradiazione normalizzato (dinamica regolabile). **Modello 3D**: il solido reale dello STEP/STL, con la base forata; *Sezione a quarto* mostra l'interno.

---

## 10. Passo 5 — Montaggio feed + piastrina

Questa scheda decide **come si fissano il feed e la piastrina λ/4 al tronchetto di guida d'onda esterno** (la flangia WR-90, WR-75 o WR-42 del tuo relè o LNA, oppure una flangia rotonda MIL da 47 GHz). La piastrina e la base del feed hanno sempre **lo stesso pattern di fori della flangia standard**, nella stessa posizione.

### 10.1 Scegli lo schema

| Schema | Come si monta | Cosa imposta FeedLab |
|---|---|---|
| **Viti dal lato del feed** | le viti entrano dal lato del feed, testa nella lamatura della base, attraversano base e piastrina e si avvitano nella flangia della guida | fori passanti in base e piastrina (Ø della flangia arrotondato al decimo: WR-42 3.07 → 3.1), lamatura nella base |
| **Viti dal lato della guida** | le viti della guida attraversano flangia e piastrina e si avvitano nella base | fori filettati passanti nella base (24 GHz M3, 10 GHz M4…), passanti nella piastrina |
| **Piastrina avvitata alla base del feed con viti in lamatura (guida avvitata alla piastrina)** | la guida si avvita alla piastrina; 4 viti a brugola (WR-42: M2.5) nelle lamature della piastrina la fissano alla base | fori della flangia filettati M3 6H nella piastrina, 4 viti piastrina→feed sugli assi (WR-42: a 9.00 mm), fori filettati ciechi nel feed |
| **Da 47 GHz: viti dal lato del feed + pin / viti della guida filettate nella base + pin** | flangia rotonda MIL; i pin della flangia allineano tutto | fori passanti o filettati (4-40), fori per i pin in piastrina e base |
| **Nessun foro** | fissaggio a cura tua | niente |

![Viti dal lato del feed]({IMG}/m23_mount_feedside.jpg)

A destra, la **sezione** del pacco (flangia della guida esterna | piastrina | base del feed | feed) mostra dove sono viti, filetti e lamature.

![Viti dal lato della guida]({IMG}/m24_mount_guideside.jpg)

![Piastrina avvitata alla base del feed con viti in lamatura (guida avvitata alla piastrina)]({IMG}/m25_mount_plate.jpg)

### 10.2 Avanzate: ogni dettaglio

Apri **⚙️ Avanzate: fori, filetti, lamature, viti, piastrina**. Ogni schema conserva le sue impostazioni.

![Menu avanzato]({IMG}/m26_mount_adv.jpg)

| Campo | Predefinito | Limiti / note |
|---|---|---|
| **Ø fori nella base del feed** | foro della flangia arrotondato (WR-42 3.1) | da misura della vite + 0.1 al Ø più grande che lascia **1 mm di metallo** verso il bordo più vicino |
| **Filettatura dei fori nella base** | 10 GHz M4 (o M3), 24 GHz M3 (M2.5, M2); equivalenti UNC; MIL 4-40 | filettati per tutto lo spessore della base |
| **Lamatura per la testa della vite (base)** | attiva con "viti dal lato del feed" | Ø e profondità modificabili (M3: 6.5 × 3.1); la base si ispessisce fino a lamatura + 1.5 mm |
| **Fori della flangia filettati nella piastrina** | attivi con lo schema IZ0JNY | 6H |
| **Ø fori della flangia nella piastrina** | come la base | regola del millimetro |
| **4 viti piastrina → feed** | attive con lo schema IZ0JNY | 24 GHz M2.5 o M2, 10 GHz M3 o M4; lunghezza = 2 × spessore della piastrina |
| **Testa delle viti** | A brugola con lamatura (ISO 4762) | oppure testa piana Phillips svasata (ISO 7046) |
| **Lamatura delle viti nella piastrina: Ø / profondità** | standard per la testa (M2.5: 5.5 × 2.5) | modificabili |
| **Fori per i pin di allineamento** | attivi (flange MIL) | passanti nella piastrina, 3 mm nella base |
| **Misura esterna della piastrina** | automatica: come la flangia, più grande se le viti della piastrina lo richiedono (WR-42 + M2.5: 25.5 mm) | puoi scrivere la tua (per esempio 27.86) |
| **Raggio angoli esterni** | 2 mm (piastrine quadrate) | |
| **Spessore della piastrina** | il λ/4 calcolato | cambia **solo se lo imposti tu**; un corpo più spesso ha una tasca sul lato feed |

![Menu avanzato, seguito]({IMG}/m27_mount_adv2.jpg)

### 10.3 3D in tempo reale

![Piastrina e feed in 3D]({IMG}/m28_mount_3d.jpg)

Sotto, la **piastrina** e il **feed con la base forata** in 3D **si aggiornano a ogni modifica**, con misura e spessore della piastrina, spessore della base e gli avvisi (per esempio "le teste delle viti toccano il corpo del feed", "la svasatura del feed sovrasta le viti: serve una chiave a brugola a L", "base quadrata allargata per tenere fori e lamature all'interno").

---

## 11. Passo 6 — Piastrina WR

![Piastrina WR]({IMG}/m29_plate.jpg)

La **piastrina λ/4** collega la guida circolare del feed alla guida rettangolare WR (design guide OE2IGL, ottimizzazione HB9PZK). L'orientamento della WR fissa la polarizzazione: il campo E è parallelo al lato corto *b*.

| Campo | Significato |
|---|---|
| **Polarizzazione** | Verticale / Orizzontale (ruota apertura e fori di 90°) |
| **Ø guida circolare del feed** | diametro d'ingresso del feed (proposto dal progetto) |
| **Raggio angoli apertura** | raggio della fresa negli angoli (FeedLab compensa la larghezza); con R2.00 sulla WR-42 l'apertura è 9.50 × 6.21 mm |
| **Versione ottimizzata** | b e spessore corretti con openEMS (consigliata) |
| **Risultati** | apertura a × b, **spessore λ/4** con la sua tolleranza critica, Z0 intermedia |

I fori vengono dalla scheda **Montaggio** (una nota ricorda lo schema).

![Vista frontale e vista 3D]({IMG}/m30_plate_views.jpg)

La **vista frontale** colora i fori per funzione: **nero** = fori della flangia della guida, **magenta** = fissaggio della piastrina (lamatura/svasatura), **verde** = pin di allineamento. **📄 Disegno PDF piastrina** dà un disegno d'officina quotato: misura esterna e metà, posizione dei fori, apertura, raggi, richiami dei fori raggruppati per funzione (**FLANGIA GUIDA**, **FISSAGGIO PIASTRINA**, **PIN ALLINEAMENTO**) e la tabella dei fori con coordinate e tolleranze. **🧊 STEP piastrina** dà il solido.

---

## 12. Passo 7 — Disegno & STEP

![Disegno & STEP]({IMG}/m31_drawing.jpg)

| Campo / pulsante | Significato |
|---|---|
| **Materiale, Titolo** | scritti nel cartiglio |
| **Tolleranza generale di lavorazione ±** | predefinita: il valore consigliato per la banda (§15.2); scritta nei PDF di feed e piastrina con le tolleranze dei fori |
| **📄 Genera PDF** | disegno A4: sezione quotata, tabella delle quote (mm e λ), cartiglio; **foglio 2** = flangia forata; tabella delle tolleranze critiche (dal §7.4) |
| **🧊 Genera STEP / 🖨️ Genera STL** | solido per CAD/CAM (filetti al Ø di preforo) / per la stampa 3D |
| **Parametri JSON** | tutte le quote e le impostazioni |

**Tolleranze dei fori nei disegni:** filetti ISO 6H · fori spina H7 (pin m6) · fori passanti +0.1/0 · lamature +0.2/0.

---

## 13. Full-wave openEMS (facoltativo)
14. Output di progetto (PDF, tabelle, file di progetto)

![openEMS]({IMG}/m32_openems.jpg)

| Sottoscheda | Cosa fa |
|---|---|
| **① Installazione openEMS** | installazione guidata su Windows (build ufficiale, cartella utente, `OPENEMS_INSTALL_PATH`, binding Python, simulazione di prova); su Linux/macOS indichi la cartella |
| **② Nuova analisi** | simulazione singola, convergenza della mesh o sweep di un parametro; oppure uno script da far girare su un altro PC |
| **③ Simulazioni** | simulazioni in corso e terminate |
| **④ Risultati** | S11, lobi, efficienza, guadagno, G/T, centro di fase; caricamento di un `results.json` da un altro PC; confronto tra simulazioni |
| **⑤ Space mapping** | corregge il progetto del risolutore rapido con il risultato di openEMS |

> **Mesh.** In **② Nuova analisi** si impostano **Celle per λ** nel feed (100 di default: le quote restano entro circa λ/200, ±0.15 mm a 10 GHz), **Celle per λ in aria** (20: fuori dal feed la mesh si allarga gradualmente), la **gradazione** (rapporto massimo tra celle vicine, 1.4) e la **simmetria** (modello intero, mezzo o quarto). La tabella sotto mostra per ogni simulazione celle, RAM e durata stimate, e si aggiorna a ogni cambio. Le linee di griglia stanno sempre su ogni spigolo del feed: raggi e lunghezze sono esatti; con poche celle per λ si perde la forma delle scanalature e delle pareti inclinate.

> **Invito alla validazione.** Ogni 5 modifiche al progetto (quote, materiale, illuminazione, base, montaggio…) compare un avviso che invita a lanciare una simulazione openEMS: è più lenta ma più precisa del simulatore veloce, valida i dati e mostra se i due risultati convergono. Con **⑤ Space mapping** il risultato di openEMS corregge poi il progetto.

---

## 14. Output di progetto (PDF, tabelle, file di progetto)

![Output di progetto]({IMG}/m35_output.jpg)

Nella scheda **📦 Output di progetto** scegli quali documenti generare, premi **⚙️ Genera** e scarica i file uno per uno oppure tutti insieme con **⬇️ Scarica tutto (ZIP)**. Ogni documento riporta in testa feed, banda, parabola e materiale, e in fondo versione di FeedLab e data UTC.

| Documento | Contenuto |
|---|---|
| **📄 Report completo di progetto (PDF)** | copertina con i risultati principali, simulazioni veloci, parabola, disegno del feed, piastrina, montaggio, openEMS e tabella di tutti i dati |
| **📈 Simulazioni veloci (PDF)** | guadagno, G/T, efficienze, taper, S11, centro di fase, Tsys e lo scenario usato; S11 su ±5 % della banda; lobo nei piani E e H con il bordo della parabola |
| **📐 Feed: disegno e simulazioni (PDF)** | il disegno quotato della scheda Disegno & STEP seguito dalle simulazioni |
| **📡 Parabola (PDF)** | dati della parabola, angolo di apertura, f/D di progetto del feed, illuminazione e scomposizione dell'efficienza |
| **🔲 Piastrina λ/4 (PDF)** | il disegno della piastrina (si include dopo aver aperto una volta la scheda 🔲 Piastrina WR) |
| **🔩 Feed + piastrina, montaggio (PDF)** | schema di montaggio, viti, spessori e sezione |
| **📋 Tabella di tutte le quote e i dati (PDF + CSV)** | ogni valore inserito o calcolato: dati di progetto, quote del feed, piastrina, risultati, openEMS; il CSV si apre con Excel / LibreOffice |
| **🖥️ Simulazioni openEMS (PDF)** | per ogni simulazione completata di questo feed e banda: guadagno, G/T, efficienza, centro di fase, fascio, S11 e lobo full-wave |
| **💾 File di progetto (.json)** | tutto il progetto: dati inseriti e risultati calcolati. Si scambia con altri radioamatori e si riapre in FeedLab |
| **🧊 Modelli 3D del feed (STEP + STL)** | come nella scheda Disegno & STEP |

**📂 Apri un file di progetto**: carica un `.feedlab.json` e premi **Apri progetto** per ritrovare banda, parabola, feed, quote modificate, materiale, illuminazione, guida e montaggio.

Lo scenario delle simulazioni (elevazione, NF, perdite, superficie, attenuazione) è quello impostato nel **Laboratorio**; se non l'hai aperto, valgono i valori predefiniti del Laboratorio.

---

## 15. Tabelle di riferimento

### 15.1 Materiali

| Materiale | σ (10⁷ S/m) | profondità di penetrazione δ (µm) a 10 / 24 / 47 / 76 GHz | Rq (µm) | Perdite × rame | Nota pratica |
|---|---|---|---|---|---|
| Rame argentato (Ag ≥ 3 µm) | 6.10 | 0.63 / 0.42 / 0.30 / 0.23 | 0.3 | 1.0× | argentatura ≥ 3-5 δ; migliore per RX a mm-wave |
| Ottone argentato | 6.10 | 0.63 / 0.42 / 0.30 / 0.23 | 0.3 | 1.0× | lavorabilità dell'ottone + perdite dell'argento |
| Rame C101 OFE (Weerg) | 5.85 | 0.65 / 0.42 / 0.30 / 0.24 | 2 | 1.0× | rame senza ossigeno; finitura di serie Ra 1.6–3.2 µm: per l'interno chiedi Ra ≤ 0.8 (perdite più basse) |
| Rame OFHC (Cu-ETP) | 5.80 | 0.65 / 0.43 / 0.30 / 0.24 | 0.4 | 1.0× | ottimo conduttore, si ossida: proteggere |
| Rame C110 ETP (PCBWay) | 5.80 | 0.65 / 0.43 / 0.30 / 0.24 | 2 | 1.0× | rame elettrolitico; finitura di serie Ra 1.6–3.2 µm: per l'interno chiedi Ra ≤ 0.8 (perdite più basse) |
| Rame T2 (JLCCNC) | 5.70 | 0.65 / 0.43 / 0.31 / 0.24 | 2 | 1.0× | rame puro 99.9 %; finitura di serie Ra 1.6–3.2 µm: per l'interno chiedi Ra ≤ 0.8 (perdite più basse) |
| Stampa 3D + elettrodeposizione rame | 5.00 | 0.70 / 0.46 / 0.33 / 0.26 | 3 | 1.1× | rugosità della stampa domina sopra 24 GHz |
| Rame dorato (Au flash su Ni) | 4.10 | 0.77 / 0.51 / 0.36 / 0.29 | 0.3 | 1.2× | evitare il nichel sotto: è magnetico e dissipa |
| Alluminio 1050 puro | 3.50 | 0.84 / 0.55 / 0.39 / 0.31 | 0.6 | 1.3× | più conduttivo ma tenero |
| Alluminio 6082-T6 Anticorodal (Weerg) | 2.60 | 0.97 / 0.64 / 0.45 / 0.36 | 2 | 1.5× | resistente alla corrosione; finitura di serie Ra 1.6–3.2 µm: per l'interno chiedi Ra ≤ 0.8 (perdite più basse) |
| Alluminio 6082/6061 T6 | 2.50 | 0.99 / 0.65 / 0.46 / 0.37 | 0.6 | 1.5× | leggero; anodizzazione solo esterna |
| Alluminio 6061-T6 (JLCCNC, PCBWay) | 2.50 | 0.99 / 0.65 / 0.46 / 0.37 | 2 | 1.5× | il più comune; finitura di serie Ra 1.6–3.2 µm: per l'interno chiedi Ra ≤ 0.8 (perdite più basse) |
| Alluminio 2011 (Weerg) | 2.30 | 1.03 / 0.68 / 0.48 / 0.38 | 2 | 1.6× | da tornio, ottima lavorabilità; finitura di serie Ra 1.6–3.2 µm: per l'interno chiedi Ra ≤ 0.8 (perdite più basse) |
| Alluminio 5052 (PCBWay) | 2.00 | 1.11 / 0.73 / 0.52 / 0.41 | 2 | 1.7× | anticorrosione; finitura di serie Ra 1.6–3.2 µm: per l'interno chiedi Ra ≤ 0.8 (perdite più basse) |
| Alluminio 7075-T6 Ergal (JLCCNC, PCBWay, Weerg) | 1.90 | 1.13 / 0.74 / 0.53 / 0.42 | 2 | 1.7× | molto resistente, conduce meno del 6061; finitura di serie Ra 1.6–3.2 µm: per l'interno chiedi Ra ≤ 0.8 (perdite più basse) |
| Alluminio 2A12 / 2024 (PCBWay) | 1.74 | 1.18 / 0.78 / 0.56 / 0.44 | 2 | 1.8× | aeronautico, conduce poco; finitura di serie Ra 1.6–3.2 µm: per l'interno chiedi Ra ≤ 0.8 (perdite più basse) |
| Alluminio 5083 (Weerg) | 1.60 | 1.24 / 0.81 / 0.58 / 0.46 | 2 | 1.9× | anticorrosione marina, conduce poco; finitura di serie Ra 1.6–3.2 µm: per l'interno chiedi Ra ≤ 0.8 (perdite più basse) |
| Ottone H59 (JLCCNC) | 1.60 | 1.24 / 0.81 / 0.58 / 0.46 | 2 | 1.9× | ottone da lavorazione; finitura di serie Ra 1.6–3.2 µm: per l'interno chiedi Ra ≤ 0.8 (perdite più basse) |
| Ottone H62 (JLCCNC) | 1.57 | 1.25 / 0.82 / 0.59 / 0.46 | 2 | 1.9× | ottone; finitura di serie Ra 1.6–3.2 µm: per l'interno chiedi Ra ≤ 0.8 (perdite più basse) |
| Ottone CuZn39Pb3 | 1.50 | 1.28 / 0.84 / 0.60 / 0.47 | 0.4 | 2.0× | ottima lavorabilità al tornio; perdite ~2× rame |
| Ottone C360 (PCBWay) | 1.50 | 1.28 / 0.84 / 0.60 / 0.47 | 2 | 2.0× | ottone da tornio (come CuZn39Pb3); finitura di serie Ra 1.6–3.2 µm: per l'interno chiedi Ra ≤ 0.8 (perdite più basse) |
| Ottone OT58 CuZn40Pb2 (Weerg) | 1.50 | 1.28 / 0.84 / 0.60 / 0.47 | 2 | 2.0× | ottone da tornio; finitura di serie Ra 1.6–3.2 µm: per l'interno chiedi Ra ≤ 0.8 (perdite più basse) |
| Bronzo CuSn12 (Weerg) | 0.55 | 2.11 / 1.38 / 0.99 / 0.78 | 2 | 3.2× | perdite alte (circa 3× l'ottone): non consigliato per l'interno |
| Acciaio inox AISI 304 | 0.14 | 4.18 / 2.74 / 1.96 / 1.54 | 0.4 | 6.4× | solo strutture: perdite elevate |
| Acciaio inox 316L (JLCCNC, PCBWay, Weerg) | 0.13 | 4.29 / 2.81 / 2.01 / 1.58 | 2 | 6.6× | solo strutture: perdite elevate |
| Stampa 3D + vernice al rame | 0.10 | 4.94 / 3.25 / 2.32 / 1.83 | 5 | 7.6× | perdite alte, solo prototipi/bande basse |
| Titanio Ti-6Al-4V (PCBWay) | 0.06 | 6.49 / 4.26 / 3.05 / 2.40 | 2 | 10.0× | solo strutture: perdite molto elevate |

I materiali con il nome del servizio (JLCCNC, PCBWay, Weerg) sono quelli lavorabili da questi servizi CNC online; la rugosità indicata (Rq ≈ 2 µm) è la loro finitura di serie: chiedendo l'interno lucidato (Ra ≤ 0.8 µm) le perdite scendono. Il pulsante **ℹ️ Informazioni sui materiali** mostra la stessa tabella con lavorabilità, prezzo, reperibilità, resistenza agli agenti atmosferici, trattamenti, pro e contro.

La corrente RF scorre in uno strato spesso pochi δ: i rivestimenti devono essere ≥ 3–5 δ, e una rugosità paragonabile a δ aumenta le perdite. FeedLab trasforma la perdita ohmica in temperatura di rumore aggiunta (Laboratorio).

### 15.2 Tolleranza generale di lavorazione

| Banda | Consigliata | Note |
|---|---|---|
| 10, 24 GHz | ±0.1 mm | diametri interni ≈ λ/100 |
| 47 GHz | ±0.05 mm | |
| 76 GHz | ±0.02 mm | |
| 122 / 134 GHz | ±0.01 mm | |

Lo spessore della piastrina λ/4 ha una sua tolleranza più stretta (WR-42: ±0.087 mm). L'analisi di tolleranza (§7.4) dice quali quote hanno bisogno di più precisione.

### 15.3 Flange standard (Flann; MIL-DTL-3922/67C)

| WR | Flangia | Forma | Misura (mm) | Posizione dei fori (mm) | Ø fori (pubblicato → FeedLab) | Vite |
|---|---|---|---|---|---|---|
| WR-90 | UBR 100 | quadrata | 41.40 | x ±15.49, y ±16.26 | 4.255 → 4.3 | M4 / 8-32 UNC |
| WR-75 | UBR 120 | quadrata | 38.30 | x ±13.21, y ±14.25 | 4.085 → 4.1 | M3 / 6-32 UNC |
| WR-42 | UBR 220 (UG-595/U) | quadrata | 22.41 | x ±8.13, y ±8.51 | 3.07 → 3.1 | M3 / 4-40 UNC |
| WR-22, WR-19 | UG-383/U | rotonda | Ø28.55 | PCD 23.81 (4 fori + 4 spine) | 3.05 → 3.1 | 4-40 UNC |
| WR-15 … WR-5 | UG-385/387/U | rotonda | Ø19.05 | PCD 14.29 (4 fori + 4 spine) | 3.05 → 3.1 | 4-40 UNC |

### 15.4 Viti, fori e teste

| Vite | Preforo | Passaggio (normale / medio) | Lamatura testa cilindrica Ø × prof. | Svasatura testa piana Ø |
|---|---|---|---|---|
| M2 | 1.6 | 2.4 / 2.4 | 4.4 × 2.1 | 4.0 |
| M2.5 | 2.05 | 2.8 / 2.9 | 5.5 × 2.5 | 4.9 |
| M3 | 2.5 | 3.2 / 3.4 | 6.5 × 3.1 | 5.7 |
| M4 | 3.3 | 4.3 / 4.5 | 8.0 × 4.4 | 8.6 |
| 2-56 UNC | 1.78 | 2.6 | 4.2 × 2.3 | 4.6 |
| 4-40 UNC | 2.26 | 3.0 / 3.4 | 5.3 × 3.0 | 5.9 |
| 6-32 UNC | 2.70 | 3.7 / 3.9 | 6.1 × 3.7 | — |
| 8-32 UNC | 3.45 | 4.3 / 4.5 | 7.9 × 4.4 | 8.6 |

Teste cilindriche ISO 4762 / ASME B18.3; teste piane ISO 7046 (90°) / UNC 82°. I fori ciechi filettati si forano a un numero pari di millimetri; il filetto arriva alla fine della vite e si ferma 3 passi (≥ 1 mm) prima del fondo.

---

## 16. Esempio completo: feed EME a 24 GHz per una offset da 2.4 m

1. **Barra laterale:** Banda **24.048 GHz**, materiale **Ottone CuZn39Pb3** (o ottone argentato), guida **WR-42**, base **Circolare**.
2. **Procedura guidata:** catalogo → **Channel Master Type 243 2.4 m**; obiettivo **Massimo G/T**; illuminazione **Automatica** o per esempio 12 dB; **Trova il feed migliore** → **Dual-Flare, IZ0JNY** → **Usa questo feed**.
3. **Progetto feed:** controlla "Progettato per f/D …"; spessore della base automatico; **Applica modifiche** dopo ogni modifica.
4. **Laboratorio:** obiettivo **EME**, NF dell'LNA e perdita di linea; leggi **Tsys** e Δ S/N; **Analizza tolleranze** a ±0.1 mm.
5. **Simulazione & S11:** S11 < −20 dB sulla banda; confronta l'**angolo a −10 dB** con l'apertura della parabola; η e centro di fase.
6. **Montaggio:** schema **Piastrina avvitata alla base del feed con viti in lamatura (guida avvitata alla piastrina)** — M3 6H nella piastrina, 4 viti a brugola M2.5 a 9.00 mm; in Avanzate imposta la misura esterna (per esempio 27.86 mm, R2) se vuoi.
7. **Piastrina WR:** raggio angoli apertura **2.00** (la tua fresa); **Disegno PDF piastrina** e **STEP piastrina**.
8. **Disegno & STEP:** tolleranza generale ±0.1 mm; **Genera PDF** (feed + flangia forata) e **Genera STEP**.
9. **Facoltativo:** openEMS prima di tagliare il metallo.

---

## 17. Problemi frequenti

| Problema | Cosa fare |
|---|---|
| "Windows ha protetto il PC" | Ulteriori informazioni → Esegui comunque |
| Non compare la finestra di aggiornamento | premi **🔄 Controlla aggiornamenti**: mostra l'errore preciso. 0.4.17/0.4.18: installa a mano una volta la versione attuale |
| Una scheda mostra solo "Per iniziare seleziona…" | scegli banda e materiale (barra laterale), parabola (Procedura guidata), tipo di feed (Progetto feed) |
| Ho cambiato una quota ma non succede niente | premi **Applica modifiche** (Progetto feed) |
| La base è più spessa del previsto | i fori ciechi delle viti della piastrina hanno bisogno di profondità: imposta tu lo spessore della base oppure usa viti più piccole o un altro schema |
| La piastrina è più grande della flangia | le viti della piastrina hanno bisogno di spazio (1 mm fuori dalla lamatura): M2, teste piane, oppure imposta la misura in Montaggio → Avanzate |
| "le teste delle viti toccano il corpo del feed" | allunga la guida d'ingresso o usa lo schema "viti dal lato della guida" |
| I feed ad anelli/scanalature non mostrano l'S11 | usa openEMS |
| I risultati sono diversi dalla mia misura | le parabole reali stanno 12–15 punti sotto; controlla focale e posizione del feed (centro di fase nel fuoco) |

---

## 18. Glossario

| Termine | Significato |
|---|---|
| **f/D** | focale / diametro; per le offset: f/D equivalente visto dal feed |
| **f/D di progetto** | l'f/D per cui è progettato il feed, dall'illuminazione scelta |
| **Taper al bordo** | livello sul bordo rispetto al centro (dB) |
| **Spillover** | potenza del feed che non colpisce la parabola (persa, raccoglie rumore dal terreno) |
| **Efficienza di illuminazione (taper)** | quanto uniformemente è usata l'apertura |
| **Tsys** | temperatura di rumore del sistema: antenna + perdite + preamplificatore |
| **G/T** | guadagno su temperatura di sistema, la cifra di merito per RX ed EME |
| **S11 / return loss** | disadattamento all'ingresso del feed |
| **Centro di fase** | il punto da cui il feed sembra irradiare: va nel fuoco |
| **Mode matching** | risolutore rapido per feed in guida circolare fatti di scalini e coni |
| **Piastrina λ/4** | tratto di adattamento a quarto d'onda tra guida circolare e rettangolare |
| **Lamatura / svasatura** | sede a fondo piano per una testa cilindrica / sede conica per una testa piana |
| **6H, H7, m6** | classi di tolleranza ISO per filetti interni, fori e spine |

---

*FeedLab è software libero (GNU GPL v3.0 o successiva), © 2026 Ivan De Cesaris, IZ0JNY, senza alcuna garanzia: i risultati sono stime di progetto da verificare con simulazione full-wave e misure. Fonti: W1GHZ Online Microwave Antenna Book, design guide OE2IGL, Balanis, Kildal e i lavori elencati nella scheda Credits.*
