# Python skripte

Eksperiment 2: [protokol AES software/AES-NI](../experiments/aes_acceleration_protocol.md).
Izolovana provera je `python scripts/aes_acceleration_smoke_check.py` (samo AES CBC,
1 KiB smoke). Obe putanje prolaze NIST KAT i dispatch pre wall/process tajmera;
izvoz zahteva sacuvanu validaciju. Protokol sadrzi komandu za kasniji rucni pilot.

Ovde se nalazi svih osam Python fajlova projekta. Eksperimentalna metodologija
je u [experiments/README.md](../experiments/README.md); zavisnosti i CUDA izvor
ostaju u `experiments/`, a rezultati u `experiments/results/`.

## Šta radi svaki fajl

| Fajl | Namena i trenutno stanje |
|---|---|
| `common.py` | Zajednički modul, nije samostalni eksperiment. Definiše CLI opcije, adaptere za DES/TDEA/AES, sintetičke ključeve, statistiku i CSV/JSON izvoz. Beleži seed, okruženje, verzije biblioteka, Git stanje i SHA-256 svih Python skripti u ovom direktorijumu. |
| `benchmark.py` | Izvršiv CPU benchmark DES-a, troključnog TDEA i AES-128/192/256 u CBC modu. Meri enkripciju i dekripciju, proverava povratnu dekripciju, odbacuje warmup i izvozi vremena i MB/s sa sredinom, medijanom i standardnom devijacijom. Podrazumevani ulazi: 1 KiB, 1 MiB i 10 MiB. |
| `aes_acceleration.py` | Izvršivo upareno poređenje softverske native AES implementacije i x86 AES-NI putanje PyCryptodome-a u CBC modu za sva tri ključa. Pre merenja proverava podršku i izbor native putanje, zatim računa vremena, throughput i odnos medijana. Softverska putanja nije AES pisan u Python-u; ARM backend nije implementiran. |
| `aes_gpu.py` | Kontrolni okvir za AES-128 ECB/CTR poređenje CPU software, CPU AES-NI i NVIDIA CUDA putanje. Ima plan, dijagnostiku okruženja, NIST validacione vektore, memorijske provere i pripremljeno odvojeno merenje kernela, transfera i ukupnog vremena. GPU benchmark još nije spreman: `../experiments/aes_gpu_kernel.cu` je namerno blokiran skeleton, a GPU tajmeri nisu hardverski validirani. |
| `avalanche_test.py` | Izvršiva demonstracija difuzije na jednom ECB bloku za DES, TDEA i AES. Odvojeno menja jedan bit poruke i jedan efektivni bit ključa i meri Hamming rastojanje. Izuzima DES paritetne bitove. Nije dokaz sigurnosti niti potpuni strict avalanche criterion test. |
| `brute_force_demo.py` | Izvršiva edukativna pretraga redukovanog AES-128 prostora sa 1–20 promenljivih bitova (podrazumevano 12). Meri pokušaje/s i ilustrativno ekstrapolira pune i očekivane pretrage prostora od 2^56 do 2^256. Ne pokušava puni DES/AES brute-force i ne daje realne procene napada na TDEA. |
| `export_results.py` | Čita postojeći direktorijum izvršavanja. Za CPU benchmark i AES-NI poređenje pravi LaTeX tabele i PNG/PDF grafikone. Za validirani CPU/GPU run priprema odvojene ECB/CTR grafikone propusnosti, latencije, overheada i ubrzanja. Odbija nevalidirane GPU rezultate; avalanche i brute-force grafikoni još nisu implementirani. Ne dodaje izlaze automatski u rad. |
| `smoke_check.py` | Integraciona provera na malim uzorcima: CLI, neispravni parametri, CSV i grafički izvoz, CPU putanje, avalanche reproduktivnost, ograničena pretraga, NIST fixture provere preko CPU reference i GPU blokade. Artefakti idu samo u `build/smoke/`. Ne validira stvarni CUDA kernel; bez AES-NI preskače hardversko CPU poređenje. |

## Pokretanje

Komande se pokreću iz korena repozitorijuma, uz Python 3.10 ili noviji:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r experiments/requirements.txt
```

Postojeće okruženje ne treba ponovo kreirati. Bez aktivacije može se koristiti
`.\.venv\Scripts\python.exe` umesto `python`. CuPy je opcionalan; izbor paketa
zavisi od stvarnog CUDA okruženja, kako je opisano u eksperimentalnom README-u.

Pet eksperimentalnih skripti bez `--run` samo prikazuje plan, bez merenja:

```powershell
python scripts/benchmark.py
python scripts/aes_acceleration.py
python scripts/aes_gpu.py
python scripts/avalanche_test.py
python scripts/brute_force_demo.py
```

Primeri stvarnih CPU pilot izvršavanja (nisu komande za konačnu studiju):

```powershell
python scripts/benchmark.py --run --purpose pilot --seed 2003 --repeats 10
python scripts/aes_acceleration.py --run --purpose pilot --seed 2003 --repeats 10
python scripts/avalanche_test.py --run --purpose pilot --seed 2003 --trials 1000
python scripts/brute_force_demo.py --run --purpose pilot --seed 2003 --bits 12 --repeats 3
```

Dijagnostika GPU-a ne meri performanse niti pravi rezultate:

```powershell
python scripts/aes_gpu.py --check
```

`--validate-only` i `--run` za GPU zahtevaju implementiran i validiran CUDA
kernel. U trenutnom stanju ne treba očekivati uspešan GPU benchmark.

Izvoz postojećeg run-a i integraciona provera:

```powershell
python scripts/export_results.py experiments/results/benchmark-pilot-ID
python scripts/smoke_check.py
```

`benchmark-pilot-ID` zameniti stvarnim imenom direktorijuma izvršavanja.
`smoke_check.py` zaista izvršava male testove i generiše tehničke artefakte;
oni nisu rezultati rada. `--help` prikazuje opcije svake CLI skripte osim
smoke provere, koja nema CLI parser. `common.py` se uvozi iz drugih skripti.

## Putanje i ograničenja

- Podrazumevani izlaz ostaje `experiments/results/<eksperiment>-<purpose>-<UTC>/`.
- `--output` menja osnovni direktorijum rezultata; relativna putanja se tumači prema radnom direktorijumu.
- CUDA izvor se pronalazi u `experiments/aes_gpu_kernel.cu` nezavisno od radnog direktorijuma.
- Postojeći rezultati se ne premeštaju i ne prepisuju. Izvoz dodaje tabele i grafikone u izabrani run direktorijum.
- DES/TDEA i deterministički ključevi služe isključivo kontrolisanom istorijskom i edukativnom poređenju, ne produkcionoj zaštiti.
- CBC CPU rezultate ne mešati sa ECB/CTR GPU rezultatima. CUDA kod nije produkciona kriptografska biblioteka.

## Eksperiment 1: aktuelni protokol

CBC validaciona prepreka je u `cpu_validation.py`, a izolovane provere su
u `cpu_smoke_check.py`: `python scripts/cpu_smoke_check.py`. One ne pokrecu
ostale eksperimente. Benchmark sada podrazumeva `software`, cuva min/max,
session ID i pre-measurement validaciju; study+auto se odbija. Detalji su u
[CPU CBC protokolu](../experiments/cpu_cbc_protocol.md).
