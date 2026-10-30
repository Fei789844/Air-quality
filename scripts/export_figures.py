"""Export original PNG outputs without rerunning or modifying the notebook."""
import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'AirQuality中文版_.ipynb'
FIGURES = [
    (74, 'sarima-rolling-forecast.png', 'SARIMA (2,1,2)(2,1,2,24), rolling one-step forecast'),
    (93, 'random-forest-forecast.png', 'Random Forest, saved test predictions'),
    (159, 'gru-24h-forecast.png', 'Supplementary GRU, first 360 train/test samples'),
]


def main():
    notebook = json.loads((ROOT / SOURCE).read_text(encoding='utf-8'))
    target = ROOT / 'assets' / 'figures'
    target.mkdir(parents=True, exist_ok=True)
    manifest = []
    for cell_index, filename, caption in FIGURES:
        images = [(i, o['data']['image/png']) for i, o in enumerate(notebook['cells'][cell_index].get('outputs', [])) if 'image/png' in o.get('data', {})]
        if len(images) != 1:
            raise ValueError(f'Expected one PNG in cell {cell_index}, found {len(images)}')
        output_index, encoded = images[0]
        binary = base64.b64decode(''.join(encoded) if isinstance(encoded, list) else encoded)
        assert binary.startswith(b'\x89PNG\r\n\x1a\n')
        (target / filename).write_bytes(binary)
        manifest.append({'file': 'assets/figures/' + filename, 'source_notebook': SOURCE, 'cell_index': cell_index, 'output_index': output_index, 'caption': caption, 'sha256': hashlib.sha256(binary).hexdigest()})
    (target / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Exported {len(manifest)} original PNG outputs.')


if __name__ == '__main__':
    main()
