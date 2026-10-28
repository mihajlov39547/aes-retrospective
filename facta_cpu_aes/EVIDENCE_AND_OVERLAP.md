# Evidence mapping and distinction from submitted SJEE article

## Primary source mapping

| Manuscript statement | Underlying evidence | Status |
|---|---|---|
| Oracle Arm64, 32 MiB CTR default OpenSSL ~4.03 GB/s | `evidence/oracle_single_session_summaries.csv`, `openssl_default`, CTR, 33554432 bytes, transform boundary; original `oracle-phase1-single-study.tar.gz` | Measured |
| Oracle Arm64, 32 MiB CTR PyCryptodome ~209 MB/s | Same file, `pycryptodome` | Measured |
| Oracle Arm64, 32 MiB CTR armcap=0 ~218 MB/s | Same file, `openssl_armcap0` | Measured; broad masking, not AES-only |
| Windows i5, 32 MiB CTR EVP ~5.54 GB/s native transform | `evidence/windows_phase1_session_summaries.csv`, `openssl_default`, CTR, 33554432 bytes, `transform`; original `windows-phase1-single-study.zip` | Measured |
| Windows i5, 32 MiB CTR EVP ~1.48 GB/s operation envelope | Same file, `operation_envelope` | Measured |
| Windows i5, 32 MiB PyCryptodome 2.88 / 1.20 GB/s | Same file, two boundaries | Measured |
| Oracle operation-envelope and two-worker results | Not included in the revised manuscript; the copied single-worker CSV supplies transform summaries only | Original draft values require a separate audit before reuse |
| CBC AES-128/192/256 software vs AES-NI | `evidence/09_eksperimentalna_analiza.tex`, section `Uticaj AES-NI` | Historical separate campaign |
| Windows AES-128/256 GCM rates, validation and AAD policy | Same, section `AES-GCM autentifikovana enkripcija`; also `mihajlovic2026validiran(1).pdf` | Historical separate campaign |
| DES/TDEA contextual comparisons | Removed from the revised manuscript to keep the focus on AES implementation and timing scope | Original evidence retained |

## Scope partition

**Submitted SJEE**: GPU-resident CTR, independent data pages, CPU/GPU comparison, H2D/D2H transfers, GPU pipeline. **Proposed Facta**: CPU-only implementation-path sensitivity, Windows/Oracle CPU native vs Python wrappers, CBC key length and GCM authentication behavior. Avoid presenting the same exact numerical analysis as a new contribution in both papers. If CPU baseline measurements are substantively reported in SJEE, cite or disclose the relationship, and have the second journal assess independent novelty.

This manuscript explicitly does NOT claim native AES instruction causation, a universal CPU architecture speed ranking, complete operation-envelope symmetry, or a new AES implementation. Independent novelty from reinterpreting the existing datasets is inherently more modest than from conducting a new experimental study. Reviewer acceptance is uncertain.

The editorial revision adds ranges of the five session medians for the 32 MiB CTR results, calculated directly from the copied CSVs. These are descriptive ranges, not confidence intervals. The instrumented operation includes benchmark diagnostics; it is not production application latency. See `REVISION_REPORT.md`.
