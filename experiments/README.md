# Lista eksperimenata

Eksperiment 1 — istorijski CPU benchmark: DES / TDEA / AES-128 / AES-192 / AES-256, CBC.
Eksperiment 2 — AES software vs AES-NI: AES-128/192/256.
Eksperiment 3 — AES-GCM: AES-128-GCM / AES-256-GCM, CPU AES-NI.
Eksperiment 4 — CUDA AES-128 baseline: prvo ECB/CTR validacija, zatim baseline.
Eksperiment 5 — CUDA optimizacija + finalno CPU/GPU poređenje.
Eksperiment 6 — brute-force demonstracija.
Eksperiment 7 — Double-DES MITM, ako ga zadržimo.
Eksperiment 8 — avalanche efekat.

# Eksperimentalni okvir

Python skripte su premeštene u `../scripts/`. Pregled svakog fajla i osnovne
komande nalaze se u [scripts/README.md](../scripts/README.md).
Sve komande ispod pokreću se iz korena repozitorijuma. Ovaj direktorijum
zadržava metodologiju, `requirements.txt`, CUDA izvor i `results/`.

Status: početni izvršivi kostur, bez merenja za članak. Osnovne petlje i izvoz
omogućavaju tehničku proveru; studija, publikacioni grafikoni i tumačenje ostaju
za kasnije. Bez `--run` prikazuje se samo plan. DES/TDEA služe istorijskom poređenju.

## Benchmark

`benchmark.py` poredi DES, troključni TDEA i AES-128/192/256 u istom CBC modu.
Veličine: 1024, 1048576, 10485760 bajtova (1 KiB, 1 MiB, 10 MiB).
Opciono: `--sizes 1024 1048576 10485760 104857600`.
Nema padding-a; veličine moraju biti deljive sa 16. Ovo nije produkcioni format.

Za svaki algoritam i bafer postoji ključ; svako ponavljanje ima novi IV i nove
objekte šifre. Warmup se odbacuje prema unapred definisanom pravilu.
Redosled algoritama meša se seedovanim generatorom. Enkripcija prethodi dekripciji,
pa efekat keša i redosleda ostaje ograničenje. Tajmer obuhvata transformaciju i
alokaciju izlaza, ne inicijalizaciju šifre, key schedule, generisanje podataka
ili proveru povratne dekripcije.

CSV čuva vreme i throughput svake operacije. Sažetak daje broj uzoraka, sredinu,
medijanu i uzoračku SD za obe metrike. Srednja propusnost je sredina pojedinačnih
propusnosti, ne količnik bajtova i srednjeg vremena. MB/s koristi 10^6 bajtova;
KiB/MiB koriste 2^10/2^20. SD nije interval poverenja.

`--aes-backend auto` dozvoljava automatski izbor, bez potvrde aktivnog AES-NI.
`--aes-backend software` traži `use_aesni=False`; pre studije validirati izvršni
put. Zvanični API: https://www.pycryptodome.org/src/cipher/aes .
Ako biblioteka ne podržava DES/TDEA, skripta završava sa greškom; nema neprimetne
zamene ili preskakanja algoritma. Promenu biblioteke posebno dokumentovati.

## AES-NI naspram softverske implementacije

`aes_acceleration.py` je zaseban upareni CBC eksperiment za AES-128/192/256:

```powershell
python scripts/aes_acceleration.py
python scripts/aes_acceleration.py --run --seed 2003 --repeats 10
```

Podrazumevane veličine su 1 KiB, 1 MiB i 10 MiB. Obe putanje dobijaju iste
poruke, ključeve, IV i referentni šifrat po paru. Ovo ponavljanje IV-a je
kontrolisani sintetički test identične poruke, ne primer produkcione upotrebe.
Varijante i četiri posla (dva backend-a puta dve operacije) mešaju se u svakoj
rundi. Referentna enkripcija, inicijalizacija, warmup i provere su van merenja.
Prethodna obrada bafera može zagrejati keš; ovo nije cold-cache benchmark.

