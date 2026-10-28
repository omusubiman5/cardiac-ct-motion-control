"""Regression self-checks of actual menu methods with synthetic draft state.

Extract methods to avoid requiring Slicer/Qt; not a GUI or live-server test.
"""
import ast
from pathlib import Path
from types import SimpleNamespace


def menu_logic():
    source = Path(__file__).resolve().parents[1] / "CStampModule.py"
    module = ast.parse(source.read_text(encoding="utf-8"))
    cls = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == "CStampModuleLogic")
    names = {"_menu_items", "_menu_payload", "op_menu_next", "op_menu_prev", "op_menu_close"}
    methods = ast.Module(body=[n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
    namespace = {}
    exec(compile(methods, str(source), "exec"), namespace)
    logic = type("MenuUnderTest", (), {k: namespace[k] for k in names})()
    logic.controller = SimpleNamespace(frozen=False, draft=SimpleNamespace(revision=7))
    logic.display_contract = SimpleNamespace(displayed={"draft_id":"d7","rev":7,"hash":"rendered"})
    logic.has_draft = lambda: True
    logic._menu_open = True
    logic._menu_index = 0
    logic.notifications = 0
    def notify():
        logic.notifications += 1
    logic._notify_state = notify
    return logic


def test_draft_menu_uses_actual_revision_instead_of_boolean():
    logic = menu_logic()
    commit = next(item for item in logic._menu_items() if item["cmd"] == "commit")
    assert commit["params"] == {"draft_id":"d7","rev":7,"hash":"rendered"}


def test_menu_cursor_refreshes_display_and_close_reports_closed_state():
    logic = menu_logic()
    assert logic.op_menu_next({})["menu"]["index"] == 1
    assert logic.op_menu_prev({})["menu"]["index"] == 0
    assert logic.notifications == 2
    response = logic.op_menu_close({})
    assert response["ok"] and not response["menu"]["open"]
    assert logic.notifications == 3
