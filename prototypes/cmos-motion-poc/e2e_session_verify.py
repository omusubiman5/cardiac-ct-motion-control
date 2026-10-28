"""End-to-end check: SlicerSessionClient against the real Slicer
command server (start_server_session.py must be running).

Exercises the full protocol path a hand-driven session uses:
hello -> arm -> aim -> stamp -> move/rotate/tilt/reverse/reset ->
commit -> query_result -> menu -> disarm. Prints a JSON result.
Not for clinical use.
"""
import ctypes
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from session_client import SlicerSessionClient  # noqa: E402


def focus_slicer_window() -> bool:
    """Bring the running Slicer main window to the foreground so the
    server-side foreground gate (SR-006) accepts commands. Returns
    False when no Slicer window can be found (e.g. headless runs —
    the gate is satisfied there anyway)."""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    found = []

    enum_proc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
    )

    def _callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        # read the process image name; skip on any failure
        handle = kernel32.OpenProcess(0x1000, False, pid.value)  # QUERY_LIMITED_INFORMATION
        if handle:
            try:
                buf = ctypes.create_unicode_buffer(512)
                size = ctypes.c_ulong(512)
                if kernel32.QueryFullProcessImageNameW(
                    handle, 0, buf, ctypes.byref(size)
                ):
                    if "SlicerApp" in buf.value:
                        found.append(hwnd)
            finally:
                kernel32.CloseHandle(handle)
        return True

    user32.EnumWindows(enum_proc(_callback), 0)
    if not found:
        return False
    hwnd = found[0]
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    # Windows restricts SetForegroundWindow to foreground processes;
    # attaching our input queue to the foreground thread is the
    # standard way a verification tool takes focus deliberately.
    fg = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(fg, None)
    our_thread = kernel32.GetCurrentThreadId()
    if fg_thread and fg_thread != our_thread:
        user32.AttachThreadInput(fg_thread, our_thread, True)
    try:
        ok = bool(user32.SetForegroundWindow(hwnd))
        user32.BringWindowToTop(hwnd)
        user32.SetActiveWindow(hwnd)
    finally:
        if fg_thread and fg_thread != our_thread:
            user32.AttachThreadInput(fg_thread, our_thread, False)
    return ok


