import os
import ast
import re

tests_dir = r"g:/minecraft_desktop/tests"
total_test_methods = 0
empty_tests = []
dummy_assertions = []
mock_usages = []
file_summaries = {}

for root, dirs, files in os.walk(tests_dir):
    for f in files:
        if f.startswith("test_") and f.endswith(".py"):
            filepath = os.path.join(root, f)
            rel_path = os.path.relpath(filepath, tests_dir)
            with open(filepath, "r", encoding="utf-8") as fp:
                code = fp.read()
            
            # Check mock imports/usage
            if "mock" in code.lower():
                # Check whether it's unittest.mock or a mock class written for testing logic
                for line_no, line in enumerate(code.splitlines(), 1):
                    if re.search(r'\b(unittest\.mock|from unittest import mock|from mock import|MagicMock|patch\(|@patch)\b', line):
                        mock_usages.append((rel_path, line_no, line.strip()))

            # Parse AST
            try:
                tree = ast.parse(code, filename=filepath)
            except SyntaxError as e:
                print(f"Syntax error in {rel_path}: {e}")
                continue

            test_count_in_file = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    total_test_methods += 1
                    test_count_in_file += 1
                    # Check if body is just 'pass' or docstring + pass
                    body = node.body
                    real_stmts = [s for s in body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]
                    if len(real_stmts) == 0 or (len(real_stmts) == 1 and isinstance(real_stmts[0], ast.Pass)):
                        empty_tests.append((rel_path, node.name, node.lineno))
                    
                    # Check for assert True or self.assertTrue(True)
                    for stmt in ast.walk(node):
                        if isinstance(stmt, ast.Assert):
                            if isinstance(stmt.test, ast.Constant) and stmt.test.value is True:
                                dummy_assertions.append((rel_path, node.name, stmt.lineno, "assert True"))
                        elif isinstance(stmt, ast.Call):
                            if isinstance(stmt.func, ast.Attribute) and stmt.func.attr == "assertTrue":
                                if len(stmt.args) > 0 and isinstance(stmt.args[0], ast.Constant) and stmt.args[0].value is True:
                                    dummy_assertions.append((rel_path, node.name, stmt.lineno, "self.assertTrue(True)"))

            file_summaries[rel_path] = test_count_in_file

print(f"Total test files examined: {len(file_summaries)}")
print(f"Total test methods found: {total_test_methods}")
print(f"Empty tests (pass only): {len(empty_tests)}")
for item in empty_tests:
    print(f"  EMPTY TEST: {item}")

print(f"Dummy assertions (e.g. assertTrue(True)): {len(dummy_assertions)}")
for item in dummy_assertions:
    print(f"  DUMMY ASSERTION: {item}")

print(f"Unittest mock library usages: {len(mock_usages)}")
for item in mock_usages:
    print(f"  MOCK USAGE: {item}")

print("\nTest counts per file:")
for f, count in sorted(file_summaries.items()):
    print(f"  {f}: {count} tests")
