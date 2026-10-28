"""Enumerate 3D Slicer menus and report entries that still contain only ASCII text."""

import json
import re

import slicer


def normalized(text):
    return text.replace("&", "").replace("...", "").strip()


def is_ascii_only_label(text):
    label = normalized(text)
    return bool(re.search(r"[A-Za-z]", label)) and all(ord(char) < 128 for char in label)


menus = []
untranslated = []


def visit_menu(menu, path):
    for action in menu.actions():
        text = action.text.strip()
        if not text or action.isSeparator():
            continue
        item_path = path + [text]
        record = {"path": " > ".join(item_path), "objectName": action.objectName}
        menus.append(record)
        if is_ascii_only_label(text):
            untranslated.append(record)
        submenu = action.menu()
        if submenu:
            visit_menu(submenu, item_path)


main_window = slicer.util.mainWindow()
for top_action in main_window.menuBar().actions():
    title = top_action.text.strip()
    top_menu = top_action.menu()
    if top_menu:
        visit_menu(top_menu, [title])

result = {
    "language": str(slicer.app.userSettings().value("language", "")),
    "menuEntryCount": len(menus),
    "asciiOnlyEntryCount": len(untranslated),
    "asciiOnlyEntries": untranslated,
}
print("SLICER_JAPANESE_MENU_AUDIT=" + json.dumps(result, ensure_ascii=False))
slicer.util.exit()
