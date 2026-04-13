import ast
import collections
import subprocess
import os
import re
import glob

print("=== 1. DUPLICATE ROUTE CHECK ===")
files_to_check = ['app/routes/student.py', 'app/routes/warden.py', 'app/routes/staff.py', 'app/routes/auth.py', 'app/routes/api.py', 'app/routes/admin.py']
for fpath in files_to_check:
    if os.path.exists(fpath):
        with open(fpath, encoding='utf-8') as f:
            tree = ast.parse(f.read())
        names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        dupes = [n for n, c in collections.Counter(names).items() if c > 1]
        if dupes:
            print(f"Duplicate functions in {fpath}: {dupes}")
        else:
            print(f"No duplicates in {fpath}")

print("\n=== 2. IMPORT CHECK ===")
res = subprocess.run([r'.\venv\Scripts\python.exe', '-c', "from app import create_app; app = create_app('development'); print('App import: OK')"], capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print(res.stderr)

print("\n=== 3. FLASK ROUTES CHECK ===")
res = subprocess.run([r'.\venv\Scripts\flask.exe', 'routes'], capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print(res.stderr)

print("\n=== 4. MISSING TEMPLATE CHECK ===")
templates_dir = 'app/templates'
existing = set()
for root, dirs, files in os.walk(templates_dir):
    for f in files:
        existing.add(os.path.relpath(os.path.join(root, f), templates_dir).replace('\\\\', '/').replace('\\', '/'))

route_files = glob.glob('app/routes/*.py')
missing = []
for rf in route_files:
    with open(rf, encoding='utf-8') as f:
        content = f.read()
    found = re.findall(r"render_template\(['\"]([^'\"]+)['\"]", content)
    for t in found:
        if t not in existing:
            missing.append((rf, t))
print("Missing templates:", missing if missing else "None")

print("\n=== 5. UNDEFINED URL_FOR CHECK ===")
files = glob.glob('app/routes/*.py') + glob.glob('app/templates/**/*.html', recursive=True)
endpoints = set()
for f in files:
    try:
        with open(f, encoding='utf-8') as fh:
            for m in re.finditer(r"url_for\(['\"]([^'\"]+)['\"]", fh.read()):
                endpoints.add(m.group(1))
    except Exception:
        pass
print('url_for calls found:', sorted(endpoints))

print("\n=== 6. PYTEST CHECK ===")
res = subprocess.run([r'.\venv\Scripts\python.exe', '-m', 'pytest', '-v'], capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print(res.stderr)

print("\n=== 7. MISSING MIGRATION CHECK ===")
res = subprocess.run([r'.\venv\Scripts\flask.exe', 'db', 'check'], capture_output=True, text=True)
if res.returncode != 0:
    print("Flask db check failed:")
    print(res.stdout)
    if res.stderr:
        print(res.stderr)
    res2 = subprocess.run([r'.\venv\Scripts\flask.exe', 'db', 'current'], capture_output=True, text=True)
    print("Flask db current output:")
    print(res2.stdout)
    if res2.stderr:
        print(res2.stderr)
else:
    print(res.stdout)
    if res.stderr:
        print(res.stderr)

print("\n=== 8. REQUIREMENTS CHECK ===")
res = subprocess.run([r'.\venv\Scripts\pip.exe', 'check'], capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print(res.stderr)

print("\n=== 9. PYTHON SYNTAX CHECK ===")
res = subprocess.run([r'.\venv\Scripts\python.exe', '-m', 'py_compile', 'app/routes/student.py', 'app/routes/warden.py', 'app/routes/staff.py', 'app/routes/auth.py', 'app/routes/api.py', 'app/routes/admin.py', 'app/__init__.py', 'app/models.py', 'config.py'], capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print(res.stderr)
