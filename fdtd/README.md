# FeedLab FDTD — ottimizzazione iterativa dei feed con openEMS

Ambiente riproducibile per far girare **openEMS** (FDTD full-wave) in serie e cercare, per una data f/D della
parabola, la geometria di feed con la massima efficienza d'illuminazione. Non fa parte del programma
Windows/Linux: è uno strumento di ricerca che usa i moduli di FeedLab (`geometry`, `openems_sim`,
`deep_analysis`, `efficiency`).

## Installazione

| Dove | Comando | Tempo |
|---|---|---|
| Container cloud pulito (Ubuntu 24.04, senza Docker) | `bash fdtd/setup_cloud.sh` | ~5 min (compila openEMS v0.37.0) |
| Docker | `docker build -t feedlab-fdtd -f fdtd/Dockerfile .` | ~6 min |
| Debian/Ubuntu locale | `sudo bash fdtd/install_openems.sh` | ~5 min |

openEMS finisce in `/opt/openEMS`, i binding Python in `/opt/openEMS/venv` (versione fissata con `OPENEMS_TAG`).

## Uso

```bash
PY=/opt/openEMS/venv/bin/python
$PY fdtd/benchmark.py --fD 0.6                         # feed pubblicati, stesse regole (tabella di riferimento)
$PY fdtd/optimize.py --family w2imu --fD 0.6 --budget 60
$PY fdtd/optimize.py --family dualflare --fD 0.6 --method de --budget 150
$PY fdtd/optimize.py --family profile --fD 0.6 --seed-mm  # profilo libero, partenza dal mode matching
$PY fdtd/optimize.py --family w2imu --fD 0.6 --confirm    # migliore e partenza di nuovo a --confirm-cpl
```

Con Docker: `docker run --rm -v "$PWD/fdtd/results:/work/fdtd/results" -v "$PWD/fdtd/runs:/work/fdtd/runs" feedlab-fdtd python fdtd/optimize.py ...`

- **Famiglie**: `w2imu` (A, B, semiangolo, C), `dualflare` (scalino + cono 1 + cilindro + cono 2),
  `profile` (profilo liscio monotono PCHIP con scalino d'ingresso). Quote in λ: il risultato vale per ogni
  banda alla stessa f/D. La simulazione gira a `--f0` (10.368 GHz).
- **Metodi**: `nm` Nelder-Mead dal progetto di letteratura (locale, poche decine di run), `de` evoluzione
  differenziale (globale, centinaia di run).
- **Cache**: ogni run openEMS sta in `fdtd/runs/<hash>/` (solo json e log; i campi grezzi si cancellano).
  Un'ottimizzazione interrotta riparte da dove era: i punti già simulati costano zero.
- **Risultati**: `fdtd/results/<famiglia>_fD<f/D>.jsonl` (tutte le valutazioni), `*_best.json`, `*_confirm.json`.

## Impostazioni di simulazione (`fdtd_eval.EvalConfig`)

- eccitazione f0 ± 10 % (impulso corto), campo lontano a f0·(1−b), f0, f0·(1+b), S11 valutato solo in f0 ± b;
- **sempre 100 celle/λ nel feed** (regola di Ivan, dalla 0.4.29): le linee di griglia stanno su ogni spigolo,
  le pareti oblique e le scanalature restano entro ±λ/200 (±0.15 mm a 10 GHz); fuori dal feed la mesh si
  allarga con rapporto 1.4 fino a 20 celle/λ in aria; linee più vicine di 0.2 celle si fondono;
- **mezzo modello** (parete PEC in x = 0, `symmetry=2`): metà RAM e tempo. Verifica W2IMU a 40 celle/λ:
  intero η 78.18 %, S11 −40.8 dB; mezzo 78.06 %, −37.8 dB; quarto (PEC + PMC) 77.52 %, −29.2 dB, quindi
  il quarto non si usa;
- massimo 400 000 passi; una simulazione che non scende sotto −22 dB di energia (cavità chiusa, instabilità)
  è scartata con penalità 1.0.

A 16 celle/λ (prima della 0.4.29): W2IMU 29 s, Axial Corrugated 95 s (4 core). A 100 celle/λ servono ore
(corrugato f/D 0.4 a 10 GHz: ~110 M celle, ~10 GB di RAM con il mezzo modello).

## Figura di merito

Per ciascuna frequenza f0·(1−b), f0, f0·(1+b) (b = 2 % di default), dal campo lontano openEMS (NF2FF):

η(f) = spillover × taper × fase × cross-pol (Kildal/W1GHZ, `feedlab.efficiency`) × (1 − |S11(f)|²)

con il feed in **un solo** centro di fase, trovato a f0 e tenuto fisso in banda. FOM = media di η(f),
meno 0.01 per ogni dB di S11 sopra −20 dB e per ogni λ di lunghezza oltre 12 λ. Il blocking non è incluso
(offset, oppure si aggiunge dopo per il prime focus).

## Validazione (W2IMU, f/D 0.6, 10.368 GHz)

| Celle/λ | Celle | FDTD | η f0 | η media ±2 % | S11 max |
|---|---|---|---|---|---|
| 14 | 0.40 M | 49 s | 75.9 % | 74.5 % | −24.2 dB |
| 20 | 0.82 M | 82 s | 76.8 % | 75.9 % | −26.5 dB |
| 26 | 1.53 M | 174 s | 77.0 % | 76.1 % | −28.8 dB |

(4 core, mesh uniforme). A 16 celle/λ l'errore resta entro ~1.5 punti, ma le quote si arrotondano troppo
(±0.6 mm a 10 GHz con 24 celle/λ): dalla 0.4.29 si cerca e si conferma a 100 celle/λ. Il valore converge sul ~77 % del W2IMU riportato da W1GHZ.
