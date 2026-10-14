# Archive recovery and extraction audit

Archive inputs were extracted into isolated temporary directories using Python tarfile/zipfile. Each extracted regular file was checked byte-for-byte by SHA-256 against the decompressed member stream. Original archives and prior imported directories were not overwritten.

Numerical estimator discrepancies are reported separately: **0**. A malformed prior extraction is an import failure, not evidence that the original measurements failed.

## t4

Archive: `C:/Projects/aes/experiments/results_orchestrated/t4-colab/heterogeneous-core-v1-20261014T105540691660Z-9bb918a84386.tar.gz`

SHA-256: `1104a0dd49cc13949e993bb2ef70204a390ee393d3e9777d47297937a65f4c6b`

| format | regular_files | raw_csv_files | source_snapshots | pax_path_records | maximum_member_path_characters |
|---|---|---|---|---|---|
| tar | 135 | 5 | 55 | 130 | 213 |


Prior import: `C:/Projects/aes/experiments/results_orchestrated/t4-colab/heterogeneous-core-v1-20261014T105540691660Z-9bb918a84386`. It contains 36 files; 31 surviving paths match exactly the first 100 characters of longer archive paths, with matching content hashes.

The 100-character boundary matches the legacy tar name field. The archive supplies full names via PAX path records. This pattern strongly supports an earlier extractor ignoring long-path metadata, with colliding truncated names overwriting siblings. It does not identify the extraction application. It is distinct from the ordinary Windows MAX_PATH boundary; shortening the destination alone would not fix ignored PAX names.

The analysis reads full member names through the archive library, rejects traversal/links/duplicate paths, and never uses a hand-parsed 100-byte name field. `--scratch-root` supports a short temporary parent when Windows path handling requires it. Full member names, sizes, hashes and prior-import matches are in `archive_extraction_receipts.json`. The damaged import remains preserved as evidence; the authoritative analysis input is the intact archive.
