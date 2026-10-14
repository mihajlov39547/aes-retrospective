# Python skripte

The central cross-platform CLI is `run_all_experiments.py`; see the
[orchestration guide](../experiments/ORCHESTRATION.md) for the audited registry,
JSON configurations, platform manifests, validation, resume and aggregation.
Study aggregation requires all configured seeds and required metrics. Verification
reports scientific completeness separately from technical success, including CUDA
skips. The `heterogeneous-core-{smoke,pilot}.json` and `heterogeneous-core.json`
configurations provide a paired-only GPU workflow. Benchmarks need PyCryptodome
and psutil (CUDA also NumPy/CuPy); matplotlib is only required for plotting.
Start with `python scripts/run_all_experiments.py list` or
`python scripts/run_all_experiments.py run --config experiments/configs/cpu-smoke.json`.

Eksperiment 2: [protokol AES software/AES-NI](../experiments/aes_acceleration_protocol.md).
Izolovana provera je `python scripts/aes_acceleration_smoke_check.py` (samo AES CBC,
1 KiB smoke). Obe putanje prolaze NIST KAT i dispatch pre wall/process tajmera;
izvoz zahteva sacuvanu validaciju. Protokol sadrzi komandu za kasniji rucni pilot.

The registry lists seven active experiments, the disabled GPU scaffold and the
optional exporter. Native legacy outputs default to `experiments/results/`;
orchestrated runs use `experiments/results_orchestrated/`.
The `publication_quality` compatibility field means dataset completeness and
integrity only, not statistical or scientific publication readiness.

## Šta radi svaki fajl

| Fajl | Namena i trenutno stanje |
|---|---|
| `common.py` | Zajednički modul, nije samostalni eksperiment. Definiše CLI opcije, adaptere za DES/TDEA/AES, sintetičke ključeve, statistiku i CSV/JSON izvoz. Beleži seed, okruženje, verzije biblioteka, Git stanje i SHA-256 svih Python skripti u ovom direktorijumu. |
| `benchmark.py` | Izvršiv CPU benchmark DES-a, troključnog TDEA i AES-128/192/256 u CBC modu. Meri enkripciju i dekripciju, proverava povratnu dekripciju, odbacuje warmup i izvozi vremena i MB/s sa sredinom, medijanom i standardnom devijacijom. Podrazumevani ulazi: 1 KiB, 1 MiB i 10 MiB. |
| `aes_acceleration.py` | Izvršivo upareno poređenje softverske native AES implementacije i x86 AES-NI putanje PyCryptodome-a u CBC modu za sva tri ključa. Pre merenja proverava podršku i izbor native putanje, zatim računa vremena, throughput i odnos medijana. Softverska putanja nije AES pisan u Python-u; ARM backend nije implementiran. |
| `aes_gpu.py` | Inactive legacy scaffold. Its `aes_gpu_kernel.cu` intentionally cannot compile; excluded from executable suites. |
| `avalanche_test.py` | Izvršiva demonstracija difuzije na jednom ECB bloku za DES, TDEA i AES. Odvojeno menja jedan bit poruke i jedan efektivni bit ključa i meri Hamming rastojanje. Izuzima DES paritetne bitove. Nije dokaz sigurnosti niti potpuni strict avalanche criterion test. |
| `brute_force_demo.py` | Izvršiva edukativna pretraga redukovanog AES-128 prostora sa 1–20 promenljivih bitova (podrazumevano 12). Meri pokušaje/s i ilustrativno ekstrapolira pune i očekivane pretrage prostora od 2^56 do 2^256. Ne pokušava puni DES/AES brute-force i ne daje realne procene napada na TDEA. |
| `export_results.py` | Plot exporter for CBC, AES-NI and the old scaffold schema; does not support operational paired CUDA/GCM/avalanche/keyspace schemas. Export into a separate copy. |
| `smoke_check.py` | Legacy omnibus check with obsolete avalanche/keyspace assumptions. Use the seven dedicated checks below. |
| `aes_gcm_benchmark.py` | Operational CPU AES-GCM benchmark with tamper rejection validation. |
| `aes_cuda_baseline.py` | Operational standalone CUDA AES-128; CPU reference validates correctness, not paired CPU performance. |
| `aes_cuda_cpu_gpu.py` | Operational paired CPU software/AES-NI/CUDA baseline/v1 ECB/CTR measurements; resident and prepared-buffer pipeline scopes are separate. T-table is optional and absent from final archived timings. |
| `run_all_experiments.py` | Central sequential runner with preflight, validation, isolated artifacts, safe resume and suite aggregation. |


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

Active benchmark scripts without `--run` display plans without measurements:

```powershell
python scripts/benchmark.py
python scripts/aes_acceleration.py
python scripts/aes_gcm_benchmark.py
python scripts/aes_cuda_baseline.py
python scripts/aes_cuda_cpu_gpu.py
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

CUDA discovery and paired smoke planning:

```powershell
python scripts/run_all_experiments.py doctor --config experiments/configs/heterogeneous-core-smoke.json
python scripts/run_all_experiments.py plan --config experiments/configs/heterogeneous-core-smoke.json
```

Seven dedicated legacy smoke checks (small workloads; CUDA checks need a working GPU):

```powershell
python scripts/cpu_smoke_check.py
python scripts/aes_acceleration_smoke_check.py
python scripts/aes_gcm_smoke_check.py
python scripts/aes_cuda_baseline_smoke_check.py
python scripts/aes_cuda_cpu_gpu_smoke_check.py
python scripts/avalanche_smoke_check.py
python scripts/brute_force_demo_smoke_check.py
```

These generate technical artifacts, not study results. Operational CUDA benchmarks
validate kernels before measurements. Device discovery alone is insufficient.
The inactive scaffold remains intentionally blocked.

## Putanje i ograničenja

- Podrazumevani izlaz ostaje `experiments/results/<eksperiment>-<purpose>-<UTC>/`.
- `--output` menja osnovni direktorijum rezultata; relativna putanja se tumači prema radnom direktorijumu.
- Operational kernels: `experiments/aes_cuda_baseline.cu`, `aes_cuda_optimized.cu`, `aes_cuda_ttable.cu`. The inactive scaffold uses `aes_gpu_kernel.cu`.
- Existing results must remain unchanged. Export plots into a separate copy of the native result directory.
- DES/TDEA i deterministički ključevi služe isključivo kontrolisanom istorijskom i edukativnom poređenju, ne produkcionoj zaštiti.
- CBC CPU rezultate ne mešati sa ECB/CTR GPU rezultatima. CUDA kod nije produkciona kriptografska biblioteka.

## Eksperiment 1: aktuelni protokol

CBC validaciona prepreka je u `cpu_validation.py`, a izolovane provere su
u `cpu_smoke_check.py`: `python scripts/cpu_smoke_check.py`. One ne pokrecu
ostale eksperimente. Benchmark sada podrazumeva `software`, cuva min/max,
session ID i pre-measurement validaciju; study+auto se odbija. Detalji su u
[CPU CBC protokolu](../experiments/cpu_cbc_protocol.md).
