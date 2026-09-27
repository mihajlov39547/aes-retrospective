# Eksperimentalni okvir

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
python experiments/aes_acceleration.py
python experiments/aes_acceleration.py --run --seed 2003 --repeats 10
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

Izvoz: `python experiments/export_results.py experiments/results/aes_acceleration-pilot-ID`.
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

## Otvoreni zadaci

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
