"""CStampModule — non-clinical C-stamp overlay for 3D Slicer.

Mouse-driven prototype implementing the IDLE/DRAFT/COMMITTED/CANCELLED
state machine from docs/03 on a separated overlay layer. It never
modifies the source CT/DICOM, the heart model, or previously committed
events. Committed events go to an append-only JSONL ledger.

Not for clinical use.
"""
from __future__ import annotations

import ctypes
import json
import math
import os
import sys
import hashlib
import copy
import time
import uuid

import qt
import slicer
import vtk
from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleLogic,
    ScriptedLoadableModuleWidget,
)

_MODULE_DIR = os.path.dirname(os.path.realpath(__file__))
_DATA_ROOT = os.environ.get('CSTAMP_WORKSPACE_ROOT', os.path.normpath(os.path.join(_MODULE_DIR, '..', '..')))
_LOADED_SOURCE_HASHES = {}
for _directory, _subdirs, _files in os.walk(_MODULE_DIR):
    _subdirs[:] = [d for d in _subdirs if d not in {'tests','__pycache__'}]
    for _filename in _files:
        if _filename.endswith('.py'):
            _path = os.path.join(_directory, _filename)
            with open(_path, 'rb') as _source_stream:
                _LOADED_SOURCE_HASHES[os.path.relpath(_path,_MODULE_DIR).replace('\\','/')] = hashlib.sha256(_source_stream.read()).hexdigest()
if _MODULE_DIR not in sys.path:
    sys.path.insert(0, _MODULE_DIR)

from cstamp import (  # noqa: E402
    CStampController,
    CTemplate,
    EventLedger,
    PlanStore,
    PlanTracker,
    StampState,
    StateError,
    placement_from_dict,
)
from command_protocol import CommandDispatcher  # noqa: E402
from view_commands import apply_to_camera, parse_command  # noqa: E402
from cstamp.contracts import DisplayContract, digest
from cstamp.target_registry import TargetRegistry
from cstamp.runtime_contract import RuntimePolicy
from cstamp.storage_selection import load_selection, save_selection


DEFAULT_SURFACE_NAME = "CARTOmesh_1-OG"
DEFAULT_LEDGER_PATH = os.path.normpath(
    os.path.join(
        _DATA_ROOT, "artifacts", "cstamp", "events.jsonl"
    )
)
DRAFT_CURVE_NAME = "CStamp-DRAFT"
PERFORMED_POINTS_NAME = "CStamp-PERFORMED"
PERFORMED_SHAPE_PREFIX = "CStamp-shape-"
PLANNED_POINTS_NAME = "CStamp-PLANNED-points"
PLANNED_SHAPE_PREFIX = "CStamp-planned-shape-"
GHOST_CURVE_NAME = "CStamp-PLANNED-GHOST"

DEFAULT_PLAN_REGISTRY_PATH = os.path.normpath(os.path.join(_DATA_ROOT, 'artifacts', 'cstamp', 'plans.jsonl'))


