# Eksperiment 1: CBC CPU review i protokol

Studija nije pokrenuta. Ovaj dokument dopunjuje README samo za eksperiment 1.

## Review

Pregledani: benchmark.py i sve njegove funkcije iz common.py (parser/positive,
print_plan, modules, key_for, block_size, cipher, stats, metadata/command_output,
write_csv/save_run), exporter, smoke_check, scripts/README.md, experiments/README.md,
results/README.md, requirements.txt i poglavlje 09. Poglavlje rada nije menjano.

- random.Random(seed).randbytes: reproduktivni sinteticki podaci i kljucevi,
  ne bezbedan generator. AES kljucevi: 16/24/32 bajta.
- DES: 8 bajtova, efektivno 56 bitova; biblioteka ignorise LSB paritet.
  Normalizacija nije potrebna; poseban test proverava paritetnu ekvivalenciju.
- TDEA: 24 bajta sa neparnim paritetom. Stari adjust_key_parity odbijao je
  K1=K2 i K2=K3, ali dozvoljavao K1=K3. Sada su sve tri komponente razlicite
  posle normalizacije pariteta, sto garantuje trokljucni slucaj.
- IV: novi sinteticki bafer od 8 (DES/TDEA) ili 16 bajtova (AES) po paru.
  Isti IV je u odgovarajucoj enkripciji/dekripciji. Nema padding-a.
  Pozitivne velicine deljive sa 16 validne su za oba bloka.
- Svi algoritmi dele plaintext po velicini; kljuc je fiksan po algoritmu/velicini.
  Novi CBC objekti, key schedule, IV i generisanje podataka su van tajmera.
- Timed region: jedan Python poziv, native CBC, alokacija i vracanje izlaza,
  sa overhead-om tajmera/pristupa metodi. Prethodni izlazi sada se oslobadjaju
  van timed regiona. Ovo nije samo vreme kriptografske primitive.
- Warmup: isti tok, unapred fiksiran broj rundi, bez upisa u statistiku.
  Algoritmi se seedovano mesaju po rundi, velicine prate CLI redosled.
  Enkripcija prethodi dekripciji: ogranicenje redosleda/kesa, bez cold-cache tvrdnje.
- Round-trip ostaje van tajmera, uz obaveznu nezavisnu KAT prepreku pre warmup-a.
- MB/s = bytes / 1e6 / seconds = bytes * 1000 / nanoseconds.
  Mean throughput je prosek pojedinacnih throughput vrednosti, ne bytes/mean(time).
- statistics.stdev koristi n-1. Count/mean/median/stdev/min/max cuvaju se za
  vreme i throughput. SD nije interval poverenja. Raw ima nanosekunde, sekunde,
  MB/s, UUID sesije, repeat, order_index, algoritam, mod, operaciju i velicinu.
- Metadata: CPU/OS/RAM/jezgra, Python/executable, verzije biblioteka, pip freeze,
  seed/argv, Git commit i kratak Git status (prazan=clean), SHA-256 svih skripti.
  Run cuva i kopije cetiri relevantna izvora; commit sam ne opisuje dirty kod.
  Snapshot napajanja/opterecenja/RAM-a/afiniteta pre i posle nije kontinuiran nadzor.

## Validacija i backend

cpu_validation.py omogucava proveru bez benchmarka, preko istog common.cipher.
cpu_smoke_check.py izoluje eksperiment 1; postojeci smoke_check.py pokrece i druge
eksperimente i zato nije izvrsavan u ovoj sesiji.

