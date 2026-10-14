"""Traceable reports and deterministic publication-style offline figures."""
from collections import defaultdict
from pathlib import Path
from .core import SIZES,SEEDS,ACTIVE_SOURCES,stats,csvwrite,read,sha


def fmt(value):
    if value is None:return 'unavailable'
    if isinstance(value,float):return f'{value:.6g}'
    return str(value).replace('|','/').replace('\n','; ')


def table(rows,columns):
    return '\n'.join(['| '+' | '.join(columns)+' |','|'+'|'.join(['---']*len(columns))+'|']+
                     ['| '+' | '.join(fmt(row.get(k)) for k in columns)+' |' for row in rows])+'\n'


def import_report(out,receipts,discrepancy_count):
    lines=['# Archive recovery and extraction audit',
           'Archive inputs were extracted into isolated temporary directories using Python tarfile/zipfile. Each extracted regular file was checked byte-for-byte by SHA-256 against the decompressed member stream. Original archives and prior imported directories were not overwritten.',
           f'Numerical estimator discrepancies are reported separately: **{discrepancy_count}**. A malformed prior extraction is an import failure, not evidence that the original measurements failed.']
    for label,r in receipts.items():
        prior=r.get('prior_import',{})
        lines.extend([f'## {label}',f"Archive: `{r['archive']['path']}`\n\nSHA-256: `{r['archive']['sha256']}`",
                      table([r],['format','regular_files','raw_csv_files','source_snapshots','pax_path_records','maximum_member_path_characters'])])
        if prior:
            lines.append(f"Prior import: `{prior['path']}`. It contains {prior['files']} files; {prior['truncated_100_character_matches']} surviving paths match exactly the first 100 characters of longer archive paths, with matching content hashes.")
            if prior['truncated_100_character_matches']:
                lines.append('The 100-character boundary matches the legacy tar name field. The archive supplies full names via PAX path records. This pattern strongly supports an earlier extractor ignoring long-path metadata, with colliding truncated names overwriting siblings. It does not identify the extraction application. It is distinct from the ordinary Windows MAX_PATH boundary; shortening the destination alone would not fix ignored PAX names.')
        lines.append('The analysis reads full member names through the archive library, rejects traversal/links/duplicate paths, and never uses a hand-parsed 100-byte name field. `--scratch-root` supports a short temporary parent when Windows path handling requires it. Full member names, sizes, hashes and prior-import matches are in `archive_extraction_receipts.json`. The damaged import remains preserved as evidence; the authoritative analysis input is the intact archive.')
    (out/'IMPORT_RECOVERY.md').write_text('\n\n'.join(lines)+'\n',encoding='utf-8')


