"""Inspect archived inputs and export saved notebook metrics; no model training.

Run from any directory: python scripts/inspect_project.py
"""
import ast
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = 'AirQuality中文版_.ipynb'
NUMBER = r'([0-9]+(?:\.[0-9]+)?)'


def main():
    notebook = json.loads((ROOT / NOTEBOOK).read_text(encoding='utf-8'))
    syntax_errors = []
    for index, cell in enumerate(notebook['cells']):
        if cell['cell_type'] == 'code':
            try:
                ast.parse(''.join(cell['source']))
            except SyntaxError as exc:
                syntax_errors.append({'cell_index': index, 'error': str(exc)})
    specifications = [
        ('SARIMA (2,1,2)(0,1,0,24)', 68, 'rolling_1_step'),
        ('SARIMA (2,1,2)(2,1,2,24)', 73, 'rolling_1_step'),
        ('SARIMAX', 82, 'fixed_origin_with_observed_exogenous'),
        ('Random Forest (final saved fit)', 91, 'tabular_with_observed_exogenous'),
        ('Gradient Boosting', 98, 'tabular_with_observed_exogenous'),
        ('Bagging', 103, 'tabular_with_observed_exogenous'),
        ('MLP', 119, 'tabular_test_used_for_validation'),
        ('LSTM (1 timestep)', 129, 'one_timestep_test_used_for_validation'),
        ('GRU (1 timestep)', 139, 'one_timestep_test_used_for_validation'),
        ('GRU (24 timestep supplement)', 158, '24_timestep_test_used_for_validation'),
    ]
    metrics = []
    for model, index, protocol in specifications:
        outputs = notebook['cells'][index].get('outputs', [])
        text = '\n'.join(''.join(o.get('text', [])) for o in outputs)
        row = {'model': model, 'cell_index': index, 'protocol': protocol}
        for label in ['RMSE', 'MAE', 'MSE', 'R²']:
            match = re.search(r'(?<![A-Za-z])' + re.escape(label) + r'\s*[:=]\s*' + NUMBER, text)
            if match:
                row['r2' if label == 'R²' else label.lower()] = float(match.group(1))
        if len(row) == 3:
            raise ValueError(f'Missing saved metrics for {model} in cell {index}')
        metrics.append(row)
    inputs = {}
    for name in ['AirQualityUCI.csv', 'Rome_meteo.csv', 'merged_df.csv']:
        path = ROOT / name
        with path.open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.reader(handle, delimiter=';' if name == 'AirQualityUCI.csv' else ',')
            if name == 'Rome_meteo.csv':
                for _ in range(3):
                    next(reader)
            header = next(reader)
            rows = [r for r in reader if any(v.strip() for v in r)]
        if name == 'Rome_meteo.csv':
            dates = [datetime.fromisoformat(r[0]) for r in rows]
        else:
            dates = [datetime.strptime(r[0] + ' ' + r[1], '%d/%m/%Y %H.%M.%S') for r in rows]
        inputs[name] = {
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'rows_nonempty': len(rows),
            'time_min': min(dates).isoformat(),
            'time_max': max(dates).isoformat(),
            'duplicate_timestamps': len(dates) - len(set(dates)),
            'columns': header,
        }
    evidence = {
        'source_notebook': NOTEBOOK,
        'source_notebook_sha256': hashlib.sha256((ROOT / NOTEBOOK).read_bytes()).hexdigest(),
        'cell_index_convention': 'zero_based',
        'metrics_status': 'saved_outputs_only_not_retrained',
        'syntax_errors': syntax_errors,
        'inputs': inputs,
        'metrics': metrics,
    }
    (ROOT / 'results').mkdir(exist_ok=True)
    (ROOT / 'results' / 'evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with (ROOT / 'results' / 'saved_metrics.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['model', 'cell_index', 'protocol', 'rmse', 'mae', 'mse', 'r2'])
        writer.writeheader()
        writer.writerows(metrics)
    print(json.dumps({'code_cells_parse': not syntax_errors, 'metric_rows': len(metrics), 'data_rows': {k: v['rows_nonempty'] for k, v in inputs.items()}}, ensure_ascii=False))
    if syntax_errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