`use_aesni=True` sam ne garantuje akceleraciju. Pre merenja proveravaju se
CPU AES-NI podrška, dostupnost native modula i inicijalizacijski pozivi
`AESNI_start_operation` naspram `AES_start_operation` za sva tri ključa.
Privatni bibliotečki interfejsi posmatraju se samo tokom provere i vraćaju pre
merenja. Ako provera ne uspe, eksperiment staje bez izvoza rezultata.
Metapodaci čuvaju brojeve poziva, verziju i hash AES Python modula.
Ovo potvrđuje izbor bibliotečke putanje, ne predstavlja instrukcijski trag CPU-a.

Softverska putanja je prenosivi kompajlirani AES u istoj biblioteci, uz
`use_aesni=False`; nije čista Python implementacija ni obećanje constant-time
ponašanja. Trenutni eksperiment je za x86 AES-NI. ARM crypto extensions zahtevaju
poseban backend i ostaju budući rad.

Pored vremena i MB/s (sredina, medijana, SD), sažetak daje
`speedup_vs_software_median = median(t_software) / median(t_backend)`.
Softverska referenca ima faktor 1; AES-NI faktor ne mora biti veći od 1.
Ne zaključivati iz vrlo malog uzorka niti prenositi CBC odnos na GCM/CTR.
Ovo je poređenje današnjih implementacija na istom CPU-u, ne rekonstrukcija 2003.

