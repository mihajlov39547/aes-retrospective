# Final paired CPU/GPU aggregate

Metric aggregation: median of five session medians; times in ms, throughput decimal MB/s.
Speedup: median of five within-session CPU median time / GPU median time ratios. Not ratio of aggregate throughputs.
All raw observations retained; no outlier filtering or pooling.
Resident N=1 is separate from pipeline kernel component; latter is not used as resident data.
CPU output allocation included; GPU host/device buffers preallocated. Setup excluded on both paths.
ttable occurs in validation/source metadata only, never in timed final rows.
Separate paired study: completed standalone CUDA baseline table is not overwritten or pooled.
Single CPU/GPU platform, Windows/WDDM, dynamic clocks and fixed size order limit generalization. No causal diagnosis.

## Accepted sessions

- 2003: aes_cuda_cpu_gpu-study-20260930T205447700308Z (1200 raw, 60 summary, validation PASS)
- 2004: aes_cuda_cpu_gpu-study-20260930T205542542732Z (1200 raw, 60 summary, validation PASS)
- 2005: aes_cuda_cpu_gpu-study-20260930T205652619168Z (1200 raw, 60 summary, validation PASS)
- 2006: aes_cuda_cpu_gpu-study-20260930T205851562886Z (1200 raw, 60 summary, validation PASS)
- 2007: aes_cuda_cpu_gpu-study-20260930T205950403576Z (1200 raw, 60 summary, validation PASS)

## Excluded pilots

- aes_cuda_cpu_gpu-pilot-20260930T202051083522Z: Pilot only
- aes_cuda_cpu_gpu-pilot-20260930T203448131002Z: Pilot only; ttable not selected for final study

All summary medians and session speedups were checked against raw rows / median times.
Pair hashes agree across six jobs per pair; source snapshots and GPU/runtime match across sessions.
No experiments, benchmark/kernel edits or modifications to source results.
