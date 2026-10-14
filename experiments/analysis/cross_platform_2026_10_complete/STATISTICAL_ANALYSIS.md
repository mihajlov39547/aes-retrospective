# Independent statistical analysis

3 eligible primary platforms, 15 sessions. Each retained native CSV contributes 1200 raw rows and 60 groups. Saved summaries (including all extended statistics) and all available aggregate exports are compared independently. Discrepancies: 0.

| platform | metric | groups | median_session_CV | max_session_CV |
|---|---|---|---|---|
| gtx1650ti | seconds_median | 20 | 0.0189117 | 0.0722179 |
| gtx1650ti | kernel_seconds_median | 40 | 0.0372497 | 0.0782804 |
| gtx1650ti | end_to_end_seconds_median | 20 | 0.0669377 | 0.282491 |
| t4 | seconds_median | 20 | 0.022659 | 0.0631982 |
| t4 | kernel_seconds_median | 40 | 0.0529662 | 0.175757 |
| t4 | end_to_end_seconds_median | 20 | 0.0246299 | 0.123485 |
| t600 | seconds_median | 20 | 0.18658 | 0.393254 |
| t600 | kernel_seconds_median | 40 | 0.141933 | 0.27069 |
| t600 | end_to_end_seconds_median | 20 | 0.209714 | 0.576565 |

CVs above are variation across five session medians, not raw repetition CVs. Both levels are exported separately. Small-input timings can have substantial quantization/dispatch overhead; zero Windows process-time diagnostics are not zero encryption time. Primary wall and CUDA event timers must remain positive. No flags trigger exclusion.

All numeric rows are traceable by platform/run_id, seed(s), backend, mode, bytes and scope to `experiments/cuda_paired/seed-<seed>/native/raw.csv`. Full input hashes and selected paths are in `reproducibility_manifest.json`. Derived contrasts retain per-session values in `session_contrasts.csv`; no platforms are pooled.

## Measurement diagnostics

| platform | seed | zero_process_time_rows | mixed_clock_component_exceeds_total_rows |
|---|---|---|---|
| gtx1650ti | 2003 | 240 | 0 |
| gtx1650ti | 2004 | 234 | 0 |
| gtx1650ti | 2005 | 241 | 0 |
| gtx1650ti | 2006 | 245 | 0 |
| gtx1650ti | 2007 | 237 | 0 |
| t4 | 2003 | 0 | 0 |
| t4 | 2004 | 0 | 0 |
| t4 | 2005 | 0 | 0 |
| t4 | 2006 | 0 | 0 |
| t4 | 2007 | 0 | 0 |
| t600 | 2003 | 250 | 0 |
| t600 | 2004 | 259 | 0 |
| t600 | 2005 | 257 | 0 |
| t600 | 2006 | 246 | 0 |
| t600 | 2007 | 257 | 0 |

Zero process-time readings diagnose clock granularity, not invalid primary wall times. A mixed host/device component sum is not an exact common-clock decomposition; any excess counts need separate instrumentation, not correction of observations. All repetition-level Tukey flags and extrema remain in session_level_statistics.csv.
