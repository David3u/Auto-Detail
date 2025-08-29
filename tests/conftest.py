"""Pytest configuration and stubs for auto_detail tests.

Provides stub modules for click, colorama, InquirerPy, and backend so tests can
run without external dependencies. Also exposes a fixture to load a fresh
instance of auto_detail/auto_detail.py for each test.
"""

import sys
import types
import importlib.util
import uuid
from pathlib import Path
import pytest  # pylint: disable=import-error


class _StubClick(types.ModuleType):
    def command(self, *_args, **_kwargs):
        """Stub decorator emulating click.command; returns function unchanged."""
        def decorator(func):
            """No-op decorator wrapper."""
            return func

        return decorator

    def option(self, *_args, **_kwargs):
        """Stub decorator emulating click.option; returns function unchanged."""
        def decorator(func):
            """No-op decorator wrapper."""
            return func

        return decorator


def _ensure_stub_modules():
    # click
    if "click" not in sys.modules:
        sys.modules["click"] = _StubClick("click")

    # colorama
    if "colorama" not in sys.modules:
        colorama = types.ModuleType("colorama")

        class Fore:  # pylint: disable=too-few-public-methods
            """Stub color constants used by tests."""
            GREEN = ""
            WHITE = ""
            YELLOW = ""

        class Style:  # pylint: disable=too-few-public-methods
            """Stub style constants."""
            RESET_ALL = ""

        def init(*_args, **_kwargs):
            """No-op colorama.init stub."""
            return None

        colorama.Fore = Fore
        colorama.Style = Style
        colorama.init = init
        sys.modules["colorama"] = colorama

    # InquirerPy.inquirer
    if "InquirerPy" not in sys.modules:
        inquirer_module = types.ModuleType("InquirerPy")
        inquirer_ns = types.SimpleNamespace()

        def _unconfigured(*_args, **_kwargs):
            """Default stub; tests should patch confirm/select before use."""
            raise RuntimeError("Inquirer stub not configured for this test")

        inquirer_ns.confirm = _unconfigured
        inquirer_ns.select = _unconfigured
        inquirer_module.inquirer = inquirer_ns
        sys.modules["InquirerPy"] = inquirer_module

    # backend
    if "backend" not in sys.modules:
        backend = types.ModuleType("backend")
        backend.list_details = lambda: None
        backend.clear_details = lambda: None
        backend.get_diff = lambda: ""
        backend.generate_pr_details = lambda diff, reasons: []
        backend.write_note = lambda description, summary, type_: "notes/file.yaml"
        backend.edit_detail = lambda diff, detail, pr_reasons, edit: detail
        sys.modules["backend"] = backend


def load_auto_detail_module():
    """Load auto_detail/auto_detail.py as a fresh module instance with stubs in place."""
    _ensure_stub_modules()
    module_name = f"auto_detail_under_test_{uuid.uuid4().hex}"
    auto_detail_path = Path(__file__).resolve().parents[1] / "auto_detail.py"
    spec = importlib.util.spec_from_file_location(module_name, str(auto_detail_path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def load_auto_detail():
    """Yield a freshly loaded auto_detail module with stubs configured."""
    return load_auto_detail_module()
