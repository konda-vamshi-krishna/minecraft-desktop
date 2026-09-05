import os
import re
import sys

src_dir = r"g:/minecraft_desktop/src"
errors = []
warnings = []
all_includes = []
struct_defs = {}

for root, dirs, files in os.walk(src_dir):
    for f in files:
        if f.endswith(('.c', '.h')):
            filepath = os.path.join(root, f)
            rel_path = os.path.relpath(filepath, src_dir)
            with open(filepath, 'r', encoding='utf-8', errors='replace') as fp:
                lines = fp.readlines()
            
            brace_count = 0
            paren_count = 0
            bracket_count = 0
            
            for line_no, line in enumerate(lines, 1):
                # Strip comments for syntax checks
                line_clean = re.sub(r'//.*', '', line)
                
                # Check for malformed includes
                inc_match = re.match(r'^\s*#\s*include\s*(.*)', line_clean)
                if inc_match:
                    inc_target = inc_match.group(1).strip()
                    all_includes.append((rel_path, line_no, inc_target))
                    if not (inc_target.startswith('<') and inc_target.endswith('>')) and not (inc_target.startswith('"') and inc_target.endswith('"')):
                        errors.append(f"Malformed #include at {rel_path}:{line_no}: '{line.strip()}'")
                    else:
                        if inc_target.startswith('"') and inc_target.endswith('"'):
                            header_name = inc_target[1:-1]
                            if "proposed_" in header_name:
                                errors.append(f"Proposed header included at {rel_path}:{line_no}: {header_name}")
                            # Check resolution: relative to file or relative to src/
                            cand1 = os.path.normpath(os.path.join(root, header_name))
                            cand2 = os.path.normpath(os.path.join(src_dir, header_name))
                            if not (os.path.isfile(cand1) or os.path.isfile(cand2)):
                                errors.append(f"Unresolved local include at {rel_path}:{line_no}: {header_name} (neither {cand1} nor {cand2} exists)")
                
                # Check struct definitions
                struct_match = re.search(r'\btypedef\s+struct\s+([A-Za-z0-9_]+)\s*\{', line_clean)
                if struct_match:
                    sname = struct_match.group(1)
                    if sname not in struct_defs:
                        struct_defs[sname] = []
                    struct_defs[sname].append(f"{rel_path}:{line_no}")
                
                struct_match2 = re.search(r'^\s*struct\s+([A-Za-z0-9_]+)\s*\{', line_clean)
                if struct_match2:
                    sname = struct_match2.group(1)
                    if sname not in struct_defs:
                        struct_defs[sname] = []
                    struct_defs[sname].append(f"{rel_path}:{line_no}")

print(f"Total files checked in src/: {sum(len(files) for _, _, files in os.walk(src_dir))}")
print(f"Total #include directives checked: {len(all_includes)}")
print(f"Errors found: {len(errors)}")
for e in errors:
    print("  ERROR:", e)

print("\nStruct definitions found:")
for sname, locs in sorted(struct_defs.items()):
    if len(locs) > 1:
        print(f"  DUPLICATE STRUCT: {sname} defined at: {locs}")
    else:
        if "Raycast" in sname or "Hit" in sname:
            print(f"  {sname}: {locs}")

print(f"\nRaycastHit occurrences:")
for sname, locs in struct_defs.items():
    if sname == "RaycastHit":
        print(f"  RaycastHit definition count = {len(locs)} at {locs}")
