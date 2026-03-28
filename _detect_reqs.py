import os, ast, sys

root = '.'
modules = set()

for dirpath, dirnames, filenames in os.walk(root):
    # Skip hidden directories like .git, .venv, etc.
    dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in {'__pycache__', 'venv', '.venv'}]
    for fname in filenames:
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(dirpath, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                src = f.read()
        except Exception:
            continue
        try:
            tree = ast.parse(src, filename=fpath)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split('.')[0]
                    modules.add(top)
            elif isinstance(node, ast.ImportFrom):
                # Skip relative imports (local modules)
                if node.level and node.level > 0:
                    continue
                if node.module is None:
                    continue
                top = node.module.split('.')[0]
                modules.add(top)

# Built-in / stdlib detection
stdlib = set()
if hasattr(sys, 'stdlib_module_names'):
    stdlib = set(sys.stdlib_module_names)
else:
    # Fallback minimal stdlib set
    stdlib.update([
        'os','sys','re','math','json','datetime','asyncio','logging','traceback','subprocess','pathlib','typing','itertools','functools','collections','threading','time','random','http','unittest','sqlite3'
    ])

# Also treat some always-builtins as stdlib
stdlib.update({'builtins', 'types', 'enum'})

# Detect local packages/modules
local_modules = set()
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in {'__pycache__', 'venv', '.venv'}]
    rel = os.path.relpath(dirpath, root)
    pkg_name = rel.replace(os.sep, '.') if rel != '.' else None
    if pkg_name and '__init__.py' in filenames:
        local_modules.add(pkg_name.split('.')[0])
    for fname in filenames:
        if fname.endswith('.py'):
            mod_name = os.path.splitext(fname)[0]
            local_modules.add(mod_name)

third_party = sorted(m for m in modules if m not in stdlib and m not in local_modules and not m.startswith('_'))

for m in third_party:
    print(m)
