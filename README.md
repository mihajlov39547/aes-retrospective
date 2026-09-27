# Od DES-a do AES-a

Inicijalni pregledno-eksperimentalni rad na srpskom jeziku, latinicom.
Radni naslov: **Od DES-a do AES-a: više od dve decenije razvoja, primene i perspektive simetrične kriptografije u telekomunikacijama**.

English title: **From DES to AES: More Than Two Decades of Evolution, Applications and Perspectives of Symmetric Cryptography in Telecommunications**.

Cilj je retrospektiva očekivanja iz 2001–2003. prema iskustvu do 2026, uz manji eksperimentalni deo. Projekat nije kompletan članak, novi algoritam niti reprodukcija magistarskog rada. Autor je Marko Mihajlović; afilijacija i kontakt biće dodati kasnije. Zaključak ostaje otvoren do završetka istraživanja.

## Struktura

Svi projektni izvori su prikazani; lokalno okruženje, Git baza i generisani build fajlovi skraćeni su.

```text
.
├── .gitignore
├── main.tex
├── build.ps1
├── references.bib
├── README.md
├── chapters/
│   ├── 00_abstract.tex
│   ├── 01_uvod.tex
│   ├── 02_osnove_simetricne_kriptografije.tex
│   ├── 03_des.tex
│   ├── 04_triple_des.tex
│   ├── 05_nastanak_aes.tex
│   ├── 06_aes.tex
│   ├── 07_poredjenje_des_3des_aes.tex
│   ├── 08_primene_u_telekomunikacijama.tex
│   ├── 09_eksperimentalna_analiza.tex
│   ├── 10_prediction_vs_reality.tex
│   ├── 11_savremeni_izazovi_i_future_work.tex
│   └── 12_zakljucak.tex
├── figures/
│   └── README.md
├── tables/
│   ├── README.md
│   ├── poredjenje.tex
│   ├── aes_cpu_gpu.tex
│   └── prediction_vs_reality.tex
├── experiments/
│   ├── README.md
│   ├── requirements.txt
│   ├── common.py
│   ├── benchmark.py
│   ├── aes_acceleration.py
│   ├── aes_gpu.py
│   ├── aes_gpu_kernel.cu
│   ├── avalanche_test.py
│   ├── brute_force_demo.py
│   ├── export_results.py
│   ├── smoke_check.py
│   └── results/
│       └── README.md
├── bibliography/
│   └── notes.md
├── build/                    # generisani PDF, logovi i tehničke provere
├── .venv/                    # lokalno Python okruženje
├── .git/                     # postojeći repozitorijum
├── .powershell/              # postojeća lokalna konfiguracija
└── start-codex.ps1            # postojeća skripta
```

## Poglavlja

| Fajl | Planirani sadržaj |
|---|---|
| 00 | Radni sažeci i ključne reči na oba jezika, bez rezultata. |
| 01 | Istorijski trenutak, centralno pitanje, doprinos i metod izbora literature. |
| 02 | Blokovske šifre, Feistel/SPN, ključ, konfuzija/difuzija, ECB/CBC/CTR/GCM i AEAD. |
| 03 | DES: istorija, runde, raspored ključa, implementacija i ograničenja. |
| 04 | TDEA: EDE, dve/tri komponente ključa, MITM, performanse, blok i povlačenje. |
| 05 | NIST konkurs, kandidati, kriterijumi, Rijndael i nastanak AES-a. |
| 06 | AES state, transformacije, GF aritmetika, dekripcija, kriptoanaliza i bočni kanali. |
| 07 | Istorijsko i savremeno poređenje; centralna prazna tabela. |
| 08 | IPsec/VPN, TLS, Wi-Fi, mobilni sistemi, infrastruktura i IoT. |
| 09 | Benchmark, AES-NI naspram softvera, reproduktivnost, brute-force i avalanche. |
| 10 | Očekivanja naspram ishoda, AEAD, performanse i kvantni model. |
| 11 | Dizajnerska retrospektiva, AES-192, blok, implementacije, Ascon i future work. |
| 12 | Struktura odgovora na centralno pitanje, bez konačne ocene. |

