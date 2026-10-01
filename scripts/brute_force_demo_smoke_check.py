"""Isolated small CPU integration checks; never runs a pilot or study."""
import csv
import hashlib
import json
import math
import random
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import brute_force_demo as demo


def main():
    with tempfile.TemporaryDirectory(prefix='aes-search-smoke-') as temporary:
        root = Path(temporary)
        command = [sys.executable, str(Path(demo.__file__))]
        plan = subprocess.run(command + ['--output', str(root)], capture_output=True, text=True)
        assert plan.returncode == 0 and not list(root.iterdir()), plan.stderr
        for options in (['--bits', '0'], ['--bits', '13'],
                        ['--profile', 'pilot', '--bits', '23'],
                        ['--profile', 'study', '--bits', '29'],
                        ['--purpose', 'study'], ['--algorithm', 'DES'],
                        ['--mode', 'CBC'], ['--target-position', 'end', 'end']):
            result = subprocess.run(command + options, capture_output=True, text=True)
            assert result.returncode != 0, options
        with patch.object(demo, 'perf_counter_ns', side_effect=AssertionError('Gate used timer')):
            validation = demo.validate('smoke', 'smoke')
            assert validation['passed'], validation
        with patch.object(demo, 'encrypt', return_value=bytes(32)):
            assert not demo.validate('broken', 'smoke')['passed']
        failed = demo.arguments(['--output', str(root / 'failed')])
        with patch.object(demo, 'perf_counter_ns', side_effect=AssertionError('Measured failed gate')):
            try:
                demo.run(failed, validator=lambda session, purpose: dict(passed=False, session_id=session, purpose=purpose))
            except RuntimeError:
                pass
            else:
                raise AssertionError('Failed validation accepted')
        assert not list((root / 'failed').rglob('raw.csv'))
        assert not list((root / 'failed').rglob('summary.csv'))

        output = root / 'passed'
        args = demo.arguments(['--run', '--bits', '8', '--repeats', '2', '--seed', '2003', '--output', str(output)])
        real_timer = demo.perf_counter_ns
        def guarded_timer():
            reports = list(output.glob('brute_force_demo-validation-*/validation.json'))
            assert len(reports) == 1 and json.loads(reports[0].read_text())['passed']
            return real_timer()
        with patch.object(demo, 'perf_counter_ns', side_effect=guarded_timer):
            directory = demo.run(args)
        def rows(name):
            with (directory / name).open(newline='') as stream:
                return list(csv.DictReader(stream))
        raw, summary, extrapolations = rows('raw.csv'), rows('summary.csv'), rows('extrapolations.csv')
        assert len(raw) == 8 and len(summary) == 4 and len(extrapolations) == 18
        rng = random.Random(2003)
        for row in raw:
            index = demo.target_index(row['scenario'], 8, rng)
            assert int(row['target_index']) == int(row['found_index']) == index
            assert int(row['candidates_checked']) == index + 1
            seconds = int(row['wall_elapsed_ns']) / 1e9
            assert seconds > 0 and float(row['elapsed_seconds']) == seconds
            assert math.isclose(float(row['candidates_per_second']), (index + 1) / seconds)
            assert math.isclose(float(row['expected_full_scan_time']), 2 * float(row['expected_half_scan_time']))
        for row in summary:
            group = [float(r['candidates_per_second']) for r in raw if r['scenario'] == row['scenario']]
            for name, value in [('count', len(group)), ('mean', statistics.mean(group)),
                                ('median', statistics.median(group)), ('stdev', statistics.stdev(group)),
                                ('min', min(group)), ('max', max(group))]:
                assert math.isclose(float(row['candidates_per_second_' + name]), value)
        metadata = json.loads((directory / 'metadata.json').read_text())
        assert metadata['validation_passed'] and metadata['seed'] == 2003
        assert metadata['algorithm'] == 'AES-128' and metadata['mode'] == 'ECB'
        assert metadata['keyspace_size'] == 256 and metadata['reduced_key_bits'] == 8
        assert len(metadata['measurements']) == 8
        assert metadata['validation_sha256'] == hashlib.sha256((directory / 'validation.json').read_bytes()).hexdigest()
        for name, digest in metadata['source_sha256'].items():
            assert hashlib.sha256((directory / 'source' / name).read_bytes()).hexdigest() == digest
        assert (directory / 'report.md').exists() and (directory / 'results.json').exists()
        rate = next(float(r['candidates_per_second_median']) for r in summary if r['scenario'] == 'end')
        pilot_rng = random.Random(2003)
        count = sum(demo.target_index(position, 20, pilot_rng) + 1 for _ in range(3) for position in demo.POSITIONS)
        print(f'PASS: CLI, {len(validation["tests"])} validation checks, gate ordering/failure, counts, formulas, statistics, deterministic targets, exports and hashes.')
        print(f'Smoke-only end-scan rate: {rate:.0f} candidates/s; rough 20-bit/3-repeat pilot estimate: {count/rate:.1f} seconds. Short-run estimate only.')


if __name__ == '__main__':
    main()
