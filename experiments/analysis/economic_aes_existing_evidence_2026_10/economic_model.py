"""Pure cost calculations; no hardware, price services or benchmark imports."""
import math

HOURLY_RATIOS = (0.50, 0.75, 1.00, 1.25, 1.50, 2.00)

def seconds_per_gb(throughput_mb_s):
    if not math.isfinite(throughput_mb_s) or throughput_mb_s <= 0:
        raise ValueError('Positive finite decimal MB/s required')
    return 1000 / throughput_mb_s

def cost_per_gb(throughput_mb_s, hourly_cost):
    if not math.isfinite(hourly_cost) or hourly_cost < 0:
        raise ValueError('Finite nonnegative hourly cost required')
    return seconds_per_gb(throughput_mb_s) * hourly_cost / 3600

def decision(cpu_cost, gpu_cost):
    if math.isclose(cpu_cost, gpu_cost, rel_tol=1e-12, abs_tol=1e-15):
        return 'equal'
    return 'GPU' if gpu_cost < cpu_cost else 'CPU'

def break_even(f_cpu, f_gpu, c_cpu, c_gpu, feasible_volume=None):
    """Return candidate and direction; feasibility needs an explicit period volume."""
    if any(not math.isfinite(x) or x < 0 for x in (f_cpu,f_gpu,c_cpu,c_gpu)):
        raise ValueError('Costs must be finite and nonnegative')
    fixed, saving = f_gpu-f_cpu, c_cpu-c_gpu
    if saving == 0:
        return dict(volume_gb=None, status='equal at every volume' if fixed == 0 else
                    'no positive break-even under these assumptions', direction='no crossing')
    candidate = fixed/saving
    if not math.isfinite(candidate) or candidate <= 0:
        return dict(volume_gb=None, status='no positive break-even under these assumptions', direction='no positive crossing')
    feasible = 'economic feasibility unknown' if feasible_volume is None else (
        'within specified volume' if candidate <= feasible_volume else 'outside specified volume')
    return dict(volume_gb=candidate, status=feasible,
                direction='GPU cheaper above candidate' if saving > 0 else 'GPU cheaper below candidate')