Brute-force i avalanche su pododeljci 09; dizajnerska retrospektiva i future work objedinjeni su u 11. Sadržajni zadaci su u `% TODO:` komentarima, koji se ne štampaju u PDF-u.

## Kompilacija

Potrebni su TeX Live ili MiKTeX, XeLaTeX, Biber i latexmk (na Windows-u i Perl),
kao i instaliran font Times New Roman. UTF-8, fontspec i Babel `serbian` omogućavaju srpsku latinicu.
Planirana AES ilustracija ima označen okvir, pa nema nedostajućih slika.

Iz korena projekta:

```powershell
.\build.ps1
```

Rezultat je `build/aes20y.pdf`. Bibliografiju automatski obrađuje Biber.
Skripta radi i kada se pozove punom putanjom iz drugog direktorijuma; pri grešci
prekida rad i ne prijavljuje stari PDF kao uspešno izgrađen.
Direktna komanda: `latexmk -xelatex -interaction=nonstopmode -halt-on-error -jobname=aes20y -outdir=build main.tex`.
Alternativa bez latexmk, takođe iz korena:

```powershell
New-Item -ItemType Directory -Force build
xelatex -interaction=nonstopmode -halt-on-error -jobname=aes20y -output-directory=build main.tex
biber --input-directory=build --output-directory=build aes20y
xelatex -interaction=nonstopmode -halt-on-error -jobname=aes20y -output-directory=build main.tex
xelatex -interaction=nonstopmode -halt-on-error -jobname=aes20y -output-directory=build main.tex
```

Za isključivanje sadržaja promeniti `\showsummarytrue` u `\showsummaryfalse`.
Neutralni `article` naknadno prilagoditi časopisu. Paketi uključuju `graphicx`,
`amsmath`, `booktabs`, `siunitx`, `hyperref`, `cleveref`, `biblatex` i `csquotes`.
Koristiti postojeće oznake `sec:`, `fig:` i `tab:` za cross-reference.

## Python

### Novi CPU/GPU eksperiment

Dodati su `experiments/aes_gpu.py`, `experiments/aes_gpu_kernel.cu` i
`tables/aes_cpu_gpu.tex`. Poglavlje 9 sada obuhvata tri AES-128 putanje u
ECB/CTR modu: CPU software, CPU AES-NI i NVIDIA CUDA. CBC ostaje odvojeni
istorijski CPU eksperiment. Poglavlja 6 i 10 povezuju ovu metodologiju sa
paralelizacijom i retrospektivom, bez unapred pretpostavljene prednosti GPU-a.

```powershell
python experiments/aes_gpu.py
python experiments/aes_gpu.py --check
```

