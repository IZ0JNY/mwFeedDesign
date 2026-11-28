# Modifiche per la prossima versione (0.4.30)

**Regola:** ogni 5 modifiche si fa una nuova build e la si pubblica su GitHub.

| # | Richiesta | Stato |
|---|---|---|

---

# Versione 0.4.29 (pubblicata, BETA TEST)

| # | Richiesta | Stato |
|---|---|---|
| 1 | **Parabola Gibertini OP 150 L** nel catalogo: offset 155 × 166 cm, F/D 0.66, 43.3 dBi a 10.95 GHz (η ≈ 68 %) | ✅ fatto |
| 2 | **Parabole offset custom fino a 12 m**: diametro, asse corto e focale (fino a 24 m) ammessi per offset fino a 12 m (prima 5–10 m), anche in «Ho misurato la mia parabola» | ✅ fatto |
| 3 | **Niente feed divisi per f/D nella lista**: tolto «Feed 0.4 f/D» (0.4.28); i feed ottimizzati con openEMS per f/D 0.4 (corrugato 83.5 %, Chaparral 80.1 %, VE4MA 80.3 %, W2IMU 73.5 %) sono file progetto in `fdtd/results/feedlab/` (10 e 24 GHz, parabole 3 e 3.7 m) da aprire con «📂 Apri progetto»; i progetti 0.4.28 con «Feed 0.4 f/D» si aprono come Axial Corrugated con le stesse quote; manuali IT/EN | ✅ fatto |
| 4 | **Mesh openEMS a 100 celle/λ**: nella parte openEMS (② Nuova analisi) si impostano celle per λ nel feed (fino a 120, default 100), celle per λ in aria (default 20, mesh graduata), gradazione e simmetria (intero, mezzo, quarto di modello), con stima di celle, RAM e durata; 100 celle/λ anche negli script openEMS e CST di Disegno & STEP (con stima), nello space mapping e nell'ottimizzatore `fdtd/`; manuali IT/EN | ✅ fatto |

---

# Versione 0.4.28 (pubblicata, BETA TEST)

| # | Richiesta | Stato |
|---|---|---|
| 1 | **Feed 0.4 f/D** nel catalogo dei feed: testa corrugata (8 scanalature assiali) ottimizzata con openEMS per f/D 0.4 (`fdtd/`, 200 simulazioni), 83.5 % con S11 ≤ −21 dB in f0 ± 2 %, verificata a 10.368 e 24.048 GHz; proposta dalla procedura guidata a 10 e 24 GHz per f/D 0.35–0.47; disegno, modello 3D e quote modificabili come l'Axial Corrugated | ✅ fatto |
| 2 | **Tab su più righe**: la barra dei tab in alto va a capo, così tutti i tab sono visibili senza scorrere in orizzontale | ✅ fatto |
| 3 | **Script per simulatori**: openEMS (script Python autonomo) e macro VBA per CST, scheda Disegno & STEP e Output di progetto | ✅ fatto |

---

# Versione 0.4.27 (pubblicata, BETA TEST)

| # | Richiesta | Stato |
|---|---|---|
| 1 | **Nomi dei feed con la virgola**: l'autore segue il nome dopo una virgola, senza parentesi («Axial Corrugated Feedhorn CT1DMK, parametric calculation OE2IGL», «W2IMU Dual-Mode Feedhorn, parametric calculation OE2IGL», «Large W2IMU flare 30°, W1GHZ/W1FKF», «Dual-mode 'optimum' Skobelev, W1GHZ», «Tromba rettangolare, G3RPE», «Dual-Flare, IZ0JNY») in interfaccia, report, manuali e documenti | ✅ fatto |
| 2 | **Titoli corti**: nel titolo del disegno, nell'intestazione e nella copertina del report il nome del feed senza «Feedhorn» e la banda in GHz (24.048 → «24 GHz», 10.368 → «10 GHz»); nelle schede e nelle tabelle restano il nome completo e la frequenza esatta | ✅ fatto |
| 3 | **Nome dei file salvati a scelta**: casella «Nome file» precompilata col nome predefinito in Disegno & STEP, Piastrina, Output di progetto e openEMS; se la si lascia così si usa il predefinito, l'estensione si aggiunge da sola | ✅ fatto |
| 4 | Scheda 🧊 Modello 3D: vista 3D più grande (altezza 900 px, margini ridotti, camera più vicina) per usare tutto lo spazio | ✅ fatto |

---

# Versione 0.4.26 (pubblicata, BETA TEST)

| # | Richiesta | Stato |
|---|---|---|
| 1 | **FeedLab per Linux**: pacchetto .deb (Debian/Ubuntu) e AppImage (un solo file, senza installazione), compilati da GitHub Actions (`linux/build.sh`) e pubblicati nella stessa release di Windows; finestra propria GTK/WebKit o browser | ✅ fatto |
| 2 | **Nomi neutri dei feed**: «Axial Corrugated Feedhorn CT1DMK (parametric calculation OE2IGL)» e «W2IMU Dual-Mode Feedhorn (parametric calculation OE2IGL)» al posto di «versione migliorata»/«ottimizzato»; «Pickett-Potter» e «W2IMU dual-mode» senza autori nel nome (restano nei crediti); tolti i giudizi (migliore, il più efficiente…) da nomi e descrizioni dei feed in interfaccia, manuali IT/EN e documenti | ✅ fatto |

---

# Versione 0.4.25 (pubblicata, BETA TEST)

