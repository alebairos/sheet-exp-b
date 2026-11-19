"""Discover function packages under src/functions without a shared hand-edited table."""
from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


def discover_functions() -> dict[str, ModuleType]:
    """Import each immediate subpackage of src.functions and return {name: module}."""
    package = importlib.import_module("src.functions")
    found: dict[str, ModuleType] = {}
    for mod in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if not mod.ispkg:
            continue
        short = mod.name.rsplit(".", 1)[-1]
        if short.startswith("_") or short == "registry":
            continue
        found[short] = importlib.import_module(mod.name)
    return found
