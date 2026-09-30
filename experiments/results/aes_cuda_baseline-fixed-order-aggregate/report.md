# CUDA baseline: final fixed-order aggregation

Accepted: pinned pipeline, fixed ascending 1 KiB / 16 KiB / 1 MiB / 16 MiB / 32 MiB.
All five sessions passed validation (18 tests), SHA-256 source/validation checks, raw-order checks,
200 raw / 10 summary row checks, and recomputation of seven summary medians from all raw rows.
Same source snapshots and GPU/runtime across the five sessions. Warmup 5; repeats 20.

## Accepted sessions

- Seed 2003: `aes_cuda_baseline-study-20260930T192042160435Z`
- Seed 2004: `aes_cuda_baseline-study-20260930T192923097888Z`
- Seed 2005: `aes_cuda_baseline-study-20260930T192947822337Z`
- Seed 2006: `aes_cuda_baseline-study-20260930T193012721398Z`
- Seed 2007: `aes_cuda_baseline-study-20260930T193037735239Z`

## Excluded from final table (preserved on disk)

- Seed 2004: `aes_cuda_baseline-study-20260930T192111373219Z`; Rotated size order excluded from final table by requested protocol.
- Seed 2005: `aes_cuda_baseline-study-20260930T192140369513Z`; Rotated size order excluded from final table by requested protocol.
- Seed 2006: `aes_cuda_baseline-study-20260930T192211525875Z`; Rotated size order excluded from final table by requested protocol.
- Seed 2007: `aes_cuda_baseline-study-20260930T192238736383Z`; Rotated size order excluded from final table by requested protocol.

## Aggregation and scope

Each of the 10 output rows is the median of five session medians for each of seven metrics.
No raw rows or outliers were removed. Values are stored without presentation rounding.
32 MiB remains in the standard table. 64/100 MiB remain diagnostic/limitations only.
Diagnostic and rotated sessions must not be merged into this final table.
Fixed size order may confound size with progression/thermal state; no new stability claim is made.
The legacy metadata study_protocol string remains untouched; selection uses the actual arguments.
No experiments, kernel edits, LaTeX changes, commits or pushes were performed.

Reproduce offline: `.\.venv\Scripts\python.exe experiments/results/aes_cuda_baseline-fixed-order-aggregate/aggregate.py`
