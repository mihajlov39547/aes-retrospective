# Methodology and Results revision

| Section | Before | After | Reduction |
| --- | ---: | ---: | ---: |
| Methodology | 1,527 | 1,241 | 18.73% |
| Results | 1,758 | 1,021 | 41.92% |
| Combined | 3,285 | 2,262 | 31.14% |

Counts include headings, prose, captions, table notes, and table words and numerical
entries, including the separate files included by Results. Displayed equations,
LaTeX commands, comments, citation keys, reference identifiers, and layout arguments
are excluded. Words and numbers are counted as alphanumeric tokens, keeping internal
hyphens, apostrophes, periods, and slashes within a token. This source-based convention
counts the new tables rather than treating text moved into tables as deleted content.
The baseline is the manuscript at the start of this revision.

The combined reduction is slightly above the approximate 25--30% target. Methodology
received a smaller reduction to retain reproducibility details; Results received a
larger reduction because interpretation and repeated numerical descriptions were
already covered in Discussion or could be consolidated into tables.

## Editorial changes

- Removed all four Methodology and six Results subsection headings. Their labels
  remain as aliases of the corresponding section; existing references still resolve.
- Restricted Methodology to the evaluated implementations, validation, inputs,
  execution schedule, timing boundaries, data verification, and statistical methods.
- Preserved all six equations verbatim, including throughput estimation, hierarchical
  session aggregation, and paired acceleration. Preserved the platform table.
- Clarified input generation, counter construction, output verification, pairing
  digests, and record checks using the original archived harness. These details were
  checked in all fifteen session source copies. No implementation was changed.
- Removed persuasive descriptions, repeated explanations of GPU parallelism and
  transfer costs, and Results commentary about applications, causal mechanisms,
  generalizability, and deployment. The existing Discussion already covers these
  interpretations and limitations, so it was not expanded with duplicate paragraphs.
- Preserved the existing figure environment, caption, label, placement option, and
  image files. Retained all citation keys and cross-reference targets.

## Tables

- Updated the existing 32 MiB speedup overview without changing its numerical values
  or caption. Bold pipeline medians and directional counts identify gains in all
  five sessions. Mixed results, including T600 ECB, are not highlighted as consistent
  improvements. The table generator now preserves this formatting.
- Added a six-row table of resident and pipeline throughput for both modes and all
  three systems, consolidating the absolute-throughput findings.
- Added a five-row CTR pipeline table covering the complete input-size grid, with
  paired speedup medians and favorable-session counts for each system.

## Verification

The original experiment records in `experiments/results_orchestrated/` were read
without modification. The T4 records were read directly from the authoritative
archive without extracting or rewriting it. Original file hashes were checked;
9,000 selected observations from fifteen sessions were reconstructed into session
medians and paired speedups and compared with the saved audited aggregates.
The existing numerical claims agreed, including ranges, throughput, host mode
ratios, T600 CTR variability, and local throughput reductions. Added table values
and workload-size findings were obtained from this reconstruction.

The complete project was built with `build_sjee.ps1` (pdfLaTeX, BibTeX, and two
further pdfLaTeX passes). The final 21-page PDF has no LaTeX warnings, overfull or
underfull boxes, unresolved citations, undefined references, or duplicate labels.
The equations and original figure environment match the baseline exactly.
`git diff --check` passes. All changed files are inside `sjee/`.