| # | Richiesta | Stato |
|---|---|---|
| 1 | openEMS a 10 GHz: la parete della guida d'ingresso (0.5 mm fissi) cadeva tra le linee della griglia (celle di 1.3 mm) e la guida restava aperta; ora è spessa almeno due celle con le sue linee. Dual-Flare a 10368.2 MHz: 47.1 dBi, η 76 %, S11 < −18 dB; test di regressione | ✅ fatto |
| 2 | Inglese: note «migliore G/T su offset» e «classico W1GHZ» tradotte; «—» al posto di «None» nella tabella dei feed | ✅ fatto |

---

# Versione 0.4.24 (pubblicata, BETA TEST)

| # | Richiesta | Stato |
|---|---|---|
| 1 | **Dual-Flare (IZ0JNY) compatto**: tabella riottimizzata per f/D 0.6–0.9 (stesso G/T entro 0.01 dB, +0.02 dB di guadagno, 2–18 % più corto, S11 ≤ −25 dB su ±1 %); openEMS a 24048.2 MHz (30 celle/λ: S11 −24.9 dB, η 66.5 %) e 47088.2 MHz (S11 −21.6 dB) sulla CM243. A 10368.2 MHz la simulazione openEMS dà S11 −2.6 dB ed η 35 % per entrambi i feed (vecchio e nuovo): problema di impostazione della simulazione a 10 GHz (porta/dominio), da indagare | ✅ fatto |
| 2 | **File di progetto (.json)**: dati inseriti e risultati calcolati (guadagno, G/T, efficienze, taper, S11, lobi, Tsys, piastrina, openEMS); si scambia e si riapre in FeedLab | ✅ fatto |
| 3 | **Scheda «📦 Output di progetto»**: PDF a scelta (report completo, simulazioni veloci, feed, parabola, piastrina, feed + piastrina, tabella di tutte le quote e i dati + CSV, openEMS), file di progetto, STEP/STL, ZIP di tutto | ✅ fatto |
| 4 | Icona della piastrina: 🔲 al posto della spina elettrica | ✅ fatto |
| 5 | Catalogo parabole: materiali e note solo in italiano (niente tedesco) e tradotti in inglese («vetroresina» → fibreglass…); test automatico | ✅ fatto |
| 6 | EMELab: programma separato nel repository IZ0JNY/EMELab; tolto da FeedLab | ✅ fatto |
| 7 | Studio di sintesi di feed EME per la Channel Master 243 (relazione in docs/studi) e strumenti di sintesi | ✅ fatto |

---

# Archivio: versione 0.4.23 (pubblicata, BETA TEST)