Izvoz: `python scripts/export_results.py experiments/results/aes_acceleration-pilot-ID`.
Dobijaju se CSV/JSON pri merenju i LaTeX/PNG/PDF pri izvozu, sa jasno označenim
putanjama. Rezultati ostaju izvan članka do analize.
API i dispatch provereni su prema
[zvaničnoj dokumentaciji](https://www.pycryptodome.org/src/cipher/aes) i
[izvornom kodu verzije 3.23.0](https://github.com/Legrandin/pycryptodome/blob/v3.23.0/lib/Crypto/Cipher/AES.py).
Promene privatnih interfejsa pri nadogradnji zahtevaju novu proveru.

## Avalanche

`avalanche_test.py` obrađuje jedan blok u ECB modu radi izolovanja primitive.
Svaki uzorak menja odvojeno jedan bit poruke i jedan efektivni bit ključa.
DES/TDEA paritet (LSB svakog bajta) isključen je iz izbora; TDEA ima tri komponente.
Promena koja degeneriše TDEA ponovo se uzorkuje i broji u metapodacima.
Biblioteka ignoriše DES paritet; ne zahteva njegovu dodatnu izmenu za transformaciju.

Čuvaju se Hamming distance i udeo izmenjenih bitova, uz LSB-first numeraciju
pozicija u bajtu. Normalizacija omogućava poređenje blokova od 64 i 128 bita.
Ovo nije potpuni strict avalanche criterion test niti dokaz sigurnosti.
SD jednog uzorka je `null` u JSON-u i prazno polje u CSV-u.

## Redukovana pretraga

`brute_force_demo.py` koristi AES-128 sa 1–20 promenljivih bitova, ostalim bitovima
nula, podrazumevano 12. Uniformni cilj se traži redom, uz dva poznata bloka.
Brzina uključuje konstruisanje ključa, inicijalizaciju šifre, enkripciju i poređenje.

Izmereni pokušaji/s ilustrativno se primenjuju na apstraktne prostore
2^56, 2^112, 2^128, 2^192 i 2^256. Celo pretraživanje je N/r, očekivano (N+1)/(2r),
za jedan uniformni cilj. Čuvaju se sekunde i godine u naučnoj notaciji i log10.
Godina je 365.25 dana. Starost svemira ostaje TODO do provere izvora.

Ovo nisu stvarne procene DES/TDEA/AES napada. Jedna AES/Python brzina služi
ilustraciji rasta prostora; ASIC/GPU, paralelizacija i MITM menjaju model.
TDEA sigurnost nije zbir dužina tri ključa.

## Reproduktivnost i izvoz

`common.py` obezbeđuje adaptere, statistiku i direktorijume sa UTC run ID-jem.
Beleži seed, argumente, Python, OS, CPU, jezgra, RAM, verzije biblioteka, commit,
Git status, SHA-256 skripti i beleške. `--notes` služi za napajanje, opterećenje,
termalno stanje i druga ograničenja; te promenljive nisu automatski kontrolisane.
Nepotpunu CPU identifikaciju na pojedinim platformama dopuniti beleškama.
Deterministički sintetički ključevi nisu za produkciju.

Run sadrži `raw.csv`, `summary.csv`, `results.json`, `metadata.json` i, kada pip
radi, `requirements-lock.txt`. Za reprodukciju koristiti iste verzije i kod.
Generisani direktorijumi su Git-ignored; odabrane konačne podatke kasnije
eksplicitno arhivirati i verzionisati.

`export_results.py <run_directory>` izvozi oba benchmark eksperimenta: `booktabs` tabelu
za landscape prikaz i PNG/PDF grafikone sredina sa SD. Avalanche raspodele i
brute-force log-grafikoni ostaju TODO. Nijedan eksport se ne dodaje u `main.tex`.

## GPU CUDA okvir

`scripts/aes_gpu.py` je pripremljen kontrolni okvir, a `experiments/aes_gpu_kernel.cu` **nije
implementacija AES-a**: sadrži potpis funkcija, pravila indeksiranja i eksplicitnu
kompilacionu blokadu. Nema GPU rezultata. Ostaje implementacija, pregled i
validacija CUDA jezgra, zatim provera tajmera na stvarnom GPU-u. Okvir se ne
predstavlja kao production-ready biblioteka.

```text
experiments/
|-- README.md
|-- requirements.txt
|-- aes_gpu_kernel.cu
|-- results/
    |-- README.md
```

### Okruženje i opcionalna instalacija

```powershell
nvidia-smi
nvcc --version
python scripts/aes_gpu.py --check
```

Nedostatak `nvcc` ne dokazuje da nema runtime-a/NVRTC-a. Verzija CUDA koju
prikazuje drajver nije potvrda verzije instaliranog Toolkit-a.
Izabrati **jedan** odgovarajući CuPy paket prema
[zvaničnom uputstvu](https://docs.cupy.dev/en/stable/install.html).
Primeri su `cupy-cuda12x` za kompatibilno CUDA 12.x okruženje i
`cupy-cuda13x` za odgovarajuće CUDA 13.x okruženje; ovo nisu automatske
preporuke za lokalni računar. Proveriti dostupnost wheel-a za OS/Python i
potrebne CUDA runtime/NVRTC biblioteke. Ne instalirati više CuPy varijanti zajedno.
Posle izbora: `python -m pip install IME_ODGOVARAJUCEG_CUPY_PAKETA`.
`python -c "import cupy; cupy.show_config()"` proverava stvarno okruženje.
`requirements.txt` namerno ne instalira nijedan CUDA paket.

Lokalna dijagnostika 2026-09-27: GTX 1650 Ti, compute capability 7.5,
4096 MiB, drajver 610.62; CuPy nije instaliran, `nvcc` nije pronađen u PATH-u.
To nisu benchmark podaci i ne dokazuje se dostupnost CUDA runtime-a.

### Validaciona blokada

```powershell
python scripts/aes_gpu.py
python scripts/aes_gpu.py --check
# Tek posle implementacije kernela i podešavanja CUDA okruženja:
python scripts/aes_gpu.py --validate-only
python scripts/aes_gpu.py --run --purpose pilot --repeats 10 --warmup 2
```

Plan/check ne mere performanse niti kreiraju rezultate. Run u sadašnjem stanju
završava greškom: kernel nije implementiran. Posle implementacije **svaki run**
mora da prođe NIST SP 800-38A F.1.1 i F.5.1 (jedan i četiri bloka), poređenje sa
CPU referencom, granice thread-block-a, nepotpun CTR blok i prenos brojača.
Porede se ključ, plaintext i puni 128-bitni big-endian početni brojač.
Promena reda bajtova ili modulo-64 inkrement nije dozvoljena.
Testovi funkcionalnosti nisu dokaz sigurnosti.

CPU putanje proveravaju se za konkretne ECB/CTR modove preko postojećeg
`verify_dispatch`. Ako AES-NI nije dostupan ili se putanja ne može potvrditi,
tropolno poređenje završava kao nepotpuno. Nema tihog označavanja auto putanje
kao software. ARM akceleracija još nema adapter.

### Protokol merenja

Samo AES-128 enkripcija: ECB je test primitive, CTR glavni paralelni mod.
CBC rezultati iz drugih skripti ne ulaze u iste grafikone. ECB nije preporuka
za zaštitu podataka; CTR ovde nema autentifikaciju. AES-192/256 na GPU-u ostaju
opciono proširenje nakon validacije.

Ulazi: 1 KiB, 16 KiB, 1 MiB, 16 MiB, 100 MiB, 1 GiB. `--sizes` prima bajtove,
`--threads` 64/128/256, `--device` indeks GPU-a. Po veličini se proverava RAM
(budžet 6x ulaz) i GPU memorija (2x ulaz + rezerva), uz 30% slobodne rezerve.
Nedovoljan kapacitet preskače veličinu sa razlogom u `method.skipped_sizes`.
Allocation failure odbacuje delimične uzorke te veličine. Ne preskaču se
kriptografske greške. Ako su sve veličine preskočene, run prijavljuje razloge,
bez praznog benchmark-a.

Obe CPU putanje i GPU koriste iste podatke po veličini/modu. Redosled backend-a
meša se seedovanim generatorom. Ponovljeni ključ/counter i isti ulaz služe samo
kontrolisanom testu. Prvo kompajliranje i svi warmup uzorci su van statistike.
JIT/keširanje opisani su u
[RawKernel dokumentaciji](https://docs.cupy.dev/en/stable/reference/generated/cupy.RawKernel.html).

Vremena su u ms, throughput u MiB/s (2^20 bajtova):

| Polje | Značenje |
|---|---|
| `kernel_ms` | CUDA events oko kernela, uz sinhronizaciju završnog događaja. |
| `transfer_ms` | Zidno H2D + D2H vreme, uključujući staging i sinhronizaciju. |
| `end_to_end_ms` | GPU: H2D + kernel + D2H + sinhronizacija; CPU: kreiranje šifre + enkripcija/alokacija izlaza. |
| `crypto_ms` | CPU enkripcija, bez kreiranja objekta šifre. |
| `resident_kernel_ms` | Dodatni prolaz kernela nad već prisutnim podacima. |
| `resident_end_to_end_ms` | Zidno vreme tog dodatnog poziva i sinhronizacije bez transfera. |
| `throughput_mib_s` | Veličina / ukupno vreme. |
| `kernel_throughput_mib_s` | Veličina / vreme kernela. |

GPU baferi su unapred alocirani, host baferi su pageable, prenosi su serijski na
jednom stream-u. GPU key expansion/upload, JIT i alokacije su izuzeti; kod CPU-a
setup je uključen u ukupno, ali izuzet iz `crypto_ms`. Jasno navesti ovu razliku.
Ovo nije cold-start aplikativno vreme. Dodatni scenario sa alokacijama i key
setup-om tek treba uvesti. GPU baferi i ključevi nisu bezbedno obrisani.

Sredina, medijana, uzoračka SD, minimum, maksimum i broj uzoraka čuvaju se po
veličini/modu/backend-u. Pre studije dodati nezavisne sesije i kontrolu napajanja,
takta i opterećenja. Event merenje i rezidentni prolaz nisu validirani na GPU-u
dok skeleton nije implementiran. Ne tumačiti SD kao interval poverenja.

### Datoteke i grafikoni

`experiments/results/aes_cpu_gpu-<purpose>-<UTC>/` sadržaće standardne
`raw.csv`, `summary.csv`, `metadata.json`, `results.json` i verzije paketa,
kao i eksplicitne `aes_cpu_gpu_raw.csv`, `aes_cpu_gpu_summary.csv` i
`aes_cpu_gpu_environment.json`. Nema prepisivanja prethodnih izvršavanja.
Okruženje uključuje CPU, jezgra, AES-NI, GPU, capability/memoriju, driver,
runtime, CuPy/Python/OS/PyCryptodome i hash CUDA izvora. Nedostajuće vrednosti
ostaju `null` uz objašnjenje.

Obavezne raw kolone su `backend,algorithm,mode,key_bits,input_bytes,iteration,
kernel_ms,transfer_ms,end_to_end_ms,throughput_mib_s`. CPU GPU-polja su prazna,
ne nule. Backend oznake: `cpu_software`, `cpu_aesni`, `gpu_cuda`.

`export_results.py` prihvata samo GPU run sa zabeleženom validacijom i potpunim
grupama. Za svaki mod zasebno priprema četiri PDF/PNG grafikona:
`throughput_vs_size`, `latency_vs_size`, `gpu_overhead_breakdown` i
`speedup_vs_size`, uz `aes_cpu_gpu_table.tex`. Propusnost poredi CPU ukupno,
GPU kernel i GPU ukupno; faktori su CPU AES-NI medijana / GPU medijana.
Rezidentna latencija ostaje posebno dostupna u CSV-u.
Grafikoni ne pretpostavljaju da GPU ikada prelazi CPU.

Breakdown koristi srednja vremena iz istog transfer/kernel prolaza.
Ostatak `end_to_end - transfer - kernel` nije čisto vreme launch-a: uključuje
Python, event i sinhronizacijski overhead, uz različite časovnike. Ako je
negativan, grafikon ga označava kao mernu nesigurnost umesto prikrivanja.
Ukoliko nema stvarnih validiranih podataka, grafikoni se ne generišu.

### Granice i sledeći koraci

Ne ispituju se constant-time svojstva, side-channel/fault-injection otpornost
ni sigurno upravljanje ključevima. GPU kod služi isključivo performansnoj studiji.
Ostaje: implementacija tri CUDA funkcije iz ABI ugovora, hardverska validacija,
provera CUDA merenja i izvoza stvarnih grafikona, pa pilot i puna studija.
Osnova: NVIDIA Programming Model / Intro to CUDA Python i CuPy dokumentacija;
reference su dodate u `references.bib`, bez preuzetih benchmark rezultata.

## Preostali zajednički zadaci

- TODO: Proveriti implementacije prema objavljenim test vektorima sa izvorima.
- TODO: Definisati broj nezavisnih sesija, kontrolu opterećenja i veličinu uzorka.
- TODO: Razmotriti encrypt/decrypt redosled, Python overhead, keš i temperaturu.
- TODO: Odvojeno meriti setup i AEAD; ne mešati CBC i GCM.
- TODO: Za studiju pregledati zapis provere AES-NI dispatch-a; za jače tvrdnje dodati profilisanje instrukcija i ponoviti na više CPU modela.
- TODO: Pripremiti grafikone raspodele i prikaz nesigurnosti.
- TODO: Pregledati svaku tabelu pre uključivanja u članak.

`smoke_check.py` proverava tok na malim uzorcima, izvoz, broj zapisa, odbijanje
neispravnih parametara i reproduktivnost netajmiranih avalanche rezultata.
Izlazi su u `build/smoke/` i nisu rezultati rada.
