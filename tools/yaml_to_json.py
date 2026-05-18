"""Converte os YAMLs de config/ em um único JSON consumido pelo build.

Rodado pela Python do sistema (não a embarcada no GIMP), porque a do GIMP
é externally-managed (PEP 668) e não tem pyyaml.

Uso:
    python tools/yaml_to_json.py <config_dir> <output_json>
"""

import json
import sys
from pathlib import Path

import yaml


def main():
    if len(sys.argv) != 3:
        print('Uso: python tools/yaml_to_json.py <config_dir> <output_json>', file=sys.stderr)
        sys.exit(2)

    config_dir = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    combined = {
        'invite': yaml.safe_load((config_dir / 'invite.yaml').read_text(encoding='utf-8')),
        'layout': yaml.safe_load((config_dir / 'layout.yaml').read_text(encoding='utf-8')),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(combined, default=str, indent=2), encoding='utf-8')
    print('Config JSON gravado em:', out_path)


if __name__ == '__main__':
    main()
