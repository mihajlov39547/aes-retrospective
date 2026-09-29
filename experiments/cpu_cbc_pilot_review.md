# Eksperiment 1: izvestaj posle pilota, 2026-09-29

Izvrsen je samo CBC pilot. Nema study run-a ni izmena teksta rada.
Detaljan review koda i metodologije: [cpu_cbc_protocol.md](cpu_cbc_protocol.md).

## 1. Pregledano

scripts/benchmark.py; sve funkcije common.py koje poziva direktno i posredno;
scripts/export_results.py, scripts/smoke_check.py, scripts/README.md,
experiments/README.md, experiments/results/README.md, requirements.txt i
chapters/09_eksperimentalna_analiza.tex. Pregledani su i instalirani AES/DES/DES3
adapteri PyCryptodome 3.23.0 i autoritativni izvori CBC vektora.
Postojeci smoke_check nije pokrenut jer izvrsava i druge eksperimente.

## 2. Promene i razlozi

| Fajl | Promena | Razlog |
|---|---|---|
| scripts/common.py | Odbija i K1=K3 posle pariteta; stats dodaje min/max | Strogo trokljucni TDEA i potpuna statistika; postojeca polja zadrzana |
| scripts/cpu_validation.py | Objavljeni CBC vektori, obe operacije, software dispatch, persistirani PASS/FAIL | Round-trip sam nije dovoljan; prekid pre merenja |
| scripts/benchmark.py | Obavezna prepreka; software default; study+auto odbijen; oslobadjanje starih izlaza van tajmera; UUID/order/ns; environment pre/posle; arhiva izvora | Jedna eksplicitna AES putanja, precizan timed region, sledljivost |
| scripts/export_results.py | Odbija CBC bez validacije i odgovarajuceg hash-a; tri znacajne cifre za throughput | Ne izvoziti nevalidirane rezultate; manje lazne preciznosti |
| scripts/cpu_smoke_check.py | Sest izolovanih grupa testova | Provera samo eksperimenta 1, ukljucujuci deset namerno neispravnih putanja |
| scripts/README.md, experiments/README.md | Dopune sa vezom na protokol | Evidencija novog ponasanja |
| experiments/cpu_cbc_protocol.md | Detaljan review i pre-pilot plan | Metodologija definisana pre merenja |

Nisu menjani AES acceleration/CUDA/GCM/brute-force/avalanche ni poglavlje rada.

## 3. Funkcionalna validacija

| Algoritam | Enkripcija/dekripcija | Izvor |
|---|---|---|
| DES | PASS/PASS | FIPS 81, Table C1, tri CBC bloka |
| TDEA, tri kljuca | PASS/PASS | NIST CBC-TDES example pp. 1-3, cetiri bloka |
| AES-128 | PASS/PASS | NIST SP 800-38A F.2.1/F.2.2, cetiri bloka |
| AES-192 | PASS/PASS | NIST SP 800-38A F.2.3/F.2.4, cetiri bloka |
| AES-256 | PASS/PASS | NIST SP 800-38A F.2.5/F.2.6, cetiri bloka |

Linkovi izvora su u protokolu i svakom validation.json. Poznati ciphertext je
nezavisan fixture za dekripciju. Komanda `.\.venv\Scripts\python.exe scripts/cpu_smoke_check.py`
zavrsila je sa sest proslih testova. Negativni testovi potvrdjuju STOP pre
perf_counter_ns/save_run za svaku operaciju svakog algoritma.

U pilotu validacija zavrsava 14:54:45.665 UTC, a merna faza pocinje
14:54:46.714 UTC. Vektori, ulazi i dokazi su u
[validation.json](results/benchmark-pilot-20260929T145458153902Z/validation.json).
Ovo je funkcionalna provera, ne formalna sertifikacija ili dokaz sigurnosti.

## 4. AES backend

Iskljucivo software: use_aesni=False -> kompajlirani _raw_aes.
Potvrdjena po dva native initialization poziva za svaki AES kljuc; pristup
AES-NI modulu je tokom provere zabranjen. To nije instrukcijski trag.
Ne uvodimo prednost namenskih AES instrukcija samo za AES, ali i dalje merimo
konkretne implementacije na savremenom CPU-u, ne apstraktne algoritme ili 2003.
Razlike u implementaciji, duzini bloka i broju rundi ostaju deo poredjenja.

## 5. Tacna pilot komanda

