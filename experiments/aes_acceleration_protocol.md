# Eksperiment 2: AES software naspram AES-NI, CBC

Status: pripremljen i funkcionalno proveren; pravi pilot i study nisu pokrenuti
u ovoj sesiji. Eksperiment 1 i njegovi rezultati nisu menjani.

## Cilj i review

Ovo meri efekat AES-NI hardverske akceleracije u konkretnoj PyCryptodome
implementaciji na testiranom Intel CPU-u. Ne predstavlja opstu tvrdnju o svim
AES implementacijama ili svim procesorima. Obuhvat: AES-128/192/256, CBC bez
padding-a, software i AES-NI. Nema auto rezultata niti drugih modova.

Pregledani su aes_acceleration.py, common.py, export_results.py, postojeca
cpu_validation.py logika, wall/process instrumentacija benchmark.py i oba
README-a. Postojeci paired design i dispatch provera bili su odgovarajuci;
nedostajali su CBC KAT za obe putanje, persistirana validacija, procesno vreme
i validaciona prepreka izvoza. Prethodni izlaz mogao je biti oslobodjen unutar
narednog timed regiona; sada se brise van oba tajmera.

Zajednicki common.py ostaje neizmenjen: stats vec daje count/mean/median/sample
SD/min/max, a save_run cuva CSV/JSON, verzije, Git commit/status i hash-eve izvora.
Uvoze se samo AES vektori iz cpu_validation.py i environment_snapshot iz
benchmark.py; time se ne pokrecu eksperimenti 1 ili drugi eksperimenti.

## Putanje i validaciona prepreka

- software: eksplicitno use_aesni=False, kompajlirani `_raw_aes`.
- aesni: eksplicitno use_aesni=True, `_raw_aesni`.
- Probe zahteva CPU AES-NI capability i ucitanu native biblioteku. Odsustvo
  bilo kog uslova zaustavlja run; nema fallback rezultata pod AES-NI oznakom.
- Dispatch provera posmatra AES_start_operation i AESNI_start_operation za
  svaki kljuc/putanju. Zahteva dva poziva trazene i nula druge putanje.
  CBC koristi isti cbc_cipher factory u proveri, KAT-u i benchmarku.
- Ovo je bibliotecka dispatch validacija, ne instrukcijski trace. Privatni
  handle-i vracaju se cak i pri gresci, pre bilo kog merenja.

Funkcionalna prepreka koristi iste objavljene cetvoroblokovske CBC vektore kao
eksperiment 1: [NIST SP 800-38A F.2.1-F.2.6](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf).
Za svaki od tri kljuca proveravaju se software encrypt/decrypt i AES-NI
encrypt/decrypt: ukupno 12 operacija. Dekripcija prima objavljeni ciphertext,
ne rezultat upravo izvrsene enkripcije. Obe putanje moraju dati iste rezultate.

Pre prvog wall/process tajmera (i warmup-a) cuva se
aesni-validation-<purpose>-<session UUID>.json. Zapis sadrzi PASS/FAIL, izvore,
kljuc/IV/plaintext/ocekivani ciphertext, dispatch evidence, identitet sesije,
purpose i UTC pocetak/kraj. Neuspeh ostavlja FAIL zapis bez performance CSV-a.
Uspesan run kopira zapis u validation.json; metadata cuva isti zapis i SHA-256.

## Upareni dizajn i redosled

Jedan sinteticki plaintext po velicini dele sva tri AES kljuca. Kljuc je fiksan
po algoritmu/velicini. Svaka runda/algoritam dobija novi IV od 16 bajtova.
Obe putanje koriste identicne plaintext, kljuc, IV i velicinu. Za dekripciju
koriste isti referentni ciphertext pripremljen software putanjom izvan tajmera.
Svaki izmereni izlaz poredi se sa ocekivanim rezultatom izvan tajmera.

random.Random(seed) generise sinteticke podatke i reproduktivno mesa redosled
AES varijanti i cetiri posla (2 backend-a x 2 operacije) po rundi/algoritmu.
Redosled nije fiksno software-prvo niti encrypt-prvo. Ovo mesanje je statisticko,
ne garantuje savrsen balans u kratkom uzorku. Raw cuva variant_order/job_order,
repeat, session_id i pair_id (size:repeat:algorithm:operation); par se identifikuje
kombinacijom session_id/pair_id. Kljucevi i ponovljeni IV u paru su samo sinteticki test.

## Tajmeri i metadata

Primarna metrika: perf_counter_ns, monotonic wall elapsed timer. Meri jedan
CBC transform poziv sa alokacijom/vracanjem izlaza. Cipher construction/key
schedule, generisanje podataka, IV, referentna enkripcija, validacija, provera
rezultata i oslobadjanje prethodnog izlaza nisu u timed regionu.

Redosled: process_time_ns start, perf_counter_ns start, transformacija,
perf_counter_ns end, process_time_ns end. Raw cuva wall_elapsed_ns,
process_cpu_ns, process_to_wall_ratio, seconds i throughput_MB_s.

- seconds = wall_elapsed_ns / 1e9.
- throughput_MB_s = bytes * 1000 / wall_elapsed_ns (decimalni MB/s).
- process_to_wall_ratio = process_cpu_ns / wall_elapsed_ns; samo dijagnostika,
  ne speedup. Nula i odnos >1 nisu greske, posebno za 1 KiB i grube CPU tajmere.

