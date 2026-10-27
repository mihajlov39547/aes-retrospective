# Readiness report — 2026-10-27

**Ready for the Colab T4 smoke gate. No five-session campaign has been launched.** The local implementation has no known unresolved ciphertext-correctness failure. Colab hardware/software availability and performance remain unvalidated until that gate executes.

Implemented: sequential native EVP page batching and continuous control; one-launch page-aware CUDA using unchanged historical AES rounds; injective test nonces and overflow guards; four distinct timing boundaries; randomized paired scheduling; validation and source/provenance records; raw JSONL/CSV; session/campaign aggregation; Windows and Colab scripts; methodology/schema documentation.

## Completed validation

| Check | Result |
|---|---|
| Native Windows MSVC build | Passed; MSVC 19.51, x64 `/O2 /MD` |
| Windows OpenSSL identity | OpenSSL 3.6.5; imports resolved to `C:\OpenSSL-Win64\bin\libcrypto-3-x64.dll`, matching recorded hash |
| CPU capability | i5-10300H CPUID AES available and OpenSSL AES capability bit enabled; actual instructions not traced |
| New Windows tests | 14 passed |
| New Linux tests | 14 passed under Ubuntu WSL, GCC build with `-O3 -Wall -Wextra -Werror`, OpenSSL 3.0.13 |
| Existing CPU regression suite | 14 passed |
| Existing Colab regression suite | 12 run, one skipped, no failures |
| Local GTX 1650 Ti | CC 7.5; CuPy 13.6.0; CUDA runtime/NVRTC 12.9 |
| Local GPU correctness | All 25 vector, oracle, counter and workload cases passed |
| Final end-to-end smoke | 72 validated raw records: 24 warm-up + 48 measured; both layouts, all batch sizes and all three scheduled paths |
| Aggregation of final smoke | Passed complete-order/pair checks; 40 separately named boundary summaries |
| Colab setup shell syntax | Passed `bash -n`; installation and T4 execution pending |
| Historical files | Git status shows only the new Phase 2 experiment directory; no tracked historical or manuscript edits |

Native Windows build and GPU smoke ran through `windows.ps1`, not WSL. The separate WSL check validated Linux compilation/CPU correctness only. The smoke measurements are too small and use different hardware from the intended T4 campaign; no performance conclusion is drawn.

Local evidence is retained under `results/local-smoke-final/`: `metadata.json`, `validation.json`, `raw.jsonl`, `raw.csv`, `inputs.jsonl`, planned/actual execution order, source snapshots and `summary.json`. Earlier `local-smoke-v1/` and `local-smoke-v2/` are preserved. Builds and result directories are ignored by Git; copy them explicitly when archiving results.

## Next execution

Exact Windows, Colab setup, T4 smoke and later full-study commands are in [README.md](README.md). In Colab, upload/checkout the **complete updated repository** first, select T4, run setup and then the explicit smoke command. The later `--campaign` command reruns a smoke gate and starts five independent processes with a common runtime identity. It must be invoked separately; setup does not launch the campaign.

## Remaining methodological limits

CPU transform / prepared GPU pipeline is the primary prepared-workload comparison, including GPU payload transfers. CPU FFI/setup are excluded there; GPU host launch/event/synchronization costs are included. CPU operation / GPU prepared pipeline is asymmetric because GPU preparation and final conversion are excluded. Resident GPU results are compute-only. Allocation, host output copies and transfer diagnostics remain visible, but residuals do not identify a unique causal overhead. No symmetric full application envelope is claimed.

The saved historical Colab summaries were inspected; some imported metadata filenames are truncated, limiting a full historical provenance audit. New comparisons use only new same-runtime matched inputs. Parquet framing, authentication, metadata encryption and production nonce management remain explicitly out of scope. See [METHODOLOGY.md](METHODOLOGY.md) for the exact boundaries, statistics and limitations.
