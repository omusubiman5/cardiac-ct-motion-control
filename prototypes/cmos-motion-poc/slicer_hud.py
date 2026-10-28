"""Read-only menu feedback visible over Slicer without taking keyboard focus.

Contains protocol state only: no camera pixels, landmarks or scene data.
The server remains the authority for every action and foreground gate.
"""
from __future__ import annotations

import ctypes
import os
import tkinter as tk
from ctypes import wintypes

from target_guard import Win32TargetApi
from hand_menu import MAIN, EDIT

LABELS = {
    "mode_view": "視点操作（パン・回転・ズーム）",
    "mode_aim": "C焼き印（照準・仮配置）",
    "mode_review": "既存Cの選択・訂正モード",
    "reset_view": "視点を戻す", "disarm": "操作受付を停止",
    "mode_move": "Cの位置を移動", "mode_rotate": "Cの開口方向を回転",
    "mode_tilt": "Cの傾きを調整", "commit": "Cを確定",
    "cancel_draft": "Cの配置を取り消す",
    "draft_resume": "仮Cの編集を再開",
    "layer_toggle": "計画／実績を切り替える",
    "load_plan": "計画を読み込む", "skip_plan": "予定をスキップ",
    "plan_create": "計画を作成", "plan_rev_begin": "計画を訂正",
    "plan_rev_save": "計画の訂正を保存", "plan_rev_cancel": "計画の訂正を取消",
    "out_of_plan": "計画外の記録", "load_session": "保存記録を読み込む",
    "revoke_selected": "選択記録の撤回", "audit_confirm": "監査確認",
}
SHAPES = {"thumb": "親指", "two": "2本指", "three": "3本指",
          "fist": "グー", "open_palm": "開いた手", "point": "人差し指",
          "pinch": "つまみ", "none": "手なし", "unknown": "不明"}


def menu_rows(items, index, opened):
    """Display every server entry in its original order, with a single cursor."""
    rows = []
    for i, item in enumerate(items):
        label = LABELS.get(item, "理由：" + item[7:] if item.startswith("reason:") else item)
        rows.append(("▶ " if opened and i == index % len(items) else "　 ") + label)
    if not items:
        rows.append("　 C焼き印（🤟でメニューを取得）")
    return rows


