# Manuscript revision

The paper was edited from the abstract through the conclusion, using SJEE as a structural reference while retaining the CPU-only research question.

## Structure and language

- Abstract: research context, study design, principal findings and practical relevance (141 words).
- Introduction: motivation, explicit research question, three contributions and section roadmap.
- Related work: AES implementation research, benchmarking methodology and the specific empirical question addressed here.
- Methodology: platforms, payload sizes, correctness checks, timing inclusions and aggregation.
- Results: interpretation immediately accompanies each library, timing-scope, CBC and GCM finding.
- General discussion: implications, limitations, generalization, applications, analogies and future experiments.
- Conclusion: concise answer to the research question and next steps.

Repeated disclaimers, references to unrelated GPU experiments and peripheral DES/TDEA comparisons were removed from the prose. Publication-overlap notes remain in EVIDENCE_AND_OVERLAP.md.

## Technical clarifications

The operation interval is now described as an instrumented benchmark call, including diagnostics, rather than production application latency. The native and Python transform intervals remain explicitly distinguished. The speedup equation now labels the direction of comparison unambiguously. GCM setup exclusions and authentication work are stated explicitly.

The main 32 MiB CTR medians were checked against evidence/windows_phase1_session_summaries.csv and evidence/oracle_single_session_summaries.csv. Added session ranges are minima and maxima of the five session medians. No new performance experiments were run. CBC/GCM figures retain the values in the copied Chapter 9 evidence.

The earlier Oracle operation-envelope value (approximately 1.06 GB/s) and two-worker observation (approximately 2.03 GB/s) were omitted: the original evidence map marked them as requiring an audit, and the copied single-worker summaries do not supply the broader operation interval. This revision does not replace those missing values with estimates.

## Literature

Added and checked against primary research records:

- K?sper and Schwabe, *Faster and timing-attack resistant AES-GCM*, ePrint 2009/129: https://research.tue.nl/en/publications/faster-and-timing-attack-resistant-aes-gcm-2/
- Mytkowicz et al., *Producing Wrong Data Without Doing Anything Obviously Wrong!*, ASPLOS 2009: https://sape.inf.usi.ch/publications/asplos09.html
- Kalibera and Jones, *Rigorous Benchmarking in Reasonable Time*, ISMM 2013: https://kar.kent.ac.uk/33611/

The bibliography now contains nine cited entries in first-citation order. Unused DES/TDEA references were removed.

## Validation

Both formats were rebuilt with build_facta.ps1 -Target All. The PDF uses the existing SJEE settings and contains 13 pages including references; the font and page geometry were not reduced. All PDF pages were visually reviewed. DOCX structural/template validation covers three tables, three vector figures, two display equations and nine references, with no reported warnings. Word pagination has not been visually verified and can differ from the LaTeX PDF.

Build logs and PDF review images are in build/editorial/. The pre-edit content snapshot is in build/editorial/before/.