Prva komanda prikazuje plan, druga otkriva CPU/GPU okruženje bez merenja.
CUDA fajl je namerno blokiran skeleton: potrebno je implementirati i validirati
AES-128 pre `--validate-only` i `--run`. Ni GPU merenja ni grafikoni još nisu
generisani. CuPy je opciona zavisnost; konkretan paket bira se nakon provere
runtime-a, drajvera, platforme i Python verzije, prema uputstvu u
[eksperimentalnom README-u](experiments/README.md#gpu-cuda-okvir).

Izvoz je pripremljen za stvarne, validirane podatke:
`python experiments/export_results.py experiments/results/aes_cpu_gpu-pilot-ID`.
U poddirektorijumima `ECB/` i `CTR/` nastaju `throughput_vs_size.pdf`,
`latency_vs_size.pdf`, `gpu_overhead_breakdown.pdf` i `speedup_vs_size.pdf`,
uz PNG kopije i LaTeX tabelu. Bez validacije exporter odbija GPU grafikone.

### Osnovne zavisnosti

Python 3.10 ili noviji. Postojeće odgovarajuće `.venv` ne treba ponovo praviti:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r experiments/requirements.txt
```

Aktivacija nije obavezna: može se direktno koristiti `.\.venv\Scripts\python.exe`.
Linux/macOS: `python3 -m venv .venv` i `source .venv/bin/activate`.
Direktne zavisnosti: PyCryptodome, matplotlib, psutil. Statistika, CSV i JSON
koriste standardnu biblioteku; pandas nije potreban, NumPy dolazi uz matplotlib.
Tačne instalirane verzije beleže se po izvršavanju u `requirements-lock.txt`.

Bez `--run` skripte prikazuju plan bez merenja i kreiranja rezultata:

```powershell
python experiments/benchmark.py
python experiments/aes_acceleration.py
python experiments/avalanche_test.py
python experiments/brute_force_demo.py
```

Primeri budućeg pilot-pokretanja, nakon pregleda metodologije:

```powershell
python experiments/benchmark.py --run --seed 2003 --repeats 10
python experiments/aes_acceleration.py --run --seed 2003 --repeats 10
python experiments/avalanche_test.py --run --seed 2003 --trials 1000
python experiments/brute_force_demo.py --run --seed 2003 --bits 12 --repeats 3
```

Izlazi su u `experiments/results/<run-id>/`: pojedinačna merenja, sažetak,
JSON metapodaci i verzije okruženja. Namena je podrazumevano `pilot`.
`--purpose study` je samo oznaka, ne naučna validacija.

`python experiments/export_results.py experiments/results/benchmark-pilot-ID`
iz postojećeg benchmark direktorijuma generiše `benchmark_table.tex`,
`benchmark.png` i `benchmark.pdf`. Nema automatskog uvoza u članak.
Isti exporter prihvata direktorijum `aes_acceleration-pilot-ID` i generiše
`aes_acceleration_table.tex`, `aes_acceleration.png` i `aes_acceleration.pdf`.
Ovaj eksperiment poredi AES-NI sa prenosivim kompajliranim AES-om iste biblioteke,
uz proveru izbora putanje pre merenja. Bez AES-NI podrške prekida se sa objašnjenjem,
bez lažnog hardverskog rezultata. Ne predstavlja rekonstrukciju performansi iz 2003.

`python experiments/smoke_check.py` proverava male uzorke i izvoz.
Izlazi su u `build/smoke/`, sa oznakom `smoke`, i nisu rezultati rada.
Metod i otvoreni zadaci su u [experiments/README.md](experiments/README.md).

## Bibliografija i metodološka pravila

`references.bib` sadrži 12 početnih zapisa: FIPS 46-3, FIPS 197 (2001 i 2023),
NIST izveštaj o AES izboru, predlog Rijndaela (1999), SP 800-67 Rev. 2,
obaveštenja o povlačenju DES/TDEA, SP 800-38A/38D i RFC 4106/8446.
URL-ovi i datum provere nalaze se uz zapise. Nepotvrđeni metapodaci su izostavljeni.

[bibliography/notes.md](bibliography/notes.md) navodi zadatke za kriptoanalizu,
bočne kanale, AES-NI, Sweet32, telekomunikacione profile, kvantne resurse i
aktuelne standarde. RFC 8446 je istorijski izvor; proveriti njegovog naslednika.
Početna bibliografija nije dovoljan dokaz svih tvrdnji o stanju u 2026.

Razlikovati algoritam, mod i protokol; teorijski, praktičan i implementacioni napad;
veličinu ključa i efektivnu sigurnost. AES ne opisivati kao „neprobojan“.
DES/TDEA nisu preporuke za novu zaštitu. Seedovani ključevi služe samo sintetičkim
merenjima. Ne pisati zaključak pre literature i rezultata.
Sledeća faza je istraživanje i pisanje poglavlja jedno po jedno.
