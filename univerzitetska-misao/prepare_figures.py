"""Rebuild manuscript figures from audited CSVs; never executes benchmarks."""
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / 'experiments/analysis/economic_aes_existing_evidence_2026_10'

def rows(name):
    with (DATA / name).open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))

def save(fig, name):
    fig.tight_layout()
    fig.savefig(ROOT / (name + '.pdf'), metadata={'CreationDate': None, 'ModDate': None})
    plt.close(fig)

def main():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
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
    ax.set_xlabel('Veličina ulaza (MiB)')
    ax.set_ylabel('Propusnost (decimalni MB/s)')
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
    ax.axhline(1, color='.4', linestyle='--', label='Jednaka vremena')
    ax.set_xticks(range(4), ['1', '4', '16', '32'])
    ax.set_xlim(-.4, 3.4)
    ax.set_ylim(.45, 1.12)
    ax.set_xlabel('Broj nezavisnih stranica od 1 MiB (diskretne kategorije)')
    ax.set_ylabel('Odnos vremena CPU EVP / GPU pipeline')
    ax.legend(frameon=False, loc='upper left')
    save(fig, 't4_page_batch_ratios')
    names = ['RECONSTRUCTED_RESULTS.csv', 'SUPPLEMENTARY_RESULTS.csv']
    manifest = {'inputs': {name: hashlib.sha256((DATA / name).read_bytes()).hexdigest()
                           for name in names},
                'primary_estimator': 'median of five session throughput medians',
                'T4_estimator': 'median of five session CPU/GPU median-time ratios',
                'T4_categories': [1, 4, 16, 32], 'new_measurements': False}
    (ROOT / 'figure_provenance.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
