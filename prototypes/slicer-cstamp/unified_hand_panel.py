"""Slicer-owned fixed docks; memory-only optional camera and guarded UI requests."""
import base64
import importlib.util
from pathlib import Path
import time
import uuid
import math
import qt
import slicer


# --- concept palette (docs/images UI concept 2026-10-13) -----------------
BG = '#0a1826'
CARD = '#0f2438'
CARD2 = '#122c44'
BORDER = '#21405c'
ACCENT = '#2fd6e4'
ACCENT_BG = 'rgba(47,214,228,0.13)'
TEXT = '#e8f2fc'
MUTED = '#8ba5bd'
AMBER = '#f2b33d'
GREEN = '#35d17c'
RED = '#e0534f'

PANEL_STYLE = (
    'QWidget{background:%s;color:%s;font-size:13px}'
    'QLabel{background:transparent}'
    'QFrame#card{background:%s;border:1px solid %s;border-radius:8px}'
    'QPushButton{background:%s;border:1px solid %s;border-radius:6px;padding:6px 10px;color:%s}'
    'QPushButton:hover{border-color:%s}'
    'QPushButton:disabled{color:#5d7284;border-color:#1a3049}'
    'QPushButton:checked{background:%s;border-color:%s;color:#06222a}'
    'QPushButton#primary{background:#19c8d8;border:none;color:#06222a;font-weight:bold;font-size:14px;padding:10px}'
    'QPushButton#primary:disabled{background:#1a4b55;color:#48707c}'
    'QListWidget{background:%s;border:1px solid %s;border-radius:8px;outline:none}'
    'QListWidget::item{padding:9px 10px;margin:2px 4px;border:1px solid transparent;border-radius:6px}'
    'QListWidget::item:selected{background:%s;border:1px solid %s;color:%s}'
    'QProgressBar{border:1px solid %s;border-radius:4px;text-align:center;background:%s;height:14px}'
    'QProgressBar::chunk{background:%s;border-radius:3px}'
    'QScrollArea{background:%s;border:none}'
    'QTabWidget::pane{border:1px solid %s;border-radius:6px;top:-1px}'
    'QTabBar::tab{background:%s;color:%s;padding:7px 14px;border:1px solid %s;border-bottom:none;'
    'border-top-left-radius:6px;border-top-right-radius:6px}'
    'QTabBar::tab:selected{background:%s;color:%s;border-color:%s}'
    'QLineEdit,QComboBox,QDoubleSpinBox{background:%s;border:1px solid %s;border-radius:4px;padding:4px;color:%s}'
    'QCheckBox{color:%s}'
    % (BG, TEXT, CARD, BORDER, CARD2, BORDER, TEXT, ACCENT, ACCENT, ACCENT,
       '#0d2033', BORDER, ACCENT_BG, ACCENT, TEXT,
       BORDER, '#0d2033', ACCENT, BG,
       BORDER, '#0d2033', MUTED, BORDER, CARD2, TEXT, ACCENT,
       '#0d2033', BORDER, TEXT, TEXT)
)


