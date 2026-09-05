import os
import re
import sys

src_dir = 'g:/minecraft_desktop/src'
include_pattern = re.compile(r'^\s*#\s*include\s*([\"<])([^>\"]+)([\">])')
malformed_pattern = re.compile(r'^\s*#\s*include\s+[^\"<]')

errors = []
total_includes = 0

for root, dirs, files in os.walk(src_dir):
    for f in files:
        if f.endswith(('.c', '.h')):
            fpath = os.path.join(root, f)
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                for line_idx, line in enumerate(fp, 1):
                    line_str = line.strip()
                    if line_str.startswith('#include'):
                        total_includes += 1
                        if malformed_pattern.match(line_str):
                            errors.append(f'{fpath}:{line_idx}: Malformed include: {line_str}')
                            continue
                        m = include_pattern.match(line_str)
                        if not m:
                            errors.append(f'{fpath}:{line_idx}: Unrecognized include syntax: {line_str}')
                            continue
                        delim_open, inc_path, delim_close = m.groups()
                        if delim_open == '"':
                            # Local include: resolve relative to file dir or relative to src/
                            dir_path = os.path.dirname(fpath)
                            target1 = os.path.normpath(os.path.join(dir_path, inc_path))
                            target2 = os.path.normpath(os.path.join(src_dir, inc_path))
                            if not os.path.exists(target1) and not os.path.exists(target2):
                                errors.append(f'{fpath}:{line_idx}: File not found: {inc_path}')

print(f'Total includes verified: {total_includes}')
if errors:
    print(f'Errors found ({len(errors)}):')
    for e in errors:
        print('  ' + e)
    sys.exit(1)
else:
    print('ALL includes resolved cleanly and syntax is valid!')
