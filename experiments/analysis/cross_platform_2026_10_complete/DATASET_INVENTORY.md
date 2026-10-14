# Dataset inventory

| platform | run_id | role | eligible | path |
|---|---|---|---|---|
| gtx1650ti | heterogeneous-core-v1-20261014T102836520134Z-1472bd2f13cf | primary | True | C:/Projects/aes/experiments/results_orchestrated/first-gpu-windows/6748c32fac83b2916aa48311/heterogeneous-core-v1-20261014T102836520134Z-1472bd2f13cf |
| t4 | heterogeneous-core-v1-20261014T105540691660Z-9bb918a84386 | primary | True | C:/Projects/aes/experiments/results_orchestrated/t4-colab/heterogeneous-core-v1-20261014T105540691660Z-9bb918a84386.tar.gz!/heterogeneous-core-v1-20261014T105540691660Z-9bb918a84386 |
| t600 | heterogeneous-core-v1-20261014T064407642462Z-636c48c0ebaf | primary | True | C:/Projects/aes/experiments/results_orchestrated/second-gpu/aa12d1868e30b6956f14d503/heterogeneous-core-v1-20261014T064407642462Z-636c48c0ebaf |

Selection hints locate candidates only; eligibility requires manifest, gate, source and raw-data verification. Exactly one primary per requested platform; failed candidates are excluded, never replaced silently by older runs.

## Discovered orchestrated runs

| run_id | purpose | gpu | seeds | state | claimed_completeness |
|---|---|---|---|---|---|
| aes-retrospective-v1-20261014T062540264291Z-27450d55936c | smoke | unavailable | [] | COMPLETED | complete |
| aes-retrospective-v1-20261013T192737729903Z-8fe4193f4071 | smoke | NVIDIA GeForce GTX 1650 Ti | [] | COMPLETED | unavailable |
| aes-retrospective-v1-20261014T102222216016Z-85ff440e10f5 | smoke | NVIDIA GeForce GTX 1650 Ti | [] | COMPLETED | complete |
| aes-retrospective-v1-20261013T192800232371Z-d51cef5fe69a | smoke | unavailable | [] | COMPLETED | unavailable |
| heterogeneous-core-v1-20261014T102544853713Z-077f10df37d7 | smoke | NVIDIA GeForce GTX 1650 Ti | [2003] | COMPLETED | complete |
| heterogeneous-core-v1-20261014T102643559984Z-6b5539ee5db2 | pilot | NVIDIA GeForce GTX 1650 Ti | [2003] | COMPLETED | complete |
| heterogeneous-core-v1-20261014T102320449214Z-6df07fd261db | smoke | NVIDIA GeForce GTX 1650 Ti | [2003] | COMPLETED | complete |
| heterogeneous-core-v1-20261014T102836520134Z-1472bd2f13cf | study | NVIDIA GeForce GTX 1650 Ti | [2003, 2004, 2005, 2006, 2007] | COMPLETED | complete |
| heterogeneous-core-v1-20261014T052148776495Z-77ee04798042 | smoke | NVIDIA GeForce GTX 1650 Ti | [2003] | COMPLETED | complete |
| aes-retrospective-v1-20261013T192011118209Z-60a2388c43cd | smoke | NVIDIA GeForce GTX 1650 Ti | [2003] | COMPLETED | unavailable |
| aes-retrospective-v1-20261013T192322603723Z-3ba4198a682a | smoke | NVIDIA GeForce GTX 1650 Ti | [2003] | COMPLETED | unavailable |
| aes-retrospective-v1-20261013T192901216221Z-43cf644c10de | smoke | NVIDIA GeForce GTX 1650 Ti | [2003] | COMPLETED | unavailable |
| aes-retrospective-v1-20261013T195426370169Z-2105030eedf3 | smoke | unavailable | [] | COMPLETED | complete |
| heterogeneous-core-v1-20261014T064407642462Z-636c48c0ebaf | study | NVIDIA T600 Laptop GPU | [2003, 2004, 2005, 2006, 2007] | COMPLETED | complete |
| heterogeneous-core-v1-20261014T062721460708Z-8f1dc933c951 | smoke | unavailable | [2003] | INCOMPLETE | partial |
| heterogeneous-core-v1-20261014T063706124553Z-f31c521ee472 | smoke | NVIDIA T600 Laptop GPU | [2003] | COMPLETED | complete |
| heterogeneous-core-v1-20261014T105540691660Z-9bb918a84386 | study | Tesla T4 | [2003, 2004, 2005, 2006, 2007] | COMPLETED | complete |

## Archived paired studies (optional historical comparison)

| run_id | seed | role |
|---|---|---|
| aes_cuda_cpu_gpu-study-20260930T205447700308Z | 2003 | historical only; not pooled |
| aes_cuda_cpu_gpu-study-20260930T205542542732Z | 2004 | historical only; not pooled |
| aes_cuda_cpu_gpu-study-20260930T205652619168Z | 2005 | historical only; not pooled |
| aes_cuda_cpu_gpu-study-20260930T205851562886Z | 2006 | historical only; not pooled |
| aes_cuda_cpu_gpu-study-20260930T205950403576Z | 2007 | historical only; not pooled |

Use `--historical-run LABEL=RUN_DIRECTORY` for an additional complete orchestrated comparison. These rows retain a historical role and are excluded from primary figures; archived native sessions are inventoried only, not silently assembled into a new suite.

All numeric rows are traceable by platform/run_id, seed(s), backend, mode, bytes and scope to `experiments/cuda_paired/seed-<seed>/native/raw.csv`. Full input hashes and selected paths are in `reproducibility_manifest.json`. Derived contrasts retain per-session values in `session_contrasts.csv`; no platforms are pooled.