def bridge_module():
    path = Path(__file__).resolve().parents[1] / 'cmos-motion-poc/ui_bridge.py'
    spec = importlib.util.spec_from_file_location('cardiac_ui_memory', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _icon(name, color='#9db4c8', size=18):
    """Small monochrome glyphs drawn with QPainter (no emoji fonts)."""
    pixmap = qt.QPixmap(size, size)
    pixmap.fill(qt.QColor(0, 0, 0, 0))
    painter = qt.QPainter(pixmap)
    painter.setRenderHint(qt.QPainter.Antialiasing)
    pen = qt.QPen(qt.QColor(color))
    pen.setWidthF(1.6)
    painter.setPen(pen)
    painter.setBrush(qt.QBrush(qt.QColor(0, 0, 0, 0)))
    m = size / 18.0
    if name == 'eye':
        painter.drawEllipse(qt.QRectF(1.5 * m, 5 * m, 15 * m, 8 * m))
        painter.setBrush(qt.QBrush(qt.QColor(color)))
        painter.drawEllipse(qt.QRectF(7 * m, 7 * m, 4 * m, 4 * m))
    elif name == 'c':
        painter.drawArc(qt.QRectF(2 * m, 2 * m, 14 * m, 14 * m), 55 * 16, 250 * 16)
    elif name == 'cursor':
        path = qt.QPainterPath()
        path.moveTo(4 * m, 2 * m)
        path.lineTo(15 * m, 9 * m)
        path.lineTo(9.5 * m, 10.5 * m)
        path.lineTo(12 * m, 16 * m)
        path.lineTo(9.5 * m, 17 * m)
        path.lineTo(7 * m, 11.5 * m)
        path.lineTo(4 * m, 14 * m)
        path.closeSubpath()
        painter.drawPath(path)
    elif name == 'doc':
        painter.drawRoundedRect(qt.QRectF(4 * m, 2 * m, 10 * m, 14 * m), 1.5 * m, 1.5 * m)
        painter.drawLine(qt.QPointF(6.5 * m, 6 * m), qt.QPointF(11.5 * m, 6 * m))
        painter.drawLine(qt.QPointF(6.5 * m, 9 * m), qt.QPointF(11.5 * m, 9 * m))
        painter.drawLine(qt.QPointF(6.5 * m, 12 * m), qt.QPointF(10 * m, 12 * m))
    elif name == 'hand':
        painter.drawRoundedRect(qt.QRectF(4.5 * m, 8 * m, 9 * m, 8 * m), 3 * m, 3 * m)
        for i, h in enumerate((5, 2.5, 1.5, 3)):
            painter.drawRoundedRect(
                qt.QRectF((4.5 + i * 2.4) * m, h * m, 2.1 * m, 7 * m), 1 * m, 1 * m)
    elif name == 'check':
        path = qt.QPainterPath()
        path.moveTo(3 * m, 9.5 * m)
        path.lineTo(7.5 * m, 14 * m)
        path.lineTo(15 * m, 4 * m)
        painter.drawPath(path)
    elif name == 'x':
        painter.drawLine(qt.QPointF(4 * m, 4 * m), qt.QPointF(14 * m, 14 * m))
        painter.drawLine(qt.QPointF(14 * m, 4 * m), qt.QPointF(4 * m, 14 * m))
    elif name == 'rotate':
        painter.drawArc(qt.QRectF(2.5 * m, 3 * m, 13 * m, 13 * m), 20 * 16, 270 * 16)
        painter.drawLine(qt.QPointF(15.5 * m, 6 * m), qt.QPointF(15.5 * m, 2 * m))
        painter.drawLine(qt.QPointF(15.5 * m, 2 * m), qt.QPointF(11.8 * m, 3.5 * m))
    elif name == 'undo':
        painter.drawArc(qt.QRectF(2.5 * m, 3 * m, 13 * m, 13 * m), 160 * 16, 270 * 16)
        painter.drawLine(qt.QPointF(2.5 * m, 6 * m), qt.QPointF(2.5 * m, 2 * m))
        painter.drawLine(qt.QPointF(2.5 * m, 2 * m), qt.QPointF(6.2 * m, 3.5 * m))
    elif name == 'tilt':
        painter.drawLine(qt.QPointF(1.5 * m, 15 * m), qt.QPointF(16.5 * m, 15 * m))
        painter.drawLine(qt.QPointF(3 * m, 11.5 * m), qt.QPointF(13.5 * m, 5.5 * m))
    elif name == 'swap':
        painter.drawLine(qt.QPointF(2.5 * m, 6 * m), qt.QPointF(15.5 * m, 6 * m))
        painter.drawLine(qt.QPointF(12.5 * m, 3.5 * m), qt.QPointF(15.5 * m, 6 * m))
        painter.drawLine(qt.QPointF(12.5 * m, 8.5 * m), qt.QPointF(15.5 * m, 6 * m))
        painter.drawLine(qt.QPointF(2.5 * m, 12 * m), qt.QPointF(15.5 * m, 12 * m))
        painter.drawLine(qt.QPointF(5.5 * m, 9.5 * m), qt.QPointF(2.5 * m, 12 * m))
        painter.drawLine(qt.QPointF(5.5 * m, 14.5 * m), qt.QPointF(2.5 * m, 12 * m))
    elif name == 'cross':
        painter.drawEllipse(qt.QRectF(4 * m, 4 * m, 10 * m, 10 * m))
        painter.drawLine(qt.QPointF(9 * m, 1 * m), qt.QPointF(9 * m, 5 * m))
        painter.drawLine(qt.QPointF(9 * m, 13 * m), qt.QPointF(9 * m, 17 * m))
        painter.drawLine(qt.QPointF(1 * m, 9 * m), qt.QPointF(5 * m, 9 * m))
        painter.drawLine(qt.QPointF(13 * m, 9 * m), qt.QPointF(17 * m, 9 * m))
    elif name == 'stop':
        painter.setBrush(qt.QBrush(qt.QColor(color)))
        painter.drawRoundedRect(qt.QRectF(4 * m, 4 * m, 10 * m, 10 * m), 2 * m, 2 * m)
    elif name == 'play':
        path = qt.QPainterPath()
        path.moveTo(5 * m, 3 * m)
        path.lineTo(15 * m, 9 * m)
        path.lineTo(5 * m, 15 * m)
        path.closeSubpath()
        painter.setBrush(qt.QBrush(qt.QColor(color)))
        painter.drawPath(path)
    elif name == 'back':
        painter.drawLine(qt.QPointF(15 * m, 9 * m), qt.QPointF(4 * m, 9 * m))
        painter.drawLine(qt.QPointF(8 * m, 5 * m), qt.QPointF(4 * m, 9 * m))
        painter.drawLine(qt.QPointF(8 * m, 13 * m), qt.QPointF(4 * m, 9 * m))
    elif name == 'camera':
        painter.drawRoundedRect(qt.QRectF(2 * m, 5 * m, 14 * m, 10 * m), 2 * m, 2 * m)
        painter.drawEllipse(qt.QRectF(6.5 * m, 7.5 * m, 5 * m, 5 * m))
        painter.drawLine(qt.QPointF(5 * m, 5 * m), qt.QPointF(6.5 * m, 2.5 * m))
        painter.drawLine(qt.QPointF(6.5 * m, 2.5 * m), qt.QPointF(11.5 * m, 2.5 * m))
        painter.drawLine(qt.QPointF(11.5 * m, 2.5 * m), qt.QPointF(13 * m, 5 * m))
    painter.end()
    return qt.QIcon(pixmap)


_MENU_ICONS = {
    'view': 'eye', 'c': 'c', 'review': 'cursor', 'records': 'doc',
    'stop': 'stop', 'disarm': 'stop', 'move': 'cross', 'rotate': 'rotate',
    'tilt': 'tilt', 'reverse': 'swap', 'reset_dir': 'undo', 'confirm': 'check',
    'cancel': 'x', 'resume_draft': 'play', 'main': 'back', 'edit': 'back',
    'commit': 'check', 'layer': 'swap', 'reset_view': 'eye',
    'revoke_event': 'x', 'confirm_audit': 'check',
    'cancel_plan_revision': 'x', 'save_plan_revision': 'check',
    'edit_plan_item': 'cross', 'delete_plan_item': 'x',
    'add_plan_item': 'cross', 'move_plan_item': 'play', 'reorder_plan': 'play',
    'out_of_plan': 'doc', 'skip_plan': 'play', 'load_plan': 'doc',
    'load_session': 'doc', 'save_session': 'doc', 'create_plan': 'doc',
    'query_result': 'doc', 'reasons': 'doc', 'plans': 'doc',
    'plan_versions': 'doc', 'creators': 'doc', 'storages': 'doc',
    'plan_items': 'doc', 'begin_plan_revision': 'doc',
}
_NAV_KEYS = {'view', 'c', 'review', 'records', 'reasons', 'plans',
             'plan_versions', 'creators', 'storages', 'plan_items',
             'confirm', 'edit', 'main'}


def _fixed_dock(name):
    dock = qt.QDockWidget(name, slicer.util.mainWindow())
    dock.setObjectName(name)
    dock.setFeatures(qt.QDockWidget.NoDockWidgetFeatures)
    dock.setAllowedAreas(qt.Qt.LeftDockWidgetArea | qt.Qt.RightDockWidgetArea)
    dock.setTitleBarWidget(qt.QWidget(dock))
    return dock


def _set_chip(label, text, color):
    label.setText(text)
    label.setStyleSheet(
        'color:%s;border:1px solid %s;border-radius:10px;padding:2px 12px;font-size:12px'
        % (color, BORDER))


def _chip(text, color):
    label = qt.QLabel()
    _set_chip(label, text, color)
    return label


class TopStatusBar:
    """Concept top strip: product title, live status chips, demo badge."""

    def __init__(self):
        self.bar = qt.QToolBar('CardiacStatusBar', slicer.util.mainWindow())
        self.bar.setObjectName('CardiacStatusBar')
        self.bar.setMovable(False)
        self.bar.setFloatable(False)
        self.bar.setStyleSheet(
            'QToolBar{background:#0c1f33;border:none;border-bottom:1px solid %s;spacing:14px;padding:4px 10px}'
            % BORDER)
        title = qt.QLabel('CARDIAC MOTION CONTROL')
        title.setStyleSheet('color:%s;font-weight:bold;font-size:14px;letter-spacing:1px' % TEXT)
        self.bar.addWidget(title)
        sub = qt.QLabel('|  3D Slicer')
        sub.setStyleSheet('color:%s;font-size:12px' % MUTED)
        self.bar.addWidget(sub)
        self.bar.addSeparator()
        self.chip_state = _chip('● 停止中', AMBER)
        self.chip_link = _chip('● 認識未接続', MUTED)
        self.chip_owner = _chip('入力：ハンド', ACCENT)
        self.bar.addWidget(self.chip_state)
        self.bar.addWidget(self.chip_link)
        self.bar.addWidget(self.chip_owner)
        spacer = qt.QWidget()
        spacer.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Preferred)
        self.bar.addWidget(spacer)
        badge = qt.QLabel('非臨床デモ')
        badge.setStyleSheet('color:%s;border:1px solid %s;border-radius:4px;'
                            'padding:2px 10px;font-size:12px' % (AMBER, AMBER))
        self.bar.addWidget(badge)
        slicer.util.mainWindow().addToolBar(qt.Qt.TopToolBarArea, self.bar)

    def update(self, value, logic):
        fresh = bool(value and 0 <= time.time() - value.get('ts', 0) < 2.0
                     and value.get('connected'))
        armed = fresh and bool(value.get('armed'))
        _set_chip(self.chip_state, '● 受付中' if armed else '● 停止中',
                  GREEN if armed else AMBER)
        _set_chip(self.chip_link, '● 認識接続' if fresh else '● 認識未接続',
                  GREEN if fresh else MUTED)
        owner = getattr(getattr(logic, 'dispatcher', None), 'input_owner', 'hand')
        _set_chip(self.chip_owner,
                  '入力：ハンド' if owner == 'hand' else '入力：マウス',
                  ACCENT if owner == 'hand' else AMBER)