class CStampModule(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "C Stamp"
        self.parent.categories = ["Cardiac CT Motion Control"]
        self.parent.contributors = ["Cardiac CT Motion Control project"]
        self.parent.helpText = (
            "Non-clinical C-stamp planning overlay. Mouse places a draft "
            "C on the allowed surface, adjusts its direction, then an "
            "explicit commit writes one event to a separated ledger. "
            "Not for clinical use."
        )
        self.parent.acknowledgementText = "3D Slicer scripted module."


class CStampModuleWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = CStampModuleLogic()

        box = qt.QVBoxLayout()
        self.layout.addLayout(box)

        self.statusLabel = qt.QLabel()
        box.addWidget(self.statusLabel)
        self.sizeButton = qt.QPushButton("C焼き印のサイズ設定（mm）")
        self.sizeButton.clicked.connect(lambda: self.logic.op_size_settings({}))
        box.addWidget(self.sizeButton)
        self.mouseHandover = qt.QPushButton('マウス操作へ切替（手操作を失効）')
        self.mouseHandover.clicked.connect(self.onMouseHandover)
        box.addWidget(self.mouseHandover)
        self.handHandover = qt.QPushButton('ハンド操作へ戻す（開始待ち）')
        self.handHandover.clicked.connect(self.onHandHandover)
        box.addWidget(self.handHandover)
        self.mouseAction = qt.QComboBox()
        self._mouse_actions = [
            ('仮Cの位置をクリックで調整','move_pick'), ('仮C編集を再開','resume_draft'),
            ('計画を作成','create_plan'), ('登録計画を読み込む','load_plan'),
            ('計画訂正を開始','begin_plan_revision'), ('選択予定のCを編集','edit_plan_item'),
            ('予定Cを追加','add_plan_item'), ('選択予定の削除を確認','delete_plan_item'),
            ('予定項目を選択','select_plan_item'), ('予定を次へ移動','move_plan_item'),
            ('実施順を変更','reorder_plan'), ('予定をスキップ','skip_plan'),
            ('計画訂正を保存','save_plan_revision'), ('計画訂正を取消','cancel_plan_revision'),
            ('登録計画を選択','select_plan'), ('保存された計画版を比較','select_plan_version'), ('作成者を選択','select_creator'),
            ('保存先を選択','select_storage'), ('理由を選択','select_reason'),
            ('計画外を宣言','set_out_of_plan'), ('既存Cをクリックで選択','review_pick'),
            ('選択Cを再表示','show_c'), ('選択Cを訂正','begin_correction'),
            ('選択記録の撤回を確認','revoke_event'), ('表示した監査内容を確定','confirm_audit'),
            ('保存状態を確認','save_session'), ('保存記録を読み込む','load_session'),
            ('前の確定要求を照会','query_result')]
        for label, command in self._mouse_actions:
            self.mouseAction.addItem(label,command)
        self.mouseChoice = qt.QComboBox()
        self.mouseAction.currentIndexChanged.connect(lambda _i:self._update_mouse_choices())
        box.addWidget(self.mouseAction)
        box.addWidget(self.mouseChoice)
        self.mouseExecute = qt.QPushButton('選択した操作を実行')
        self.mouseExecute.clicked.connect(self.onMouseAction)
        box.addWidget(self.mouseExecute)
        self.mouseDetails = qt.QLabel()
        self.mouseDetails.setWordWrap(True)
        box.addWidget(self.mouseDetails)

        form = qt.QFormLayout()
        box.addLayout(form)

        self.surfaceCombo = slicer.qMRMLNodeComboBox()
        self.surfaceCombo.nodeTypes = ["vtkMRMLModelNode"]
        self.surfaceCombo.setMRMLScene(slicer.mrmlScene)
        try:
            self.surfaceCombo.setCurrentNode(
                slicer.util.getNode(DEFAULT_SURFACE_NAME)
            )
        except slicer.util.MRMLNodeNotFoundException:
            pass
        form.addRow("対象表面", self.surfaceCombo)

        self.ledgerEdit = qt.QLineEdit(self.logic.ledger_path)
        form.addRow("台帳(JSONL)", self.ledgerEdit)
        self.targetRegistryEdit = qt.QLineEdit(self.logic.target_registry_path)
        form.addRow('対象登録（準備時）', self.targetRegistryEdit)
        self.runtimeManifestEdit = qt.QLineEdit(self.logic.runtime_manifest_path)
        form.addRow('実効構成（準備時）', self.runtimeManifestEdit)

        self.layerCombo = qt.QComboBox()
        self.layerCombo.addItem("操作記録 (PERFORMED)", "PERFORMED")
        self.layerCombo.addItem("計画 (PLANNED)", "PLANNED")
        self.layerCombo.currentIndexChanged.connect(lambda _i:self.onMouseLayer())
        form.addRow("確定レイヤー", self.layerCombo)

        self.planEdit = qt.QLineEdit("")
        self.planEdit.setPlaceholderText(
            "PLANNEDイベントを含むJSONL計画ファイル"
        )
        form.addRow("計画(JSONL)", self.planEdit)
        self.registryEdit = qt.QLineEdit(self.logic.plan_registry_path)
        form.addRow('計画版台帳（準備時のみ変更）',self.registryEdit)
        self.newRegistryButton = qt.QPushButton('新規計画台帳を準備（既存履歴は保持）')
        self.newRegistryButton.clicked.connect(self.onNewPlanRegistry)
        box.addWidget(self.newRegistryButton)
        self.saveStorageButton = qt.QPushButton('台帳保存先を保存（次回起動にも適用）')
        self.saveStorageButton.clicked.connect(self.onSaveStorage)
        box.addWidget(self.saveStorageButton)
        self.storageFeedback = qt.QLabel()
        self.storageFeedback.setWordWrap(True)
        box.addWidget(self.storageFeedback)

        self.stampButton = qt.QPushButton("照準→スタンプ（仮配置）")
        self.stampButton.setCheckable(True)
        self.stampButton.clicked.connect(self.onStamp)
        box.addWidget(self.stampButton)

        row = qt.QHBoxLayout()
        for label, slot in (
            ("開口 +15°", lambda: self._adjust("rotate", 15.0)),
            ("開口 -15°", lambda: self._adjust("rotate", -15.0)),
            ("傾斜 +15°", lambda: self._adjust("tilt", 15.0)),
            ("傾斜 -15°", lambda: self._adjust("tilt", -15.0)),
            ("進行反転", lambda: self._adjust("reverse", 0.0)),
            ("方向リセット", lambda: self._adjust("reset", 0.0)),
        ):
            button = qt.QPushButton(label)
            button.clicked.connect(slot)
            row.addWidget(button)
        box.addLayout(row)

        sliderRow = qt.QHBoxLayout()
        sliderRow.addWidget(qt.QLabel("開口方向（連続）"))
        self.openingSlider = qt.QSlider(qt.Qt.Horizontal)
        self.openingSlider.minimum = -180
        self.openingSlider.maximum = 180
        self.openingSlider.value = 0
        self.openingSlider.valueChanged.connect(self.onOpeningSlider)
        sliderRow.addWidget(self.openingSlider)
        box.addLayout(sliderRow)
        tiltRow = qt.QHBoxLayout()
        tiltRow.addWidget(qt.QLabel('面の傾き（連続）'))
        self.tiltSlider = qt.QSlider(qt.Qt.Horizontal)
        self.tiltSlider.minimum = -85
        self.tiltSlider.maximum = 85
        self.tiltSlider.valueChanged.connect(self.onTiltSlider)
        tiltRow.addWidget(self.tiltSlider)
        box.addLayout(tiltRow)

        row = qt.QHBoxLayout()
        self.commitButton = qt.QPushButton("確定（操作記録）")
        self.commitButton.clicked.connect(self.onCommit)
        row.addWidget(self.commitButton)
        self.cancelButton = qt.QPushButton("取消")
        self.cancelButton.clicked.connect(self.onCancel)
        row.addWidget(self.cancelButton)
        box.addLayout(row)

        self.reshapeButton = qt.QPushButton("確定点のC型を再表示")
        self.reshapeButton.clicked.connect(self.onReshape)
        box.addWidget(self.reshapeButton)

        self.loadLedgerButton = qt.QPushButton("台帳を読込（全イベント復元）")
        self.loadLedgerButton.clicked.connect(self.onLoadLedger)
        box.addWidget(self.loadLedgerButton)

        row = qt.QHBoxLayout()
        self.loadPlanButton = qt.QPushButton("計画を読込（ゴースト表示）")
        self.loadPlanButton.clicked.connect(self.onLoadPlan)
        row.addWidget(self.loadPlanButton)
        self.skipPlanButton = qt.QPushButton("計画をスキップ")
        self.skipPlanButton.clicked.connect(self.onSkipPlan)
        row.addWidget(self.skipPlanButton)
        box.addLayout(row)

        row = qt.QHBoxLayout()
        row.addWidget(qt.QLabel("視点操作ポート"))
        self.portEdit = qt.QLineEdit("18944")
        self.portEdit.setMaximumWidth(80)
        row.addWidget(self.portEdit)
        self.serverButton = qt.QPushButton("受付開始")
        self.serverButton.setCheckable(True)
        self.serverButton.clicked.connect(self.onServerToggle)
        row.addWidget(self.serverButton)
        box.addLayout(row)

        box.addStretch(1)
        self.logic.on_stamp_done = self._on_stamp_done
        self.logic.on_state_changed = self._refresh
        self._refresh()

    def cleanup(self):
        self.logic.stop_command_server()
        self.logic.exit_aim_mode()
        ScriptedLoadableModuleWidget.cleanup(self)

    def _on_stamp_done(self):
        self.stampButton.setChecked(False)
        self._refresh()

    # --- slots ---------------------------------------------------------

    def onMouseLayer(self):
        try:
            self._mouse_command('select_layer', {'layer':self.layerCombo.currentData})
        except StateError as error:
            slicer.util.warningDisplay(str(error))
        self._refresh()

    def _mouse_command(self, cmd, params=None):
        if not getattr(self.logic, 'dispatcher', None):
            self.logic.dispatcher = CommandDispatcher(self.logic)
        response = self.logic.dispatcher.dispatch_local(cmd, params, input_method='mouse')
        if not response.get('ok'):
            raise StateError(response.get('reason','操作を拒否しました'))
        return response

    def _update_mouse_choices(self):
        if not hasattr(self,'mouseChoice'):
            return
        cmd = self.mouseAction.currentData
        choices = self.logic._registered_choices()
        category = {'select_plan':'plans','select_creator':'creators','select_storage':'storages',
                    'select_reason':'reasons','select_plan_item':'plan_items','select_plan_version':'plan_versions'}.get(cmd)
        values = choices.get(category,[]) if category else []
        if getattr(self,'_mouse_choice_signature',None) == (cmd,values):
            return
        self._mouse_choice_signature = (cmd,list(values))
        self.mouseChoice.clear()
        for value in values:
            self.mouseChoice.addItem(str(value),str(value))

    def onMouseAction(self):
        try:
            cmd = self.mouseAction.currentData
            value = self.mouseChoice.currentData
            params = {'plan_revision':self.logic._plan_binding()}
            fields = {'select_plan':'plan_id','select_creator':'creator','select_storage':'storage','select_reason':'reason'}
            if cmd in fields:
                params[fields[cmd]] = value
            elif cmd == 'select_plan_item':
                params['item_id'] = value
            elif cmd == 'select_plan_version':
                params['version'] = int(value)
            elif cmd in {'edit_plan_item','delete_plan_item'}:
                params['item_id'] = self.logic._selected_plan_item
            elif cmd in {'move_plan_item','reorder_plan'}:
                params.update(self.logic.op_status({})['result']['reorder_selection'])
            elif cmd == 'confirm_audit':
                params['audit'] = copy.deepcopy(self.logic._pending_audit)
            elif cmd == 'query_result':
                params['req'] = getattr(self,'_mouse_commit_req',None)
            elif cmd in {'move_pick','review_pick'}:
                self._mouse_command('select_mode',{'mode':'move' if cmd=='move_pick' else 'review'})
                self.logic.enter_aim_mode(self.surfaceCombo.currentNode())
                return
            self._mouse_command(cmd,params)
        except (StateError,RuntimeError,ValueError) as error:
            slicer.util.warningDisplay(str(error))
        self._refresh()

    def onHandHandover(self):
        try:
            self._mouse_command('claim_input',{'owner':'hand'})
        except StateError as error:
            slicer.util.warningDisplay(str(error))
        self._refresh()

    def onMouseHandover(self):
        try:
            self._refresh()
            self._mouse_command('claim_input', {'owner':'mouse'})
            self._mouse_command('arm')
            if self.logic.has_draft() and self.logic.controller.frozen:
                self._mouse_command('resume_draft')
        except StateError as error:
            slicer.util.warningDisplay(str(error))
        self._refresh()

    def _adjust(self, op, degrees):
        try:
            if op == "rotate":
                self._mouse_command('select_mode', {'mode':'rotate'})
                self._mouse_command('rotate_opening', {'delta_deg':degrees})
            elif op == "tilt":
                self._mouse_command('select_mode', {'mode':'tilt'})
                self._mouse_command('tilt', {'delta_deg':degrees})
            elif op == "reverse":
                self._mouse_command("reverse")
            else:
                self._mouse_command("reset_dir")
        except StateError as error:
            slicer.util.warningDisplay(str(error))
        self._refresh()

    def onStamp(self, checked):
        try:
            if checked:
                self._mouse_command('select_mode', {'mode':'aim'})
                self.logic.enter_aim_mode(self.surfaceCombo.currentNode())
            else:
                self.logic.exit_aim_mode()
        except (StateError, RuntimeError, ValueError) as error:
            slicer.util.warningDisplay(str(error))
            self.stampButton.setChecked(False)
        self._refresh()

    def onCommit(self):
        try:
            displayed = self.logic.display_contract.displayed
            if not displayed:
                raise StateError('仮Cの描画完了を待ってください')
            params = {k:displayed[k] for k in ('draft_id','rev','hash')}
            placement = displayed['placement']
            center = ', '.join(f'{v:.3f}' for v in placement['anchor'])
            normal = ', '.join(f'{v:.4f}' for v in placement['plane']['normal'])
            opening = ', '.join(f'{v:.4f}' for v in placement['opening_dir'])
            direction = '正方向' if placement['path_dir'] == 1 else '逆方向'
            answer = qt.QMessageBox.question(slicer.util.mainWindow(), 'C確定の確認',
                f"対象：{displayed['target']['model_name']}\n対象ID：{displayed['target'].get('target_id','未登録')}\n仮C：{displayed['draft_id']} 版{displayed['rev']}\n直径：{displayed['template']['radius']*2:g}mm\n中心（RAS mm）：{center}\n開口角：{placement['in_plane_angle']*180/3.141592653589793:.3f}°\n開口方向：{opening}\n面の法線：{normal}\n進行方向：{direction}\nhash：{displayed['hash']}\n確定しますか？",
                qt.QMessageBox.Yes | qt.QMessageBox.No)
            if answer == qt.QMessageBox.Yes:
                response = self._mouse_command('commit', params)
                self._mouse_commit_req = self.logic._request_context['req']
        except StateError as error:
            slicer.util.warningDisplay(str(error))
        self._refresh()

    def onLoadPlan(self):
        try:
            count = self._mouse_command('load_plan')['result']['planned']
            slicer.util.infoDisplay(
                f"計画 {count} 件を読込みました（次の計画をゴースト表示）"
            )
        except (StateError, RuntimeError, OSError) as error:
            slicer.util.warningDisplay(str(error))
        self._refresh()

    def onSkipPlan(self):
        try:
            self._mouse_command('skip_plan', {'plan_revision':self.logic._plan_binding()})
        except StateError as error:
            slicer.util.warningDisplay(str(error))
        self._refresh()

    def onCancel(self):
        try:
            self._mouse_command("cancel")
        except StateError as error:
            slicer.util.warningDisplay(str(error))
        self._refresh()

    def onReshape(self):
        try:
            self.logic.reshape_selected()
        except (StateError, RuntimeError) as error:
            slicer.util.warningDisplay(str(error))
        self._refresh()

    def onLoadLedger(self):
        try:
            count = self._mouse_command('load_session')['result']['restored']
            slicer.util.infoDisplay(
                f"確定イベント {count} 件を復元しました"
            )
        except (StateError, RuntimeError, OSError) as error:
            slicer.util.warningDisplay(str(error))
        self._refresh()

    def onOpeningSlider(self, value):
        try:
            draft = self.logic.controller.draft
            if draft is None:
                return
            self._mouse_command('select_mode', {'mode':'rotate'})
            self._mouse_command('rotate_opening', {'delta_deg':value-math.degrees(draft.placement.in_plane_angle)})
        except StateError:
            pass
        self._refresh()

    def onTiltSlider(self, value):
        draft = self.logic.controller.draft
        if draft is None:
            return
        old = getattr(self,'_tilt_slider_value',0)
        try:
            self._mouse_command('select_mode',{'mode':'tilt'})
            self._mouse_command('tilt',{'delta_deg':value-old})
            self._tilt_slider_value = value
        except StateError as error:
            slicer.util.warningDisplay(str(error))
        self._refresh()

    def onServerToggle(self, checked):
        try:
            if checked:
                self.logic.start_command_server(int(self.portEdit.text))
                self.logic._unified_hand_panel.attach_mouse_widget(self.parent)
            else:
                self.logic.stop_command_server()
        except (ValueError, RuntimeError) as error:
            slicer.util.warningDisplay(str(error))
            self.serverButton.setChecked(False)

    def onNewPlanRegistry(self):
        if self.logic.has_draft() or (self.logic.dispatcher and self.logic.dispatcher.armed):
            qt.QMessageBox.warning(self.parent, '準備できません', '仮Cを明示確定または取消し、操作を停止してください。')
            return
        path = qt.QFileDialog.getSaveFileName(self.parent, '新規計画台帳', '', 'JSONL (*.jsonl)')
        if isinstance(path, tuple): path = path[0]
        if not path: return
        try:
            with open(path, 'x', encoding='utf-8') as stream:
                stream.flush(); os.fsync(stream.fileno())
            self.registryEdit.text = path
            self.onSaveStorage()
        except OSError as error:
            qt.QMessageBox.warning(self.parent, '台帳を準備できません', str(error))

    def onSaveStorage(self):
        try:
            self.logic.configure_storage(self.ledgerEdit.text, self.registryEdit.text)
        except (OSError, ValueError, RuntimeError, KeyError) as error:
            self.storageFeedback.text = '保存できません：'+str(error)
            return
        self.storageFeedback.text = '保存しました。次回起動もこの台帳を使用します。'
        self._refresh()

    def _refresh(self):
        # preparation-side resources are registered here; wire commands
        # may only refer to these, not arbitrary paths (plan §共通契約)
        prepared = not self.logic.has_draft() and not (self.logic.dispatcher and self.logic.dispatcher.armed)
        self.newRegistryButton.setEnabled(prepared)
        self.saveStorageButton.setEnabled(prepared)
        for edit in (self.ledgerEdit, self.planEdit, self.registryEdit,self.surfaceCombo,
                     self.targetRegistryEdit, self.runtimeManifestEdit):
            edit.setEnabled(prepared)
        if prepared:
            self.logic.plan_path = self.planEdit.text
            self.logic.surface_node = self.surfaceCombo.currentNode()
            self.logic.target_registry_path = self.targetRegistryEdit.text
            self.logic.runtime_manifest_path = self.runtimeManifestEdit.text
        self.layerCombo.blockSignals(True)
        index = self.layerCombo.findData(self.logic.active_layer)
        if index >= 0:
            self.layerCombo.setCurrentIndex(index)
        self.layerCombo.blockSignals(False)
        self.statusLabel.text = self.logic.status_text()
        if self.logic._storage_error:
            self.storageFeedback.text = '台帳保存先を再指定して保存してください：'+self.logic._storage_error
        self._update_mouse_choices()
        self.mouseDetails.text = ('監査確認待ち：'+str(self.logic._pending_audit) if self.logic._pending_audit else '') + ('\n計画読込拒否：'+self.logic._registry_error if self.logic._registry_error else '')
        plan_view = self.logic._plan_view()
        if plan_view:
            delta = plan_view['difference_to_latest']
            self.mouseDetails.text += '\n計画%s 第%s版／最新保存%s版%s\n版hash：%s\n選択版→最新保存版：追加%s／削除%s／位置変更%s／方向変更%s' % (
                plan_view['plan_id'],plan_view['version'],plan_view['latest_version'],
                '（比較専用・編集不可）' if plan_view['read_only'] else '',plan_view['hash'],
                len(delta['added']),len(delta['removed']),len(delta['moved']),len(delta['rotated']))
        if self.logic._target_error:
            self.mouseDetails.text += '\n'+self.logic._target_error
        draft = self.controller_draft_angle()
        self.openingSlider.blockSignals(True)
        self.openingSlider.value = draft
        self.openingSlider.blockSignals(False)
        current = self.logic.controller.draft
        if current:
            initial = current.initial_placement
            angle = math.degrees(math.atan2(-sum(current.placement.normal[i]*initial.v[i] for i in range(3)),
                                           sum(current.placement.normal[i]*initial.normal[i] for i in range(3))))
        else:
            angle = 0
        self._tilt_slider_value = angle
        self.tiltSlider.blockSignals(True)
        self.tiltSlider.value = round(angle)
        self.tiltSlider.blockSignals(False)

    def controller_draft_angle(self):
        draft = self.logic.controller.draft
        if draft is None or self.logic.controller.frozen:
            return 0
        return int(math.degrees(draft.placement.in_plane_angle))


class CStampModuleLogic(ScriptedLoadableModuleLogic):
    """Bridges the pure cstamp state machine to MRML display nodes.

    DRAFT  -> single cyan curve node named CStamp-DRAFT (仮配置)
    COMMITTED -> one point in the CStamp-PERFORMED fiducial list plus a
                 hidden full-C curve node (read-only reconstruction)
    """

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        self.template = CTemplate(radius=2.5)  # Baseline diameter 5 mm specified by user (2026-10-12).
        self.controller = CStampController(template=self.template, id_factory=lambda: "draft-"+uuid.uuid4().hex)
        self._committed: dict[str, dict] = {}
        self._aim_observer = None
        self._aim_model = None
        self._command_server = None
        self.dispatcher: CommandDispatcher | None = None
        self._plan = PlanTracker()
        self._last_match = None
        self.display_contract = DisplayContract()
        self._target_binding = None
        self._request_context = {}
        self._pending_audit = None
        self._selected_plan_item = None
        self.creator_candidates = ['operator', 'demo_reviewer']
        self._creator = 'operator'
        self.storage_registry = {'default': DEFAULT_LEDGER_PATH}
        self._series_id = 'nonclinical-cstamp-series'
        self.on_stamp_done = None
        # registered (preparation-time) resources; wire commands may only
        # use these, never arbitrary paths (plan §共通契約)
        self.ledger_path = DEFAULT_LEDGER_PATH
        self.plan_path = ""
        self.surface_node = None
        self.target_registry_path = os.environ.get('CSTAMP_TARGET_REGISTRY', os.path.join(_DATA_ROOT, 'artifacts', 'cstamp', 'targets.json'))
        self._target_error = ''
        self.runtime_manifest_path = os.environ.get('CSTAMP_RUNTIME_MANIFEST', os.path.join(_DATA_ROOT, 'artifacts', 'cstamp', 'runtime.json'))
        self._scene_digest_cache = None
        self.scene_reference = os.environ.get('CSTAMP_SCENE_REFERENCE') or None
        self.active_layer = "PERFORMED"
        # non-contact aim state and hand-operation bookkeeping
        self._aim: dict = {"valid": False, "anchor": None, "normal": None,
                           "nx": 0.0, "ny": 0.0}
        self._correction_of = None
        self._selected_event_id = None
        self._menu_open = False
        self._menu_index = 0
        self.on_state_changed = None  # widget refresh hook
        # plan revision registry and audit bookkeeping (docs/23 unit 7)
        self._plan_store = PlanStore()
        self.plan_registry_path = DEFAULT_PLAN_REGISTRY_PATH
        self.storage_selection_path = os.environ.get('CSTAMP_STORAGE_SELECTION',
            os.path.join(os.path.dirname(DEFAULT_LEDGER_PATH), 'storage-selection.json'))
        self._storage_error = ''
        try:
            stored = load_selection(self.storage_selection_path)
            if stored:
                self.ledger_path, self.plan_registry_path = stored['events'], stored['plans']
                self.storage_registry['default'] = self.ledger_path
        except (OSError, ValueError, KeyError, RuntimeError) as error:
            self._storage_error = str(error)
            self.ledger_path = self.plan_registry_path = ''
            self.storage_registry = {}
        self._registry_error = ''
        self._pending_reason = None
        self._pending_reason_binding = None
        self._pending_out_of_plan = False
        self._revoked: set[str] = set()
        # preparation-registered reason categories; select_reason only
        # accepts one of these — free-text reasons are rejected (docs/23)
        self.reason_candidates = [
            "operator", "position_changed", "visibility",
            "plan_superseded", "out_of_plan",
        ]
        # baseline camera pose captured on first 3D view access;
        # reset_view restores exactly this (no C data touched)
        self._baseline_camera = None

    # --- status ---------------------------------------------------------

    def configure_storage(self, events, plans):
        if self.has_draft() or (self.dispatcher and self.dispatcher.armed):
            raise StateError('仮Cを明示確定または取消し、操作を停止してください')
        if self._pending_audit or any(p.working is not None for p in self._plan_store.plans.values()):
            raise StateError('未保存の計画・監査を完了してから保存先を変更してください')
        selected = save_selection(self.storage_selection_path, events, plans)
        events_changed = self.ledger_path != selected['events']
        changed = (self.ledger_path, self.plan_registry_path) != (selected['events'], selected['plans'])
        self.ledger_path, self.plan_registry_path = selected['events'], selected['plans']
        self.storage_registry = {'default': self.ledger_path}
        self._storage_error = ''
        if changed:
            self._active_plan = None
            self._selected_plan_item = self._selected_event_id = None
            self._plan = PlanTracker()
            self._plan_store = PlanStore()
            self._registry_loaded_path = None
            self._pending_reason = self._pending_reason_binding = None
            self._correction_of = None
            self._pending_out_of_plan = False
            self._update_ghost()
        if events_changed:
            # Old scene overlays remain visible; only events explicitly loaded
            # from this ledger may become correction/revocation targets.
            self._committed = {}
            self._revoked = set()
        self._ensure_plan_registry()
        return selected

    def status_text(self) -> str:
        draft = self.controller.draft
        suffix = f" / {draft.draft_id}" if draft else ""
        frozen = " / frozen" if self.controller.frozen else ""
        aim = " / 照準中" if self._aim_observer else ""
        text = f"状態: {self.controller.state.value}{suffix}{frozen}{aim}"
        if self.dispatcher is not None:
            armed = "受付中" if self.dispatcher.armed else "受付停止"
            owner = 'マウス' if self.dispatcher.input_owner == 'mouse' else 'ハンド' 
            text += (
                f"\n入力:{owner} {armed} / モード: {self.dispatcher.mode}"
                f" / レイヤー: {self.active_layer}"
            )
            if self._aim["valid"]:
                text += " / 照準: 有効"
            elif self.dispatcher.mode in ("aim", "move"):
                text += " / 照準: 表面外"
            if self._menu_open:
                items = self._menu_items()
                shown = " > ".join(
                    f"[{i['label']}]" if n == self._menu_index
                    else i["label"]
                    for n, i in enumerate(items)
                )
                text += f"\nメニュー: {shown}"
        if self._plan.entries:
            s = self._plan.status()
            text += (
                f"\n計画: 残{s['remaining']}/{s['total']}"
                f" (一致{s['matched']} スキップ{s['skipped']}"
                f" 計画外{s['out_of_plan']})"
            )
        if self._last_match is not None:
            m = self._last_match
            if m.matched:
                text += (
                    f"\n照合: 計画{m.planned_event_id[:8]} "
                    f"Δ位置{m.anchor_delta_mm:.1f}mm"
                    f" Δ法線{m.normal_delta_deg:.1f}°"
                )
            else:
                text += "\n照合: 計画外の操作として記録"
        return text

    # --- aim / stamp -----------------------------------------------------

    def enter_aim_mode(self, model_node):
        """Next left click in the 3D view places one DRAFT on the allowed
        surface (AIM_SURFACE -> STAMP_DRAFT)."""
        if model_node is None:
            raise RuntimeError("対象表面のモデルノードを選択してください")
        if self._aim_observer:
            return
        self._aim_model = model_node
        interactor = (
            slicer.app.layoutManager()
            .threeDWidget(0)
            .threeDView()
            .interactor()
        )
        self._aim_observer = interactor.AddObserver(
            vtk.vtkCommand.LeftButtonPressEvent, self._on_aim_click, 1.0
        )
        self._mouse_dragging = False
        self._move_observer = interactor.AddObserver(vtk.vtkCommand.MouseMoveEvent,self._on_mouse_move,1.0)
        self._release_observer = interactor.AddObserver(vtk.vtkCommand.LeftButtonReleaseEvent,self._on_mouse_release,1.0)

    def exit_aim_mode(self):
        if not self._aim_observer:
            return
        interactor = (
            slicer.app.layoutManager()
            .threeDWidget(0)
            .threeDView()
            .interactor()
        )
        interactor.RemoveObserver(self._aim_observer)
        for name in ('_move_observer','_release_observer'):
            token = getattr(self,name,None)
            if token is not None:
                interactor.RemoveObserver(token)
                setattr(self,name,None)
        self._mouse_dragging = False
        self._aim_observer = None
        self._aim_model = None

    def _on_mouse_move(self, interactor, _event):
        if getattr(self,'_mouse_dragging',False):
            try:
                interactor.GetCommand(self._move_observer).SetAbortFlag(1)
                self._stamp_at_position(interactor,self._aim_model)
            except (StateError,RuntimeError):
                self._mouse_dragging = False
                self.exit_aim_mode()

    def _on_mouse_release(self, interactor, _event):
        if getattr(self,'_mouse_dragging',False):
            self.exit_aim_mode()
            if self.on_stamp_done:
                self.on_stamp_done()

    def _on_aim_click(self, interactor, _event):
        moving = self.dispatcher and self.dispatcher.mode == 'move'
        self._mouse_dragging = moving
        try:
            interactor.GetCommand(self._aim_observer).SetAbortFlag(1)
            self._stamp_at_position(interactor, self._aim_model)
        except (StateError, RuntimeError) as error:
            slicer.util.warningDisplay(str(error))
        finally:
            if not moving:
                self.exit_aim_mode()
                if self.on_stamp_done:
                    self.on_stamp_done()

    def _stamp_at_position(self, interactor, model_node):
        x, y = interactor.GetEventPosition()
        width, height = interactor.GetRenderWindow().GetSize()
        if not self.dispatcher:
            raise StateError('explicitly hand over to mouse first')
        params = {'nx':x/max(width,1), 'ny':1-y/max(height,1)}
        command = 'select_event' if self.dispatcher.mode == 'review' else 'move_draft' if self.has_draft() else 'aim'
        response = self.dispatcher.dispatch_local(command, params, input_method='mouse')
        if not response.get('ok'):
            raise StateError(response.get('reason','surface selection rejected'))
        if command == 'aim':
            response = self.dispatcher.dispatch_local('stamp', input_method='mouse')
            if not response.get('ok'):
                raise StateError(response.get('reason','stamp rejected'))

    def _three_d_view(self):
        layout = slicer.app.layoutManager()
        if layout is None:
            raise RuntimeError("3Dビューがありません")
        return layout.threeDWidget(0).threeDView()

    def _renderer(self):
        view = self._three_d_view()
        render_window = view.renderWindow()
        if render_window is None:
            raise RuntimeError("レンダーウィンドウがありません")
        renderer = render_window.GetRenderers().GetFirstRenderer()
        return view, renderer

    def _raycast_surface(self, nx: float, ny: float, model_node):
        """Normalized view coords (0..1, y top-down like the camera
        image) -> (anchor, normal) on the allowed surface, or None."""
        view, renderer = self._renderer()
        width, height = view.renderWindow().GetSize()
        x = max(0.0, min(1.0, nx)) * width
        y = (1.0 - max(0.0, min(1.0, ny))) * height
        return self._intersect_display(renderer, x, y, model_node)

    def _intersect_display(self, renderer, x, y, model_node):
        renderer.SetDisplayPoint(x, y, 0.0)
        renderer.DisplayToWorld()
        near = list(renderer.GetWorldPoint()[:3])
        renderer.SetDisplayPoint(x, y, 1.0)
        renderer.DisplayToWorld()
        far = list(renderer.GetWorldPoint()[:3])

        polydata = model_node.GetPolyData()
        if polydata is None or polydata.GetNumberOfCells() == 0:
            raise RuntimeError("対象表面にポリゴンデータがありません")
        parent = model_node.GetParentTransformNode()
        if parent is not None:
            matrix = vtk.vtkMatrix4x4()
            if not parent.GetMatrixTransformToWorld(matrix):
                raise StateError('nonlinear target transform is not permitted')
            transform = vtk.vtkTransform()
            transform.SetMatrix(matrix)
            world_filter = vtk.vtkTransformPolyDataFilter()
            world_filter.SetInputData(polydata)
            world_filter.SetTransform(transform)
            world_filter.Update()
            polydata = world_filter.GetOutput()
        locator = vtk.vtkCellLocator()
        locator.SetDataSet(polydata)
        locator.BuildLocator()
        t = vtk.mutable(0.0)
        hit_point = [0.0, 0.0, 0.0]
        pcoords = [0.0, 0.0, 0.0]
        sub_id = vtk.mutable(0)
        cell_id = vtk.mutable(0)
        hit = locator.IntersectWithLine(
            near, far, 1e-6, t, hit_point, pcoords, sub_id, cell_id
        )
        if not hit:
            return None
        cell = polydata.GetCell(cell_id.get())
        p0 = cell.GetPoints().GetPoint(0)
        p1 = cell.GetPoints().GetPoint(1)
        p2 = cell.GetPoints().GetPoint(2)
        e1 = [p1[i] - p0[i] for i in range(3)]
        e2 = [p2[i] - p0[i] for i in range(3)]
        normal = [
            e1[1] * e2[2] - e1[2] * e2[1],
            e1[2] * e2[0] - e1[0] * e2[2],
            e1[0] * e2[1] - e1[1] * e2[0],
        ]
        length = math.sqrt(sum(c * c for c in normal))
        if length < 1e-12:
            return None
        return tuple(hit_point), tuple(c / length for c in normal)

    def stamp_on_surface(self, anchor, normal, model_node):
        """Create the DRAFT at a known surface point (also used by the
        headless verification without an interactor)."""
        self.controller.stamp(anchor, normal)
        self._draft_surface_name = model_node.GetName()
        self._update_draft_curve()

    # --- adjustment -----------------------------------------------------

    def rotate(self, delta):
        self.controller.rotate_opening(delta)
        self._update_draft_curve()

    def rotate_to(self, absolute_angle):
        """Set the opening direction to an absolute in-plane angle
        (continuous adjustment via the slider)."""
        draft = self.controller.draft
        if draft is None:
            raise StateError("no active DRAFT")
        delta = absolute_angle - draft.placement.in_plane_angle
        if delta:
            self.controller.rotate_opening(delta)
            self._update_draft_curve()

    def tilt(self, delta):
        self.controller.tilt_plane(0.0, delta)
        self._update_draft_curve()

    def reverse(self):
        self.controller.reverse_path()
        self._update_draft_curve()

    def reset(self):
        self.controller.reset_direction()
        self._update_draft_curve()

    # --- commit / cancel -------------------------------------------------

    def commit(self, ledger_path, layer="PERFORMED",
               input_method="mouse", expected_revision=None):
        if not ledger_path:
            raise StateError("台帳パスを指定してください")
        ledger = EventLedger(self.plan_registry_path if layer == 'PLANNED' else ledger_path)
        if layer == 'PLANNED':
            plan_id = getattr(self, '_active_plan', None)
            if not plan_id or self._plan_store.get(plan_id).working is None:
                raise StateError('begin a plan working version before placing planned C')
        model_name = getattr(self, "_draft_surface_name", "")
        declared_out_of_plan = self._pending_out_of_plan
        if declared_out_of_plan:
            self._require_reason()
        event = {
            "event_kind": "cstamp",
            "layer": layer,
            "scene": {
                "model_node": model_name,
                "coordinate_system": {
                    "name": "RAS",
                    "units": "mm",
                    "axes": "Slicer RAS",
                },
            },
            "input_method": input_method,
            "correction_of": self._correction_of,
            "out_of_plan_declared": declared_out_of_plan or None,
            "revoked": False,
            'series_id': self._series_id,
            'time_source': 'system UTC',
            'target_identity': self._target_identity(),
            'displayed_snapshot': copy.deepcopy(self.display_contract.displayed),
            'request_receipt': copy.deepcopy(self._request_context),
            'render_ack_ns': self.display_contract.acknowledged_ns,
            'reason': self._pending_reason if declared_out_of_plan else None,
            'planned_event_id': self._plan.current.event_id if layer == 'PERFORMED' and self._plan.current and not declared_out_of_plan else None,
            'plan_delta': self._draft_plan_delta() if layer == 'PERFORMED' and not declared_out_of_plan else None,
        }
        def persist(candidate):
            candidate['save_started_ns'] = time.perf_counter_ns()
            if layer != 'PLANNED':
                return ledger.append(candidate)
            # Prepare a complete working registry copy before the single durable write.
            staged = PlanStore()
            staged.plans = copy.deepcopy(self._plan_store.plans)
            item = copy.deepcopy(candidate)
            import uuid
            item.setdefault('event_id', uuid.uuid4().hex)
            if self._selected_plan_item:
                staged.replace_rendered_geometry(self._active_plan, self._selected_plan_item,
                                 {k:item[k] for k in ('placement','shape_points','template','target_identity','displayed_snapshot')})
            else:
                staged.add_item(self._active_plan, item)
            working = staged.get(self._active_plan).working
            candidate.update({'event_id':item['event_id'], 'record_type':'planned_item_commit',
                              'plan_id':working.plan_id, 'version':working.version,
                              'working_items':copy.deepcopy(working.items),
                              'creator':working.creator, 'approval':working.approval,
                              'created_ts':working.created_ts})
            saved = ledger.append(candidate)
            self._plan_store = staged
            return saved
        stored = self.controller.commit(
            persist, event, expected_revision=expected_revision
        )
        self._last_save_timing = {'req':self._request_context.get('req'), 'event_id':stored.get('event_id'),
                                  'persisted_ns':getattr(ledger,'last_persisted_ns',None),
                                  'render_ack_ns':self.display_contract.acknowledged_ns}
        if stored.get("deduplicated"):
            return stored
        self._selected_plan_item = None
        self._correction_of = None
        self._pending_out_of_plan = False
        self._pending_reason = None
        self._committed[stored["event_id"]] = stored
        self._replace_draft_curve_with_committed(stored)
        if layer == "PERFORMED" and self._plan.entries:
            if declared_out_of_plan:
                # explicitly declared out-of-plan: consume no planned
                # entry, record the declaration (AC-024)
                self._last_match = None
                self._plan.out_of_plan_ids.append(stored["event_id"])
            else:
                self._last_match = self._plan.record_performed(stored, active_only=True)
            # The active target and geometric deltas were saved in the C event
            # in the same atomic write; no second append can partially succeed.
            self._update_ghost()
        return stored

    def cancel(self):
        self.controller.cancel()
        self._correction_of = None
        self._remove_node(DRAFT_CURVE_NAME)

    # --- re-display -------------------------------------------------------

    def reshape_selected(self):
        """Re-display the full C of the selected committed point
        (read-only, FR-026 / AC-016)."""
        points = self._performed_points()
        index = -1
        for i in range(points.GetNumberOfControlPoints()):
            if points.GetNthControlPointSelected(i):
                index = i
                break
        if index < 0:
            raise RuntimeError("確定点を選択してください")
        label = points.GetNthControlPointLabel(index)
        event_id = label.split(":", 1)[1] if ":" in label else None
        stored = self._committed.get(event_id)
        if stored is None:
            raise RuntimeError("選択した点の確定イベントが見つかりません")
        shape = self._shape_node(event_id)
        shape.SetDisplayVisibility(True)

    # --- ledger reload ----------------------------------------------------

    def load_ledger(self, ledger_path):
        """Restore every committed event from the JSONL ledger into the
        scene: one fiducial point plus a hidden full-C curve per event.
        Already-restored events are skipped (AC-008/018)."""
        ledger = EventLedger(ledger_path)
        events = ledger.events()
        current_target = self._target_identity()
        for event in events:
            if event.get('event_kind') == 'cstamp' and event.get('target_identity') != current_target:
                raise StateError('ledger target identity mismatch; no events restored')
        self._revoked.update(e['target_event_id'] for e in events if e.get('record_type') == 'event_revoked')
        restored = 0
        for stored in events:
            # skip match records and non-performed layers
            if stored.get("record_type") or "placement" not in stored:
                continue
            if stored.get("layer", "PERFORMED") != "PERFORMED":
                continue
            event_id = stored["event_id"]
            if event_id in self._committed or self._point_exists(event_id):
                self._committed[event_id] = stored
                continue
            self._committed[event_id] = stored
            placement = placement_from_dict(stored["placement"])
            curve = self._curve_node(
                f"{PERFORMED_SHAPE_PREFIX}{event_id}"
            )
            curve.RemoveAllControlPoints()
            for p in stored.get("shape_points") or placement.transform_points(
                CTemplate().local_points(placement.path_dir)
            ):
                curve.AddControlPointWorld(vtk.vtkVector3d(*p))
            display = curve.GetDisplayNode()
            display.SetColor(0.2, 0.5, 1.0)
            curve.SetDisplayVisibility(False)

            points = self._performed_points()
            index = points.AddControlPointWorld(
                vtk.vtkVector3d(*stored["placement"]["anchor"])
            )
            points.SetNthControlPointLabel(
                index, f"操作記録:{event_id}"
            )
            points.GetDisplayNode().SetColor(1.0, 0.2, 0.2)
            restored += 1
        return restored

    def _point_exists(self, event_id: str) -> bool:
        """True if the performed list already holds this event's point
        (makes reload idempotent across logic instances)."""
        try:
            points = slicer.util.getNode(PERFORMED_POINTS_NAME)
        except slicer.util.MRMLNodeNotFoundException:
            return False
        for i in range(points.GetNumberOfControlPoints()):
            if points.GetNthControlPointLabel(i).endswith(event_id):
                return True
        return False

    # --- plan following (PLANNED layer) -------------------------------------

    def load_plan(self, plan_path: str) -> int:
        """Load PLANNED-layer events from a ledger file and show the
        next planned C as the ghost target."""
        if not plan_path:
            raise StateError("計画ファイルパスを指定してください")
        ledger = EventLedger(plan_path)
        planned = [
            e
            for e in ledger.events()
            if not e.get("record_type")
            and e.get("layer") == "PLANNED"
            and "placement" in e
        ]
        if not planned:
            raise RuntimeError("計画イベント(PLANNED)が見つかりません")
        self._plan.load(planned)
        for entry in self._plan.entries:
            self._committed[entry.event_id] = entry.event
        self._update_ghost()
        return len(planned)

    def skip_planned(self):
        entry = self._plan.skip_current()
        self._update_ghost()
        if entry is None:
            raise StateError("スキップできる計画がありません")
        return entry

    def _update_ghost(self):
        """Show the current planned C as a dim green ghost curve
        (AC-020). Removed when the plan is finished."""
        current = self._plan.current
        if current is None:
            self._remove_node(GHOST_CURVE_NAME)
            return
        node = self._curve_node(GHOST_CURVE_NAME)
        node.SetName(GHOST_CURVE_NAME)
        node.RemoveAllControlPoints()
        for p in current.event.get("shape_points", []):
            node.AddControlPointWorld(vtk.vtkVector3d(*p))
        display = node.GetDisplayNode()
        display.SetColor(0.2, 0.9, 0.4)
        display.SetSelectedColor(0.2, 0.9, 0.4)
        display.SetOpacity(0.45)
        node.SetDisplayVisibility(True)

    # --- hand-command ops (CommandDispatcher target) ----------------------
    #
    # Every op_* method is reachable only through the dispatcher's
    # envelope/armed/mode/draft gates. Anything not on the allowlist is
    # inert; no arbitrary Python or node editing is exposed.

    def has_draft(self):
        return (
            self.controller.state is StampState.DRAFT
            and self.controller.draft is not None
        )

    def on_session_reset(self):
        """New session: keep the frozen draft, drop hand-specific UI
        state. Never auto-arms (plan §共通契約)."""
        self._menu_open = False
        self._menu_index = 0
        self._selected_event_id = None
        self._correction_of = None
        if self.has_draft():
            self.controller.on_recognition_loss()
        self._notify_state()

    def on_disconnect(self):
        """Transport loss: freeze (not cancel) an active draft."""
        if self.has_draft():
            self.controller.on_recognition_loss()
        self._menu_open = False
        self._notify_state()

    def _notify_state(self):
        if self.on_state_changed:
            try:
                self.on_state_changed()
            except Exception:  # noqa: BLE001
                pass

    def op_arm(self, params):
        self._notify_state()
        return {"ok": True}

    def op_disarm(self, params):
        self._menu_open = False
        if self.has_draft():
            self.controller.on_recognition_loss()
        self._notify_state()
        return {"ok": True}

    def op_size_settings(self, params):
        panel = getattr(self, '_unified_hand_panel', None)
        if panel is not None:
            panel.show_size()
            return {"ok": True}
        from size_settings import show_size_settings
        show_size_settings(self)
        return {"ok": True}

    def op_status(self, params):
        return {"ok": True, "result": {
            "text": self.status_text(),
            "state": self.controller.state.value,
            "frozen": self.controller.frozen,
            "diameter_mm": self.controller.template.radius * 2.0,
            "draft_diameter_mm": self.controller.draft_template.radius * 2.0 if self.has_draft() else None,
            "rev": self.controller.draft.revision if self.has_draft() else None,
            "aim_valid": self._aim["valid"],
            "layer": self.active_layer,
            "plan": self._plan.status() if self._plan.entries else None,
            'displayed': copy.deepcopy(self.display_contract.displayed),
            'pending_audit': copy.deepcopy(self._pending_audit),
            'choices': self._registered_choices(),
            'plan_revision': self._plan_binding(),
            'plan_view': self._plan_view(),
            'plan_delta': self._draft_plan_delta(),
            'selected_plan_item': self._selected_plan_item,
            'reorder_selection': self._reorder_selection(),
            'view_application': copy.deepcopy(getattr(self, '_last_view_application', None)),
        }}

    def op_diagnose(self, params):
        """Read-only per-gate report; never rejects and never mutates.
        Answers 'which blocks are failing' in one pass instead of
        discovering each gate sequentially through rejected commands."""
        checks = []
        def check(name, fn):
            try:
                detail = fn()
                checks.append({'name': name, 'ok': True, 'detail': detail})
            except Exception as error:
                checks.append({'name': name, 'ok': False, 'detail': str(error)})
        check('storage', self._diagnose_storage)
        policy = [None]
        def load_policy():
            policy[0] = RuntimePolicy.load(self.runtime_manifest_path)
            return policy[0].sha256[:16]
        check('runtime_manifest', load_policy)
        if policy[0] is not None:
            def sources():
                self._verify_slicer_sources(policy[0])
                return '%d files' % len(_LOADED_SOURCE_HASHES)
            check('slicer_sources', sources)
            def version():
                actual = str(slicer.app.applicationVersion)
                expected = policy[0].document['slicer_version']
                if actual != expected:
                    raise StateError('actual %s != prepared %s' % (actual, expected))
                return actual
            check('slicer_version', version)
        registry = [None]
        def load_registry():
            registry[0] = TargetRegistry.load(self.target_registry_path)
            return '%d target(s)' % len(registry[0].document['targets'])
        check('target_registry_file', load_registry)
        if policy[0] is not None and registry[0] is not None:
            def registry_match():
                expected = policy[0].document['target_registry_sha256']
                if registry[0].sha256 != expected:
                    raise StateError('registry %s != prepared %s' % (registry[0].sha256[:12], expected[:12]))
                return registry[0].sha256[:16]
            check('registry_matches_manifest', registry_match)
        if registry[0] is not None:
            check('target_identity', lambda: self._diagnose_target(registry[0]))
        check('surface_node', self._diagnose_surface)
        dispatcher = self.dispatcher
        return {'ok': True, 'result': {
            'checks': checks,
            'all_ok': all(item['ok'] for item in checks),
            'state': {
                'armed': bool(dispatcher.armed) if dispatcher else None,
                'mode': dispatcher.mode if dispatcher else None,
                'layer': dispatcher.layer if dispatcher else None,
                'draft': self.has_draft(),
                'input_owner': dispatcher.input_owner if dispatcher else None,
                'session': bool(dispatcher.session) if dispatcher else None,
                'foreground': bool(self.foreground_ok()),
            },
        }}

    def _diagnose_storage(self):
        if self._storage_error:
            raise StateError(self._storage_error)
        return 'ledger=%s' % (self.ledger_path or 'none')

    def _diagnose_target(self, registry):
        try:
            observed = self._observe_target_identity()
        except Exception as error:
            raise StateError('observation unavailable: %s' % error)
        best = None
        for row in registry.document['targets']:
            diff = {}
            for key in ('scene_id', 'model_name', 'model_sha256', 'transform_sha256', 'scene_sha256'):
                expected = row.get(key)
                if expected is not None and expected != observed.get(key):
                    diff[key] = (str(expected)[:12], str(observed.get(key))[:12])
            if best is None or len(diff) < len(best):
                best = diff
        if best:
            raise StateError('; '.join('%s expected %s actual %s' % (key, value[0], value[1])
                                       for key, value in sorted(best.items())))
        return 'target matched: %s' % observed['model_name']

    def _diagnose_surface(self):
        node = self._surface()
        if node is None:
            raise StateError('permitted surface unavailable')
        return node.GetName()

    def _reorder_selection(self):
        ids = [entry.event_id for entry in self._plan.entries]
        if self.active_layer == 'PLANNED' and self._active_plan in self._plan_store.plans:
            plan = self._plan_store.get(self._active_plan)
            ids = [item.get('event_id') or item.get('item_id') for item in (plan.working or plan.current).items]
        index = ids.index(self._selected_plan_item) if self._selected_plan_item in ids else 0
        return {'from_index': index, 'to_index': (index + 1) % len(ids) if ids else -1}

    def op_select_mode(self, params):
        self._notify_state()
        return {"ok": True, "result": {"mode": params["mode"]}}

    def op_select_layer(self, params):
        self.active_layer = params["layer"]
        self._notify_state()
        return {"ok": True, "result": {"layer": self.active_layer}}

    # --- view ------------------------------------------------------------

    def _view_command(self, payload):
        """Validate through view_commands.parse_command (identical caps)
        and apply to the first 3D view camera."""
        command = parse_command(json.dumps(payload))
        if command is None:
            return {"ok": False, "reason": "invalid view command"}
        try:
            view = self._three_d_view()
        except RuntimeError:
            return {"ok": False, "reason": "no 3D view"}
        camera_node = view.cameraNode()
        if camera_node is None:
            return {"ok": False, "reason": "no camera"}
        camera = camera_node.GetCamera()
        self._capture_baseline(camera)
        def camera_values():
            return {'position': list(camera.GetPosition()), 'focal': list(camera.GetFocalPoint()),
                    'distance': camera.GetDistance(), 'parallel_scale': camera.GetParallelScale(),
                    'view_angle': camera.GetViewAngle(), 'clipping_range': list(camera.GetClippingRange())}
        before = camera_values()
        apply_to_camera(camera, command)
        camera.Modified()
        # Dolly/rotation changes eye-space depth. Keeping the old planes can
        # clip the entire model even though the command and render succeeded.
        view.renderWindow().GetRenderers().GetFirstRenderer().ResetCameraClippingRange()
        application = {'req': getattr(self, '_request_context', {}).get('req'),
                       'cmd': payload['cmd'], 'before': before, 'after': camera_values(),
                       'applied_ns': time.perf_counter_ns(), 'rendered_ns': None}
        self._last_view_application = application
        window = view.renderWindow()
        old = getattr(self, '_view_render_observer', None)
        if old:
            old[0].RemoveObserver(old[1])
        def rendered(_caller, _event):
            application['rendered_ns'] = time.perf_counter_ns()
            window.RemoveObserver(token)
            if getattr(self, '_view_render_observer', None) == (window, token):
                self._view_render_observer = None
        token = window.AddObserver(vtk.vtkCommand.EndEvent, rendered)
        self._view_render_observer = (window, token)
        view.scheduleRender()
        return {"ok": True, 'result': {'view_application': copy.deepcopy(application)}}

    def op_view_rotate(self, params):
        return self._view_command({
            "cmd": "rotate",
            "dx": params.get("dx"),
            "dy": params.get("dy"),
        })

    def op_view_pan(self, params):
        return self._view_command({
            "cmd": "pan",
            "dx": params.get("dx"),
            "dy": params.get("dy"),
        })

    def op_zoom(self, params):
        return self._view_command({
            "cmd": "zoom",
            "ratio": params.get("ratio"),
        })

    def foreground_ok(self):
        """True when this Slicer process owns the foreground window.

        Uses Win32 GetForegroundWindow + process-id comparison: it is
        non-blocking and does not re-enter Qt widget state, so it is
        safe to call from inside the QTcpServer socket callback. A
        headless run has no main window at all — there is no window to
        lose, so the gate is satisfied there (tests/headless only).
        When a window exists but another process is foreground, the
        dispatcher blocks all editing and view commands (SR-006)."""
        try:
            window = slicer.util.mainWindow()
        except Exception:  # noqa: BLE001
            window = None
        if window is None:
            return True
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return False
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            return int(pid.value) == os.getpid()
        except Exception:  # noqa: BLE001
            # cannot determine foreground -> fail closed
            return False

    def _capture_baseline(self, camera):
        if self._baseline_camera is None:
            self._baseline_camera = {
                "position": list(camera.GetPosition()),
                "focal": list(camera.GetFocalPoint()),
                "view_up": list(camera.GetViewUp()),
                'parallel_projection':camera.GetParallelProjection(),
                'parallel_scale':camera.GetParallelScale(),
                'view_angle':camera.GetViewAngle(),
            }

    def op_reset_view(self, params):
        """Restore the baseline camera pose captured at first use.
        Camera only — model, draft, and ledger are untouched.
        (RESET_VIEW adoption decision: plan §決定事項, docs/01/10)"""
        try:
            view = self._three_d_view()
        except RuntimeError:
            return {"ok": False, "reason": "no 3D view"}
        camera_node = view.cameraNode()
        if camera_node is None:
            return {"ok": False, "reason": "no camera"}
        if self._baseline_camera is None:
            self._capture_baseline(camera_node.GetCamera())
            return {"ok": True, "result": {"baseline_recorded": True}}
        base = self._baseline_camera
        camera = camera_node.GetCamera()
        camera.SetPosition(*base["position"])
        camera.SetFocalPoint(*base["focal"])
        camera.SetViewUp(*base["view_up"])
        camera.SetParallelProjection(base['parallel_projection'])
        camera.SetParallelScale(base['parallel_scale'])
        camera.SetViewAngle(base['view_angle'])
        camera.Modified()
        view.scheduleRender()
        return {"ok": True, "result": {"restored": True}}

    # --- aim / stamp / draft edit -----------------------------------------

    def _surface(self):
        if self.surface_node is None:
            return None
        if self.surface_node.GetScene() != slicer.mrmlScene:
            return None
        try:
            polydata = self.surface_node.GetPolyData()
        except AttributeError:
            return None
        if polydata is None or polydata.GetNumberOfCells() == 0:
            return None
        if self.surface_node.GetName() != DEFAULT_SURFACE_NAME:
            return None
        current = self._target_identity()
        if self._target_binding is None:
            self._target_binding = current
        elif current != self._target_binding:
            self._aim['valid'] = False
            self.controller.on_recognition_loss()
            return None
        return self.surface_node

    def _observe_target_identity(self):
        node = self.surface_node
        if node is None:
            raise StateError('no permitted surface')
        if node.GetScene() != slicer.mrmlScene:
            raise StateError('permitted surface was removed from the current scene')
        poly = node.GetPolyData()
        if poly is None:
            raise StateError('no permitted surface data')
        from vtk.util.numpy_support import vtk_to_numpy
        h = hashlib.sha256()
        for array in (poly.GetPoints().GetData(), poly.GetPolys().GetData()):
            h.update(vtk_to_numpy(array).tobytes())
        transform = vtk.vtkMatrix4x4()
        parent = node.GetParentTransformNode()
        if parent is not None and not parent.GetMatrixTransformToWorld(transform):
            raise StateError('nonlinear target transform is not permitted')
        matrix = [[transform.GetElement(i,j) for j in range(4)] for i in range(4)]
        scene_id = self.scene_reference or slicer.mrmlScene.GetURL() or 'nonclinical-demo'
        scene_hash = None
        if scene_id != 'nonclinical-demo' and os.path.isfile(scene_id):
            scene_stat = os.stat(scene_id)
            cache_key = (scene_id, scene_stat.st_mtime_ns, scene_stat.st_size)
            if self._scene_digest_cache and self._scene_digest_cache[0] == cache_key:
                scene_hash = self._scene_digest_cache[1]
            else:
                scene_hash = self._hash_scene_file(scene_id)
                self._scene_digest_cache = (cache_key, scene_hash)
        observed = {'model_name': node.GetName(),
                'model_sha256': h.hexdigest(), 'transform': matrix,
                'scene_id': scene_id, 'scene_sha256': scene_hash,
                'transform_sha256': digest(matrix)}
        return observed

    def _target_identity(self):
        observed = self._observe_target_identity()
        try:
            registered = TargetRegistry.load(self.target_registry_path).match(observed)
        except (OSError, ValueError) as error:
            self._aim['valid'] = False
            self.controller.on_recognition_loss()
            self.display_contract.displayed = None
            self._target_error = '対象登録を確認してください：' + str(error)
            raise StateError(self._target_error) from error
        self._target_error = ''
        return registered

    @staticmethod
    def _hash_scene_file(scene_id):
            scene_digest = hashlib.sha256()
            with open(scene_id, 'rb') as stream:
                for chunk in iter(lambda: stream.read(1024*1024), b''):
                    scene_digest.update(chunk)
            return scene_digest.hexdigest()

    def verify_runtime_hello(self, actual):
        registry = TargetRegistry.load(self.target_registry_path)
        policy = RuntimePolicy.load(self.runtime_manifest_path)
        self._verify_slicer_sources(policy)
        return policy.verify(actual, str(slicer.app.applicationVersion), registry.sha256)

    def _verify_slicer_sources(self, policy):
        if policy.document.get('slicer_software_sha256') != _LOADED_SOURCE_HASHES:
            raise ValueError('loaded Slicer source differs from prepared configuration')
        for relative, expected in _LOADED_SOURCE_HASHES.items():
            with open(os.path.join(_MODULE_DIR,relative), 'rb') as stream:
                if hashlib.sha256(stream.read()).hexdigest() != expected:
                    raise ValueError('Slicer source changed while running; stop and load the prepared release')

    def verify_runtime_local(self):
        policy = RuntimePolicy.load(self.runtime_manifest_path)
        self._verify_slicer_sources(policy)
        policy.verify_local(str(slicer.app.applicationVersion), TargetRegistry.load(self.target_registry_path).sha256)
        return policy.sha256

    def verify_runtime_request(self, requested, accepted):
        policy = RuntimePolicy.load(self.runtime_manifest_path)
        self._verify_slicer_sources(policy)
        policy.verify_local(str(slicer.app.applicationVersion), TargetRegistry.load(self.target_registry_path).sha256)
        if requested != policy.sha256 or accepted != policy.sha256:
            raise ValueError('runtime configuration changed; stop and reconnect explicitly')

    def verify_action_target(self, cmd, params):
        if self._storage_error and cmd not in {'status', 'disarm', 'claim_input', 'size_settings'}:
            raise StateError('台帳保存先が無効です。準備画面で再指定してください：'+self._storage_error)
        writes={'stamp','commit','begin_plan_revision','edit_plan_item','delete_plan_item','add_plan_item',
                'move_plan_item','save_plan_revision','cancel_plan_revision','skip_plan','reorder_plan',
                'begin_correction','set_out_of_plan'}
        if cmd in writes:
            view = self._plan_view()
            if view and view['read_only']:
                raise StateError('historical plan is read-only; select the latest saved version before editing or recording')
        guarded={'arm','aim','stamp','move_draft','rotate_opening','tilt','reverse','reset_dir','commit',
                 'resume_draft','resize_draft','edit_plan_item','add_plan_item','begin_correction',
                 'load_session','load_plan','show_c','view_rotate','view_pan','zoom','reset_view'}
        if cmd not in guarded:
            return
        try:
            if self._surface() is None:
                raise StateError('target identity changed or unavailable')
        except (OSError,ValueError,RuntimeError) as error:
            self._aim['valid']=False
            self.controller.on_recognition_loss()
            self.display_contract.displayed=None
            self.display_contract.pending=None
            if self.dispatcher:
                self.dispatcher.armed=False
            raise StateError('operation rejected before mutation: '+str(error))

    def _require_displayed(self, params):
        if self._surface() is None:
            raise StateError('target identity changed or unavailable')
        snapshot = self.display_contract.require(params, self.controller.draft)
        node = self._curve_node(DRAFT_CURVE_NAME)
        draft = self.controller.draft
        points = draft.placement.transform_points(self.controller.draft_template.local_points(draft.placement.path_dir))
        if node.GetNumberOfControlPoints() != len(points):
            raise StateError('visible draft was modified')
        for i, expected in enumerate(points):
            actual = [0.,0.,0.]
            node.GetNthControlPointPositionWorld(i, actual)
            if math.dist(expected, actual) > 1e-8:
                raise StateError('visible draft was modified')
        if snapshot['target'] != self._target_identity():
            raise StateError('displayed target changed')
        return snapshot

    def query_persisted_result(self, request_id):
        for path in (self.ledger_path,self.plan_registry_path):
            if path:
                result = EventLedger(path).request_result(request_id)
                if result:
                    return result
        return None

    def _registered_choices(self):
        try:
            self._ensure_plan_registry()
        except (ValueError,KeyError,OSError) as error:
            self._registry_error = '旧形式・破損・不明な計画履歴。準備時に検証可能な計画版台帳を選択してください：'+str(error)
            return {'plans':[], 'creators':list(self.creator_candidates),'storages':list(self.storage_registry),
                    'plan_items':[], 'plan_versions':[], 'reasons':list(self.reason_candidates)}
        self._registry_error = ''
        return {'plans': list(self._plan_store.plans), 'creators': list(self.creator_candidates),
                'storages': list(self.storage_registry),
                'plan_items': [(i.get('event_id') or i.get('item_id')) for i in self._visible_plan_version().items] if getattr(self,'_active_plan',None) in self._plan_store.plans else [e.event_id for e in self._plan.entries],
                'plan_versions': [v.version for v in self._plan_store.get(self._active_plan).versions] if getattr(self,'_active_plan',None) in self._plan_store.plans else [],
                'reasons': list(self.reason_candidates)}

    def _visible_plan_version(self):
        plan = self._plan_store.get(self._active_plan)
        selected = getattr(self,'_review_plan_version',None)
        return plan.working or (self._plan_store.saved_version(plan.plan_id,selected) if selected is not None else plan.current)

    def _plan_view(self):
        plan_id = getattr(self,'_active_plan',None)
        if plan_id not in self._plan_store.plans:
            return None
        from cstamp.plan_revision import compare_saved_geometry
        plan = self._plan_store.get(plan_id)
        selected = self._visible_plan_version()
        return {'plan_id':plan_id,'version':selected.version,'latest_version':plan.current.version,
                'hash':digest(selected.items),
                'read_only':plan.working is None and selected.version != plan.current.version,
                'difference_to_latest':compare_saved_geometry(selected,plan.current)}

    def _plan_binding(self):
        plan_id = getattr(self, '_active_plan', None)
        if not plan_id or plan_id not in self._plan_store.plans:
            return None
        version = self._visible_plan_version()
        return {'plan_id':plan_id, 'version':version.version, 'hash':digest(version.items),
                'active_item':self._plan.current.event_id if self._plan.current else None,
                'execution_order_hash':digest([[e.event_id,e.skipped,e.matched_performed_id] for e in self._plan.entries])}

    def _check_plan_binding(self, params):
        current = self._plan_binding()
        if current is None or params.get('plan_revision') != current:
            raise StateError('plan identity/version/hash mismatch')

    def _draft_plan_delta(self):
        if not self.has_draft() or self._plan.current is None:
            return None
        from cstamp.plan import compare_placement
        from cstamp.state_machine import _placement_dict
        return compare_placement(_placement_dict(self.controller.draft.placement),
                                 self._plan.current.event['placement'])

    def _apply_aim(self, nx, ny):
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in (nx,ny)):
            raise StateError('normalized aim coordinates must be finite and within 0..1')
        surface = self._surface()
        if surface is None:
            self._aim = {"valid": False, "anchor": None, "normal": None,
                         "nx": nx, "ny": ny}
            self._update_aim_marker()
            return {"ok": False, "reason": "no allowed surface"}
        hit = self._raycast_surface(nx, ny, surface)
        if hit is None:
            self._aim = {"valid": False, "anchor": None, "normal": None,
                         "nx": nx, "ny": ny}
            self._update_aim_marker()
            return {"ok": True,
                    "result": {"valid": False}}
        anchor, normal = hit
        self._aim = {"valid": True, "anchor": anchor, "normal": normal,
                     "nx": nx, "ny": ny}
        self._update_aim_marker()
        return {"ok": True,
                "result": {"valid": True, "point": list(anchor)}}

    def op_aim(self, params):
        return self._apply_aim(
            float(params.get("nx", 0.0)), float(params.get("ny", 0.0))
        )

    def op_stamp(self, params):
        if not self._aim["valid"]:
            return {"ok": False,
                    "reason": "aim is not on the allowed surface"}
        surface = self._surface()
        self.stamp_on_surface(
            self._aim["anchor"], self._aim["normal"], surface
        )
        self._notify_state()
        return {"ok": True,
                "draft_id": self.controller.draft.draft_id}

    def op_move_draft(self, params):
        surface = self._surface()
        if surface is None:
            return {"ok": False, "reason": "no allowed surface"}
        nx = float(params.get("nx", 0.0))
        ny = float(params.get("ny", 0.0))
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in (nx,ny)):
            raise StateError('normalized coordinates must be finite and within 0..1')
        hit = self._raycast_surface(nx, ny, surface)
        if hit is None:
            # off-surface aim: keep the last safe placement (plan §配置位置)
            self._aim = {"valid": False, "anchor": None, "normal": None,
                         "nx": nx, "ny": ny}
            self._update_aim_marker()
            return {"ok": False,
                    "reason": "off-surface; draft unchanged"}
        anchor, normal = hit
        self._aim = {"valid": True, "anchor": anchor, "normal": normal,
                     "nx": nx, "ny": ny}
        self._update_aim_marker()
        self.controller.move_draft(anchor, normal)
        self._update_draft_curve()
        return {"ok": True,
                "draft_id": self.controller.draft.draft_id,
                "result": {"rev": self.controller.draft.revision}}

    def op_rotate_opening(self, params):
        delta = float(params.get("delta_deg", 0.0))
        if not math.isfinite(delta):
            return {"ok": False, "reason": "delta out of range"}
        # Clamp, not reject: fast gesture frames must not be dropped.
        delta = max(-45.0, min(45.0, delta))
        self.controller.rotate_opening(math.radians(delta))
        self._update_draft_curve()
        return {"ok": True,
                "result": {"rev": self.controller.draft.revision}}

    def op_tilt(self, params):
        delta = float(params.get("delta_deg", 0.0))
        if not math.isfinite(delta):
            return {"ok": False, "reason": "delta out of range"}
        # Clamp, not reject: fast gesture frames must not be dropped.
        delta = max(-45.0, min(45.0, delta))
        self.controller.tilt_plane(0.0, math.radians(delta))
        self._update_draft_curve()
        return {"ok": True,
                "result": {"rev": self.controller.draft.revision}}

    def op_reverse(self, params):
        self.controller.reverse_path()
        self._update_draft_curve()
        return {"ok": True,
                "result": {"rev": self.controller.draft.revision}}

    def op_reset_dir(self, params):
        self.controller.reset_direction()
        self._update_draft_curve()
        return {"ok": True,
                "result": {"rev": self.controller.draft.revision}}

    def op_commit(self, params):
        self._require_displayed(params)
        rev = params.get("rev")
        if rev is not None and (
            not isinstance(rev, int) or isinstance(rev, bool)
        ):
            return {"ok": False, "reason": "rev must be int"}
        self.display_contract.saving = True
        try:
            stored = self.commit(
                self.ledger_path,
                layer=self.active_layer,
                input_method=self._request_context.get('input_method', 'hand'),
                expected_revision=rev,
            )
        except StateError as error:
            # stale-snapshot commit is a rejection, not an error path
            return {"ok": False, "reason": str(error)}
        finally:
            self.display_contract.saving = False
        self._notify_state()
        return {"ok": True, "event_id": stored["event_id"],
                "result": {"draft_revision": stored.get(
                    "draft_revision")}}

    def op_cancel(self, params):
        self.cancel()
        self._notify_state()
        return {"ok": True}

    def op_resume_draft(self, params):
        if not self.controller.frozen:
            return {"ok": False, "reason": "draft is not frozen"}
        self.controller.resume()
        self._notify_state()
        return {"ok": True}

    # --- plan / session ----------------------------------------------------

    def _append_record(self, record):
        if not self.ledger_path:
            raise StateError('register a ledger path before recording')
        EventLedger(self.ledger_path).append(record)

    def op_select_plan(self, params):
        self._ensure_plan_registry()
        if self.has_draft():
            raise StateError('finish draft before changing plan')
        plan_id = params.get('plan_id')
        self._plan_store.get(plan_id)
        self._active_plan = plan_id
        self._review_plan_version = None
        return {'ok':True, 'result':{'plan_revision':self._plan_binding()}}

    def op_select_plan_version(self, params):
        self._check_plan_binding(params)
        if self.has_draft():
            raise StateError('finish draft before changing the displayed plan version')
        plan = self._plan_store.get(self._active_plan)
        if plan.working is not None:
            raise StateError('finish or explicitly cancel the open plan revision before comparing saved versions')
        version = self._plan_store.saved_version(plan.plan_id,params.get('version'))
        self._review_plan_version = None if version.version == plan.current.version else version.version
        self._selected_plan_item = None
        self._pending_reason = None
        self._plan.load(copy.deepcopy(version.items))
        self._update_ghost()
        self._notify_state()
        return {'ok':True,'result':{'plan_revision':self._plan_binding(),'plan_view':self._plan_view()}}

    def op_select_creator(self, params):
        creator = params.get('creator')
        if creator not in self.creator_candidates:
            raise StateError('unregistered creator')
        self._creator = creator
        return {'ok':True, 'result':{'creator':creator}}

    def op_select_storage(self, params):
        key = params.get('storage')
        if key not in self.storage_registry or self.has_draft():
            raise StateError('unregistered storage or active draft')
        self.ledger_path = self.storage_registry[key]
        return {'ok':True, 'result':{'storage':key}}

    def op_load_plan(self, params):
        self._ensure_plan_registry()
        plan_id = getattr(self, '_active_plan', None)
        if plan_id in self._plan_store.plans:
            items = self._visible_plan_version().items
            self._plan.load(items)
            self._update_ghost()
            count = len(items)
        elif self.plan_path:
            count = self.load_plan(self.plan_path)
        else:
            raise StateError('select a registered plan')
        self._notify_state()
        return {"ok": True, "result": {"planned": count}}

    def op_select_plan_item(self, params):
        item_id = params.get('item_id')
        if item_id is not None:
            self._check_plan_binding(params)
            ids = self._registered_choices()['plan_items']
            if item_id not in ids:
                raise StateError('selected item is no longer registered')
            index = ids.index(item_id)
        else:
            index = params.get("index")
        if not isinstance(index, int):
            return {"ok": False, "reason": "index must be int"}
        try:
            if self.active_layer == 'PLANNED' and getattr(self,'_active_plan',None):
                version = self._visible_plan_version()
                if not (0 <= index < len(version.items)):
                    raise IndexError('index out of range')
                self._selected_plan_item = version.items[index].get('event_id') or version.items[index].get('item_id')
                return {'ok':True, 'result':{'selected':self._selected_plan_item}}
            entry = self._plan.select(index)
        except (IndexError, ValueError) as error:
            return {"ok": False, "reason": str(error)}
        self._selected_plan_item = entry.event_id
        self._update_ghost()
        return {"ok": True,
                "result": {"selected": entry.event_id}}

    def op_skip_plan(self, params):
        self._check_plan_binding(params)
        self._require_reason()
        reason = self._pending_reason
        entry = self._plan.current
        if entry is None:
            return {"ok": False, "reason": "no plan to skip"}
        self._append_record({
            "record_type": "plan_skip",
            "planned_event_id": entry.event_id,
            "reason": reason,
        })
        entry.skipped = True
        self._pending_reason = None
        self._update_ghost()
        self._notify_state()
        return {"ok": True,
                "result": {"skipped": entry.event_id}}

    def op_reorder_plan(self, params):
        self._check_plan_binding(params)
        self._require_reason()
        from_index = params.get("from_index")
        to_index = params.get("to_index")
        if not isinstance(from_index, int) or not isinstance(to_index, int):
            return {"ok": False, "reason": "indices must be int"}
        try:
            staged = copy.deepcopy(self._plan)
            entry = staged.reorder(from_index, to_index)
        except IndexError as error:
            return {"ok": False, "reason": str(error)}
        self._append_record({
            'reason':self._pending_reason, 'plan_revision':self._plan_binding(),
            "record_type": "plan_reorder",
            "planned_event_id": entry.event_id,
            "from_index": from_index,
            "to_index": to_index,
        })
        self._plan = staged
        self._pending_reason = None
        self._update_ghost()
        return {"ok": True,
                "result": {"moved": entry.event_id}}

    # --- plan revision management (FR-034, unit 7) -------------------------

    def _resolve_plan_id(self, params):
        self._ensure_plan_registry()
        plan_id = params.get("plan_id") or getattr(
            self, "_active_plan", None
        )
        if not plan_id:
            # fall back to the only registered plan if there is exactly
            # one — never guess between multiple plans
            ids = list(self._plan_store.plans)
            if len(ids) == 1:
                plan_id = ids[0]
        if not plan_id:
            raise StateError("plan_id required")
        if plan_id != getattr(self,'_active_plan',None):
            raise StateError('explicitly select the registered plan first')
        return plan_id

    def _ensure_plan_registry(self):
        path = self.plan_registry_path
        if getattr(self,'_registry_loaded_path',None) != path:
            restored = PlanStore()
            restored.restore(EventLedger(path).events())
            self._plan_store = restored
            self._registry_loaded_path = path

    def _append_plan_record(self, record):
        EventLedger(self.plan_registry_path).append(record)

    def op_create_plan(self, params):
        self._ensure_plan_registry()
        before = copy.deepcopy(self._plan_store.plans)
        version = self._plan_store.create_plan(
            plan_id=params.get("plan_id"),
            items=params.get("items") or [],
            creator=self._creator,
        )
        self._active_plan = version.plan_id
        self._review_plan_version = None
        record = {
            "record_type": "plan_created",
            "plan_id": version.plan_id,
            "version": version.version,
            "item_count": len(version.items),
            "creator": version.creator,
            'items': copy.deepcopy(version.items),
            'created_ts': version.created_ts, 'approval': version.approval,
        }
        try:
            self._append_plan_record(record)
        except Exception:
            self._plan_store.plans = before
            raise
        self._plan_store.begin_revision(version.plan_id)
        return {"ok": True, "result": {
            "plan_id": version.plan_id, "version": version.version}}

    def op_begin_plan_revision(self, params):
        self._check_plan_binding(params)
        try:
            plan_id = self._resolve_plan_id(params)
            working = self._plan_store.begin_revision(plan_id)
            self._review_plan_version = None
        except (KeyError, ValueError) as error:
            return {"ok": False, "reason": str(error)}
        return {"ok": True, "result": {
            "plan_id": plan_id, "working_version": working.version}}

    def op_edit_plan_item(self, params):
        self._check_plan_binding(params)
        item_id = params.get("item_id")
        if not isinstance(item_id, str) or self.has_draft():
            raise StateError('select one planned item with no active draft')
        working = self._plan_store._require_working(self._resolve_plan_id(params))
        item = working.items[self._plan_store._item_index(working, item_id)]
        placement = placement_from_dict(item['placement'])
        template = item.get('template') or {}
        self.controller.template = CTemplate(**{k:v for k,v in template.items() if k in ('radius','opening_deg','segments','template_id','version','extra')})
        self.controller.seed_draft(placement)
        self._selected_plan_item = item_id
        self.active_layer = 'PLANNED'
        if self.dispatcher:
            self.dispatcher.layer = 'PLANNED'
        self._update_draft_curve()
        return {'ok':True, 'draft_id':self.controller.draft.draft_id,
                'result':{'edited':item_id, 'rev':self.controller.draft.revision}}

    def op_add_plan_item(self, params):
        self._check_plan_binding(params)
        self._plan_store._require_working(self._resolve_plan_id(params))
        if self.has_draft():
            raise StateError('finish current draft first')
        self._selected_plan_item = None
        self.active_layer = 'PLANNED'
        if self.dispatcher:
            self.dispatcher.layer = 'PLANNED'
            self.dispatcher.mode = 'aim'
        return {'ok':True, 'result':{'mode':'aim', 'layer':'PLANNED'}}

    def op_delete_plan_item(self, params):
        self._check_plan_binding(params)
        item_id = params.get('item_id')
        if not isinstance(item_id, str):
            raise StateError('select item before deletion review')
        self._require_reason()
        self._plan_store._item_index(self._plan_store._require_working(self._active_plan), item_id)
        self._pending_audit = {'kind':'delete_plan_item', 'item_id':item_id,
                               'plan_revision':self._plan_binding(), 'reason':self._pending_reason}
        return {'ok':True, 'result':{'pending_audit':copy.deepcopy(self._pending_audit)}}

    def op_move_plan_item(self, params):
        self._check_plan_binding(params)
        self._require_reason()
        from_index = params.get("from_index")
        to_index = params.get("to_index")
        if not isinstance(from_index, int) or not isinstance(
            to_index, int
        ):
            return {"ok": False, "reason": "indices must be int"}
        try:
            self._plan_store.move_item(
                self._resolve_plan_id(params), from_index, to_index
            )
        except (IndexError, KeyError, ValueError, StateError) as error:
            return {"ok": False, "reason": str(error)}
        return {"ok": True}

    def op_save_plan_revision(self, params):
        """Freeze the working copy as the newest plan version; the
        previous version is never overwritten (FR-034)."""
        self._check_plan_binding(params)
        self._require_reason()
        before = copy.deepcopy(self._plan_store.plans)
        reason_before = self._plan_store.pending_reason
        try:
            plan_id = self._resolve_plan_id(params)
            record = self._plan_store.save_revision(plan_id)
        except (KeyError, ValueError, StateError) as error:
            return {"ok": False, "reason": str(error)}
        try:
            self._append_plan_record(record)
        except Exception:
            self._plan_store.plans = before
            self._plan_store.pending_reason = reason_before
            raise
        return {"ok": True, "result": {
            "plan_id": plan_id,
            "version": record["version"],
            "diff": record["diff"],
        }}

    def op_cancel_plan_revision(self, params):
        self._check_plan_binding(params)
        try:
            self._plan_store.cancel_revision(
                self._resolve_plan_id(params)
            )
        except (KeyError, ValueError, StateError) as error:
            return {"ok": False, "reason": str(error)}
        return {"ok": True}

    # --- audit commands -------------------------------------------------

    def _reason_context(self):
        return {'plan_revision':self._plan_binding(),
                'selected_event':self._selected_event_id,
                'selected_plan_item':self._selected_plan_item}

    def _require_reason(self):
        if not self._pending_reason or self._pending_reason_binding != self._reason_context():
            raise StateError('select reason again for the current target and plan version')
        return self._pending_reason

    def op_select_reason(self, params):
        reason = params.get("reason")
        if not isinstance(reason, str) or not reason:
            return {"ok": False, "reason": "reason (str) required"}
        if reason not in self.reason_candidates:
            return {"ok": False,
                    "reason": "unregistered reason category"}
        self._pending_reason = reason
        self._pending_reason_binding = self._reason_context()
        self._plan_store.pending_reason = reason
        return {"ok": True, "result": {"reason": reason}}

    def op_set_out_of_plan(self, params):
        """Declare the next PERFORMED commit as out-of-plan: the commit
        consumes no planned entry and the declaration is recorded
        (AC-024). A following commit clears the flag."""
        self._require_reason()
        self._pending_out_of_plan = True
        return {"ok": True, "result": {"out_of_plan": True}}

    def op_revoke_event(self, params):
        """Mark a committed event as revoked via a new audit record.
        The original event is never modified or deleted (FR-015)."""
        event_id = params.get("event_id") or self._selected_event_id
        if not isinstance(event_id, str) or not event_id:
            return {"ok": False, "reason": "event_id (str) required"}
        if event_id not in self._committed:
            return {"ok": False, "reason": "unknown event"}
        self._require_reason()
        if event_id != self._selected_event_id:
            raise StateError("review the selected event before requesting revocation")
        self._pending_audit = {'kind':'event_revoked','target_event_id':event_id,
                               'target_hash':digest(self._committed[event_id]),
                               'reason':self._pending_reason}
        return {"ok": True, "result": {"pending_audit": copy.deepcopy(self._pending_audit)}}

    def op_confirm_audit(self, params):
        """Operator acknowledgement of an audit/match record, stored as
        its own append-only record."""
        if self._pending_audit is not None:
            pending = copy.deepcopy(self._pending_audit)
            if params.get('audit') != pending:
                raise StateError('audit target changed; review again')
            if pending['kind'] == 'delete_plan_item':
                self._check_plan_binding(pending)
                self._plan_store.delete_item(self._active_plan, pending['item_id'])
            else:
                target = pending['target_event_id']
                if digest(self._committed[target]) != pending['target_hash']:
                    raise StateError('audit target hash mismatch')
                self._append_record({'record_type':pending['kind'], **pending})
                self._revoked.add(target)
            self._pending_audit = None
            self._pending_reason = None
            return {'ok':True, 'result':{'confirmed':pending}}
        raise StateError('no independently reviewed audit is pending')
    # --- review / correction ------------------------------------------------

    def op_select_event(self, params):
        """Pick the committed event whose anchor is nearest to the aim
        ray (REVIEW mode). Stores the selection read-only."""
        view, renderer = self._renderer()
        nx = float(params.get("nx", 0.0))
        ny = float(params.get("ny", 0.0))
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in (nx,ny)):
            raise StateError('normalized coordinates must be finite and within 0..1')
        width, height = view.renderWindow().GetSize()
        x = max(0.0, min(1.0, nx)) * width
        y = (1.0 - max(0.0, min(1.0, ny))) * height
        renderer.SetDisplayPoint(x, y, 0.0)
        renderer.DisplayToWorld()
        near = list(renderer.GetWorldPoint()[:3])
        renderer.SetDisplayPoint(x, y, 1.0)
        renderer.DisplayToWorld()
        far = list(renderer.GetWorldPoint()[:3])
        direction = [f - n for f, n in zip(far, near)]
        length = math.sqrt(sum(c * c for c in direction)) or 1.0
        direction = [c / length for c in direction]

        best_id = None
        best_dist = math.inf
        for event_id, event in self._committed.items():
            if event.get('layer','PERFORMED') != 'PERFORMED':
                continue
            anchor = (event.get("placement") or {}).get("anchor")
            if anchor is None:
                continue
            rel = [a - n for a, n in zip(anchor, near)]
            t = sum(r * d for r, d in zip(rel, direction))
            closest = [n + t * d for n, d in zip(near, direction)]
            dist = math.sqrt(sum(
                (a - c) ** 2 for a, c in zip(anchor, closest)
            ))
            if dist < best_dist:
                best_dist = dist
                best_id = event_id
        if best_id is None or best_dist > 15.0:
            return {"ok": False,
                    "reason": "no committed event near the aim ray"}
        self._selected_event_id = best_id
        return {"ok": True,
                "event_id": best_id,
                "result": {"distance_mm": best_dist}}

    def op_show_c(self, params):
        event_id = self._selected_event_id or params.get("event_id")
        if not event_id or event_id not in self._committed:
            return {"ok": False, "reason": "no selected event"}
        shape = self._shape_node(event_id)
        shape.SetDisplayVisibility(True)
        return {"ok": True, "event_id": event_id}

    def op_begin_correction(self, params):
        """Seed a DRAFT from the selected committed event. The original
        event stays immutable; commit carries correction_of (FR-015)."""
        event_id = self._selected_event_id or params.get("event_id")
        event = self._committed.get(event_id) if event_id else None
        if event is None:
            return {"ok": False, "reason": "no selected event"}
        placement = placement_from_dict(event["placement"])
        draft = self.controller.seed_draft(placement)
        self._correction_of = event_id
        self._draft_surface_name = (
            event.get("scene") or {}
        ).get("model_node", "")
        self._update_draft_curve()
        self._notify_state()
        return {"ok": True, "draft_id": draft.draft_id,
                "result": {"correction_of": event_id}}

    # --- session save / load ------------------------------------------------

    def op_save_session(self, params):
        """Events are appended at commit time; save confirms the ledger
        is readable and reports its committed count (no rewrite)."""
        if not self.ledger_path:
            return {"ok": False, "reason": "no ledger path registered"}
        ledger = EventLedger(self.ledger_path)
        count = sum(
            1 for e in ledger.events()
            if not e.get("record_type") and "placement" in e
        )
        return {"ok": True, "result": {"committed": count,
                                       "path": self.ledger_path}}

    def op_load_session(self, params):
        if not self.ledger_path:
            return {"ok": False, "reason": "no ledger path registered"}
        count = self.load_ledger(self.ledger_path)
        self._notify_state()
        return {"ok": True, "result": {"restored": count}}

    # --- on-screen operation menu --------------------------------------------

    def _menu_items(self):
        """Context-dependent menu entries (label -> dispatch cmd)."""
        draft = self.controller.draft if self.has_draft() else None
        items = []
        if self.controller.frozen:
            items.append({"label": "draft_resume", "cmd": "resume_draft"})
        if draft:
            items += [
                {"label": "mode_move", "cmd": "select_mode",
                 "params": {"mode": "move"}},
                {"label": "mode_rotate", "cmd": "select_mode",
                 "params": {"mode": "rotate"}},
                {"label": "mode_tilt", "cmd": "select_mode",
                 "params": {"mode": "tilt"}},
                {"label": "mode_view", "cmd": "select_mode",
                 "params": {"mode": "view"}},
                # explicit commit binds the displayed draft revision
                # (ONI-001) — the menu is an independent explicit op
                {"label": "commit", "cmd": "commit",
                 "params": {k:v for k,v in (self.display_contract.displayed or {}).items() if k in ("draft_id","rev","hash")}},
                {"label": "cancel_draft", "cmd": "cancel"},
            ]
        else:
            items += [
                {"label": "mode_view", "cmd": "select_mode",
                 "params": {"mode": "view"}},
                {"label": "mode_aim", "cmd": "select_mode",
                 "params": {"mode": "aim"}},
                {"label": "mode_review", "cmd": "select_mode",
                 "params": {"mode": "review"}},
                {"label": "reset_view", "cmd": "reset_view"},
                {"label": "layer_toggle", "cmd": "select_layer",
                 "params": {"layer": "PLANNED"
                            if self.active_layer == "PERFORMED"
                            else "PERFORMED"}},
                {"label": "load_plan", "cmd": "load_plan"},
                {"label": "skip_plan", "cmd": "skip_plan",
                 "params": {"reason": "operator"}},
                {"label": "plan_create", "cmd": "create_plan"},
            ]
            working = self._working_plan_id()
            if working and self._plan_store.get(working).working is None:
                items.append({"label": "plan_rev_begin",
                              "cmd": "begin_plan_revision"})
            elif working:
                items += [
                    {"label": "plan_rev_save",
                     "cmd": "save_plan_revision"},
                    {"label": "plan_rev_cancel",
                     "cmd": "cancel_plan_revision"},
                ]
            items += [
                {"label": "out_of_plan", "cmd": "set_out_of_plan"},
                {"label": "load_session", "cmd": "load_session"},
            ]
            if self._selected_event_id:
                items += [
                    {"label": "revoke_selected", "cmd": "revoke_event"},
                    {"label": "audit_confirm", "cmd": "confirm_audit"},
                ]
            if (self._pending_out_of_plan
                    or self._selected_event_id
                    or (working
                        and self._plan_store.get(working).working)):
                items += [
                    {"label": f"reason:{r}", "cmd": "select_reason",
                     "params": {"reason": r}}
                    for r in self.reason_candidates
                ]
        items.append({"label": "disarm", "cmd": "disarm"})
        return items

    def _working_plan_id(self):
        """Plan id the revision menu acts on, or None when nothing is
        registered/unambiguous."""
        plan_id = getattr(self, "_active_plan", None)
        if plan_id and plan_id in self._plan_store.plans:
            return plan_id
        ids = list(self._plan_store.plans)
        return ids[0] if len(ids) == 1 else None

    def _menu_payload(self):
        items = self._menu_items()
        return {
            "open": self._menu_open,
            "index": self._menu_index,
            "items": [item["label"] for item in items],
        }

    def op_menu_open(self, params):
        self._menu_open = True
        self._menu_index = 0
        self._notify_state()
        return {"ok": True, "menu": self._menu_payload()}

    def op_menu_next(self, params):
        if not self._menu_open:
            return {"ok": False, "reason": "menu is closed"}
        items = self._menu_items()
        self._menu_index = (self._menu_index + 1) % len(items)
        self._notify_state()
        return {"ok": True, "menu": self._menu_payload()}

    def op_menu_prev(self, params):
        if not self._menu_open:
            return {"ok": False, "reason": "menu is closed"}
        items = self._menu_items()
        self._menu_index = (self._menu_index - 1) % len(items)
        self._notify_state()
        return {"ok": True, "menu": self._menu_payload()}

    def op_menu_confirm(self, params):
        if not self._menu_open or self.dispatcher is None:
            return {"ok": False, "reason": "menu is closed"}
        items = self._menu_items()
        item = items[self._menu_index % len(items)]
        self._menu_open = False
        result = self.dispatcher.dispatch_local(
            item["cmd"], item.get("params")
        )
        result["menu"] = self._menu_payload()
        self._notify_state()
        return result

    def op_menu_close(self, params):
        self._menu_open = False
        self._notify_state()
        return {"ok": True, "menu": self._menu_payload()}

    # --- aim marker -----------------------------------------------------------

    def _update_aim_marker(self):
        """Yellow fiducial at the current aim intersection; red marker
        stays hidden while the aim is off-surface."""
        if not self._aim["valid"]:
            self._remove_node("CStamp-AIM")
            return
        points = self._points_node_aim()
        if points.GetNumberOfControlPoints() == 0:
            points.AddControlPointWorld(
                vtk.vtkVector3d(*self._aim["anchor"])
            )
        else:
            points.SetNthControlPointPositionWorld(
                0, *self._aim["anchor"]
            )
        display = points.GetDisplayNode()
        display.SetColor(1.0, 0.9, 0.1)
        display.SetSelectedColor(1.0, 0.9, 0.1)

    def _points_node_aim(self):
        try:
            return slicer.util.getNode("CStamp-AIM")
        except slicer.util.MRMLNodeNotFoundException:
            return slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLMarkupsFiducialNode", "CStamp-AIM"
            )

    # --- MRML helpers -----------------------------------------------------

    def _update_draft_curve(self):
        draft = self.controller.draft
        target = self._target_identity()
        node = self._curve_node(DRAFT_CURVE_NAME)
        world = draft.placement.transform_points(
            self.controller.draft_template.local_points(draft.placement.path_dir)
        )
        modifying = node.StartModify()
        try:
            node.RemoveAllControlPoints()
            for p in world:
                node.AddControlPointWorld(vtk.vtkVector3d(*p))
        finally:
            node.EndModify(modifying)
        node.SetName(DRAFT_CURVE_NAME)
        display = node.GetDisplayNode()
        display.SetColor(0.0, 0.8, 0.9)  # cyan = 仮配置
        display.SetSelectedColor(0.0, 0.8, 0.9)
        display.SetPointLabelsVisibility(False)
        display.SetPropertiesLabelVisibility(False)
        snapshot = self.display_contract.request(draft, self.controller.draft_template,
                                                 target)
        view = self._three_d_view()
        window = view.renderWindow()
        old = getattr(self, '_render_ack_observer', None)
        if old:
            old[0].RemoveObserver(old[1])
        render_request = self._request_context.get('req')
        def rendered(_caller, _event):
            current = self.controller.draft
            if not self.has_draft() or current.draft_id != snapshot['draft_id'] or current.revision != snapshot['rev']:
                return
            if node.GetNumberOfControlPoints() != len(world):
                return
            for i, expected in enumerate(world):
                actual = [0.,0.,0.]
                node.GetNthControlPointPositionWorld(i, actual)
                if math.dist(actual, expected) > 1e-8:
                    return
            if self.display_contract.displayed is None:
                self.display_contract.acknowledge(snapshot['hash'])
                self._last_render_timing = {'req':render_request,
                                            'draft_id':snapshot['draft_id'],'revision':snapshot['rev'],
                                            'acknowledged_ns':self.display_contract.acknowledged_ns}
                self._notify_state()
        token = window.AddObserver(vtk.vtkCommand.EndEvent, rendered)
        self._render_ack_observer = (window, token)
        view.scheduleRender()

    def _replace_draft_curve_with_committed(self, stored):
        layer = stored.get("layer", "PERFORMED")
        prefix = (
            PERFORMED_SHAPE_PREFIX
            if layer == "PERFORMED"
            else PLANNED_SHAPE_PREFIX
        )
        draft_curve = self._curve_node(DRAFT_CURVE_NAME)
        draft_curve.SetName(f"{prefix}{stored['event_id']}")
        draft_curve.GetDisplayNode().SetColor(
            *(0.2, 0.5, 1.0) if layer == "PERFORMED" else (0.2, 0.9, 0.4)
        )
        draft_curve.SetDisplayVisibility(False)

        points = self._points_node(layer)
        anchor = stored["placement"]["anchor"]
        index = points.AddControlPointWorld(vtk.vtkVector3d(*anchor))
        label = "操作記録" if layer == "PERFORMED" else "計画"
        points.SetNthControlPointLabel(
            index, f"{label}:{stored['event_id']}"
        )
        points.GetDisplayNode().SetColor(
            *(1.0, 0.2, 0.2) if layer == "PERFORMED" else (0.2, 0.9, 0.4)
        )

    def _curve_node(self, name):
        try:
            return slicer.util.getNode(name)
        except slicer.util.MRMLNodeNotFoundException:
            return slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLMarkupsCurveNode", name
            )

    def _points_node(self, layer):
        name = (
            PERFORMED_POINTS_NAME
            if layer == "PERFORMED"
            else PLANNED_POINTS_NAME
        )
        try:
            return slicer.util.getNode(name)
        except slicer.util.MRMLNodeNotFoundException:
            return slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLMarkupsFiducialNode", name
            )

    def _performed_points(self):
        return self._points_node("PERFORMED")

    def _shape_node(self, event_id):
        return slicer.util.getNode(f"{PERFORMED_SHAPE_PREFIX}{event_id}")

    def _remove_node(self, name):
        try:
            slicer.mrmlScene.RemoveNode(slicer.util.getNode(name))
        except slicer.util.MRMLNodeNotFoundException:
            pass

    # --- typed command server (localhost only) ---------------------------

    def start_command_server(self, port: int):
        """Listen on 127.0.0.1:<port> for the typed command protocol
        (command_protocol.py). Every line gets a JSON accept/reject
        response. Only allowlisted commands run; a disconnect freezes
        (never cancels) an active draft and disarms the session."""
        if self._command_server is not None:
            return
        self.dispatcher = CommandDispatcher(self)
        try:
            self._command_server = _CommandServer(port, self.dispatcher)
            from unified_hand_panel import install
            install(self)
        except Exception:
            self.dispatcher = None
            raise

    def stop_command_server(self):
        if self._command_server is None:
            return
        self._command_server.close()
        self._command_server = None
        self.dispatcher = None


