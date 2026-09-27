# Rezultati

CPU/GPU proširenje još nema rezultate. Posle implementacije i validacije
izlazi će biti u zasebnom `aes_cpu_gpu-<purpose>-<UTC>/` direktorijumu:
`aes_cpu_gpu_raw.csv`, `aes_cpu_gpu_summary.csv`, `aes_cpu_gpu_environment.json`
i standardni run fajlovi. Izvoz kreira odvojene `ECB/` i `CTR/` grafikone.
Preskočene veličine i razlozi čuvaju se uz metodologiju; nisu nulti rezultati.

U inicijalnom projektu nema rezultata za rad. Skripte pri eksplicitnom `--run` kreiraju zaseban direktorijum sa CSV/JSON datotekama, metapodacima i zaključanim verzijama okruženja. `pilot` i `smoke` nisu rezultati za članak. Identifikator direktorijuma povezuje podatke, tabelu i grafikon. Nijedan rezultat se automatski ne uključuje u LaTeX.
