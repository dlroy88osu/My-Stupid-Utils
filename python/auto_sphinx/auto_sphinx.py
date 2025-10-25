import importlib
import os
import webbrowser
from datetime import datetime
from pathlib import Path
from subprocess import check_call

# Install dependencies
imps = ['sphinx', 'sphinx-rtd-theme', 'pathspec']
for imp in imps:
    try:
        importlib.import_module(imp.replace('-', '_'))
    except Exception:
        check_call(['pip', 'install', imp])

from pathspec import PathSpec  # noqa: E402

# =============================================================================
# [ Configuration ]
# =============================================================================
gitignore_path = '.gitignore'
mapping_entry_point = 'path to where you want it to start mapping'
project_name = 'name of project'
author_name = 'your name'

# any extra dirs you don't care about mapping for the sake of docs
ignored_dirs = ['__pycache__', '.pytest_cache', '.git', '.vscode', '_tests']


# =============================================================================
# [ Init Sphinx ]
# =============================================================================
def check_init_sphinx() -> None:
    if not os.path.exists('docs') or not os.path.exists('docs/conf.py'):
        os.makedirs('docs', exist_ok=True)
        check_call([
            'sphinx-quickstart', '-q', '-p', project_name, '-a', author_name
        ], cwd='docs')

        config = f'''
import os
import sys
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../{mapping_entry_point}'))

project = '{project_name}'
copyright = '{datetime.now().strftime('%Y')}, {author_name}'
author = '{author_name}'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
'''
        with open('docs/conf.py', 'w') as f:
            f.write(config)


# =============================================================================
# [ Map Repository ]
# =============================================================================
def map_repo() -> dict:
    patterns = []
    if os.path.exists(gitignore_path):
        patterns = list(Path(gitignore_path).read_text().splitlines())

    patterns.extend(['.git/', '__pycache__/', '.pytest_cache/', '*.pyc'])
    ignored = PathSpec.from_lines('gitwildmatch', patterns)

    def build_tree(path: str) -> dict:
        tree = {}
        if not os.path.exists(path):
            return tree

        for entry in sorted(os.listdir(path)):
            if entry in ignored_dirs:
                continue
            if entry.startswith('.'):
                continue

            full_path = os.path.join(path, entry)
            rel_path = os.path.relpath(full_path, mapping_entry_point)

            if ignored.match_file(rel_path.replace(os.sep, '/')):
                continue

            if os.path.isdir(full_path):
                tree[entry] = build_tree(full_path)
            elif entry.endswith('.py'):
                tree.setdefault('__files__', []).append(entry[:-3])

        return tree

    root = os.path.basename(os.path.abspath(mapping_entry_point))
    return {root: build_tree(mapping_entry_point)}


# =============================================================================
# [ Update index.rst ]
# =============================================================================
def update_index(modules: list[str]) -> None:
    idx_path = 'docs/index.rst'

    if os.path.exists(idx_path):
        content = Path(idx_path).read_text()
        base = content.split('.. toctree::')[0].rstrip()
    else:
        msg = f"{project_name} Documentation"
        base = f'{msg}\n{"=" * len(msg)}\n\n'

    new_content = (base + '\n\n.. toctree::\n    :maxdepth: 2\n    '
                   ':caption: Contents:\n\n')
    for mod in modules:
        new_content += f'    {mod}\n'

    Path(idx_path).write_text(new_content)


# =============================================================================
# [ Create RST Files - WITH separate pages for each .py file ]
# =============================================================================
def create_rst_files(tree: dict, parent: str = '') -> list[str]:
    '''Create .rst files for packages AND individual Python files'''

    for f in os.listdir('docs'):
        if f.endswith('.rst'):
            os.remove(f'docs/{f}')

    modules = []

    for name, content in tree.items():
        if name == '__files__':
            continue

        module_path = f'{parent}.{name}' if parent else name
        modules.append(module_path)

        # Create package/module RST
        rst_path = f'docs/{module_path}.rst'
        title = module_path
        rst_content = f'{title}\n{"=" * len(title)}\n\n'

        # Document the package itself
        rst_content += (f'.. automodule:: {module_path}\n   :members:\n   '
                        ':undoc-members:\n   :show-inheritance:\n\n')

        # Get subdirectories and files
        subdirs = [k for k in content.keys()
                   if k != '__files__' and isinstance(content[k], dict)]
        files = content.get('__files__', [])

        # If there are subdirs or files, add them to toctree
        if subdirs or files:
            rst_content += '.. toctree::\n   :maxdepth: 1\n\n'

            # Add subdirectories
            for subdir in subdirs:
                rst_content += f'   {module_path}.{subdir}\n'

            # Add files as separate pages
            for file_mod in files:
                rst_content += f'   {module_path}.{file_mod}\n'

            rst_content += '\n'

        Path(rst_path).write_text(rst_content)

        # Create separate RST file for EACH Python file
        for file_mod in files:
            file_module_path = f'{module_path}.{file_mod}'
            file_rst_path = f'docs/{file_module_path}.rst'
            file_title = file_module_path

            file_rst_content = f'{file_title}\n{"=" * len(file_title)}\n\n'
            file_rst_content += (f'.. automodule:: {file_module_path}\n   '
                                 ':members:\n   :undoc-members:\n   '
                                 ':show-inheritance:\n')

            Path(file_rst_path).write_text(file_rst_content)
            modules.append(file_module_path)

        # Recurse into subdirectories
        for subdir in subdirs:
            modules.extend(create_rst_files(
                {subdir: content[subdir]}, module_path))

    return modules


# =============================================================================
# [ Main ]
# =============================================================================
if __name__ == '__main__':
    check_init_sphinx()

    tree = map_repo()
    root_name = list(tree.keys())[0]
    print(f"      Root: {root_name}")

    all_modules = create_rst_files(tree[root_name], parent=root_name)
    top_level = [m for m in all_modules if m.count('.') == 1]
    update_index(top_level)

    if os.name == 'nt':
        check_call(['.\\docs\\make.bat', 'html'], shell=True)
    else:
        check_call(['make', 'html'], cwd='docs')

    dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(dir, 'docs', '_build', 'html', 'index.html')
    webbrowser.open(path)

    msg = f"✓ DONE - Open in browser: {path}"

    print("\n" + "=" * (len(msg) + 2))
    print(msg)
    print("=" * (len(msg) + 2))