class _CommandServer:
    """QTcpServer loopback listener driving the CommandDispatcher.

    Single-client policy: a new connection replaces the previous one and
    the dispatcher is notified so the old session is disarmed."""

    def __init__(self, port: int, dispatcher: CommandDispatcher):
        if not 1024 <= port <= 65535:
            raise ValueError("port must be 1024-65535")
        self._dispatcher = dispatcher
        self._server = qt.QTcpServer()
        self._server.newConnection.connect(self._on_connection)
        self._sockets = []
        address = qt.QHostAddress(qt.QHostAddress.LocalHost)
        if not self._server.listen(address, port):
            raise RuntimeError(
                f"port {port} を待受できません: "
                f"{self._server.errorString()}"
            )

    def close(self):
        sockets, self._sockets = self._sockets, []
        for socket in sockets:
            socket.disconnectFromHost()
            socket.deleteLater()
        self._dispatcher.on_disconnect()
        self._server.close()

    def _on_connection(self):
        socket = self._server.nextPendingConnection()
        if socket is None:
            return
        # single client: replace any previous connection
        old_sockets, self._sockets = self._sockets, [socket]
        if self._dispatcher.input_owner == 'hand':
            self._dispatcher.on_disconnect()
        socket.readyRead.connect(lambda: self._read(socket))
        socket.disconnected.connect(lambda: self._drop(socket))
        for old in old_sockets:
            old.disconnectFromHost()
            old.deleteLater()

    def _drop(self, socket):
        if socket not in self._sockets:
            return  # retired or already dropped; cannot reset the new client
        self._sockets.remove(socket)
        socket.deleteLater()
        if not self._sockets:
            # A retired hand transport must not cancel explicit mouse ownership.
            if self._dispatcher.input_owner == 'hand':
                self._dispatcher.on_disconnect()

    def _read(self, socket):
        if socket not in self._sockets:
            return
        while socket.canReadLine():
            raw = bytes(socket.readLine().data())
            response = self._dispatcher.handle_line(raw)
            socket.write(
                (json.dumps(response) + "\n").encode("utf-8")
            )
            socket.flush()