Iz C:\Projects\aes:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark.py --run --purpose pilot --aes-backend software --sizes 1024 1048576 10485760 --warmup 2 --repeats 5 --seed 2003 --notes "Experiment 1 diagnostic pilot only; desktop workload not controlled; temperature and clocks not monitored; AC and power scheme captured automatically."
```

Izvoz je proveren komandom:

```powershell
.\.venv\Scripts\python.exe scripts/export_results.py experiments/results/benchmark-pilot-20260929T145458153902Z
```

## 6. Dijagnostika pilota

Run: [benchmark-pilot-20260929T145458153902Z](results/benchmark-pilot-20260929T145458153902Z/metadata.json).
CPU Intel Core i5-10300H; Python 3.12.10; PyCryptodome 3.23.0;
matplotlib 3.11.2; psutil 7.2.2. Git commit
a925586c3f6f1071397b98b28004b2df51472252, dirty stanje sacuvano.
Merna faza sa pripremom i warmup-om traje 10.3 s, bez validacije/snapshot-a/izvoza.

| Ulaz | Medijana CV vremena preko 10 kombinacija | Raspon CV | Najveci max/min unutar kombinacije |
|---|---:|---:|---:|
| 1 KiB | 22% | 4.1-66% | 4.13 |
| 1 MiB | 46% | 27-78% | 5.78 |
| 10 MiB | 7.2% | 2.0-12% | 1.31 |

CV = uzoracka SD / srednje vreme, pet uzoraka po kombinaciji. Ovo je gruba
dijagnostika malog uzorka, ne rangiranje algoritama. Najveci CV na 1 MiB
ima AES-256 encrypt (78%); ni vecina drugih kombinacija nije stabilna.
CPU opterecenje pre/posle: 34.9%/28.3%; ne dokazuje uzrok svakog sporog uzorka,
ali ne odgovara mirnom sistemu. AC ukljucen; Balanced power plan; svih osam
logickih CPU-a u afinitetu. Slobodno oko 5.7 GiB RAM-a. Temperature/taktovi nepoznati.

Potvrdjeno: 150 raw/30 summary redova, CSV/JSON saglasnost, throughput formula,
nezavisno ponovno racunanje svih statistika, prethodna validacija, hash validacije
i hash-evi arhiviranih izvora. PNG/PDF/LaTeX izvozi postoje sa oznakom pilot.
Detalji: [pilot_diagnostics.json](results/benchmark-pilot-20260929T145458153902Z/pilot_diagnostics.json).
Nista nije ukljuceno u rad.

## 7. Predlog finalnog protokola (jos nije izvrsavan)

- Ulazi: 1 KiB, 1 MiB, 10 MiB. 1 KiB tumaciti kao biblioteku/poziv sa overhead-om.
- Software, CBC bez padding-a; ista definicija vremena i alokacije kao u pilotu.
- Tri warmup runde i 20 ponavljanja po kombinaciji; pet zasebnih Python procesa.
- Seedovi 2003-2007; algoritmi seedovano mesani u svakoj rundi.
  Velicine po sesijama: [1 KiB,1 MiB,10 MiB], [1 MiB,10 MiB,1 KiB],
  [10 MiB,1 KiB,1 MiB], [1 KiB,10 MiB,1 MiB], [10 MiB,1 MiB,1 KiB].
  Enkripcija prethodi dekripciji; ne tumaciti razliku kao izolovan algoritamski efekat.
- Cuvati sve postojece raw metrike i mean/median/sample SD/min/max/count po sesiji.
  Glavni prikaz: medijane sesija i njihov raspon/SD; ne objedinjavati ponavljanja
  kao nezavisne sesije i ne predstavljati SD kao interval poverenja.
- AC, isti zabelezeni power plan, bez aktivnih korisnickih/background poslova.
  Ispravka posle review-a: korisnik rucno proverava priblizno idle stanje bez
  namerno pokrenutog konkurentskog workload-a. Raniji predlog CPU <5% tokom
  60 s je povucen. Ukupno CPU opterecenje je samo environment metadata,
  ne performance rezultat niti automatski kriterijum validnosti run-a.
- Power/turbo politika ista za sve sesije; hladjenje/ventilacija isti, bez
  promene profila usred rada. Zabeleziti temperaturu/takt ako postoji pouzdan
  senzor; inace eksplicitno ostaviti nepoznato i ne tvrditi da throttling ne postoji.
- Poznati prekid/promena napajanja: celu sesiju oznaciti, sacuvati i ponoviti;
  ne brisati pojedinacne outlier-e. Zakljucati verziju izvora pre studije.

100 MiB sada ne predlazem u osnovnom skupu. Mogao bi dodati streaming/memorijsku
tacku, ali 10 MiB vec daje dovoljno dug poziv za glavno pitanje. Nema dokaza da
10 MiB predstavlja memorijski plateau; tu tvrdnju ne praviti. Gruba linearna
procena iz pilota: tri velicine sa 5x23 runde oko 3 min samih transformacija,
a dodatnih 100 MiB oko 24 min vise, bez pripreme/mirovanja. To nisu izmerena
vremena buduce studije. Za 100 MiB racunati najmanje 600 MiB radne rezerve plus
OS; trenutni RAM bi to podneo. Memorija nije razlog iskljucenja; dodatna vrednost
u odnosu na vreme i termalni uticaj trenutno nije dovoljna. 1 GiB nije potreban.

## 8. Otvoreni problemi

1. Visoko opterecenje i velika varijansa; pre studije ponoviti kontrolisan pilot
   sa predlozenim warmup/repeats i istim velicinama. U ovoj sesiji nije ponovljen.
2. Nema kontinuiranih temperatura/taktova niti dokaza o odsustvu throttling-a.
3. Mali ulaz je osetljiv na Python/tajmer/scheduler; ne tumaciti ga kao cistu
   kriptografsku brzinu. Namerno nije uveden novi batch benchmark posle pilota.
4. Redosled encrypt->decrypt i efekti kesa ostaju eksplicitna granica protokola.
5. Rezultati su lokalni i gitignored po postojecem pravilu; arhivirati ceo run
   (ukljucujuci source i lock) pre studije/publikacije. Dirty izvor pilota sacuvan je.
6. Privatni dispatch API zahteva novu proveru pri promeni PyCryptodome verzije.

## 9. Status

Kod i validaciona prepreka su prosli provere, ali ovaj pilot nije potvrdio
stabilne uslove. Potrebni su miran sistem, dokumentovana power/thermal politika
i kontrolisan ponovni pilot pre studije. Nema studijskih rezultata.

NOT READY FOR STUDY RUN
