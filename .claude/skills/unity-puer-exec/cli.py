#!/usr/bin/env python3
import importlib.util
from pathlib import Path


def _load_product_module():
    module_path = Path(__file__).resolve().parents[3] / "cli" / "python" / "direct_exec_client.py"
    spec = importlib.util.spec_from_file_location("unity_puer_exec_product_direct_exec_client", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MODULE = _load_product_module()

for _name in dir(_MODULE):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_MODULE, _name)
