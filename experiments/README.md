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

`export_results.py <run_directory>` trenutno izvozi benchmark: `booktabs` tabelu
za landscape prikaz i PNG/PDF grafikone sredina sa SD. Avalanche raspodele i
brute-force log-grafikoni ostaju TODO. Nijedan eksport se ne dodaje u `main.tex`.

## Otvoreni zadaci

- TODO: Proveriti implementacije prema objavljenim test vektorima sa izvorima.
- TODO: Definisati broj nezavisnih sesija, kontrolu opterećenja i veličinu uzorka.
- TODO: Razmotriti encrypt/decrypt redosled, Python overhead, keš i temperaturu.
- TODO: Odvojeno meriti setup i AEAD; ne mešati CBC i GCM.
- TODO: Potvrditi izvršni put pre AES-NI on/off poređenja.
- TODO: Pripremiti grafikone raspodele i prikaz nesigurnosti.
- TODO: Pregledati svaku tabelu pre uključivanja u članak.

`smoke_check.py` proverava tok na malim uzorcima, izvoz, broj zapisa, odbijanje
neispravnih parametara i reproduktivnost netajmiranih avalanche rezultata.
Izlazi su u `build/smoke/` i nisu rezultati rada.