process_time_ns meri CPU vreme trenutnog procesa, bez vremena kada proces nije
izvrsavan. Ne predstavlja hardverske cikluse. Njegov siri interval obuhvata i wall
timer bookkeeping; dodatna instrumentacija ima overhead izvan wall intervala.
Metadata cuva nazive i get_clock_info rezolucije oba tajmera. Jedinica ns ne
garantuje ns rezoluciju. Ne racuna se CPU-time throughput.

Environment snapshot pre/posle belezi ukupni CPU utilization, RAM, napajanje,
power plan i afinitet kao kontekst. Nema automatskog CPU threshold gate-a,
menjanja prioriteta/afiniteta/power plana niti kontrole drugih procesa.
Korisnik rucno pokrece kada je sistem priblizno idle, bez namernog konkurentskog
workload-a. Temperature/taktovi nisu nadzirani; ne tvrditi odsustvo throttling-a.

Run cuva Git commit/dirty status, seed/argv, Python/OS/CPU/jezgra/RAM, verzije
PyCryptodome/matplotlib/psutil, pip freeze, hash AES modula i SHA-256 skripti.
source/ arhivira aes_acceleration.py, common.py, cpu_validation.py, benchmark.py
(environment helper) i export_results.py. Generated rezultati su gitignored;
za kasniju reprodukciju arhivirati ceo run.

## Statistika, izvoz i ogranicenja

Po algorithm x backend x operation x size x session cuvaju se count, mean,
median, sample SD (n-1), min i max za seconds i throughput_MB_s. Iste zasebne
dijagnosticke statistike cuvaju se za process_cpu_ns i process_to_wall_ratio.
Mean throughput je prosek pojedinacnih propusnosti, ne bytes/mean(time).

speedup_vs_software_median = software_median_seconds / backend_median_seconds.
Software red je 1.0; AES-NI red je odnos medijana wall vremena (ne odnos mean
throughput-a niti medijana pojedinacnih odnosa). Faktor ne mora biti veci od 1.
SD nije interval poverenja. Buduce sesije analizirati odvojeno, ne tretirati
unutarsesijska ponavljanja kao nezavisne procese.

Exporter zahteva sacuvanu uspesnu validaciju sa odgovarajucim hash-em, svim KAT
i dispatch zapisima, identitetom sesije/purpose i zavrsetkom pre merenja.
Proverava i potpunost summary parova i speedup formulu pre pravljenja izlaza:

- aes_acceleration_table.tex: software/AES-NI, wall throughput statistike i faktor.
- aes_acceleration.png/.pdf: odvojene putanje, mean wall throughput +/- sample SD.
- aes_acceleration_speedup.png/.pdf: AES-NI faktor za svaki kljuc i software=1 linija.

Purpose i run ID vidljivi su u izlazima; pilot/smoke nisu rezultati rada.
Nista se automatski ne dodaje u rad. Stari acceleration run bez nove validacione
evidencije ne moze se izvesti kao validiran; ne izmisljati retroaktivnu validaciju.

Mali ulazi ukljucuju Python/timer overhead, prethodna enkripcija zagreva kes,
a CBC ima zavisnosti blokova. Rezultati nisu cold-start niti dokaz sigurnosti
ili constant-time svojstava. Ne prenositi zakljucke na GCM, GPU ili druge CPU-e.
Promena PyCryptodome privatnog API-ja zahteva novi review; bibliotecki dispatch
je proveren lokalno na 3.23.0, a ne garantovan za sve buduce verzije.

## Izolovana provera i kasnije rucno merenje

Izvrseno samo:

```powershell
.\.venv\Scripts\python.exe scripts/aes_acceleration_smoke_check.py
```

Rezultat: pet grupa testova PASS. Ukljucene su svih 12 KAT operacija, capability
i dispatch, negativni testovi nedostupnosti/fallback-a/neispravnog KAT-a, identicni
ulazi u paru, deterministicko mesanje, timer granice, nula/>1 process ratio,
raw/summary formule i validirani izvoz. Jedini stvarni merni run ima purpose=smoke,
1 KiB, warmup 1 i repeats 2 (24 raw i 12 summary redova). Dodatne instrumentacione
provere koriste mock tajmere i privremene direktorijume, ne performance rezultate.

Artefakti: build/aes-acceleration-smoke/aes_acceleration-smoke-20260929T160138763952Z/.
Nema otvorene funkcionalne prepreke za rucni pilot; stabilnost tek treba proceniti.

Sledecu komandu korisnik izvrsava rucno iz korena projekta; NIJE izvrsena:

```powershell
.\.venv\Scripts\python.exe scripts/aes_acceleration.py --run --purpose pilot --sizes 1024 1048576 10485760 --warmup 3 --repeats 20 --seed 2003
```

Ocekivano: 720 raw i 36 summary redova. Velicine ostaju 1 KiB/1 MiB/10 MiB;
100 MiB/1 GiB nisu dodati. Default ostaje kompatibilan, a komanda eksplicitno
zadaje predlozeni warmup/repeats. Posle analize pilota moguc je protokol sa pet
nezavisnih procesa, seedovima 2003-2007, warmup 3/repeats 20 i rotiranjem redosleda
velicina preko --sizes. CLI cuva zadati redosled. Taj study nije pokrenut niti
automatski zakazan.
