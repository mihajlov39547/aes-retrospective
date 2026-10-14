# Ranked follow-up experiments

| Rank | Experiment | Scientific value | Implementation cost |
|---|---|---|---|
| 0 | Verify archive extraction and retained input hashes (completed when all three studies pass) | Required before three-platform claims; zero new measurement | Very low; data handling only |
| 1 | Randomize/counterbalance size order; densely sample 1–32 MiB, especially 8–24 MiB; repeat independent sessions | Distinguishes a local 16 MiB feature from working-set/time-order effects | Low–medium; separately versioned protocol |
| 2 | Same-host CPU ECB/CTR controls: fixed library/build then version crossover, explicit backend, preallocated-output variant kept separate | Tests mode-path, output-allocation and library hypotheses without platform confounding | Medium; separate validated timing variants |
| 3 | Synchronized per-iteration GPU clocks, temperature/power, host CPU frequency/load and memory/page telemetry | Tests throttling/scheduling/allocation associations with anomaly | Medium; quantify instrumentation overhead |
| 4 | Pipeline decomposition with explicit host enqueue/wait boundaries and device transfer/kernel events; pinned/pageable controls | Separates transfer service, synchronization and launch costs; existing H2D/D2H host intervals are insufficient | Medium–high; maintain original scope as reference |
| 5 | Repeat across days and independent Colab allocations/hosts; more session replicates | Tests session/host generalizability, improves uncertainty estimates | Low code, high machine-time cost |
| 6 | Same hardware/software dual-boot comparison with controlled clocks and power | Only then addresses OS-specific effects | High operational cost |

No benchmarks are run by this analysis. Preserve all original results, include
new protocol/source identities, validate every path before timing, and avoid
post-hoc outlier removal. Additional experiments must be separately authorized.