class SlicerHud:
    def __init__(self):
        self.api = Win32TargetApi()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Cardiac Hand Menu")
        self.root.overrideredirect(True)
        self.root.geometry("400x580+25+75")
        self.root.configure(bg="#122640", padx=12, pady=12)
        self.status = tk.Label(self.root, bg="#122640", fg="#69ff9f",
                               font=("Yu Gothic UI", 14, "bold"), anchor="w")
        self.status.pack(fill="x")
        self.heading = tk.Label(self.root, bg="#122640", fg="white",
                                font=("Yu Gothic UI", 18, "bold"), anchor="w")
        self.heading.pack(fill="x", pady=(8, 10))
        self.body = tk.Frame(self.root, bg="#122640")
        self.body.pack(fill="both", expand=True)
        self.guide = tk.Label(self.root, bg="#122640", fg="#dceaff",
                              font=("Yu Gothic UI", 11), justify="left", anchor="w",
                              wraplength=370)
        self.guide.pack(fill="x", pady=(12, 0))
        self.feedback = tk.Label(self.root, bg="#122640", fg="#ffce64",
                                 font=("Yu Gothic UI", 10), justify="left", anchor="w",
                                 wraplength=370)
        self.feedback.pack(fill="x", pady=(6, 0))
        self.size_button = tk.Button(self.root, text="⚙ C焼き印のサイズ設定（mm）", bg="#29425e",
                                     fg="white", font=("Yu Gothic UI", 11),
                                     command=self._show_size_settings)
        self.size_button.pack(fill="x", pady=(10, 0))
        self.current_ops = None
        self.row_signature = None
        self.root.update_idletasks()
        self.u32 = ctypes.WinDLL("user32", use_last_error=True)
        self.u32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        self.u32.GetAncestor.restype = wintypes.HWND
        self.hwnd = self.u32.GetAncestor(self.root.winfo_id(), 2)
        self.u32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        self.u32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        self.u32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        style = self.u32.GetWindowLongPtrW(self.hwnd, -20)
        # WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW: the panel never becomes the target.
        self.u32.SetWindowLongPtrW(self.hwnd, -20, style | 0x08000000 | 0x80)
        self.u32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                       ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self.u32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        self.visible = False
        self.previous_text = ""

    def update(self, ops):
        self.current_ops = ops
        hwnd = self.api.foreground_hwnd()
        image = self.api.image_path_of(self.api.process_id_of(hwnd)) if hwnd else ""
        visible = os.path.basename(image).casefold() == "slicerapp-real.exe"
        if visible != self.visible:
            if visible:
                self.root.deiconify()
                self.u32.SetWindowPos(self.hwnd, -1, 0, 0, 0, 0, 0x13)  # topmost, noactivate
                self.u32.ShowWindow(self.hwnd, 4)  # SW_SHOWNOACTIVATE
            else:
                self.root.withdraw()
            self.visible = visible
        state = ops.client.last_state
        if ops.panel_menu:
            self._render_panel(ops)
            self.root.update_idletasks()
            self.root.update()
            return
        mode = {"view": "視点", "aim": "C照準", "review": "C選択"}.get(state.get("mode"), state.get("mode", "不明"))
        lines = [f"ハンド操作：{'受付中' if ops.armed else '停止中'} ／ {mode}",
                 "認識：" + SHAPES.get(ops._shape.value, ops._shape.value)]
        if not ops.armed:
            lines += ["開始：開いた片手を1.5秒保持"]
        elif ops.menu_open and ops.menu_lines:
            lines += [f"メニュー：開　{ops.menu_index + 1} / {len(ops.menu_lines)}",
                      "親指上：前へ　親指下：次へ・末尾で戻る　グー：決定"]
        elif state.get("mode") == "aim" and not ops.draft:
            aim = "有効" if ops.aim_valid is True else "表面外" if ops.aim_valid is False else "未取得"
            lines += ["🤟：メニュー呼出し",
                      f"照準：{aim} ／ 仮C：なし",
                      "人差し指を動かす：表面に照準を合わせる",
                      "グー：Cを仮配置（照準が有効なとき）"]
        elif ops.draft:
            lines += ["🤟：メニュー呼出し",
                      "仮C：あり ／ 人差し指：位置 ／ つまみ：開口方向",
                      "3本指：方向を初期化 ／ グー：確定へ ／ 親指下：取消"]
        elif state.get("mode") == "view":
            lines += ["🤟：メニュー呼出し",
                      "開いた手：回転 ／ 人差し指：パン",
                      "つまみ：ズーム ／ 3本指：視点を初期化",
                      "親指上：C呼出"]
        else:
            lines += ["🤟：メニュー呼出し",
                      "親指上：C呼出 ／ 人差し指：指す"]
        if not ops.menu_open:
            lines += ["", "メニュー：閉（🤟で開く）"]
        lines += menu_rows(ops.menu_lines, ops.menu_index, ops.menu_open)
        reason = ops.last_response.get("reason")
        if reason:
            lines.append("拒否：" + reason)
        rendered = "\n".join(lines)
        if rendered != self.previous_text:
            self.guide.configure(text=rendered)
            height = min(self.root.winfo_screenheight() - 100, max(420, len(lines) * 26 + 25))
            self.root.geometry(f"460x{height}+25+75")
            self.previous_text = rendered
        self.root.update_idletasks()
        self.root.update()

    def _render_panel(self, ops):
        menu = ops.panel_menu
        opened = menu.opened and ops.armed
        entries = menu.entries if opened else EDIT if ops.draft else MAIN
        page = menu.page if opened else "edit" if ops.draft else "main"
        titles = {"main": "メニュー", "edit": "C焼き印｜編集メニュー",
                  "records": "計画・記録", "reasons": "理由の選択", "confirm": "C焼き印｜確定の確認"}
        state = ops.client.last_state
        self.status.configure(text=("● 受付中" if ops.armed else "● 停止中")
                              + ("　 仮Cあり" if ops.draft else "")
                              + "　" + state.get("layer", ""),
                              fg="#69ff9f" if ops.armed else "#ffce64")
        self.heading.configure(text=titles[page] + ("：開" if opened else "：閉"))
        signature = (tuple(entries), menu.index if opened else -1, ops.draft)
        if signature != self.row_signature:
            for child in self.body.winfo_children():
                child.destroy()
            start = (menu.index // 6) * 6 if opened and len(entries) > 6 else 0
            for i, entry in enumerate(entries[start:start + 6], start):
                selected = opened and i == menu.index
                disabled = ops.draft and entry.key in {"review", "records"}
                bg = "#008cbd" if selected else "#122640"
                card = tk.Frame(self.body, bg=bg, highlightthickness=2,
                                highlightbackground="#00e1ff" if selected else "#29425e")
                card.pack(fill="x", pady=3)
                title = ("▶  " if selected else "　 ") + entry.label
                tk.Label(card, text=title, bg=bg, fg="#8fa2b8" if disabled else "white",
                         font=("Yu Gothic UI", 13 if len(entries) > 7 else 16, "bold"),
                         anchor="w", padx=8, pady=5).pack(fill="x")
                detail = "仮Cの編集完了後に選択できます" if disabled else entry.detail
                if detail:
                    tk.Label(card, text=detail, bg=bg, fg="#dceaff",
                             font=("Yu Gothic UI", 10), anchor="w", padx=35).pack(fill="x", pady=(0, 5))
            self.row_signature = signature
        if not ops.armed:
            recognized = getattr(ops, "recognition_shape", ops._shape).value
            guide = ("認識：" + SHAPES.get(recognized, recognized)
                     + f"\n開始保持：{ops._arm_hold.elapsed_s:.1f} / {ops._arm_hold.hold_s:.1f} 秒"
                     + "\n" + getattr(ops, "recognition_detail", "")
                     + "\n開始：5本の指を開き、手のひらをカメラへ"
                     + "\n手形が変わると保持時間は0に戻ります")
        elif opened:
            guide = "親指上：前へ　親指下：次へ・末尾で戻る\nグー：決定"
            if len(entries) > 6:
                guide += f"\n項目 {menu.index + 1} / {len(entries)}（次へで一覧を送る）"
            if page == "confirm":
                guide += "\n手を一度下げ、再びグーで確定"
        elif ops.draft:
            guide = "🤟：メニュー呼出し\n人差し指：位置　つまみ：開口方向　3本指：方向を初期化\nグー：確定の確認へ　親指下：仮配置を取消"
        elif ops.mode == "aim":
            aim = "有効" if ops.aim_valid is True else "表面外" if ops.aim_valid is False else "未取得"
            guide = f"🤟：メニュー呼出し\n照準：{aim}　人差し指で照準を移動\nグー：Cを仮配置（有効表面上）"
        elif ops.mode == "review":
            guide = "🤟：メニュー呼出し\n人差し指：既存Cを指す\n選択・訂正はメニュー項目から"
        else:
            guide = "🤟：メニュー呼出し\n開いた手：回転　人差し指：パン\nつまみ：ズーム　3本指：視点を初期化\n親指上：C呼出"
        if ops.armed:
            guide = "認識：" + SHAPES.get(ops._shape.value, ops._shape.value) + "\n" + guide
        if not ops.client.connected:
            guide = "Slicerとの接続が切れています。\n" + guide
        self.guide.configure(text=guide)
        reason = menu.notice or ("拒否：" + str(ops.last_response["reason"])
                                 if ops.last_response.get("reason") else "")
        self.feedback.configure(text=reason)
        self.root.update_idletasks()
        needed = self.root.winfo_reqheight()
        self.root.geometry(f"400x{min(self.root.winfo_screenheight() - 100, max(440, needed))}+25+75")

    def close(self):
        self.root.destroy()

    def _show_size_settings(self):
        if self.current_ops is not None:
            self.current_ops._send("size_settings")
