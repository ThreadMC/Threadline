#!/usr/bin/env python3
from pathlib import Path
import hashlib

VERSIONS_DIR = Path('server-jars/versions').resolve()
OUTPUT_ROOT = Path('mappings').resolve()
OUTPUT_ROOT.mkdir(exist_ok=True)

TINY_HEADER = 'v1\tofficial\tintermediary\tnamed\n'

def sha8(text: str) -> str:
    return hashlib.sha1(text.strip().encode('utf-8')).hexdigest()[:8]

def parse_intermediary(intermediary_path: Path):
    class_map = {}
    field_map = {}
    method_map = {}
    if not intermediary_path.exists():
        return class_map, field_map, method_map
    with intermediary_path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('v1'):
                continue
            parts = line.split('\t')
            if parts[0] == 'CLASS':
                _, obf, inter = parts[:3]
                class_map[obf] = inter
            elif parts[0] == 'FIELD':
                _, obf, sig, inter = parts[:4]
                field_map[(obf, sig)] = inter
            elif parts[0] == 'METHOD':
                _, obf, sig, inter = parts[:4]
                method_map[(obf, sig)] = inter
    return class_map, field_map, method_map

def parse_named(version_path: Path) -> None:
    version = version_path.name
    named_file = (version_path / 'mojang-mappings.txt').resolve()
    obscura_intermediary = Path(f'obscura/mappings/{version}/intermediary.tiny').resolve()
    if not named_file.exists():
        print(f'[SKIP] {version} - no mojang-mappings.txt')
        return

    class_map, field_map, method_map = parse_intermediary(obscura_intermediary)

    out_dir = (OUTPUT_ROOT / version).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'named.tiny'

    with named_file.open('r', encoding='utf-8') as src, out_file.open('w', encoding='utf-8') as dst:
        dst.write(TINY_HEADER)
        current_class = None
        current_class_inter = None
        for line in src:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if not line.startswith(' '):
                if '->' in line and line.endswith(':'):
                    parts = line.split('->')
                    if len(parts) == 2:
                        original = parts[0].strip()
                        obf = parts[1].strip()[:-1]
                        class_inter = class_map.get(obf, f'net/minecraft/class_{sha8(original)}')
                        dst.write(f'CLASS\t{obf}\t{class_inter}\t{original}\n')
                        current_class = obf
                        current_class_inter = class_inter
                continue
            if current_class is None:
                continue
            if '->' in line:
                left, right = line.split('->')
                left = left.strip()
                right = right.strip()
                if '(' in left:
                    # method
                    method_sig = left.split(' ')[-1]
                    inter = method_map.get((current_class, method_sig), right)
                    dst.write(f'METHOD\t{current_class}\t{method_sig}\t{inter}\t{right}\n')
                else:
                    # field
                    field_sig = left.split(' ')[-1]
                    inter = field_map.get((current_class, field_sig), right)
                    dst.write(f'FIELD\t{current_class}\t{field_sig}\t{inter}\t{right}\n')

    print(f'[DONE] {version} -> named.tiny')

def main():
    for version_path in sorted(VERSIONS_DIR.iterdir()):
        if version_path.is_dir():
            parse_named(version_path)

if __name__ == '__main__':
    main()