| Algoritam | Autoritativni CBC izvor |
|---|---|
| DES | [FIPS 81, Table C1](https://nvlpubs.nist.gov/nistpubs/Legacy/FIPS/fipspub81.pdf) |
| TDEA, tri kljuca | [NIST CBC-TDES example, pp. 1-3](https://csrc.nist.gov/csrc/media/projects/cryptographic-standards-and-guidelines/documents/examples/tdes_cbc.pdf) |
| AES-128/192/256 | [SP 800-38A, F.2.1-F.2.6](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf) |

Proveravaju se svi blokovi: enkripcija objavljenog plaintext-a i dekripcija
objavljenog ciphertext-a, u novim instancama. JSON sadrzi sve ulaze, ocekivani
izlaz, izvore, PASS/FAIL i UTC pocetak/kraj. Pise se pre warmup-a; greska prekida
proces bez performance CSV-a. Uspeh se kopira kao validation.json u run i vezuje
SHA-256 hash-em. Exporter odbija CBC rezultate bez ove evidencije.
Negativni testovi kvare svaku od deset putanja i proveravaju da tajmer/izvoz nisu pozvani.

Predlog i default: software, use_aesni=False. To je kompajlirani _raw_aes,
ne Python AES. Validacija posmatra AES_start_operation za tri kljuca i obe
operacije; pristup AES-NI modulu izaziva gresku. Posmatrac se uklanja pre merenja.
Potvrdjen je bibliotecki dispatch, ne trag CPU instrukcija. Lokalna verzija je
PyCryptodome 3.23.0; promena privatnog API-ja zahteva novi review.
[API](https://www.pycryptodome.org/src/cipher/aes),
[izvor 3.23.0](https://github.com/Legrandin/pycryptodome/blob/v3.23.0/lib/Crypto/Cipher/AES.py).

Auto ostaje dijagnosticka opcija, nikad oznacena kao software; study+auto se
odbija. Nema poredjenja dve AES putanje. Poredimo konkretne implementacije na
danasnjem CPU-u. Iskljucivanje AES-NI ne izjednacava optimizovanost implementacija
i ne rekonstruise racunar iz 2003. DES/TDEA nisu preporuke za savremenu zastitu.

## Pilot: plan definisan pre merenja

Jedna sesija, seed 2003, software, 1 KiB/1 MiB/10 MiB, warmup 2, repeats 5.
Ocekivano: 150 raw i 30 summary redova. Izvoz samo kao dijagnostika, bez rada.
Analiza: trajanje, CV=sample SD/mean, min/max, RAM i napajanje/opterecenje.
Jedna sesija ne procenjuje varijabilnost izmedju sesija.

100 MiB nije automatski ukljuceno: moze pokazati streaming/memorijske efekte,
ali zahteva oko deset puta vise rada od najvece postojece tacke. Glavni zivi
baferi zauzimaju oko 3x ulaz; randbytes ima dodatne prolazne alokacije.
Za planiranje ostaviti 6x ulaz i rezervu za OS. 1 GiB nije potreban.
Trosak 100 MiB posle pilota samo proceniti, jasno odvojen od merenja.

## Kandidat za studiju, pre gledanja pilota

5 nezavisno pokrenutih Python procesa, 20 ponavljanja i 3 warmup runde po velicini.
Seedovi 2003-2007; algoritmi seedovano mesani, velicine rotirane izmedju sesija.
Finalne velicine i operativni uslovi zakljucuju se nakon pilota, pre studije.
Ne povecavati uzorak dok se ne dobije zeljeni odnos algoritama.

Cuvati sve raw vrednosti, statistike po sesiji i raspodelu medijana pet sesija.
100 unutarsesijskih ponavljanja nije 100 nezavisnih sesija. Nema post hoc
brisanja sporih uzoraka. Poznati prekid/promena napajanja: celu sesiju zadrzati
kao oznacenu nevalidnu za protokol i ponoviti celu, uz razlog.

AC napajanje, isti power plan, bez korisnickog rada, update-a i drugih poslova;
pre sesije nekoliko minuta mirovanja i isti kriterijum stabilizacije.
Zabeleziti turbo/power postavke, afinitet, hladjenje i pocetno opterecenje.
Temperatura/takt nisu trenutno nadzirani: ne tvrditi odsustvo throttling-a.
Sesije ne predstavljaju vise hardverskih platformi ili implementacija.
