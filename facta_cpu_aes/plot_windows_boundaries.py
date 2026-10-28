"""Regenerate Figure 2 from the verified, archived Windows session summaries.

Run analyze_evidence.py first. Requires matplotlib; no benchmarks are executed.
"""
from hashlib import sha256
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


def main():
    audit = json.loads((ROOT / 'build/evidence/audit.json').read_text(encoding='utf-8'))
    source = audit['windows']
    assert sha256((ROOT / source['file']).read_bytes()).hexdigest() == source['sha256']
    rates = source['rates']
    keys = ['openssl_default', 'pycryptodome']
    colors = ['#244f70', '#b96827']
    boundaries = ['transform', 'operation_envelope']
    values = [[rates[f'{k}/{b}']['median_MB_s'] for b in boundaries] for k in keys]
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
        'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42})
    fig, (ax, rel) = plt.subplots(1, 2, figsize=(6.2, 3.1),
        gridspec_kw={'width_ratios': [1.55, 1]}, layout='constrained')
    for offset, vals, color, label in zip([-.18, .18], values, colors, ['OpenSSL EVP', 'PyCryptodome']):
        bars = ax.bar([offset, 1 + offset], vals, width=.34, color=color, label=label)
        ax.bar_label(bars, labels=[f'{v:.0f}' for v in vals], padding=3, fontsize=10)
    ax.set_xticks([0, 1], ['Transform', 'Instrumented\noperation'])
    ax.set_ylabel('Throughput (MB/s)')
    ax.set_ylim(0, 6900)
    ax.set_title('(a) Measured throughput', loc='left', fontsize=10)
    ax.legend(frameon=False, loc='upper right', fontsize=9)
    ax.set_axisbelow(True)
    ax.grid(axis='y', alpha=.2)
    c = audit['contrasts']
    ratios = [c['windows_transform_ratio'], c['windows_operation_ratio']]
    rel.plot([0, 1], ratios, marker='o', color='#244f70', linewidth=2)
    rel.axhline(1, color='#777777', linestyle='--', linewidth=1)
    for x, y in enumerate(ratios):
        rel.annotate(f'{y:.3f}×', (x, y), xytext=(0, 10), textcoords='offset points',
                     ha='center', weight='bold')
    rel.set_xticks([0, 1], ['Transform', 'Instrumented\noperation'])
    rel.set_xlim(-.3, 1.3)
    rel.set_ylim(.9, 2.2)
    rel.set_ylabel('OpenSSL / PyCryptodome')
    rel.set_title('(b) Relative advantage', loc='left', fontsize=10)
    rel.grid(axis='y', alpha=.2)
    fig.supxlabel('Operation / transform throughput: OpenSSL 26.7%; PyCryptodome 41.8%', fontsize=9)
    fig.savefig(ROOT / 'figures/windows_boundaries.pdf', metadata={
        'Title': 'Windows AES-128-CTR, 32 MiB: attenuation across timing boundaries',
        'Subject': 'Derived from five archived session summaries per configuration',
        'CreationDate': None, 'ModDate': None})
    fig.savefig(ROOT / 'build/evidence/windows_boundaries.png', dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