| # | Richiesta | Stato |
|---|---|---|
| 1 | Manuale dettagliato in italiano e inglese: ogni scheda e ogni campo spiegati con screenshot nuovi (33 per lingua), scheda Montaggio, illuminazione, Tsys, angolo a −10 dB, tabelle di materiali, tolleranze, flange e viti, esempio completo, problemi frequenti, glossario | ✅ fatto |
| 2 | Montaggio: la didascalia sotto la sezione non si sovrappone più alla flangia della guida esterna (più spazio sotto il disegno) | ✅ fatto |
| 3 | Schema di montaggio rinominato "Piastrina avvitata alla base del feed con viti in lamatura (guida avvitata alla piastrina)" / "Plate screwed to the feed base with counterbored screws (waveguide screwed into the plate)", senza IZ0JNY | ✅ fatto |
| 4 | Viste 3D senza l'effetto "a stella" (righe scure che partono dai fori): Plotly scartava i triangoli lunghi e sottili della tessellazione; ora vengono disegnati tutti | ✅ fatto |
| 5 | Cursore del taper al bordo anche nel Laboratorio, collegato a quello della Procedura guidata (muovendo uno si muove l'altro); il feed si riprogetta e le simulazioni si aggiornano subito | ✅ fatto |
| 6 | Materiali dei servizi CNC online JLCCNC, PCBWay e Weerg (alluminio 6061/6082/7075/5083/5052/2011/2024, ottone H59/H62/C360/OT58, rame T2/C101/C110, bronzo CuSn12, inox 316L, titanio) con conducibilità e rugosità della finitura di serie | ✅ fatto |
| 7 | Pulsante «ℹ️ Informazioni sui materiali» sopra la scelta del materiale: finestra con tabella di confronto (conducibilità, rugosità, densità, perdite rispetto al rame, lavorabilità, prezzo, reperibilità, agenti atmosferici, trattamenti, pro e contro) con voti a pallini colorati | ✅ fatto |
| 8 | Lingue coerenti: in italiano solo italiano, in inglese solo inglese (nomi delle quote del feed con descrizione tradotta, «parabola» al posto di «dish», «lato tromba» al posto di «lato horn», nomi dei feed tradotti poco (Dual-mode, Horn conico, Large W2IMU flare restano), messaggi openEMS); nuovo test automatico sul catalogo e strumento tools/lang_audit.py che controlla tutta l'interfaccia | ✅ fatto |
| 9 | Base del feed: solo «Circolare» / «Quadrata»; quadrata di default a 10 e 24 GHz (flange quadrate), circolare da 47 GHz in su | ✅ fatto |
| 10 | Ogni 5 modifiche al progetto un avviso invita a validare il feed con una simulazione openEMS (più precisa del simulatore veloce) | ✅ fatto |

---

# Archivio: versione 0.4.22 (pubblicata, BETA TEST)

| # | Richiesta | Stato |
|---|---|---|
| 1 | Grafici efficienza vs f/D con tacche ogni 0.1 (Laboratorio e Simulazione) | ✅ fatto |
| 2 | Dettaglio Tsys (antenna, perdite, preamplificatore) sotto il G/T, con effetto di +1 dB di NF | ✅ fatto |
| 3 | Angolo a −10 dB del lobo (piani E e H) segnato sul grafico polare e confrontato con l'apertura della parabola | ✅ fatto |

---

# Archivio: versione 0.4.21 (pubblicata, BETA TEST)

| # | Richiesta | Stato |
|---|---|---|
| 1 | Nuova scheda Montaggio feed + piastrina: schemi di montaggio con disegno in sezione, fori impostati da FeedLab, menu avanzato con 3D di piastrina e feed in tempo reale | ✅ fatto |

---

# Archivio: versione 0.4.20 (pubblicata, BETA TEST)

Pubblicata con 4 modifiche (il manuale dettagliato è passato alla 0.4.21).

| # | Richiesta | Stato |
|---|---|---|
| 1 | Progetto feed: spessore parete e spessore base si applicano solo con "Applica modifiche", come tutte le altre quote ("Ripristina progetto" li riporta ad automatico) | ✅ fatto |
| 2 | L'illuminazione scelta nella procedura guidata (taper al bordo o obiettivo) cambia davvero il feed: tutte le schede lo costruiscono per l'f/D di progetto, che si aggiorna subito cambiando il taper; riga "Progettato per f/D…" in Progetto feed | ✅ fatto |
| 3 | Fori nella base del feed spostati nella scheda Progetto feed (fissaggio di feed + piastrina al tronchetto di guida esterno; stessa foratura nella piastrina) | ✅ fatto |
| 4 | Testi uniformi: tutto in inglese o tutto in italiano (interfaccia, avvisi, PDF), eliminate le frasi miste | ✅ fatto |

---

# Archivio: versione 0.4.19 (pubblicata, BETA TEST)

Pubblicata con 8 modifiche (il manuale dettagliato è passato alla 0.4.20).

| # | Richiesta | Stato |
|---|---|---|
| 1 | Fori nella base del feed (viti dal lato del feed): scelta fra **con lamatura** (testa incassata, diametro e profondità modificabili) e **senza lamatura** (fori passanti, testa appoggiata sulla base) | ✅ fatto |
| 2 | Controllo aggiornamenti: la verifica del certificato di GitHub la fa Windows stesso (truststore, come il browser), così funziona anche con antivirus che ispezionano le connessioni HTTPS; ultima riserva PowerShell; l'errore mostra tutti i tentativi | ✅ fatto |
| 3 | Scheda Piastrina WR spostata prima di Disegno & STEP | ✅ fatto |
| 4 | Fori sulla base del feed alla posizione della flangia: come la flangia, maggiorati (Ø proposto e modificabile, anche sulla piastrina) o filettati passanti (10 GHz M4/M3, 24 GHz M3/M2.5/M2, o pollici), con lamatura opzionale; piastrine quadrate con gli stessi 4 fori del feed + 4 viti piastrina→feed opzionali con lamatura; piastrine e basi rotonde (da 47 GHz) con fori della flangia e pin di allineamento opzionali | ✅ fatto |
| 5 | Procedura guidata: illuminazione della parabola scelta dall'utente (taper al bordo in dB, default quella attuale), grafico e disco 3D della parabola con la superficie illuminata ombreggiata | ✅ fatto |
| 6 | Tolleranza generale di lavorazione impostabile (scheda Disegno & STEP) e tolleranze dei fori scritte nei PDF di feed e piastrina | ✅ fatto |
| 7 | Manuale più dettagliato: ogni campo spiegato con screenshot, procedura passo per passo, opzioni (fori, lamature, viti, tolleranze, materiali e loro caratteristiche) | ⏸ rinviato alla prossima versione |
| 8 | PDF di piastrina e feed: fori distinti per funzione (FLANGIA GUIDA nero, FISSAGGIO PIASTRINA magenta, PIN verde) con legenda; tabelle dei fori a capo | ✅ fatto |
| 9 | Piastrina: viti piastrina→feed a brugola con lamatura (default) o a testa piana Phillips svasate; WR-42 M2.5/M2 (M3 troppo grande); posizioni su griglia 0.5 mm (M2.5 a 9.00 come il CAD IZ0JNY); piastrina più grande della flangia quando servono le viti (1 mm dal bordo) o della misura scelta, angoli esterni arrotondati; spessore λ/4 che cambia solo se lo imposta l'utente; fori della flangia filettati nella piastrina come opzione; fori passanti arrotondati al decimo (3.07 → 3.1) e modificabili con 1 mm dal bordo | ✅ fatto |

---

# Archivio: versione 0.4.18 (pubblicata, BETA TEST)

Pubblicata con 8 modifiche.

| # | Richiesta | Stato |
|---|---|---|
| 1 | Controllo aggiornamenti più robusto su Windows (certificati di GitHub anche dal pacchetto certifi) e pulsante "🔄 Controlla aggiornamenti" nella barra laterale che mostra l'esito o l'errore | ✅ fatto |
| 2 | Installer: aggiornamento pulito (cartella python svuotata prima di copiare la nuova, così non restano pacchetti vecchi) e niente voce "nel browser" doppia nel menu Start se si cambia lingua | ✅ fatto |
| 3 | Scelta della lingua spostata dalla cima della barra laterale in fondo, sopra Credits (la lingua si sceglie già nell'installer; serve per la versione portable) | ✅ fatto |
| 4 | Materiali e marche di parabole in ordine alfabetico; tolte dal catalogo RW3BP 2.4 m, Sony DSS, le due "generico" e il link 38 GHz; tolti i nominativi dai nomi delle parabole (le fonti restano citate) | ✅ fatto |
| 5 | Tipi di feed in ordine alfabetico; il feed IZ0JNY si chiama "Dual-Flare (IZ0JNY)" | ✅ fatto |
| 6 | Scheda Piastrina WR: la vista 3D mostra tutto il feed con la base forata, non solo la base | ✅ fatto |
| 7 | Correzione errore "max() iterable argument is empty" con lamatura e flange quadrate (WR-42 ecc.) | ✅ fatto |
| 8 | Lamature: non tagliano più il corpo del feed (prima lasciavano fessure nel 3D/STEP); fori e lamature sempre dentro la base (base quadrata allargata quando la flangia standard è troppo piccola, es. WR-42 con M3 → 25.2 mm); avviso se serve una chiave a brugola a L | ✅ fatto |

---

# Archivio: versione 0.4.17 (pubblicata, BETA TEST)

Pubblicata con 8 modifiche.

| # | Richiesta | Stato |
|---|---|---|
| 1 | Lamatura delle viti sulla base del feed per tutte le flange (anche quadrate WR-90/75/42): il feed si avvita direttamente sulla guida, testa delle viti nella lamatura lato horn | ✅ fatto |
| 2 | Diametro e profondità della lamatura indicati e modificabili (valori standard proposti dal programma); la base si ispessisce da sola | ✅ fatto |
| 3 | Vista 3D ruotabile della base del feed forata (fori e lamature) nella scheda Piastrina WR; Modello 3D con i fori reali | ✅ fatto |
| 4 | Disegni PDF di piastrina e flangia: diametro dei fori e filettature (M2, M3…) indicati per ogni gruppo di fori | ✅ fatto |
| 5 | Avvio "in bianco": Seleziona frequenza / parabola / tipo di feed / materiale; le schede mostrano un invito finché non si sceglie | ✅ fatto |
| 6 | In alto a sinistra "Software progettato da Ivan IZ0JNY" al posto di "basato su W1GHZ…" | ✅ fatto |
| 7 | Procedura guidata: obiettivo predefinito Massimo G/T; nuova opzione "Massime prestazioni RX (minimo rumore)" | ✅ fatto |
| 8 | Promemoria (non vincolante) nelle schede Progetto feed e Laboratorio: dopo modifiche importanti della geometria verificare con openEMS | ✅ fatto |

---

# Archivio: versione 0.4.16 (pubblicata, BETA TEST)

Pubblicata con 5 modifiche.

| # | Richiesta | Stato |
|---|---|---|
| 1 | Cartiglio dei disegni PDF: i testi lunghi (nome del feed, materiale) vanno a capo e la riga si allarga invece di uscire dal riquadro | ✅ fatto |
| 2 | Flange rotonde (da 47 GHz): opzione "viti dal lato del feed con lamatura nella base" (testa nella lamatura sul lato horn, viti avvitate nella flangia della guida); riportata nello STEP/STL del feed e nel foglio della flangia del PDF | ✅ fatto |
| 3 | Scheda Piastrina WR: vista 3D della piastrina accanto alla vista frontale | ✅ fatto |
| 4 | Inglese completo nei Credits e nel catalogo parabole (note e fonti dei datasheet); modulo di segnalazione problemi nella lingua scelta | ✅ fatto |
| 5 | Spessore della base del feed spostato dalla barra laterale alla scheda Progetto feed (sotto lo spessore della parete) | ✅ fatto |

---

# Archivio: versione 0.4.15 (pubblicata, BETA TEST senza scadenza)

Pubblicata subito su richiesta, con 5 modifiche.

| # | Richiesta | Stato |
|---|---|---|
| 1 | Tolta la scadenza di 30 giorni e il pop-up BETA all'avvio (`beta.EXPIRY = False`; resta l'etichetta BETA TEST) | ✅ fatto |
| 2 | Licenza GPL-3.0-or-later: file `LICENSE` (anche nell'installer e nel pacchetto), sezione Licenza nei Credits con le licenze delle librerie, README, manuali, `pyproject.toml`, intestazioni SPDX | ✅ fatto |
| 3 | Credito a chi aiuta: `CONTRIBUTING.md` (contributi con la stessa licenza, firma DCO), `CONTRIBUTORS.md` e sezione "Contributori e beta tester" nei Credits | ✅ fatto |
| 4 | Avviso di nuova versione: all'avvio controlla l'ultima release su GitHub e mostra "cosa c'è di nuovo" (dalle note di rilascio, nella lingua scelta) con il pulsante di download (`feedlab/updates.py`) | ✅ fatto |
| 5 | Lavorazione CNC dell'esterno per tutti i feed a simmetria di rotazione (tranne Axial Corrugated): profilo esterno semplificato (proposte 1 e 2) e raccordi esterni facoltativi a raggio scelto, con riduzione automatica dove la parete è sottile; interno sempre a spigolo vivo; applicati a disegno, 3D e STEP/STL (`geometry.fillet_outer`) | ✅ fatto |

---

# Archivio: versione 0.4.14 (pubblicata, BETA TEST 30 giorni)

Pubblicata con 5 modifiche.

| # | Richiesta | Stato |
|---|---|---|
| 1 | IZ0JNY Dual-Flare: tolte le note "progetto nuovo, verificare con openEMS" (feed già verificato a 24 GHz, risultati nello studio `docs/IZ0JNY_DualFlare.md`, anche a griglia fine) | ✅ fatto |
| 2 | Progetto feed: dopo "Applica modifiche" i campi mostrano i valori ricalcolati (es. lunghezza del cono dopo aver cambiato l'angolo) e le quote non toccate non vengono più fissate per sbaglio | ✅ fatto |
| 3 | Disegno & STEP: indicazione chiara se la base del feed è forata (e dove si attiva la foratura, scheda Piastrina WR) | ✅ fatto |
| 4 | Inglese completo: tolte le scritte italiane rimaste nei PDF (foglio della flangia, foratura della piastrina, note) e in suggerimenti/messaggi dell'interfaccia (tolleranze, space mapping, fori di fissaggio) | ✅ fatto |
| 5 | Download nell'app desktop: i file .stp/.stl/.pdf si salvano sempre con l'estensione (finestra "Salva con nome" con il tipo di file e l'estensione predefinita) | ✅ fatto |

---

# Archivio: versione 0.4.13 (pubblicata, BETA TEST 30 giorni)

Pubblicata con 10 modifiche (comprende quelle preparate per la 0.4.12, non pubblicata).

| # | Richiesta | Stato |
|---|---|---|
| 1 | Piastrina di adattamento con la **forma e la misura della flangia**: quadrata per WR-90/WR-75/WR-42 (10 e 24 GHz), **rotonda** per le flange MIL da 47 GHz in su; più grande della flangia solo se le lamature non ci stanno (avviso) | ✅ fatto |
| 2 | **Da 47 GHz** niente viti piastrina→feed: la piastrina si appoggia sulla base del feed e le viti della guida la attraversano e si avvitano nella base (filettata passante); le spine standard allineano tutto; base rotonda come la flangia | ✅ fatto |
| 3 | **Spessore della base del feed** impostabile nella barra laterale (minimo 1 mm, vuoto = automatico); fori filettati e lunghezza delle viti seguono lo spessore | ✅ fatto |
| 4 | Sezione nella scheda Progetto feed con i **nomi delle quote** (blu lunghezze, verde diametri, rosso angoli dei flare) e stessi colori nella tabella delle quote; **angoli dei coni** IZ0JNY modificabili (la lunghezza del cono si ricalcola) | ✅ fatto |
| 5 | Laboratorio: **semiangoli dei coni** IZ0JNY tra le quote da variare | ✅ fatto |
| 6 | IZ0JNY: **profilo esterno per CNC** a scelta (parete costante, proposta 1 pieno fino alla fine del 1° cono, proposta 2 senza rientranze); interno invariato | ✅ fatto |
| 7 | **Axial Corrugated** con **sezione di guida circolare** (lunghezza L_guide impostabile, 0 = solo la testa) e base quadrata/rotonda con foratura, in un unico pezzo | ✅ fatto |
| 8 | Traduzioni inglesi corrette negli avvisi delle flange | ✅ fatto |
| 9 | **Guida circolare d'ingresso allungabile** per tutti i feed (input_length; length per guida aperta/VE4MA/Chaparral; L_guide per il corrugato) con spiegazione nella tabella delle quote | ✅ fatto |
| 10 | IZ0JNY: **quota dello scalino interno** (altezza h e lunghezza Ls) nel disegno PDF e nella sezione | ✅ fatto |

---

# Archivio: versione 0.4.11 (pubblicata, BETA TEST 30 giorni)

Pubblicata con 8 modifiche.

| # | Richiesta | Stato |
|---|---|---|
| 1 | Nuovo feed **IZ0JNY Dual-Flare** (scalino + cono 1 + cilindro di fasatura + cono 2), progettato con il solutore di FeedLab per EME: η calcolata vicina al limite teorico del modello, S11 < −30 dB, antenna più fredda (+0.2…0.7 dB di G/T rispetto al Pickett-Potter), 80.1 % a f/D 0.9. Nel wizard per f/D 0.6–0.9, con ottimizzatore, tolleranze, disegno PDF e script openEMS. Studio in docs/IZ0JNY_DualFlare.md. Da verificare full-wave | 🔄 in verifica |
| 2 | Disegni PDF: le note dei feed vanno a capo e restano dentro il foglio | ✅ fatto |
| 3 | Base del feed circolare o **quadrata** con lo stesso lato della flangia della guida (WR-90 41.40, WR-75 38.30, WR-42 22.41 mm): scelta nella barra laterale a 10 e 24 GHz; quadrata anche nel modello 3D, nello STEP/STL e nella vista della flangia del disegno PDF; con la foratura attiva segue la guida scelta per la piastrina | ✅ fatto |
| 4 | Una sola scelta della guida rettangolare nella barra laterale, limitata alle guide della banda: 10 GHz WR-90 o WR-75, 24 GHz WR-42, 47 GHz WR-22 o WR-19 (76 GHz WR-12 o WR-10…). Dimensiona la piastrina di adattamento circolare → WR, la foratura della flangia, la base quadrata (solo flange quadrate) e l'horn rettangolare | ✅ fatto |
| 5 | Disegno e modello: con la flangia forata spessa (es. IZ0JNY 24 GHz su WR-42, 8.8 mm) la parete esterna dello scalino entrava nella flangia. Ora lo scalino parte almeno una parete sopra la flangia e il raccordo è pieno; test su tutti i feed a 10 e 24 GHz | ✅ fatto |
| 6 | Installer segnalato come virus / bloccato da SmartScreen: l'avvio non usa più FeedLab.exe (copia di pythonw.exe con icona cambiata, quindi con firma digitale rotta, tipico allarme degli antivirus) ma gli interpreti originali firmati da python.org; icona FeedLab da collegamenti (AppUserModelID) e finestra; metadati di versione nel setup; file SHA256SUMS.txt nella release; la CI verifica le firme. SmartScreen sparisce solo con un certificato di firma del codice (scelta dell'autore) | ✅ fatto (firma da decidere) |
| 7 | Tolta dall'installer l'opzione di scaricare openEMS: si installa solo dall'app, scheda Full-wave openEMS → ① Installazione (l'installer non scarica più nulla) | ✅ fatto |
| 8 | **Bug openEMS**: lo script salvava i diagrammi di radiazione arrotondati a 9 decimali e il campo lontano di openEMS (~1e-11 V/m) diventava tutto zero (S11 invece era corretto). Ora 9 cifre significative; nuova opzione `--post` che ricalcola porta e campo lontano da sim_data senza rifare la simulazione; avviso nei risultati per i file vecchi | ✅ fatto |

---

# Archivio: versione 0.4.10 (pubblicata, BETA TEST 30 giorni)

Pubblicata con 3 modifiche su richiesta.

| # | Richiesta | Stato |
|---|---|---|
| 1 | Disegno PDF: si vede quale quota è quale (Di, Ds, las, D_aperture, flare_length…); Axial Corrugated con d1…d8 dentro ogni scalino, w, pitch e delta; VE4MA/Chaparral con ring_width, ring_depth, ring_setback | ✅ fatto |
| 2 | Axial Corrugated: PDF su due fogli, mezza sezione a scala doppia e feed intero | ✅ fatto |
| 3 | PDF dei disegni tutti in una lingua: note dei feed in italiano nel codice con traduzione inglese completa; cartiglio tradotto | ✅ fatto |

---

# Archivio: versione 0.4.9 (pubblicata, BETA TEST 30 giorni)

Pubblicata con 5 modifiche.

| # | Richiesta | Stato |
|---|---|---|
| 1 | Pop-up BETA: il pulsante OK non funzionava; tolto, al suo posto il testo centrato "Chiudere questa finestra per continuare (✕ in alto a destra)"; si chiude con la ✕ | ✅ fatto |
| 2 | Tolta dalla barra laterale l'opzione "Collare Ø40 mm per portaLNB commerciale" | ✅ fatto |
| 3 | Axial Corrugated: "8 gole" diventa "8 scalini" (procedura guidata, note, manuali), con le traduzioni inglesi | ✅ fatto |
| 4 | Progetto feed e Modello 3D: il feed è colorato come il materiale scelto (rame, ottone, alluminio, argento, oro, inox, stampa 3D) | ✅ fatto |
| 5 | Piastrina WR-90: viti piastra→feed storte (ruotate di 40°); ora si cercano prima posizioni simmetriche (assi, poi diagonali) che stiano sulla flangia | ✅ fatto (`tests/test_flanges.py::test_plate_screws_symmetric`) |

---

# Archivio: versione 0.4.8 (pubblicata, BETA TEST 30 giorni)

| # | Richiesta | Stato |
|---|---|---|
| 1 | Manuale per ogni lingua dell'installazione, con screenshot in quella lingua | ✅ fatto: manuali IT e EN, schermate in `docs/manual/img/<lingua>/` |
| 2 | Nuove lingue russo e portoghese | ❌ annullato: su richiesta il software è stato semplificato a **solo italiano e inglese** (tolti anche tedesco, francese e spagnolo, con i loro manuali) |
| 3 | Feed di Zdeněk OK1DFC (septum) | ❌ annullato su richiesta: è un feed per 1296 MHz, fuori dal campo di FeedLab (da 10 GHz); OK1DFC resta in bibliografia |
| 4 | Versione **BETA TEST** a scadenza: 30 giorni dall'installazione, pop-up a ogni avvio | ✅ fatto |
| 5 | **Axial Corrugated (base concept Luis CT1DMK, improved version Gerald OE2IGL)**, con le quote del foglio di calcolo v1.4 di Gerald OE2IGL, tra i tipi di feed e nella procedura guidata | ✅ fatto |
| + | Feed di Mirek OK2AQ (horn conico f/D 0.6 e corrugato f/D 0.8, 24 GHz) | ❌ tolti su richiesta |

## 1-2. Lingue e manuali
- Il software è stato semplificato: interfaccia, installer e manuali solo in **italiano e inglese**. Il catalogo delle traduzioni (`feedlab/i18n_catalog.py`) contiene coppie (it, en); con una lingua di sistema diversa dall'italiano FeedLab parte in inglese.
- Sorgenti dei manuali: `docs/manual/manuale_it.md`, `docs/manual/user_manual_en.md`; `{IMG}` diventa `img/<lingua>`.
- Schermate: `python docs/manual/tools/make_screens.py [lingue]`; PDF: `python docs/manual/build_manual.py`. L'installer include solo i PDF.

## 4. BETA TEST a scadenza
- **Modulo `feedlab/beta.py`:** al primo avvio di ogni versione salva la data nella cartella impostazioni di FeedLab (`beta.json`). Ogni nuova versione ha i suoi 30 giorni.
- **A ogni avvio:** pop-up "🧪 BETA TEST" con i giorni rimasti e la data di scadenza, che si chiude con OK o ✕. In barra laterale resta "Versione x.y.z BETA TEST".
- **Alla scadenza:** pagina di blocco con il link all'ultima versione su GitHub. Anche un orologio spostato indietro di oltre un giorno conta come scadenza.
- **Limite:** FeedLab è open source, quindi è un avviso per i tester, non una protezione. `BETA = False` produce una versione normale.
- **Test:** `tests/test_beta.py`.

## 5. Axial Corrugated (base concept Luis CT1DMK, improved version Gerald OE2IGL)
- **Corrugato assiale v1.4:** quote dai polinomi del foglio di calcolo in funzione dell'angolo di apertura (verificato a 47.088 GHz / 137°); 10–76 GHz; efficienza dell'autore 81–86% usata dalla procedura guidata, dove risulta di solito primo. Sezione, 3D, PDF e STEP; quote modificabili (passo, gole, gradino, d1…d8).
- La scheda "Feed pubblicati" è stata tolta su richiesta: i feed stanno nell'elenco dei tipi di feed insieme agli altri.
- Test: `tests/test_published_feeds.py`.

---

# Archivio: versione 0.4.7 (pubblicata)

| # | Richiesta | Stato |
|---|---|---|
| 1 | Un manuale per ogni lingua dell'installazione (IT, EN, DE, FR, ES), con gli screenshot dell'app in quella lingua | da fare |
| 3 | Riferimenti Sergei RW3BP (77 GHz), Luis CT1DMK (radioastronomia), Luis CT1DMK e Willi LX1DB (feed CP) nei calcoli e in bibliografia; nominativi nei riferimenti | ✅ fatto su `main` |
| 2 | Scelta delle viti piastrina → feed: M3/M4 a 10 GHz, M2.5/M3/M2 sopra; lunghezza = 2 × spessore piastrina arrotondata alla misura commerciale; equivalenti UNC | ✅ fatto su `main` |

## 2. Viti piastrina → feed
**Richiesta (IZ0JNY):** scegliere le viti più comuni per fissare la piastrina al feed: M3 o M4 per i 10 GHz, M3, M2.5 o M2 per le frequenze superiori. Lunghezza delle viti (e quindi dei fori filettati nel feed) = spessore della piastrina × 2 (prima × 3), arrotondato alle lunghezze commerciali 10, 12, 14, 16, 18, 20, 25 mm. Conversione per le viti UNC.

**Fatto:**
- Scheda *Piastrina WR*: menu "Viti piastrina → feed" con le misure della banda (sotto 15 GHz: M3, M4; sopra: M2.5, M3, M2; la prima è quella proposta).
- **Lunghezza:** 2 × spessore del corpo della piastrina, arrotondato alla lunghezza commerciale più vicina (a parità sceglie la più lunga; sotto 10 → 10 mm, sopra 25 → 25 mm).
- **Foro nel feed (IZ0JNY):** la vite entra nel feed per lunghezza vite − (spessore piastrina − lamatura). Il foro cieco è arrotondato per eccesso a un intero pari, senza margine aggiuntivo, ma abbastanza profondo da avere filetto fino alla punta della vite: il filetto si ferma 3 passi (min. 1 mm) prima del fondo.
- **Pollici (UNC), misura più vicina:** M2 → #2-56, M2.5 → #3-48 (meno diffusa del 4-40), M3 → #4-40, M4 → #8-32. Lunghezze ASME B18.3: 3/8", 1/2", 5/8", 3/4", 7/8", 1". Lamature per teste cilindriche ISO 4762 / ASME B18.3.
- Vite e lunghezza compaiono nella foratura del PDF della piastrina, nei fori del feed (PDF e STEP) e nella scheda.
- **Esempio a 10 GHz:** piastrina 8.85 mm → vite M3 × 18, foro di 14 mm nel feed.
- Test: `tests/test_flanges.py::test_plate_screw_choices_and_length`.

---

# Archivio: versione 0.4.6 (pubblicata)

| # | Richiesta | Stato |
|---|---|---|
| 1 | Gradino senza spessore (Pickett-Potter, Skobelev): la corona tra guida d'ingresso e flare aveva spessore assiale zero nel 2D, nel 3D, nello STEP e nel PDF | ✅ fatto su `main` |
| 2 | Quote nei disegni: spessore del gradino, spessore parete e semiangolo del flare (PDF e sezione nell'app) | ✅ fatto su `main` |
| 3 | Laboratorio: variare il semiangolo del flare (Pickett-Potter, Skobelev) e vedere cosa cambia | ✅ fatto su `main` |
| 4 | Manuali in 5 lingue | spostato alla 0.4.7 |

## 1. Spessore della parete
La parete esterna era il profilo interno spostato solo in direzione radiale: dove il profilo è orizzontale (gradino) la corona aveva spessore zero e nei tratti conici la parete era più sottile del valore impostato. Ora lo spessore è costante e misurato perpendicolarmente alla parete, con spigoli vivi agli angoli; i bordi d'apertura e la flangia restano piani. Test: `tests/test_wall_thickness.py`.

## 3. Semiangolo del flare nel Laboratorio
Per Pickett-Potter e Skobelev il flare si regola con il semiangolo α (Ø apertura fisso, la lunghezza del flare segue). Il semiangolo compare anche tra le quote modificabili; se si modificano sia angolo sia lunghezza vale l'ultimo valore inserito.

## 4. Manuali in 5 lingue con screenshot
**Piano:**
- Manuale (Markdown → PDF con `docs/manual/build_manual.py`) per italiano, inglese, tedesco, francese e spagnolo, ciascuno con gli screenshot dell'app nella stessa lingua.
- Screenshot generati in automatico in CI su Windows (Playwright + Edge): per ogni lingua si apre l'app, si sceglie la lingua e si fotografano le schede principali, così le immagini restano aggiornate a ogni versione.
- Il pulsante 📖 Manuale apre il manuale della lingua scelta; l'installer installa tutti i manuali.

---

# Archivio: versione 0.4.3

Raccolta delle richieste. Si sviluppano sul ramo `v0.4.3`. Quando ce ne sono **5** si provano tutte insieme e si pubblica il nuovo installer Windows.

| # | Richiesta | Stato |
|---|---|---|
| 1 | Balanis nelle equazioni di calcolo e nella bibliografia | ✅ fatto (ramo `v0.4.3`) |
| 2 | Analisi di tolleranza Monte Carlo, quote critiche, ottimizzazione robusta | ✅ fatto (ramo `v0.4.3`) |
| 3 | Validazione openEMS in the loop (space mapping) | ✅ fatto (ramo `v0.4.3`), da provare con openEMS vero |
| 4 | Fori, filettature, lamature e spine piastra–feed (metrico/pollici) | ✅ fatto |
| 5 | Pulsante per segnalare problemi su GitHub | ✅ fatto |
| + | Riferimento Jeff WA6KBL (controllo TM11) | ✅ fatto |

**Pubblicata come 0.4.3.**

## 1. Balanis, *Antenna Theory: Analysis and Design*
**Richiesta:** aggiungere il libro di C. A. Balanis alle equazioni di calcolo e alla bibliografia (Credits, README, base di conoscenza).

**Piano:**
- **Bibliografia:** C. A. Balanis, *Antenna Theory: Analysis and Design*, Wiley (4ª ed. 2016), da citare nei Credits (tradotto nelle 5 lingue), nel README e nella base di conoscenza.
- **Equazioni da aggiungere come verifiche indipendenti**, con un test ciascuna:
  - **Horn conico:** guadagno e perdita di fase per errore quadratico d'apertura; verifica del `conical_optimum` esistente.
  - **Horn piramidale e settoriali:** direttività con integrali di Fresnel; verifica di `pyramidal_gain_dbi` (approssimazione G3RPE/W1GHZ).
  - **Riflettore con feed cos^n:** efficienza d'apertura in forma chiusa (spillover × taper); confronto con l'integrazione numerica di FeedLab, che già coincide con il calcolo analitico entro 0.3%.
  - **Relazioni di base:** Friis, perdita di disadattamento di polarizzazione (lineare↔circolare, 3 dB), direttività/guadagno/efficienza, VSWR ↔ return loss ↔ S11.
- **Riferimenti nel codice:** ogni funzione cita "Balanis, cap. X". Il capitolo si indica solo dove è certo; il numero di equazione non si inventa.

**Fatto:** `feedlab/balanis.py` e `tests/test_balanis.py`.
- Il riflettore con feed cos^n coincide con il motore di FeedLab entro 0.0002.
- L'horn piramidale (Fresnel) coincide con l'integrale 2D dell'apertura entro 0.01 dB.
- Il confronto ha scoperto un errore: `horns.pyramidal_gain_dbi` sottostimava di 0.15–0.5 dB; ora usa la formula di Balanis.

**Nota sul PDF:** il link archive.org dato all'inizio è una copia del libro non autorizzata dall'editore, quindi non la scarico né la uso come fonte. Le equazioni del libro sono formule standard della teoria delle antenne e si possono implementare e citare senza il PDF. Se hai il libro, per controllare numero per numero bastano le pagine delle sezioni interessate.

## 2. Tolleranze di lavorazione e progetto robusto
**Origine:** commento di un utente: un buon progetto non vale nulla se le tolleranze di lavorazione non sono raggiungibili.

**Cosa fa:**
- **Monte Carlo** di tutte le quote lavorate, distribuite uniformemente in ±t oppure normali con ±t = 3σ. Le migliaia di campioni si calcolano su un modello quadratico ricavato da 1 + 2N + N(N−1)/2 run del solver rapido e verificato con alcuni run diretti.
- **Resa:** percentuale di pezzi entro la perdita ammessa e con S11 sotto il limite.
- **Quote critiche:** quota di varianza di ciascuna dimensione e tolleranza necessaria, arrotondata alle classi d'officina.
- **Ottimizzazione robusta:** massimizza media − k·σ invece del picco nominale.
- **Disegno PDF:** tabella delle tolleranze per quota.

**Accelerazione del solver:** i punti di quadratura in cache portano una valutazione da 0.75 a 0.46 s.

## 3. Space mapping con openEMS
- Il modello rapido esplora; openEMS valida 3–5 candidati.
- La differenza tra openEMS e il modello rapido (correzione costante, poi lineare nelle quote) corregge il modello rapido, che viene riottimizzato.
- Il ciclo si ripete fino alla convergenza.
- Tutto parte dalla scheda Full-wave openEMS, con il report dei passi.
