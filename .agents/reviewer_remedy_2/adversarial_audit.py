import os
import glob
import re

def audit_brackets():
    all_c_h = glob.glob('src/**/*', recursive=True)
    all_c_h = [f for f in all_c_h if os.path.isfile(f) and f.endswith(('.c', '.h'))]
    errors = 0

    for f in all_c_h:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            content = fp.read()
        cleaned = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        cleaned = re.sub(r'//.*', '', cleaned)
        cleaned = re.sub(r'"(\\.|[^"])*"', '""', cleaned)
        cleaned = re.sub(r"'(\\.|[^'])*'", "''", cleaned)
        
        stack = []
        pairs = {')': '(', '}': '{', ']': '['}
        for idx, ch in enumerate(cleaned):
            if ch in '({[':
                stack.append((ch, idx))
            elif ch in ')}]':
                if not stack:
                    print(f'Unbalanced closing {ch} in {f} at char {idx}')
                    errors += 1
                    break
                top, _ = stack.pop()
                if top != pairs[ch]:
                    print(f'Mismatched {top} and {ch} in {f} at char {idx}')
                    errors += 1
                    break
        else:
            if stack:
                print(f'Unbalanced open {stack[-1][0]} in {f}')
                errors += 1
    print(f'Bracket balance audit complete. Errors found: {errors}')

def audit_includes():
    all_c_h = glob.glob('src/**/*', recursive=True)
    all_c_h = [f for f in all_c_h if os.path.isfile(f) and f.endswith(('.c', '.h'))]
    std_headers = {
        'stdio.h', 'stdlib.h', 'stdint.h', 'stdbool.h', 'string.h', 'math.h',
        'time.h', 'stddef.h', 'assert.h', 'limits.h', 'float.h'
    }
    missing = 0
    for f in all_c_h:
        parent_dir = os.path.dirname(f)
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            for line_no, line in enumerate(fp, 1):
                s = line.strip()
                if s.startswith('#include'):
                    m = re.match(r'#include\s+["<]([^">]+)[">]', s)
                    if not m:
                        print(f'Malformed include in {f}:{line_no}: {s}')
                        missing += 1
                        continue
                    inc = m.group(1)
                    if inc in std_headers:
                        continue
                    # Check relative to file or relative to src/
                    target1 = os.path.normpath(os.path.join(parent_dir, inc))
                    target2 = os.path.normpath(os.path.join('src', inc))
                    if not (os.path.isfile(target1) or os.path.isfile(target2)):
                        print(f'Unresolved header in {f}:{line_no}: {inc}')
                        missing += 1
    print(f'Include resolution audit complete. Unresolved headers: {missing}')

if __name__ == '__main__':
    audit_brackets()
    audit_includes()