class GestureBar:
    """Concept bottom strip: the active gesture legend."""

    def __init__(self):
        self.bar = qt.QToolBar('CardiacGestureBar', slicer.util.mainWindow())
        self.bar.setObjectName('CardiacGestureBar')
        self.bar.setMovable(False)
        self.bar.setFloatable(False)
        self.bar.setStyleSheet(
            'QToolBar{background:#0c1f33;border:none;border-top:1px solid %s;spacing:18px;padding:3px 12px}'
            % BORDER)
        for text in ('I Love You 1.5秒：開始・メニュー', '親指：前へ・C呼出',
                     '親指下：次へ・戻る', 'グー：決定', '3本指：初期値'):
            label = qt.QLabel(text)
            label.setStyleSheet('color:%s;font-size:12px' % MUTED)
            self.bar.addWidget(label)
        spacer = qt.QWidget()
        spacer.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Preferred)
        self.bar.addWidget(spacer)
        tag = qt.QLabel('非臨床プロトタイプ')
        tag.setStyleSheet('color:#5d7284;font-size:11px')
        self.bar.addWidget(tag)
        slicer.util.mainWindow().addToolBar(qt.Qt.BottomToolBarArea, self.bar)


class PlacementPanel:
    """Right dock: draft geometry, C-direction previews, commit/cancel and
    the plan/ledger summary. Buttons only reuse existing command paths."""

    def __init__(self, logic, panel):
        self.logic = logic
        self.panel = panel
        self.dock = _fixed_dock('CardiacPlacementDock')
        self.dock.setAllowedAreas(qt.Qt.RightDockWidgetArea)
        content = qt.QWidget()
        content.setStyleSheet(PANEL_STYLE)
        content.setMinimumWidth(280)
        content.setMaximumWidth(360)
        scroll = qt.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setStyleSheet('QScrollArea{background:%s;border:none}' % BG)
        self.dock.setWidget(scroll)
        layout = qt.QVBoxLayout(content)
        layout.setSpacing(10)

        head = qt.QHBoxLayout()
        title = qt.QLabel('仮配置')
        title.setStyleSheet('font-size:16px;font-weight:bold;color:%s' % TEXT)
        head.addWidget(title)
        head.addStretch(1)
        self.badge = qt.QLabel('なし')
        head.addWidget(self.badge)
        layout.addLayout(head)

        card = qt.QFrame()
        card.setObjectName('card')
        form = qt.QFormLayout(card)
        form.setContentsMargins(12, 10, 12, 10)
        form.setSpacing(8)
        self.diameter = qt.QLabel('—')
        size_row = qt.QHBoxLayout()
        size_row.addWidget(self.diameter, 1)
        self.size_button = qt.QPushButton('サイズ設定')
        self.size_button.clicked.connect(self._size_settings)
        size_row.addWidget(self.size_button)
        holder = qt.QWidget()
        holder.setLayout(size_row)
        form.addRow('直径', holder)
        self.opening = qt.QLabel('—')
        form.addRow('開口方向', self.opening)
        self.tilt = qt.QLabel('—')
        form.addRow('面の傾き', self.tilt)
        self.direction = qt.QLabel('—')
        form.addRow('進行方向', self.direction)
        layout.addWidget(card)

        caption = qt.QLabel('Cの向き（開口方向のイメージ）')
        caption.setStyleSheet('color:%s;font-size:12px' % MUTED)
        layout.addWidget(caption)
        previews = qt.QHBoxLayout()
        previews.setSpacing(8)
        self.front = qt.QLabel()
        self.front.setFixedSize(150, 110)
        self.side = qt.QLabel()
        self.side.setFixedSize(150, 110)
        previews.addWidget(self.front)
        previews.addWidget(self.side)
        layout.addLayout(previews)
        self._preview_signature = None

        self.confirm = qt.QPushButton('確定へ進む')
        self.confirm.setObjectName('primary')
        self.confirm.clicked.connect(self._confirm)
        layout.addWidget(self.confirm)
        self.cancel = qt.QPushButton('仮Cを取消')
        self.cancel.clicked.connect(self._cancel)
        layout.addWidget(self.cancel)
        self.hint = qt.QLabel()
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet('color:%s;font-size:12px' % AMBER)
        layout.addWidget(self.hint)

        records_title = qt.QLabel('計画・記録')
        records_title.setStyleSheet('font-size:15px;font-weight:bold;color:%s' % TEXT)
        layout.addWidget(records_title)
        records = qt.QFrame()
        records.setObjectName('card')
        rows = qt.QFormLayout(records)
        rows.setContentsMargins(12, 10, 12, 10)
        rows.setSpacing(8)
        self.planned = qt.QLabel('--')
        self.performed = qt.QLabel('--')
        self.ledger = qt.QLabel('--')
        self.layer_label = qt.QLabel('PERFORMED')
        planned_head = qt.QWidget()
        ph = qt.QHBoxLayout(planned_head)
        ph.setContentsMargins(0, 0, 0, 0)
        icon = qt.QLabel()
        icon.setPixmap(_icon('c', AMBER).pixmap(16, 16))
        ph.addWidget(icon)
        ph.addWidget(qt.QLabel('PLANNED（予定の焼き印）'))
        rows.addRow(planned_head, self.planned)
        performed_head = qt.QWidget()
        pf = qt.QHBoxLayout(performed_head)
        pf.setContentsMargins(0, 0, 0, 0)
        icon = qt.QLabel()
        icon.setPixmap(_icon('c', ACCENT).pixmap(16, 16))
        pf.addWidget(icon)
        pf.addWidget(qt.QLabel('PERFORMED（実施の焼き印）'))
        rows.addRow(performed_head, self.performed)
        ledger_head = qt.QWidget()
        lh = qt.QHBoxLayout(ledger_head)
        lh.setContentsMargins(0, 0, 0, 0)
        dot = qt.QLabel('●')
        dot.setStyleSheet('color:%s' % RED)
        lh.addWidget(dot)
        lh.addWidget(qt.QLabel('操作記録（作業の履歴）'))
        rows.addRow(ledger_head, self.ledger)
        rows.addRow('確定レイヤー', self.layer_label)
        layout.addWidget(records)
        layout.addStretch(1)
        slicer.util.mainWindow().addDockWidget(qt.Qt.RightDockWidgetArea, self.dock)
        self.dock.show()
        self._ledger_at = 0.0
        self._ledger_count = None

    def _owner(self):
        dispatcher = getattr(self.logic, 'dispatcher', None)
        return getattr(dispatcher, 'input_owner', 'hand')

    def _size_settings(self):
        from size_settings import show_size_settings
        show_size_settings(self.logic)

    def _confirm(self):
        logic = self.logic
        if not logic.has_draft():
            self.hint.setText('仮Cがありません')
            return
        if self._owner() != 'mouse':
            # Hand ownership: surface the edit menu whose entries include
            # 確定へ進む — the guarded confirm page stays the only path.
            self.panel.request('open')
            self.hint.setText('ハンド操作中：グーまたはメニューの「確定へ進む」を選択してください')
            return
        displayed = logic.display_contract.displayed
        if not displayed:
            self.hint.setText('仮Cの描画完了を待ってください')
            return
        params = {k: displayed[k] for k in ('draft_id', 'rev', 'hash')}
        placement = displayed['placement']
        center = ', '.join(f'{v:.3f}' for v in placement['anchor'])
        normal = ', '.join(f'{v:.4f}' for v in placement['plane']['normal'])
        opening = ', '.join(f'{v:.4f}' for v in placement['opening_dir'])
        direction = '順方向' if placement['path_dir'] == 1 else '逆方向'
        answer = qt.QMessageBox.question(slicer.util.mainWindow(), 'C確定の確認',
            f"対象：{displayed['target']['model_name']}\n対象ID：{displayed['target'].get('target_id','未登録')}\n仮C：{displayed['draft_id']} 版{displayed['rev']}\n直径：{displayed['template']['radius']*2:g}mm\n中心（RAS mm）：{center}\n開口角：{placement['in_plane_angle']*180/3.141592653589793:.3f}°\n開口方向：{opening}\n面の法線：{normal}\n進行方向：{direction}\nhash：{displayed['hash']}\n確定しますか？",
            qt.QMessageBox.Yes | qt.QMessageBox.No)
        if answer == qt.QMessageBox.Yes:
            response = logic.dispatcher.dispatch_local('commit', params, input_method='mouse')
            self.hint.setText('' if response.get('ok') else '拒否：' + str(response.get('reason', '')))

    def _cancel(self):
        if not self.logic.has_draft():
            self.hint.setText('仮Cがありません')
            return
        if self._owner() != 'mouse':
            self.panel.request('open')
            self.hint.setText('ハンド操作中：親指下またはメニューの「仮配置を取り消す」を選択してください')
            return
        response = self.logic.dispatcher.dispatch_local('cancel', input_method='mouse')
        self.hint.setText('' if response.get('ok') else '拒否：' + str(response.get('reason', '')))

    def _tilt_deg(self, draft):
        initial = draft.initial_placement
        return math.degrees(math.atan2(
            -sum(draft.placement.normal[i] * initial.v[i] for i in range(3)),
            sum(draft.placement.normal[i] * initial.normal[i] for i in range(3))))

    def _ledger_lines(self):
        if time.time() - self._ledger_at < 2.0:
            return self._ledger_count
        self._ledger_at = time.time()
        try:
            with open(self.logic.ledger_path, encoding='utf-8') as stream:
                self._ledger_count = sum(1 for line in stream if line.strip())
        except (OSError, ValueError):
            self._ledger_count = None
        return self._ledger_count

    def refresh(self):
        logic = self.logic
        draft = logic.controller.draft if logic.has_draft() else None
        if draft is None:
            self.badge.setText('なし')
            self.badge.setStyleSheet('color:%s;border:1px solid %s;border-radius:9px;'
                                     'padding:1px 10px;font-size:12px' % (MUTED, BORDER))
        elif logic.controller.frozen:
            self.badge.setText('凍結')
            self.badge.setStyleSheet('color:#06222a;background:%s;border-radius:9px;'
                                     'padding:1px 10px;font-size:12px;font-weight:bold' % RED)
        else:
            self.badge.setText('未確定')
            self.badge.setStyleSheet('color:%s;border:1px solid %s;border-radius:9px;'
                                     'padding:1px 10px;font-size:12px' % (AMBER, AMBER))
        template = (logic.controller.draft_template if draft
                    else logic.controller.template)
        self.diameter.setText('%.1f mm' % (template.radius * 2.0))
        if draft:
            self.opening.setText('%.0f°' % (math.degrees(draft.placement.in_plane_angle) % 360))
            self.tilt.setText('%.0f°' % self._tilt_deg(draft))
            self.direction.setText('順方向' if draft.placement.path_dir == 1 else '逆方向')
        else:
            self.opening.setText('—')
            self.tilt.setText('—')
            self.direction.setText('—')
        self.confirm.setEnabled(draft is not None)
        self.cancel.setEnabled(draft is not None)
        self._refresh_previews(draft)
        plan = getattr(logic, '_plan', None)
        status = plan.status() if plan is not None and plan.entries else None
        self.planned.setText('%d 件' % status['total'] if status else '--')
        committed = len(getattr(logic, '_committed', {}))
        self.performed.setText('%d 件' % committed if committed else '--')
        lines = self._ledger_lines()
        self.ledger.setText('%d 件' % lines if lines is not None else '--')
        self.layer_label.setText(logic.active_layer)

    def _refresh_previews(self, draft):
        if draft is None:
            if self._preview_signature != 'empty':
                self._preview_signature = 'empty'
                self._paint_placeholder()
            return
        template = self.logic.controller.draft_template
        signature = (draft.draft_id, draft.revision, template.radius,
                     draft.placement.in_plane_angle, draft.placement.path_dir)
        if signature == self._preview_signature:
            return
        self._preview_signature = signature
        self._paint_front(template, draft)
        self._paint_side(draft)

    def _paint_placeholder(self):
        for label in (self.front, self.side):
            pixmap = qt.QPixmap(150, 110)
            pixmap.fill(qt.QColor(CARD))
            painter = qt.QPainter(pixmap)
            painter.setPen(qt.QColor(BORDER))
            painter.drawRect(0, 0, 149, 109)
            painter.setPen(qt.QColor(MUTED))
            painter.drawText(pixmap.rect(), qt.Qt.AlignCenter, '仮Cなし')
            painter.end()
            label.setPixmap(pixmap)

    def _paint_front(self, template, draft):
        from direction_preview import preview_points
        pixmap = qt.QPixmap(150, 110)
        pixmap.fill(qt.QColor(CARD))
        painter = qt.QPainter(pixmap)
        painter.setRenderHint(qt.QPainter.Antialiasing)
        painter.setPen(qt.QColor(BORDER))
        painter.drawRect(0, 0, 149, 109)
        path = qt.QPainterPath()
        scale = 34 / max(template.radius, 0.001)
        for index, (x, y) in enumerate(preview_points(template, draft.placement)):
            point = qt.QPointF(75 + x * scale, 55 - y * scale)
            if index == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        dash = qt.QPen(qt.QColor(MUTED))
        dash.setStyle(qt.Qt.DashLine)
        painter.setPen(dash)
        painter.drawLine(qt.QPointF(75, 55), qt.QPointF(140, 55))
        painter.setPen(qt.QColor(MUTED))
        painter.drawText(108, 100, '%.0f°' % (math.degrees(draft.placement.in_plane_angle) % 360))
        pen = qt.QPen(qt.QColor(ACCENT))
        pen.setWidthF(4)
        pen.setCapStyle(qt.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()
        self.front.setPixmap(pixmap)

    def _paint_side(self, draft):
        pixmap = qt.QPixmap(150, 110)
        pixmap.fill(qt.QColor(CARD))
        painter = qt.QPainter(pixmap)
        painter.setRenderHint(qt.QPainter.Antialiasing)
        painter.setPen(qt.QColor(BORDER))
        painter.drawRect(0, 0, 149, 109)
        angle = self._tilt_deg(draft)
        painter.setPen(qt.QColor(MUTED))
        painter.drawLine(qt.QPointF(12, 78), qt.QPointF(138, 78))
        painter.drawText(12, 96, '面')
        painter.save()
        painter.translate(75, 78)
        painter.rotate(-angle)
        pen = qt.QPen(qt.QColor(ACCENT))
        pen.setWidthF(4)
        pen.setCapStyle(qt.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(qt.QPointF(-26, 0), qt.QPointF(-8, 0))
        painter.drawLine(qt.QPointF(8, 0), qt.QPointF(26, 0))
        painter.setPen(qt.QPen(qt.QColor(TEXT)))
        painter.drawLine(qt.QPointF(0, -3), qt.QPointF(0, -14))
        painter.restore()
        painter.setPen(qt.QColor(MUTED))
        painter.drawText(104, 30, '%.0f°' % angle)
        painter.end()
        self.side.setPixmap(pixmap)


class UnifiedHandPanel:
    def __init__(self, logic):
        self.logic = logic
        bridge = bridge_module()
        self.state = bridge.MemoryChannel('state')
        self.requests = bridge.MemoryChannel('requests')
        self.pending = None
        self.pending_at = 0
        self.current = {}
        self.signature = None
        self.dock = _fixed_dock('CardiacUnifiedHandDock')
        self.content = qt.QWidget()
        self.content.setStyleSheet(PANEL_STYLE)
        self.content.setMinimumWidth(325)
        self.content.setMaximumWidth(420)
        self.scroll = qt.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.content)
        self.scroll.setStyleSheet('QScrollArea{background:%s;border:none}' % BG)
        self.dock.setWidget(self.scroll)
        self.layout = qt.QVBoxLayout(self.content)
        self.layout.setSpacing(10)

        header = qt.QHBoxLayout()
        hand = qt.QLabel()
        hand.setPixmap(_icon('hand', TEXT, 22).pixmap(22, 22))
        header.addWidget(hand)
        title = qt.QLabel('ハンド操作')
        title.setStyleSheet('font-size:16px;font-weight:bold')
        header.addWidget(title)
        header.addStretch(1)
        self.layout.addLayout(header)

        section = qt.QLabel('現在の操作')
        section.setStyleSheet('color:%s;font-size:12px' % MUTED)
        self.layout.addWidget(section)
        mode_card = qt.QFrame()
        mode_card.setObjectName('card')
        mode_layout = qt.QVBoxLayout(mode_card)
        mode_layout.setContentsMargins(12, 10, 12, 10)
        self.mode_label = qt.QLabel('接続待ち')
        self.mode_label.setWordWrap(True)
        self.mode_label.setStyleSheet('font-size:19px;font-weight:bold;color:%s' % ACCENT)
        mode_layout.addWidget(self.mode_label)
        self.guide = qt.QLabel()
        self.guide.setWordWrap(True)
        self.guide.setStyleSheet(
            'color:%s;font-size:16px;font-weight:bold;'
            'background:%s;border-left:5px solid %s;padding:10px;border-radius:4px'
            % (TEXT, '#0d2a38', ACCENT))
        mode_layout.addWidget(self.guide)
        self.layout.addWidget(mode_card)

        self.heading = qt.QLabel('操作メニュー')
        self.heading.setStyleSheet('color:%s;font-size:12px' % MUTED)
        self.layout.addWidget(self.heading)
        self.items = qt.QListWidget()
        self.items.setSelectionMode(qt.QAbstractItemView.NoSelection)
        self.items.setMinimumHeight(190)
        self.items.setStyleSheet('QListWidget{font-size:14px}')
        self.layout.addWidget(self.items)

        nav = qt.QGridLayout()
        nav.setSpacing(6)
        self.buttons = []
        for position, (label, action) in enumerate(
                [('メニューを開く', 'open'), ('次の項目', 'next'),
                 ('選択／決定', 'select'), ('戻る／閉じる', 'back')]):
            button = qt.QPushButton(label)
            button.clicked.connect(lambda *_, action=action: self.request(action))
            nav.addWidget(button, position // 2, position % 2)
            self.buttons.append((button, action))
        self.layout.addLayout(nav)

        recog = qt.QFrame()
        recog.setObjectName('card')
        recog_layout = qt.QVBoxLayout(recog)
        recog_layout.setContentsMargins(12, 10, 12, 10)
        recog_row = qt.QHBoxLayout()
        recog_icon = qt.QLabel()
        recog_icon.setPixmap(_icon('hand', ACCENT, 30).pixmap(30, 30))
        recog_row.addWidget(recog_icon)
        recog_text = qt.QVBoxLayout()
        recog_head = qt.QLabel('認識')
        recog_head.setStyleSheet('color:%s;font-size:12px' % MUTED)
        recog_text.addWidget(recog_head)
        self.recognition = qt.QLabel()
        self.recognition.setWordWrap(True)
        self.recognition.setStyleSheet('font-size:15px;font-weight:bold;color:%s' % ACCENT)
        recog_text.addWidget(self.recognition)
        recog_row.addLayout(recog_text, 1)
        recog_layout.addLayout(recog_row)
        self.preview_switch = qt.QPushButton('カメラを表示')
        self.preview_switch.setIcon(_icon('camera', TEXT))
        self.preview_switch.setCheckable(True)
        self.preview_switch.toggled.connect(self.toggle_preview)
        recog_layout.addWidget(self.preview_switch)
        self.preview = qt.QLabel()
        self.preview.setFixedSize(320, 240)
        self.preview.hide()
        recog_layout.addWidget(self.preview)
        self.layout.addWidget(recog)

        self.hold = qt.QProgressBar()
        self.hold.setRange(0, 150)
        self.layout.addWidget(self.hold)
        row = qt.QHBoxLayout()
        self.start = qt.QPushButton('受付開始')
        self.stop = qt.QPushButton('停止')
        self.start.clicked.connect(lambda *_: self.request('arm'))
        self.stop.clicked.connect(lambda *_: self.request('disarm'))
        row.addWidget(self.start)
        row.addWidget(self.stop)
        self.layout.addLayout(row)

        self.reason = qt.QLabel()
        self.reason.setWordWrap(True)
        self.reason.setStyleSheet('color:%s;font-size:12px' % AMBER)
        self.layout.addWidget(self.reason)
        self.size_button = qt.QPushButton('Cの直径設定（mm）を開く')
        self.size_button.clicked.connect(lambda *_: self.show_size())
        self.layout.addWidget(self.size_button)
        self.diagnose_button = qt.QPushButton('ゲート診断')
        self.diagnose_button.clicked.connect(lambda *_: self.show_diagnose())
        self.layout.addWidget(self.diagnose_button)
        self.size_container = qt.QWidget()
        self.size_layout = qt.QVBoxLayout(self.size_container)
        self.size_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.size_container)
        self.layout.addStretch(1)
        slicer.util.mainWindow().addDockWidget(qt.Qt.LeftDockWidgetArea, self.dock)
        # The standard module selector remains available from Slicer's View menu.
        module_dock = slicer.util.mainWindow().findChild(qt.QDockWidget, 'PanelDockWidget')
        if module_dock is not None:
            module_dock.hide()
        for name in ['ErrorLogDockWidget', 'PythonConsoleDockWidget']:
            diagnostic_dock = slicer.util.mainWindow().findChild(qt.QDockWidget, name)
            if diagnostic_dock is not None:
                diagnostic_dock.hide()
        try:
            view = slicer.app.layoutManager().threeDWidget(0).threeDView()
            view.setBackgroundColor(qt.QColor('#0c1f33'))
            view.setBackgroundColor2(qt.QColor(BG))
            view.scheduleRender()
        except (RuntimeError, AttributeError):
            pass
        self.placement = PlacementPanel(logic, self)
        self.topbar = TopStatusBar()
        self.gestures = GestureBar()
        self.dock.show()
        self.timer = qt.QTimer(self.dock)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()

    def request(self, action, **params):
        # One pending request; rapid mouse clicks cannot overwrite an action.
        if self.pending is not None:
            self.reason.setText('前の操作の応答を待っています')
            return
        self.pending = uuid.uuid4().hex
        self.pending_at = time.time()
        self.requests.write(dict(id=self.pending, ts=self.pending_at, action=action, **params))

    def show_diagnose(self):
        """Run the read-only per-gate report and show every check at once."""
        dispatcher = getattr(self.logic, 'dispatcher', None)
        if dispatcher is None:
            slicer.util.errorDisplay('コマンドサーバがまだ起動していません')
            return
        try:
            response = dispatcher.dispatch_local('diagnose', input_method='mouse')
        except Exception as error:
            slicer.util.errorDisplay('診断の実行に失敗しました：%s' % error)
            return
        report = (response or {}).get('result') or {}
        lines = []
        for item in report.get('checks', []):
            mark = '✓' if item.get('ok') else '✗'
            lines.append('%s %s — %s' % (mark, item.get('name'), item.get('detail')))
        state = report.get('state') or {}
        lines.append('')
        lines.append('state: armed=%s mode=%s layer=%s draft=%s owner=%s session=%s foreground=%s' % (
            state.get('armed'), state.get('mode'), state.get('layer'), state.get('draft'),
            state.get('input_owner'), state.get('session'), state.get('foreground')))
        # Non-modal: a modal exec_() blocks the panel timer, starves the
        # liveness heartbeat, and the recognizer exits after ~10 s.
        box = qt.QMessageBox(slicer.util.mainWindow())
        box.setWindowTitle('ゲート診断')
        box.setText('全ての確認が一致しています' if report.get('all_ok') else '不一致の確認項目があります')
        box.setDetailedText('\n'.join(lines))
        box.setModal(False)
        box.setAttribute(qt.Qt.WA_DeleteOnClose)
        self._diagnose_box = box
        box.show()

    def attach_mouse_widget(self, widget):
        """Keep the full existing mouse fallback inside this same dock."""
        if hasattr(self, 'tabs'):
            return
        self.tabs = qt.QTabWidget()
        self.tabs.addTab(self.scroll, 'ハンド操作')
        fallback = qt.QScrollArea()
        fallback.setWidgetResizable(True)
        fallback.setWidget(widget)
        widget.show()
        self.tabs.addTab(fallback, '詳細マウス操作')
        self.dock.setWidget(self.tabs)
        self.tabs.setCurrentIndex(0)

    def toggle_preview(self, checked):
        self.preview.setVisible(bool(checked))
        if not checked:
            self.preview.clear()
        self.request('preview', enabled=bool(checked))

    def show_size(self):
        from size_settings import show_size_settings
        old = getattr(self.logic, '_size_dialog', None)
        if old is not None:
            self.size_layout.removeWidget(old)
            old.close()
            old.deleteLater()
        dialog = show_size_settings(self.logic, parent=self.size_container)
        self.size_layout.addWidget(dialog)
        self.size_container.show()
        return dialog

    def refresh(self):
        if not hasattr(self, 'liveness'):
            self.liveness = bridge_module().MemoryChannel('liveness')
        self.liveness.write({'ts': time.time()})
        value = self.state.read()
        fresh = bool(value and 0 <= time.time() - value.get('ts', 0) < 2.0
                     and value.get('connected'))
        if self.pending is not None:
            if value and value.get('ack') == self.pending:
                self.pending = None
            elif time.time() - self.pending_at > 2.0:
                self.pending = None
                self.reason.setText('操作の応答なし。実行を再送しません')
        busy = self.pending is not None
        armed = fresh and bool(value.get('armed'))
        self.start.setEnabled(fresh and not armed and not busy)
        self.stop.setEnabled(fresh and armed and not busy)
        for button, action in self.buttons:
            button.setEnabled(armed and not busy and
                              (action == 'open' or bool(value.get('opened'))))
        self.preview_switch.setEnabled(fresh and not busy)
        self.topbar.update(value, self.logic)
        self.placement.refresh()
        if not fresh:
            self.mode_label.setText('接続待ち')
            self.guide.setText('カメラ・認識アプリの接続を確認してください')
            self.recognition.setText('—')
            self.hold.setValue(0)
            self.preview.clear()
            self.items.clear()
            self.signature = None
            self.heading.setText('操作メニュー（認識接続待ち）')
            self.reason.setText('認識アプリ未接続／応答なし')
            return
        self.current = value
        modes = {'view': '視点操作', 'aim': 'Cを置く場所を選ぶ',
                 'move': 'Cの位置を調整中', 'rotate': '開口方向を調整',
                 'tilt': 'Cの面の傾きを調整中', 'review': '既存Cの選択・訂正'}
        mode = value.get('mode')
        title = modes.get(mode, '操作状態を確認中')
        if not armed:
            title = '操作停止中'
        elif value.get('frozen') and value.get('draft'):
            title = '仮C凍結・編集停止'
        self.mode_label.setText(title + ('　・仮Cあり・未確定' if value.get('draft') else ''))
        names = {'none': '手なし', 'open_palm': '開いた手', 'iloveyou': 'I Love You（復帰）', 'thumb': '親指', 'two': '2本指',
                 'three': '3本指', 'fist': 'グー', 'point': '人差し指', 'pinch': 'つまみ', 'unknown': '不明'}
        self.recognition.setText(names.get(value.get('shape'), '不明') +
                                 ('\n' + value.get('detail', '') if value.get('detail') else ''))
        self.hold.setVisible(not armed)
        self.hold.setMaximum(int(value.get('hold_required', 1.5) * 100))
        self.hold.setValue(int(value.get('hold', 0) * 100))
        self.hold.setFormat('開始保持 %.1f / %.1f 秒' % (value.get('hold', 0), value.get('hold_required', 1.5)))
        titles = {'edit': 'C焼き印', 'main': 'メニュー', 'records': '計画・記録',
                  'reasons': '理由の選択', 'confirm': 'C確定の確認', 'plan_versions': '保存された計画版'}
        page = value.get('page')
        self.heading.setText('操作メニュー' + (('：' + titles.get(page, page)) if value.get('opened') else ''))
        if value.get('frozen') and value.get('draft'):
            guide = ('【今】仮Cが凍結中（認識が切れて保護停止）\n'
                     '【次】🤟 I Love You：凍結を解除して編集へ\n'
                     '　　　親指下：凍結したまま仮Cを取消')
        elif value.get('opened'):
            if page == 'confirm':
                guide = ('【今】C確定の確認画面\n'
                         '【次】グー：確定実行　親指下：編集に戻る')
            else:
                guide = ('【今】メニュー表示中\n'
                         '【次】親指上：前へ　親指下：次へ（末尾で戻る）\n'
                         '　　　グー：決定　🤟 I Love You：主メニュー')
        elif not armed:
            guide = ('【今】受付停止\n'
                     '【次】🤟 I Love Youを1.5秒保持：受付開始')
        elif value.get('draft'):
            guide = ('【今】仮Cを編集中（未確定）\n'
                     '【次】1本指：位置　つまみ左右：開口方向　3本指：方向を初期値\n'
                     '　　　グー：確定へ進む　親指下：仮配置を取り消す')
        elif mode == 'aim':
            guide = ('【今】照準モード\n'
                     '【次】1本指：照準を動かす　グー：仮配置\n'
                     '　　　照準：' + ('有効' if value.get('aim_valid') is True else '表面への照準を確認'))
        else:
            guide = ('【今】' + title + '\n'
                     '【次】パー：回転　1本指：パン　つまみ：ズーム　3本指：視点を戻す\n'
                     '　　　親指上：C呼出　🤟 I Love You：メニュー')
        self.guide.setText(guide + '\n手を画面外へ出す必要はありません')
        entries = value.get('entries', [])
        signature = (tuple(e.get('label', '') for e in entries), value.get('selected', -1))
        if signature != self.signature:
            self.items.clear()
            selected = value.get('selected', -1)
            for index, e in enumerate(entries):
                item = qt.QListWidgetItem(
                    _icon(_MENU_ICONS.get(e.get('key'), 'doc')),
                    e['label'] + (' ›' if e.get('key') in _NAV_KEYS else '') +
                    ('\n' + e['detail'] if e.get('detail') else ''))
                self.items.addItem(item)
                if index == selected:
                    item.setBackground(qt.QBrush(qt.QColor('#123f4d')))
                    item.setForeground(qt.QBrush(qt.QColor(ACCENT)))
            if selected >= 0:
                self.items.setCurrentRow(selected)
            else:
                self.items.clearSelection()
            self.signature = signature
        confirmation = value.get('confirmation')
        details = []
        plan_view = value.get('plan_view')
        if plan_view:
            details.append('計画%s 第%s版／最新%s版%s' % (plan_view['plan_id'], plan_view['version'], plan_view['latest_version'],
                           '（比較専用・編集不可）' if plan_view['read_only'] else ''))
            details.append('計画版hash：' + plan_view['hash'])
            difference = plan_view.get('difference_to_latest') or {}
            details.append('選択版→最新保存版：追加%s／削除%s／位置変更%s／方向変更%s' % (
                len(difference.get('added', [])), len(difference.get('removed', [])),
                len(difference.get('moved', [])), len(difference.get('rotated', []))))
        if confirmation:
            details.append('仮C：%s 版%s 直径%gmm' % (confirmation['draft_id'], confirmation['rev'], confirmation['template']['radius'] * 2))
            details.append('対象：' + str(confirmation['target'].get('model_name')))
            details.append('表示hash：' + confirmation['hash'])
            details.append('開口角：%.1f° 進行方向：%s' % (math.degrees(confirmation['placement']['in_plane_angle']), confirmation['placement']['path_dir']))
        delta = value.get('plan_delta')
        if delta:
            details.append('予定との差：位置%smm／法線%s°／開口%s°' % (delta['anchor_delta_mm'], delta['normal_delta_deg'], delta['in_plane_delta_deg']))
        if value.get('audit'):
            details.append('監査確認待ち：' + str(value['audit']))
        self.reason.setText('\n'.join(details) + ('\n' if details else '') + (value.get('reason', '') or ('開始：I Love Youを1.5秒保持、または受付開始を押す' if not armed else '')))
        if self.preview_switch.checked and value.get('preview'):
            pixmap = qt.QPixmap()
            if pixmap.loadFromData(qt.QByteArray(base64.b64decode(value['preview'])), 'JPG'):
                self.preview.setPixmap(pixmap)


def install(logic):
    existing = getattr(logic, '_unified_hand_panel', None)
    if existing is not None:
        existing.dock.show()
        return existing
    panel = UnifiedHandPanel(logic)
    logic._unified_hand_panel = panel
    return panel
