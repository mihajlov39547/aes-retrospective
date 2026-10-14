"""Version 2 scientific metric contract; no benchmark imports or estimators."""
import math

POLICY_VERSION = 2
PROCESS_DIAGNOSTICS = {
    'process_cpu_ns_median': 'Optional diagnostic CPU time, not the primary wall timer.',
    'process_to_wall_ratio_median': 'Optional diagnostic CPU/wall ratio, not a speedup.',
}


def metric_policy(experiment, row):
    """Return required metrics and explicitly optional metrics with their reasons.

    Structurally inapplicable fields (e.g. resident transfer time) are neither
    required nor optional: they must remain null in the native schema.
    """
    optional = {}
    if experiment in ('cpu_cbc', 'cpu_aesni', 'cpu_gcm'):
        required = {'seconds_median', 'throughput_MB_s_median'}
        optional = dict(PROCESS_DIAGNOSTICS)
        if experiment == 'cpu_aesni': required.add('speedup_vs_software_median')
    elif experiment == 'avalanche':
        required = {'median', 'median_normalized'}
    elif experiment == 'keyspace':
        required = {'candidates_checked_median', 'elapsed_seconds_median', 'candidates_per_second_median'}
        optional = {name+'_median': 'Derived search-time projection, not an additional measured search.'
                    for name in ('expected_full_scan_time', 'expected_half_scan_time', 'expected_uniform_hit_time')}
    elif experiment in ('cuda_baseline', 'cuda_paired'):
        if row.get('backend', '').startswith('cpu_'):
            required = {'seconds_median', 'throughput_MB_s_median', 'wall_elapsed_ns_median'}
            optional = dict(PROCESS_DIAGNOSTICS)
        else:
            scope = row['measurement']
            required = set()
            if scope in ('resident', 'pipeline'):
                required.update(('kernel_seconds_median', 'kernel_throughput_MB_s_median', 'kernel_ns_median'))
            if scope in ('pipeline', 'transfer-only'):
                required.update(('h2d_ns_median', 'd2h_ns_median', 'transfer_ns_median'))
            if scope == 'pipeline':
                required.update(('end_to_end_seconds_median', 'end_to_end_throughput_MB_s_median', 'end_to_end_ns_median'))
            if experiment == 'cuda_paired':
                ratio_scope = 'isolated' if scope == 'resident' else 'pipeline'
                required.update('speedup_'+ratio_scope+'_vs_'+cpu for cpu in ('cpu_aesni', 'cpu_software'))
                if scope == 'resident': required.add('resident_batch_ns_median')
    else:
        raise ValueError('No scientific metric contract for '+experiment)
    return required, optional


def is_metric(name):
    return name.endswith('_median') or name.startswith('speedup_') or name in ('median', 'median_normalized')


def validate_metrics(experiment, row):
    required, optional = metric_policy(experiment, row)
    for name in required:
        if row.get(name) is None: raise ValueError('Missing required metric: '+experiment+'/'+name)
    for name, value in row.items():
        if not is_metric(name) or value is None: continue
        if name not in required and name not in optional:
            raise ValueError('Metric outside documented execution scope: '+experiment+'/'+name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('Invalid numeric metric: '+name)
    return required, optional
