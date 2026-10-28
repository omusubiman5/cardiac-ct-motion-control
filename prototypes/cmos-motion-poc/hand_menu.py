"""Local navigation only; actions still use the guarded typed Slicer protocol."""
from dataclasses import dataclass
import copy


@dataclass(frozen=True)
class Entry:
    key: str
    label: str
    detail: str = ""


MAIN = [Entry("view", "視点操作", "パン・回転・ズーム"),
        Entry("c", "C焼き印", "照準・仮配置・編集")]
EDIT = [Entry("confirm", "確定へ進む", "次の確認画面で確定"),
        Entry("cancel", "仮配置を取り消す"),
        Entry("main", "主メニューに戻る")]
RECORDS = [Entry("layer", "計画／実績を切り替える"),
           Entry("create_plan", "計画を作成"), Entry("load_plan", "計画を読み込む"),
           Entry("skip_plan", "予定をスキップ"),
           Entry("begin_plan_revision", "計画の訂正を開始"),
           Entry("save_plan_revision", "計画の訂正を保存"),
           Entry("cancel_plan_revision", "計画の訂正を取り消す"),
           Entry("out_of_plan", "計画外の記録"),
           Entry("load_session", "保存記録を読み込む"),
           Entry("reset_view", "視点を戻す"),
           Entry("reasons", "理由を選ぶ"),
           Entry("revoke_event", "選択記録の撤回"), Entry("confirm_audit", "監査確認"),
           Entry("plans", "登録計画を選ぶ"), Entry("plan_versions", "保存された計画版を比較"), Entry("creators", "作成者を選ぶ"),
           Entry("storages", "保存先を選ぶ"), Entry("plan_items", "予定項目を選ぶ"),
           Entry("edit_plan_item", "選択予定のCを編集"),
           Entry("delete_plan_item", "選択予定の削除を確認"),
           Entry("add_plan_item", "予定Cを追加"),
           Entry("move_plan_item", "選択予定を次へ移動"),
           Entry("reorder_plan", "次の予定を先頭にする"),
           Entry("save_session", "操作記録の保存状態を確認"),
           Entry("query_result", "直前の確定結果を照会"),
           Entry("main", "主メニューに戻る")]
REASONS = [Entry("reason:" + key, label) for key, label in
           [("operator", "操作者の判断"), ("position_changed", "位置の変更"),
            ("visibility", "見え方"), ("plan_superseded", "計画の更新"),
            ("out_of_plan", "計画外")]] + [Entry("records", "計画・記録に戻る")]


class HandMenu:
    def __init__(self):
        self.page = "main"
        self.index = 0
        self.opened = False
        self.confirm_revision = None
        self.notice = ""
        self.choices = {}
        self.choice_snapshot = {}
        self.choice_revision = None
        self.confirm_snapshot = None

    @property
    def entries(self):
        if self.page in {'plans', 'plan_versions', 'creators', 'storages', 'plan_items'}:
            return [Entry('choose:'+self.page+':'+str(i), '第%s版' % value if self.page=='plan_versions' else str(value))
                    for i, value in enumerate(self.choice_snapshot.get(self.page, []))] + [Entry('records', '計画・記録に戻る')]
        if self.page == "edit":
            return EDIT
        if self.page == "records":
            return RECORDS
        if self.page == "reasons":
            return REASONS
        if self.page == "confirm":
            return [Entry("commit", "この仮Cを確定する", "グーを一度下げてから再度提示"),
                    Entry("edit", "編集に戻る")]
        return MAIN

    def show(self, page):
        self.page, self.index, self.opened = page, 0, True
        self.notice = ""
        self.choice_snapshot = copy.deepcopy(self.choices)

    def close(self):
        self.opened = False
        self.confirm_revision = None

    def next(self):
        self.index = (self.index + 1) % len(self.entries)

    def previous(self):
        self.index = (self.index - 1) % len(self.entries)

    def back(self):
        if self.page in {"reasons", "plans", "plan_versions", "creators", "storages", "plan_items"}:
            self.show("records")
        elif self.page in {"edit", "records"}:
            self.show("main")
        elif self.page == "confirm":
            self.show("edit")
            self.confirm_revision = None
        else:
            self.close()