def main() -> int:
    result = {}
    result["slicer_foreground"] = focus_slicer_window()
    client = SlicerSessionClient(port=18944, timeout=3.0)
    try:
        hello = client.connect()
    except OSError as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 1
    result["hello"] = hello.get("ok")
    result["session"] = bool(hello.get("session"))

    result["arm"] = client.send("arm").get("ok")
    result["status"] = client.send("status").get("ok")

    # H-08 style: declare the next commit out-of-plan, then pick the
    # reason from the registered candidates through the menu
    result["out_of_plan"] = client.send("set_out_of_plan").get("ok")
    opened = client.send("menu_open")
    items = (opened.get("menu") or {}).get("items") or []
    result["menu_reason_items"] = any(
        i.startswith("reason:") for i in items
    )
    if "reason:operator" in items:
        for _ in range(items.index("reason:operator")):
            client.send("menu_next")
        result["menu_reason_confirm"] = client.send(
            "menu_confirm").get("ok")
    else:
        client.send("menu_close")

    # aim/stamp require aim mode (mode gate is part of the contract)
    result["select_mode_aim"] = client.send(
        "select_mode", {"mode": "aim"}
    ).get("ok")
    # aim at view center; whether it hits the surface depends on the
    # current camera, so record validity either way
    aim = client.send("aim", {"nx": 0.5, "ny": 0.5})
    result["aim_response_ok"] = aim.get("ok")
    result["aim_valid"] = (aim.get("result") or {}).get("valid")

    if result["aim_valid"]:
        stamp = client.send("stamp")
        result["stamp"] = stamp.get("ok")
        result["draft_id"] = stamp.get("draft_id")

        # each edit command is gated to its own mode (plan §共通契約)
        result["select_mode_move"] = client.send(
            "select_mode", {"mode": "move"}
        ).get("ok")
        result["move_draft"] = client.send(
            "move_draft", {"nx": 0.52, "ny": 0.5}
        ).get("ok")
        result["select_mode_rotate"] = client.send(
            "select_mode", {"mode": "rotate"}
        ).get("ok")
        result["rotate_opening"] = client.send(
            "rotate_opening", {"delta_deg": 15.0}
        ).get("ok")
        result["select_mode_tilt"] = client.send(
            "select_mode", {"mode": "tilt"}
        ).get("ok")
        result["tilt"] = client.send(
            "tilt", {"delta_deg": 10.0}
        ).get("ok")
        result["reverse"] = client.send("reverse").get("ok")
        result["reset_dir"] = client.send("reset_dir").get("ok")

        commit = client.send("commit")
        result["commit"] = commit.get("ok")
        result["event_id"] = commit.get("event_id")
        # a second commit with a NEW request id on the already-committed
        # draft is rejected; the ledger gains no second event (SR-010)
        dup = client.send("commit")
        result["dup_commit_rejected"] = not dup.get("ok")
        # query_result: read-only lookup of a stored response; an
        # unknown req id is rejected
        result["query_result"] = client.send(
            "query_result", {"req": "nope-unknown"}
        )
        result["query_unknown_rejected"] = not result[
            "query_result"
        ].get("ok")
        known = client.send("query_result", {"req": "req-000004"})
        result["query_known_ok"] = known.get("ok")
    else:
        result["stamp_skipped"] = "aim not on surface"

    # reset_view restores the registered baseline camera pose
    result["reset_view"] = client.send("reset_view").get("ok")

    # plan revision management (FR-034): create -> revise -> save
    created = client.send("create_plan", {
        "plan_id": "e2e-plan",
        "items": [{"event_id": "p1"}, {"event_id": "p2"}],
    })
    result["create_plan"] = created.get("ok")
    result["begin_revision"] = client.send(
        "begin_plan_revision", {"plan_id": "e2e-plan"}
    ).get("ok")
    result["edit_item"] = client.send("edit_plan_item", {
        "plan_id": "e2e-plan", "item_id": "p2",
        "patch": {"label": "moved"},
    }).get("ok")
    saved = client.send(
        "save_plan_revision", {"plan_id": "e2e-plan"}
    )
    result["save_revision"] = saved.get("ok")
    result["diff_changed"] = (
        (saved.get("result") or {}).get("diff") or {}
    ).get("changed") == ["p2"]

    # the on-screen menu exposes plan revision items too (docs/23)
    opened = client.send("menu_open")
    items = (opened.get("menu") or {}).get("items") or []
    result["menu_plan_rev_begin"] = "plan_rev_begin" in items
    if "plan_rev_begin" in items:
        for _ in range(items.index("plan_rev_begin")):
            client.send("menu_next")
        result["menu_rev_begin_confirm"] = client.send(
            "menu_confirm").get("ok")
        opened = client.send("menu_open")
        items = (opened.get("menu") or {}).get("items") or []
        result["menu_plan_rev_save"] = "plan_rev_save" in items
        result["menu_reason_revision"] = any(
            i.startswith("reason:") for i in items
        )
        result["cancel_plan_revision"] = client.send(
            "cancel_plan_revision").get("ok")
    client.send("menu_close")

    # audit commands
    result["select_reason"] = client.send(
        "select_reason", {"reason": "operator"}
    ).get("ok")
    if result.get("event_id"):
        result["revoke_event"] = client.send(
            "revoke_event",
            {"event_id": result["event_id"], "reason": "test"},
        ).get("ok")
        result["confirm_audit"] = client.send(
            "confirm_audit", {"event_id": result["event_id"]}
        ).get("ok")

    # review-mode selection feeds the menu's revoke/audit items
    result["select_mode_review"] = client.send(
        "select_mode", {"mode": "review"}).get("ok")
    sel = client.send("select_event", {"nx": 0.5, "ny": 0.5})
    result["select_event"] = sel.get("ok")
    if sel.get("ok"):
        opened = client.send("menu_open")
        items = (opened.get("menu") or {}).get("items") or []
        result["menu_revoke_selected"] = "revoke_selected" in items
        result["menu_audit_confirm_item"] = "audit_confirm" in items
        client.send("menu_close")

    # menu flow
    opened = client.send("menu_open")
    result["menu_open"] = opened.get("ok")
    result["menu_items"] = (opened.get("menu") or {}).get("items")
    result["menu_next"] = client.send("menu_next").get("ok")
    result["menu_close"] = client.send("menu_close").get("ok")

    # invalid command must be inert
    bogus = client.send("shell", {"x": 1})
    result["bogus_rejected"] = not bogus.get("ok")

    result["disarm"] = client.send("disarm").get("ok")
    client.close()
    result["ok"] = all(
        v is not False
        for k, v in result.items()
        if k not in ("menu_items", "stamp_skipped", "session",
                     "draft_id", "event_id", "aim_valid",
                     "query_result", "slicer_foreground")
    )
    text = json.dumps(result, indent=2)
    print(text)
    out = (Path(__file__).resolve().parents[2]
           / "artifacts" / "cstamp" / "e2e_result.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
