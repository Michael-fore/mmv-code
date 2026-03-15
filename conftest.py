"""Root conftest — handles mono-repo import aliasing for all tests."""

import importlib
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

for _dir_name, _mod_name in [
    ("mmv-data", "mmv_data"),
    ("mmv-underwriting", "mmv_underwriting"),
    ("mmv-agent", "mmv_agent"),
    ("mmv-reporting", "mmv_reporting"),
]:
    _pkg_path = REPO_ROOT / _dir_name
    _init = _pkg_path / "__init__.py"
    if _init.is_file() and _mod_name not in sys.modules:
        _spec = importlib.util.spec_from_file_location(
            _mod_name,
            str(_pkg_path / "__init__.py"),
            submodule_search_locations=[str(_pkg_path)],
        )
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules[_mod_name] = _mod
        _spec.loader.exec_module(_mod)