def reports(out,studies,discovered,checks,discrepancies,aggregates,contrasts):
    primary=[s for s in studies if s['eligible'] and s['role']=='primary']
    labels={s['platform']:s for s in studies};valid={s['platform'] for s in primary}
    agg=[r for r in aggregates if r['role']=='primary']
    comparisons=[r for r in contrasts if r['platform'] in valid]
    from .cross_platform import derived
    session_contrasts=[r for s in primary for r in derived(s)]
    def write(name,text):
        (out/name).write_text(text.strip()+'\n',encoding='utf-8')
    trace='All numeric rows are traceable by platform/run_id, seed(s), backend, mode, bytes and scope to `experiments/cuda_paired/seed-<seed>/native/raw.csv`. Full input hashes and selected paths are in `reproducibility_manifest.json`. Derived contrasts retain per-session values in `session_contrasts.csv`; no platforms are pooled.'
    selection=[dict(platform=s['platform'],run_id=s['run_id'],role=s['role'],eligible=s['eligible'],path=s['display_path']) for s in studies]
    archived=[]
    root=Path(__file__).resolve().parents[2]/'experiments/results'
    for p in sorted(root.glob('aes_cuda_cpu_gpu-study-*/metadata.json')):
        m=read(p);archived.append(dict(run_id=p.parent.name,seed=m['seed'],role='historical only; not pooled'))
    write('DATASET_INVENTORY.md','# Dataset inventory\n\n'+table(selection,['platform','run_id','role','eligible','path'])+
          '\nSelection hints locate candidates only; eligibility requires manifest, gate, source and raw-data verification. Exactly one primary per requested platform; failed candidates are excluded, never replaced silently by older runs.\n\n## Discovered orchestrated runs\n\n'+table(discovered,['run_id','purpose','gpu','seeds','state','claimed_completeness'])+
          '\n## Archived paired studies (optional historical comparison)\n\n'+table(archived,['run_id','seed','role'])+
          '\nUse `--historical-run LABEL=RUN_DIRECTORY` for an additional complete orchestrated comparison. These rows retain a historical role and are excluded from primary figures; archived native sessions are inventoried only, not silently assembled into a new suite.\n\n'+trace)
    write('INTEGRITY_AUDIT.md','# Scientific integrity audit\n\n'+table(checks,['platform','seed','status','check','detail'])+
          '\nPASS means the named check passed, WARN identifies interpretation limits, FAIL excludes that study from validated numerical comparisons. A saved COMPLETED status is not proof of intact imported files.\n\n'+
          f'Independent estimator discrepancies: {len(discrepancies)}. Structural failures are in this table, not hidden by an empty discrepancy CSV. Numerical tolerance: relative 1e-10, absolute 1e-15; booleans, identities, counts and seed sets are exact.\n\n'+trace)
    platform_rows=[]
    for s in studies:
        e=s['environment'];g=e.get('gpus',[{}])[0];c=e.get('cuda',{})
        platform_rows.append(dict(platform=s['platform'],eligible=s['eligible'],run_id=s['run_id'],
              user_label={'gtx1650ti':'Windows 10','t600':'Windows 11','t4':'Google Colab/Linux'}.get(s['platform'],'user-specified'),
              captured_os=e.get('os'),captured_release=e.get('release'),captured_kernel=e.get('kernel'),
              cpu=e.get('cpu'),physical_cpus=e.get('physical_cpus'),logical_cpus=e.get('logical_cpus'),
              gpu=c.get('name'),driver=g.get('driver_version'),driver_model=g.get('driver_model.current'),
              cuda_driver=c.get('driver_version'),cuda_runtime=c.get('runtime_version'),cupy=c.get('cupy_version'),
              pycryptodome=e.get('packages',{}).get('pycryptodome'),python=e.get('python_version'),git=e.get('git',{}).get('commit')))
    csvwrite(out/'platform_environment.csv',platform_rows)
    source_rows=[]
    for s in studies:
        for name in ACTIVE_SOURCES:
            key=('experiments/' if name.endswith('.cu') else 'scripts/')+name
            source_rows.append(dict(platform=s['platform'],run_id=s['run_id'],source=name,
                manifest_declared_sha256=s['manifest']['sources'].get(key),
                independently_verified_sha256=s['sources'].get(name),
                verified_all_five_sessions=s['eligible']))
    csvwrite(out/'source_comparison.csv',source_rows)
    primary_metrics={'seconds_median','throughput_MB_s_median','kernel_seconds_median','kernel_throughput_MB_s_median','end_to_end_seconds_median','end_to_end_throughput_MB_s_median','speedup_isolated_vs_cpu_aesni','speedup_pipeline_vs_cpu_aesni'}
    csvwrite(out/'platform_comparison.csv',[r for r in agg if r['metric'] in primary_metrics],fields=None if agg else ['platform','metric'])
    write('METHODOLOGY_AND_LIMITATIONS.md', '''# Methodology and limitations

The analysis reads raw CSVs directly and never imports benchmark implementations.
The existing read-only verifier supplies a separate integrity gate, not the estimates.
Five sessions (seeds 2003–2007) each contain 1200 rows: five sizes × two modes × six
backend/scope jobs × twenty repetitions. Each session has sixty summary groups.
Five warmups are recorded in configuration and source; warmup observations are not
exported, so their actual execution is supported by provenance rather than raw rows.
AES-NI evidence observes explicit native initialization, not an instruction trace.
All three CUDA candidates pass persisted cryptographic tests; baseline/v1 alone
contribute timed rows. Successful kernel execution in those tests establishes a
working compiled kernel path, not an independent compiler diagnostic log.

Latency, throughput and diagnostic fields are independently summarized with count,
mean, median, sample SD (n−1), inclusive Q1/Q3 at (n−1)p, IQR, extrema, CV=SD/mean
and descriptive Tukey flags. Zero diagnostic means have undefined CV. No outliers
are removed. Throughput is decimal payload MB/s; workload labels use binary MiB.
Median throughput is the median of individual byte/time rates, not the reciprocal
of median time (these differ for even n). Across sessions, use the median of five
session medians. Speedup is the median of five within-session ratios of CPU median
transform time to GPU median resident-kernel or pipeline time. No raw pooling.
The twenty repetitions are nested observations, not 100 independent sessions.
No significance tests or bootstrap intervals are claimed; n=5 describes only these
sessions, not independent machines, cloud allocations or population performance.
Same-seed size/mode contrasts remain within their own platform and session.

CPU encrypt output allocation is inside its wall timer; construction/key schedule
are outside. GPU buffers are preallocated and pinned; compilation, allocation,
pinning, staging, key expansion/upload and reference checks are excluded. Resident
N=1 uses CUDA events around a single launch with transfers outside. Pipeline uses
host wall time from H2D through completed D2H, including launch/synchronization.
The pipeline kernel event component is not a substitute for resident timing.
H2D/D2H are independently recorded host intervals around synchronous copies and
their synchronization. They are not pure PCIe wire time. Event ns conversions do
not imply nanosecond resolution.

Pipeline/resident throughput ratios use within-session throughput medians. Latency
ratios use their respective time medians. Additional pipeline time is their
difference, labeled approximate residual overhead: it mixes timing scopes,
synchronization and execution variability. It is not a measurement of transfer
time. Host component times and GPU event time do not form an exact additive clock
decomposition, and medians of components do not add to a median total.

Size order is fixed ascending; modes/jobs are seeded-shuffled. Therefore allocation,
cache, thermal, clock and elapsed-time effects are confounded with size. Telemetry
before/after whole sessions cannot attribute behavior at 16 MiB. Library versions,
CPU/GPU architectures, clocks, memory, driver models and runtimes differ. This is
not an isolated Windows 10/11 comparison, nor a claim about all laptop/server GPUs.
Windows edition and Colab identity are user labels; captured OS/release/kernel are
reported separately without inferring marketing edition from NT version.

Hashes establish internal consistency, not authenticity against coordinated edits.
Matching application source does not establish identical compiler output or native
library binaries. A recorded dirty tree is disclosed and active archived source
bytes are checked. Analysis needs Python 3.10+ and matplotlib only for figures;
no CUDA runtime, GPU or cloud credentials are needed.

'''+table(platform_rows,['platform','captured_os','captured_release','captured_kernel','cpu','logical_cpus','gpu','driver','cuda_runtime','cupy','pycryptodome','git'])+'\n'+trace)
    variation=[]
    for s in primary:
        for metric in ('seconds_median','kernel_seconds_median','end_to_end_seconds_median'):
            rows=[r for r in agg if r['platform']==s['platform'] and r['metric']==metric]
            if rows:variation.append(dict(platform=s['platform'],metric=metric,groups=len(rows),median_session_CV=stats([r['session_coefficient_of_variation'] for r in rows])['median'],max_session_CV=max(r['session_coefficient_of_variation'] for r in rows)))
    write('STATISTICAL_ANALYSIS.md','# Independent statistical analysis\n\n'+
          f'{len(primary)} eligible primary platforms, {len(primary)*5} sessions. Each retained native CSV contributes 1200 raw rows and 60 groups. Saved summaries (including all extended statistics) and all available aggregate exports are compared independently. Discrepancies: {len(discrepancies)}.\n\n'+
          table(variation,['platform','metric','groups','median_session_CV','max_session_CV'])+
          '\nCVs above are variation across five session medians, not raw repetition CVs. Both levels are exported separately. Small-input timings can have substantial quantization/dispatch overhead; zero Windows process-time diagnostics are not zero encryption time. Primary wall and CUDA event timers must remain positive. No flags trigger exclusion.\n\n'+trace)
    diagnostic=[dict(platform=s['platform'],seed=m['seed'],zero_process_time_rows=m['zero_process_time_rows'],mixed_clock_component_exceeds_total_rows=m['mixed_clock_component_exceeds_total_rows']) for s in primary for m in s['metadata']]
    with (out/'STATISTICAL_ANALYSIS.md').open('a',encoding='utf-8') as stream:
        stream.write('\n## Measurement diagnostics\n\n'+table(diagnostic,['platform','seed','zero_process_time_rows','mixed_clock_component_exceeds_total_rows'])+
                     '\nZero process-time readings diagnose clock granularity, not invalid primary wall times. A mixed host/device component sum is not an exact common-clock decomposition; any excess counts need separate instrumentation, not correction of observations. All repetition-level Tukey flags and extrema remain in session_level_statistics.csv.\n')
    anomaly=[]
    for r in comparisons:
        if r['metric'].startswith('throughput_16MiB_over_'):
            anomaly.append(dict(platform=r['platform'],backend=r['backend'],scope=r['measurement'],mode=r['mode'],reference='1 MiB' if r['metric'].endswith('1048576B') else '32 MiB',ratio=r['median'],min=r['min'],max=r['max'],IQR=r['iqr'],CV=r['coefficient_of_variation'],sessions_lower=r['below_one']))
    local_dips=[];dip_groups=defaultdict(dict)
    for r in session_contrasts:
        if r['metric'].startswith('throughput_16MiB_over_'):
            key=(r['platform'],r['backend'],r['measurement'],r['mode'])
            dip_groups[key].setdefault(r['seed'],{})[r['metric']]=r['value']
    for key,byseed in sorted(dip_groups.items()):
        dips=[seed for seed,values in byseed.items() if len(values)==2 and all(v<1 for v in values.values())]
        local_dips.append(dict(zip(['platform','backend','scope','mode'],key),sessions_local_dip=len(dips),seeds=dips))
    csvwrite(out/'anomaly_local_dips.csv',local_dips,fields=None if local_dips else ['platform','backend','scope','mode','sessions_local_dip','seeds'])
    anomaly_findings=[]
    for p in sorted(valid):
        gpu=[r for r in local_dips if r['platform']==p and r['backend'].startswith('cuda_')]
        if gpu:
            anomaly_findings.append(f"{p}: {sum(r['sessions_local_dip']==5 for r in gpu)}/{len(gpu)} GPU backend/scope/mode groups show a local 16 MiB dip in every session. Direction counts range from {min(r['sessions_local_dip'] for r in gpu)} to {max(r['sessions_local_dip'] for r in gpu)} of five; this is observed repeatability, not a causal or significance claim.")
    write('ANOMALY_16MIB.md','# The 16 MiB feature\n\n'+
          '\n\n'.join(anomaly_findings)+'\n\n'+
          'For each session, divide median throughput at 16 MiB by that at 1 MiB or 32 MiB for the same backend/mode/scope. Below one means lower throughput at 16 MiB. A local dip requires both contrasts below one in the same session; the individual counts below must not be interpreted as a joint test. Full session contrasts permit that check.\n\n'+
          table(anomaly,['platform','backend','scope','mode','reference','ratio','min','max','IQR','CV','sessions_lower'])+
          '\n## Joint local-dip check\n\nA session qualifies only if 16 MiB throughput is lower than both 1 MiB and 32 MiB. Even tiny differences count directionally; these are descriptive counts, not significance tests.\n\n'+
          table(local_dips,['platform','backend','scope','mode','sessions_local_dip','seeds'])+
          '\nThese are observed size effects, not causal diagnoses. A persistent reduction from 1 MiB through both 16 and 32 MiB is a large-buffer transition, not necessarily a narrow 16 MiB anomaly. Fixed size order confounds size with time. Candidate explanations include output allocation/page behavior, working-set/cache changes, pinned-buffer/copy behavior, driver scheduling, clocks and thermal state. None is established by these data. Repeat with randomized size order, dense sizes and per-iteration telemetry before assigning a cause.\n\n'+trace)
    cpu=[]
    for r in comparisons:
        if r['metric']=='ecb_to_ctr_throughput_ratio':cpu.append(dict(platform=r['platform'],backend=r['backend'],bytes=r['bytes'],ECB_over_CTR=r['median'],min=r['min'],max=r['max'],IQR=r['iqr'],sessions_ECB_faster=r['above_one']))
    t4=next((s for s in studies if s['platform']=='t4'),None)
    t4text='T4 is not eligible: its imported bundle cannot currently support a raw-CSV-based validated ECB/CTR conclusion. Restore the original archive and rerun; no T4 rates are fabricated.' if 't4' not in valid else 'T4 dispatch and raw distributions passed the same checks as the other platforms. Ratios below summarize five session-level throughput-median contrasts, separately for every size. Consistency does not establish a library-version cause.'
    if 't4' in valid:
        r=next(r for r in cpu if r['platform']=='t4' and r['backend']=='cpu_aesni' and r['bytes']==33554432)
        t4text+=f" At 32 MiB, T4-host CPU ECB/CTR throughput ratio is {r['ECB_over_CTR']:.3f}, range {r['min']:.3f}–{r['max']:.3f} across five sessions; ECB is faster in {r['sessions_ECB_faster']}/5. This is a reproducible mode disparity on the captured cloud CPU, not a T4 GPU AES-NI property."
    write('CPU_ECB_CTR_INVESTIGATION.md','# CPU ECB versus CTR\n\n'+t4text+'\n\n'+table(cpu,['platform','backend','bytes','ECB_over_CTR','min','max','IQR','sessions_ECB_faster'])+
          '\n## Captured CPU/library facts\n\n'+table(platform_rows,['platform','cpu','physical_cpus','logical_cpus','python','pycryptodome','eligible'])+
          '\nNative dispatch details and before/after session telemetry are preserved in `session_provenance.json`. AES-NI dispatch does not guarantee identical bulk implementations for ECB and CTR. Counter generation, native mode implementation, allocation/memory effects, CPU virtualization and clock behavior are hypotheses. A version difference alone is not evidence of a version effect. A controlled same-host/library-version and allocation-policy experiment is needed; retain mode-specific validation and the same timer scope.\n\n'+trace)
    stable=[]
    for r in agg:
        if r['metric'].startswith('speedup_') and r['bytes']==33554432:
            stable.append(dict(platform=r['platform'],backend=r['backend'],mode=r['mode'],scope=r['measurement'],metric=r['metric'],median=r['median_of_sessions'],min=r['session_min'],max=r['session_max'],all_five_above_one=r['session_min']>1))
    v1=[dict(platform=r['platform'],scope=r['measurement'],mode=r['mode'],bytes=r['bytes'],median=r['median'],min=r['min'],max=r['max'],sessions_v1_faster=r['above_one']) for r in comparisons if r['metric']=='v1_vs_baseline_time_speedup']
    empirical=[]
    for p in sorted(valid):
        rows=[r for r in stable if r['platform']==p and r['metric'].endswith('cpu_aesni')]
        for scope in ('resident','pipeline'):
            values=[r for r in rows if r['scope']==scope]
            if values:empirical.append(f"{p}, 32 MiB {scope}: median GPU speedups relative to AES-NI (CPU time / GPU time) range {min(r['median'] for r in values):.3f}–{max(r['median'] for r in values):.3f} across baseline/v1 and ECB/CTR. {sum(r['all_five_above_one'] for r in values)}/{len(values)} combinations beat AES-NI in all five sessions.")
    retention=[dict(platform=r['platform'],backend=r['backend'],mode=r['mode'],metric=r['metric'],median=r['median'],min=r['min'],max=r['max']) for r in comparisons if r['bytes']==33554432 and r['metric'] in ('pipeline_to_resident_throughput_ratio','resident_to_pipeline_latency_ratio','approximate_additional_pipeline_seconds','approximate_relative_additional_pipeline_time')]
    measured_components=[dict(platform=r['platform'],backend=r['backend'],mode=r['mode'],bytes=r['bytes'],metric=r['metric'],median_of_session_medians=r['median_of_sessions']) for r in agg if r['measurement']=='pipeline' and r['metric'] in ('h2d_ns_median','d2h_ns_median','transfer_ns_median','kernel_ns_median','end_to_end_ns_median')]
    csvwrite(out/'pipeline_recorded_components.csv',measured_components,fields=None if measured_components else ['platform','backend','mode','bytes','metric'])
    write('CROSS_PLATFORM_FINDINGS.md','# Cross-platform findings\n\n'+
          f'Validated primary platforms: {", ".join(sorted(valid)) or "none"}. Comparisons retain platform, mode and scope. '+
          ('All three primary studies pass the source, raw-data and saved-estimator checks.\n\n' if {'gtx1650ti','t600','t4'}<=valid else 'A three-platform conclusion is withheld until all three imported studies pass.\n\n')+
          '\n\n'.join(empirical)+'\n\n## GPU timing speedups at 32 MiB\n\n'+table(stable,['platform','backend','mode','scope','metric','median','min','max','all_five_above_one'])+
          '\nA speedup >1 means GPU faster than the named CPU reference in all five sessions only when the minimum also exceeds one. Small-input behavior is separately shown in figures/CSVs; these rows do not claim a universal crossover.\n\n## Optimized v1 versus baseline (same scope)\n\n'+table(v1,['platform','scope','mode','bytes','median','min','max','sessions_v1_faster'])+
          '\nA value >1 means v1 has lower median time. The candidate name does not imply a gain. Full CPU software/AES-NI contrasts and pipeline/resident contrasts are in `derived_comparisons.csv`, retaining session extrema and direction counts. No cross-platform raw samples, CBC references or independently collected standalone GPU baselines are substituted.\n\n## Resident versus pipeline at 32 MiB\n\n'+
          table(retention,['platform','backend','mode','metric','median','min','max'])+
          '\nAbsolute residuals use seconds; relative residuals are (pipeline time − resident time)/resident time, not fractions of total pipeline time. Independently measured host H2D/D2H intervals and the pipeline kernel component are exported in `pipeline_recorded_components.csv` for every size. These are supported by raw fields, not reconstructed from resident subtraction. Pure PCIe service bandwidth, overlap potential, enqueue versus wait costs and allocation-inclusive application latency cannot be established without a separately instrumented experiment.\n\n'+trace)
    write('FOLLOWUP_EXPERIMENTS.md','''# Ranked follow-up experiments

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
''')
    provenance={s['platform']:s['metadata'] for s in studies}
    import json
    (out/'session_provenance.json').write_text(json.dumps(provenance,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    # Document damaged imports without treating JSON survivors as validated CSV data.
    forensic=[]
    for s in studies:
        if s['eligible']:continue
        for seed in SEEDS:
            folder=s['root']/'experiments/cuda_paired'/f'seed-{seed}'
            truncated=folder/'orchestr'
            if truncated.is_file():
                expected=read(truncated).get('artifact_hashes',{})
                matches={p.relative_to(folder).as_posix():[name for name,h in expected.items() if sha(p)==h] for p in (folder/'native').glob('*') if p.is_file()}
                forensic.append(dict(platform=s['platform'],seed=seed,hash_matched_survivors=matches,
                                     missing_original_names=sorted(set(expected)-{n for names in matches.values() for n in names})))
    if forensic:
        (out/'import_diagnostics.json').write_text(json.dumps(forensic,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        with (out/'INTEGRITY_AUDIT.md').open('a',encoding='utf-8') as f:
            f.write('\n## Truncated import diagnostics\n\n`import_diagnostics.json` records surviving file matches against sidecar SHA-256 inventories. The `m/r/s/v` survivors match metadata/results JSON/summary CSV/validation JSON, respectively; raw CSV and source snapshots are absent. The aggregate filename is also truncated. These surviving records do not replace missing input artifacts or prove the complete archive was imported. No original files were renamed or reconstructed.\n')


def figures(out,aggregates,contrasts):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.titlesize':10,'axes.labelsize':9,'savefig.dpi':240,
                         'svg.hashsalt':'aes-cross-platform-2026-10','font.family':'DejaVu Sans','pdf.fonttype':42})
    folder=out/'figures';folder.mkdir()
    colors={'cpu_aesni':'#222222','cpu_software':'#888888','cuda_baseline':'#0072B2','cuda_optimized_v1':'#D55E00'}
    platforms=['gtx1650ti','t600','t4'];names={'gtx1650ti':'GTX 1650 Ti / i5-10300H','t600':'T600 Laptop / i7-11850H','t4':'Tesla T4 / cloud CPU'}
    def save(fig,name,title):
        fig.suptitle(title,fontsize=13)
        fig.text(.5,.005,'Seeds 2003–2007; n=5 sessions; no outlier removal. Source run IDs and CSV paths: DATASET_INVENTORY.md / reproducibility_manifest.json.',ha='center',fontsize=7)
        fig.tight_layout(rect=(0,.025,1,.95))
        fig.savefig(folder/(name+'.png'),metadata={'Software':'AES offline analysis'})
        fig.savefig(folder/(name+'.pdf'),metadata={'CreationDate':None,'ModDate':None,'Creator':'AES offline analysis'})
        plt.close(fig)
    def axes():
        fig,axs=plt.subplots(3,2,figsize=(10,10),squeeze=False,sharey=True)
        for i,p in enumerate(platforms):
            for j,mode in enumerate(('ECB','CTR')):
                ax=axs[i,j];ax.set_title(names[p]+' — '+mode);ax.set_xscale('log',base=2)
                ax.set_xticks(SIZES,labels=['1 KiB','16 KiB','1 MiB','16 MiB','32 MiB'],rotation=20)
                ax.grid(True,alpha=.25);ax.set_xlabel('Payload size (binary units)')
                if not any(r['platform']==p for r in aggregates):ax.text(.5,.5,'UNAVAILABLE: study failed integrity audit',transform=ax.transAxes,ha='center',fontsize=8)
        return fig,axs
    def plot_metric(ax,p,mode,scope,metric,backend,label=None):
        rows=sorted([r for r in aggregates if r['platform']==p and r['mode']==mode and r['measurement']==scope and r['metric']==metric and r['backend']==backend],key=lambda r:r['bytes'])
        if rows:
            ax.plot([r['bytes'] for r in rows],[r['median_of_sessions'] for r in rows],marker='o',color=colors[backend],label=label or backend.replace('cuda_',''))
            ax.fill_between([r['bytes'] for r in rows],[r['session_min'] for r in rows],[r['session_max'] for r in rows],color=colors[backend],alpha=.12)
    for scope,metric,name in [('resident','kernel_throughput_MB_s_median','01_resident_throughput'),('pipeline','end_to_end_throughput_MB_s_median','02_pipeline_throughput'),('pipeline','speedup_pipeline_vs_cpu_aesni','03_pipeline_speedup_vs_aesni')]:
        fig,axs=axes()
        for i,p in enumerate(platforms):
            for j,m in enumerate(('ECB','CTR')):
                ax=axs[i,j]
                for b in colors:
                    if b.startswith('cuda'):plot_metric(ax,p,m,scope,metric,b)
                ax.set_yscale('log');ax.set_ylabel('CPU AES-NI time / GPU pipeline time' if 'speedup' in metric else 'Payload throughput (decimal MB/s)')
                if 'speedup' in metric:ax.axhline(1,color='gray',ls='--')
                if ax.get_legend_handles_labels()[0]:ax.legend(fontsize=8)
        save(fig,name,scope.capitalize()+' scope — median of five session estimates; shading = session range')
    # Matched time contrasts, computed per session before summarizing.
    def contrast_plot(name,metric,title,ylabel,scopes):
        fig,axs=axes()
        for i,p in enumerate(platforms):
            for j,m in enumerate(('ECB','CTR')):
                ax=axs[i,j]
                for backend,scope,style in scopes:
                    rows=[r for r in contrasts if r['platform']==p and r['mode']==m and r['metric']==metric and r['backend']==backend and r['measurement']==scope]
                    bysize=defaultdict(list)
                    for r in rows:bysize[r['bytes']].append(r['value'])
                    if bysize:
                        xs=sorted(bysize);ss=[stats(bysize[x]) for x in xs]
                        ax.plot(xs,[s['median'] for s in ss],style,marker='o',label=backend.replace('cuda_','')+' '+scope,color=colors[backend])
                        ax.fill_between(xs,[s['min'] for s in ss],[s['max'] for s in ss],color=colors[backend],alpha=.12)
                ax.axhline(1,color='gray',ls=':');ax.set_ylabel(ylabel)
                if ax.get_legend_handles_labels()[0]:ax.legend(fontsize=7)
        save(fig,name,title+'; median and range of five session contrasts')
    contrast_plot('04_v1_vs_baseline','v1_vs_baseline_time_speedup','Resident / pipeline kept separate — baseline time / v1 time','v1 time speedup (>1 faster)',[('cuda_optimized_v1','resident','-'),('cuda_optimized_v1','pipeline','--')])
    contrast_plot('08_pipeline_resident_ratio','pipeline_to_resident_throughput_ratio','Pipeline throughput / resident throughput','Throughput retention ratio',[(b,'pipeline/resident','-') for b in colors if b.startswith('cuda')])
    fig,axs=axes()
    for i,p in enumerate(platforms):
        for j,m in enumerate(('ECB','CTR')):
            ax=axs[i,j]
            for b in colors:
                scope='transform' if b.startswith('cpu') else 'pipeline';metric='seconds_median' if scope=='transform' else 'end_to_end_seconds_median'
                rows=sorted([r for r in aggregates if r['platform']==p and r['mode']==m and r['backend']==b and r['measurement']==scope and r['metric']==metric],key=lambda r:r['bytes'])
                if rows:ax.plot([r['bytes'] for r in rows],[100*r['session_coefficient_of_variation'] for r in rows],marker='o',color=colors[b],label=b+' '+scope)
            ax.set_ylabel('CV of five session latency medians (%)')
            if ax.lines:ax.legend(fontsize=6)
    save(fig,'05_session_variability','CPU transform / GPU pipeline — between-session latency variability')
    fig,axs=axes()
    for i,p in enumerate(platforms):
        for j,m in enumerate(('ECB','CTR')):
            ax=axs[i,j];ax.set_xlim(800000,40000000);ax.set_xticks(SIZES[2:],labels=['1 MiB','16 MiB','32 MiB'])
            for b in colors:
                for scope in (['transform'] if b.startswith('cpu') else ['resident','pipeline']):
                    metric='throughput_MB_s_median' if scope=='transform' else 'kernel_throughput_MB_s_median' if scope=='resident' else 'end_to_end_throughput_MB_s_median'
                    rows=sorted([r for r in aggregates if r['platform']==p and r['mode']==m and r['backend']==b and r['measurement']==scope and r['metric']==metric and r['bytes']>=1048576],key=lambda r:r['bytes'])
                    if rows:ax.plot([r['bytes'] for r in rows],[r['median_of_sessions'] for r in rows],marker='o',ls='--' if scope=='pipeline' else '-',color=colors[b],label=b.replace('cuda_','')+' '+scope)
            ax.set_yscale('log');ax.set_ylabel('Payload throughput (decimal MB/s)')
            if ax.lines:ax.legend(fontsize=6)
    save(fig,'06_16MiB_anomaly','1 / 16 / 32 MiB — CPU transform, GPU resident and pipeline scopes')
    fig,axs=plt.subplots(1,3,figsize=(12,4),squeeze=False,sharey=True)
    for ax,p in zip(axs[0],platforms):
        for m,style in [('ECB','-'),('CTR','--')]:
            rows=sorted([r for r in aggregates if r['platform']==p and r['backend']=='cpu_aesni' and r['metric']=='throughput_MB_s_median' and r['mode']==m],key=lambda r:r['bytes'])
            if rows:
                ax.plot([r['bytes'] for r in rows],[r['median_of_sessions'] for r in rows],style,marker='o',label=m)
                ax.fill_between([r['bytes'] for r in rows],[r['session_min'] for r in rows],[r['session_max'] for r in rows],alpha=.15)
        ax.set_title(names[p]);ax.set_xscale('log',base=2);ax.set_yscale('log');ax.set_xlabel('Payload bytes');ax.set_ylabel('Payload throughput (decimal MB/s)');ax.grid(alpha=.25)
        if ax.lines:ax.legend()
        else:ax.text(.5,.5,'Unavailable: failed import audit',transform=ax.transAxes,ha='center',fontsize=8)
    save(fig,'07_cpu_ecb_ctr','CPU AES-NI transform scope — ECB versus CTR; shading = session range')
