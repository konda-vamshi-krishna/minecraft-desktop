"""
Audit Script: Check header vs implementation symbol signature consistency.
"""
import re
import os

PROJECT_ROOT = r"g:\minecraft_desktop"

def extract_signatures(h_file):
    with open(h_file, "r", encoding="utf-8") as f:
        content = f.read()
    # Find all function prototypes
    # e.g. void Foo_Bar(int a, float b);
    matches = re.findall(r'^[a-zA-Z0-9_* ]+\s+([a-zA-Z0-9_]+)\s*\([^;)]*\)\s*;', content, re.MULTILINE)
    return set(matches)

def extract_definitions(c_file):
    with open(c_file, "r", encoding="utf-8") as f:
        content = f.read()
    # Find function definitions
    matches = re.findall(r'^[a-zA-Z0-9_* ]+\s+([a-zA-Z0-9_]+)\s*\([^;)]*\)\s*\{', content, re.MULTILINE)
    return set(matches)

def check_linkage():
    print("Checking Platform linkage...")
    plat_h = os.path.join(PROJECT_ROOT, "src", "platform", "platform.h")
    plat_c = os.path.join(PROJECT_ROOT, "src", "platform", "platform_desktop.c")
    h_funcs = extract_signatures(plat_h)
    c_funcs = extract_definitions(plat_c)
    
    missing = h_funcs - c_funcs
    print(f"  platform.h declared {len(h_funcs)} functions.")
    if missing:
        print(f"  ERROR: Missing in platform_desktop.c: {missing}")
    else:
        print("  SUCCESS: All platform functions implemented.")

    print("\nChecking Runtime linkage...")
    run_h = os.path.join(PROJECT_ROOT, "src", "core", "runtime.h")
    run_c = os.path.join(PROJECT_ROOT, "src", "core", "runtime.c")
    rh_funcs = extract_signatures(run_h)
    rc_funcs = extract_definitions(run_c)
    
    rmissing = rh_funcs - rc_funcs
    print(f"  runtime.h declared {len(rh_funcs)} functions.")
    if rmissing:
        print(f"  ERROR: Missing in runtime.c: {rmissing}")
    else:
        print("  SUCCESS: All runtime functions implemented.")

if __name__ == "__main__":
    check_linkage()
