"""Rebuild manuscript figures from audited CSVs; never executes benchmarks."""
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / 'experiments/analysis/economic_aes_existing_evidence_2026_10'

def rows(name):
    with (DATA / name).open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))

def save(fig, name):
    fig.tight_layout()
    (ROOT / 'figures').mkdir(exist_ok=True)
    fig.savefig(ROOT / 'figures' / (name + '.pdf'), metadata={'CreationDate': None, 'ModDate': None})
    plt.close(fig)

def measurement_boundaries():
    """Schematic sequences, checked against GPU.measure/measure_diagnostic and cpu_measure."""
    fig, ax = plt.subplots(figsize=(8.2, 5.9))
    ax.set(xlim=(-1, 101), ylim=(0, 106))
    ax.axis('off')

    def box(x, y, width, label, measured=False):
        ax.add_patch(Rectangle((x, y), width, 12, facecolor='.89' if measured else '.97',
                               edgecolor='.15' if measured else '.65',
                               linewidth=1.3 if measured else .7))
        ax.text(x + width/2, y+6, label, ha='center', va='center', fontsize=9)

    def arrow(x1, x2, y):
        ax.annotate('', (x2, y), (x1, y), arrowprops={'arrowstyle':'->', 'lw':.8})

    def interval(x1, x2, y, label):
        ax.plot([x1,x1,x2,x2], [y-1.8,y,y,y-1.8], color='.1', lw=1.2)
        ax.text((x1+x2)/2, y+1.2, label, fontsize=9, ha='center', va='bottom')

    ax.text(0, 103, 'A   CPU AES-NI transform', fontsize=11, weight='bold')
    interval(31, 74, 95, 'START   |   host wall time   |   END')
    box(0, 79, 27, 'Input ready\nCipher + key setup')
    box(31, 79, 43, 'One synchronous encrypt() call\nOutput allocation + AES-NI\nPython/native call + return', True)
    box(78, 79, 22, 'Reference check\nLogging')
    arrow(27,31,85); arrow(74,78,85)

    ax.text(0, 71, 'B   GPU resident / kernel-only', fontsize=11, weight='bold')
    interval(31, 58, 63, 'START event  |  STOP event')
    box(0, 47, 27, 'GPU preparation\nH2D + sync\nEvent creation')
    box(31, 47, 27, 'One AES-CTR\nkernel launch', True)
    box(62, 47, 38, 'Wait for stop event*\nRead device-event duration\nD2H + sync; output check')
    arrow(27,31,53); arrow(58,62,53)

    ax.text(0, 39, 'C   GPU prepared transfer-inclusive pipeline', fontsize=11, weight='bold')
    interval(31, 100, 31, 'START   |   host wall time   |   END')
    box(0, 15, 27, 'GPU preparation\nEvent creation\nInitial stream sync')
    box(31, 15, 21, 'H2D payload\n+ sync', True)
    box(55, 15, 21, 'Kernel + events\n+ stop-event wait', True)
    box(79, 15, 21, 'D2H payload\n+ final sync', True)
    arrow(27,31,21); arrow(52,55,21); arrow(76,79,21)

    ax.text(0, 10, '* Completion is awaited; host wait time is not added to the resident event metric.', fontsize=8.5)
    ax.text(0, 5, 'GPU preparation (excluded): device/pinned buffers, pinned staging copy, key/counter upload + expansion.', fontsize=8.5)
    ax.text(0, 0, 'All paths exclude input generation, validation, compilation, storage I/O and full application orchestration.\nGPU output-to-bytes conversion is also excluded. Sequence widths do not represent elapsed time.', fontsize=8.5, va='top')
    save(fig, 'measurement_boundaries')

def main():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    measurement_boundaries()
    primary = rows('RECONSTRUCTED_RESULTS.csv')
    fig, ax = plt.subplots(figsize=(7.2, 3.7))
    sizes = [1, 16, 32]
    series = [('cpu_aesni', 'transform', 'CPU AES-NI', '.25', '///'),
              ('cuda_baseline', 'resident', 'GPU resident', '.6', 'xx'),
              ('cuda_baseline', 'pipeline', 'GPU pipeline', '.9', '..')]
    for index, (backend, boundary, label, color, hatch) in enumerate(series):
        values = []
        for size in sizes:
            matches = [r for r in primary if r['mode'] == 'CTR' and
                       int(r['bytes']) == size * 1048576 and r['backend'] == backend
                       and r['measurement'] == boundary]
            assert len(matches) == 1 and matches[0]['sessions'] == '5'
            values.append(float(matches[0]['throughput_MB_s']))
        bars = ax.bar([x + (index - 1) * .25 for x in range(3)], values,
                      width=.25, label=label, color=color, edgecolor='black', hatch=hatch)
        ax.bar_label(bars, fmt='%.1f', fontsize=8, padding=3)
    ax.set_xticks(range(3), ['1', '16', '32'])
    ax.set_xlabel('Input size (MiB)')
    ax.set_ylabel('Throughput (decimal MB/s)')
    ax.set_ylim(0, 6200)
    ax.legend(ncol=3, loc='upper center', frameon=False, fontsize=9)
    save(fig, 'aes_throughput_comparison')

    supplementary = rows('SUPPLEMENTARY_RESULTS.csv')
    values = []
    for pages in [1, 4, 16, 32]:
        matches = [r for r in supplementary if r['campaign'] == 'T4 independent pages'
                   and r['estimator'] == 'ratio_of_medians' and r['pages'] == str(pages)]
        assert len(matches) == 1
        values.append(float(matches[0]['median']))
    fig, ax = plt.subplots(figsize=(7.2, 3.7))
    ax.scatter(range(4), values, color='black', marker='s', s=45)
    for x, value in enumerate(values):
        ax.annotate(f'{value:.4f}', (x, value), xytext=(0, 10),
                    textcoords='offset points', ha='center')
    ax.axhline(1, color='.4', linestyle='--', label='Equal times')
    ax.set_xticks(range(4), ['1', '4', '16', '32'])
    ax.set_xlim(-.4, 3.4)
    ax.set_ylim(.45, 1.12)
    ax.set_xlabel('Number of independent 1 MiB pages (discrete categories)')
    ax.set_ylabel('CPU EVP / GPU pipeline time ratio')
    ax.legend(frameon=False, loc='upper left')
    save(fig, 't4_page_batch_ratios')
    names = ['RECONSTRUCTED_RESULTS.csv', 'SUPPLEMENTARY_RESULTS.csv']
    manifest = {'inputs': {name: hashlib.sha256((DATA / name).read_bytes()).hexdigest()
                           for name in names},
                'primary_estimator': 'median of five session throughput medians',
                'T4_estimator': 'median of five session CPU/GPU median-time ratios',
                'T4_categories': [1, 4, 16, 32], 'new_measurements': False}
    diagram_sources = ['scripts/aes_cuda_cpu_gpu.py', 'scripts/aes_cuda_baseline.py',
                       'experiments/analysis/economic_aes_existing_evidence_2026_10/MEASUREMENT_BOUNDARIES.md']
    manifest['boundary_diagram_source_sha256'] = {
        name: hashlib.sha256((ROOT.parent / name).read_bytes()).hexdigest() for name in diagram_sources}
    (ROOT / 'figure_provenance.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
