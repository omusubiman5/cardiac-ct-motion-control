"""Mouse-operated millimetre dimensions dialog hosted by Slicer."""
import qt
import slicer


def show_size_settings(logic, parent=None):
    old = getattr(logic, "_size_dialog", None)
    if old is not None:
        old.close()
    dialog = qt.QDialog(parent if parent is not None else slicer.util.mainWindow())
    if parent is not None:
        dialog.setWindowFlags(qt.Qt.Widget)
    dialog.setWindowTitle("C焼き印のサイズ設定（mm）")
    layout = qt.QVBoxLayout(dialog)
    layout.addWidget(qt.QLabel("C中心線の直径をモデル座標のmmで設定します。\n画面のズーム倍率・表示上の線の太さとは別です。"))
    form = qt.QFormLayout()
    spin = qt.QDoubleSpinBox()
    spin.setRange(0.1, 200.0)
    spin.setDecimals(1)
    spin.setSingleStep(0.5)
    spin.setSuffix(" mm")
    spin.setValue(logic.controller.template.radius * 2.0)
    form.addRow("直径", spin)
    layout.addLayout(form)
    current = qt.QLabel("次のC：%.1f mm" % (logic.controller.template.radius * 2.0))
    layout.addWidget(current)
    apply_draft = qt.QCheckBox("現在の仮Cにも適用する（確定済みCは変更しない）")
    apply_draft.setEnabled(logic.has_draft() and not logic.controller.frozen)
    layout.addWidget(apply_draft)
    feedback = qt.QLabel("未適用：適用ボタンを押すと設定を変更します。")
    feedback.setWordWrap(True)
    layout.addWidget(feedback)
    resume = qt.QPushButton("マウス操作へ切り替えて仮C編集を再開")
    resume.setVisible(logic.has_draft() and logic.controller.frozen)
    def resume_draft():
        try:
            for command,params in [('claim_input',{'owner':'mouse'}),('arm',{}),('resume_draft',{})]:
                response=logic.dispatcher.dispatch_local(command,params,input_method='mouse')
                if not response.get('ok'):raise RuntimeError(response.get('reason','再開できません'))
            apply_draft.setEnabled(logic.has_draft())
            resume.setVisible(False)
            feedback.setText("マウス操作で編集を再開しました。現在の仮Cに適用する場合はチェックしてください。")
            logic._notify_state()
        except (ValueError,RuntimeError) as error:
            feedback.setText('再開しませんでした：'+str(error))
    resume.clicked.connect(resume_draft)
    layout.addWidget(resume)
    apply = qt.QPushButton("適用")
    def apply_size():
        try:
            if apply_draft.checked:
                if logic.dispatcher.input_owner != 'mouse':
                    raise RuntimeError('現在の仮Cを変更するには、先にマウス操作へ切り替えてください。次のCだけの寸法設定は切替不要です。')
                logic.verify_runtime_local()
                logic.verify_action_target('resize_draft',{})
            template = logic.controller.set_diameter_mm(float(spin.value), bool(apply_draft.checked))
            logic.template = template
            if apply_draft.checked:
                logic._update_draft_curve()
            logic._notify_state()
            current.setText("次のC：%.1f mm" % (template.radius * 2.0))
            feedback.setText("適用しました：直径 %.1f mm／%s" %
                             (template.radius * 2.0, "現在の仮C＋次のC" if apply_draft.checked else "次のCのみ"))
        except (ValueError, RuntimeError) as error:
            feedback.setText("変更しませんでした：" + str(error))
    apply.clicked.connect(apply_size)
    layout.addWidget(apply)
    close = qt.QPushButton("閉じる")
    # PythonQt forwards clicked(bool); QWidget.close() accepts no arguments.
    def close_dialog(*_):
        dialog.close()
    close.clicked.connect(close_dialog)
    layout.addWidget(close)
    logic._size_dialog = dialog
    dialog.show()
    if parent is None:
        dialog.raise_()
        dialog.activateWindow()
    return dialog
