"""Generate the original H/V conditions as pending trials, never fabricate results."""
import argparse
import itertools
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def supplementary_trials():
    """Prepare current gestures without changing the original 480-trial contract."""
    thumbs=[]
    for side,distance,tilt,attempt in itertools.product(
            ('left','right'),('distance1','distance2'),('tilt1','tilt2'),range(1,11)):
        thumbs.append({
            'trial_id':f'S-V05-thumb-down-{side}-{distance}-{tilt}-{attempt:02}',
            'case':'V-05','supplementary':True,
            'source':'本人指定：親指下で画面の選択を下へ。提示姿勢③（docs/45）',
            'shape':'thumb_down','standard_category':'Thumb_Down','side':side,
            'distance_condition':distance,'tilt_condition':tilt,'attempt':attempt,
            'wrist_orientation':'③：手首が画面の横側',
            'precondition':'受付中・主メニューが開・▶は中間項目・仮Cなし。各試行前に手を1秒下げる',
            'steps':['親指下を0.5秒以上提示','同じ形を2秒保持','手を1秒下げる'],
            'expected_intent':'menu_next_once',
            'expected_menu_delta':1,'expected_slicer_operation_count':0,
            'expectation':'選択が1項目下へ。保持継続では追加移動0。メニューを閉じず、C・カメラ・台帳変更0',
            'status':'NOT RUN','real_hand_verified':False,
            'actual_response':None,'observations':[]})

    # Repetitions below are additional nonclinical preparation conditions. They
    # are not substituted for the original V-05 clear-shape count or H/V runs.
    scenarios=[
        ('point-to-two','original-transition','docs/33 §4 E・V-05',
         '主メニュー開・中間項目・仮Cなし',
         ['人差し指1本を提示','Vへ変える途中は0.35秒未満','Vサインを0.5秒保持'],
         '途中で未意図の実行0。安定したVで選択が下へ1項目だけ移る'),
        ('two-to-three','original-transition','docs/33 §4 E・V-05',
         '主メニュー開・視点操作を選択・仮Cなし',
         ['Vサイン0.5秒でC焼き印へ選択移動','3本指へ変える途中は0.35秒未満',
          '人差し指・中指・薬指の3本を0.5秒保持'],
         '途中で実行0。安定した3本指でC照準を1回選択。仮配置・確定・取消0'),
        ('fist-to-thumb-up','original-transition','docs/33 §4 E・V-05',
         '主メニュー開・仮Cなし',
         ['グー0.5秒で閉じる','親指上へ変える途中は0.35秒未満','親指上を0.5秒保持'],
         '閉じる→開くがそれぞれ1回。開いた直後の選択追加移動0。C操作0'),
        ('open-palm-to-thumb-up','original-transition','docs/33 §4 E・V-05',
         '受付開始と手下げ完了・主メニュー開・中間項目・仮Cなし',
         ['開いた手を提示','親指上へ変える途中は0.35秒未満','親指上を0.5秒保持'],
         '途中で未意図の実行0。安定した親指上で選択が上へ1項目だけ移る'),
        ('fist-to-pinch','supplementary-transition','docs/33 §4 E グー／つまみ混同',
         '主メニュー開・仮Cなし',
         ['グーの握りと、親指・人差し指をつまむ形を交互に作る','途中形は0.35秒未満'],
         '明確な握りとつまみを区別。不明な途中形を親指操作・取消・確定へ変換しない'),
        ('unknown-half-folded','unknown','docs/33 V-05 UNKNOWN無作用',
         '主メニュー開・仮Cなし。開始／上下／選択のどの意図もないことを記録',
         ['指を半分曲げ、既定の明確形に一致させない','1秒提示してから手を下げる'],
         '不明形はUNKNOWN／無作用。メニュー選択移動・実行・C操作0。停止した場合は停止理由を記録'),
        ('unknown-partial-hand','unknown','docs/33 V-05・docs/23 X-03',
         '主メニュー開・仮Cなし。選択意図なし',
         ['指先を隠すか手の一部だけをカメラへ入れる','1秒後に完全に手を下げる'],
         '遮蔽／不明形から離散操作0。認識喪失時は停止。停止したら明示開始まで再操作0'),
        ('short-hand-exit','hand-exit','docs/33 V-06 短い認識欠落',
         '主メニュー開・中間項目・仮Cなし',
         ['親指下0.5秒で1項目下へ','0.1秒だけ画面外へ出す','同じ親指下を0.5秒提示'],
         '0.35秒未満の欠落では同じ操作を再発火しない。下移動は合計1回。C操作0'),
        ('released-hand-reentry','hand-reentry','docs/33 V-06 独立した再提示',
         '主メニュー開・中間項目・仮Cなし',
         ['親指下0.5秒で1項目下へ','手を1秒画面外へ下げる','親指下0.5秒を新しく提示'],
         '受付が維持された場合だけ独立した下移動が各1回。停止した場合は再提示だけで再開せず、明示再開後にやり直す'),
        ('thumb-up-down-roundtrip','supplementary-direction','本人指定：親指上で上、親指下で下（docs/45）',
         '主メニュー開・中間項目・仮Cなし',
         ['親指上0.5秒','手を1秒下げる','親指下0.5秒','手を1秒下げる',
          '親指下0.5秒','手を1秒下げる','親指上0.5秒'],
         '上→下→下→上に各1項目、最終選択は開始位置と同じ。保持で追加移動0。メニューを閉じない'),
        ('thumb-down-outside-menu','supplementary-context','docs/45 現行割当：親指下はメニュー外無操作',
         '受付中・メニュー閉・仮Cなし',
         ['親指下を1秒提示','手を1秒下げる','親指下を1秒再提示'],
         '開閉・選択・カメラ・C・保存の作用0'),
        ('fist-hold-back','supplementary-context','docs/33 §4 E・docs/23 H-11',
         '試験専用の仮Cあり・C編集メニュー開',
         ['グー0.5秒','グーを2秒保持','手を1秒下げる','グー0.5秒','閉じたら提示を終了'],
         'C編集→主メニュー→閉。保持だけでは次階層へ進まない。取消・確定0、仮C保持'),
    ]
    transitions=[]
    for scenario,kind,source,precondition,steps,expectation in scenarios:
        for side,attempt in itertools.product(('left','right'),range(1,11)):
            transitions.append({
                'trial_id':f'S-V05-{scenario}-{side}-{attempt:02}',
                'case':'V-05','related_case':'V-06','supplementary':True,
                'scenario':scenario,'kind':kind,'source':source,
                'repetition_basis':'補助条件：左右各10試行。原文の明確形480試行へ算入しない',
                'side':side,'distance_condition':'distance1','tilt_condition':'tilt1',
                'attempt':attempt,
                'wrist_orientation':'親指上下は③（横側）、他の明確形は④（下側）',
                'precondition':precondition,'steps':list(steps),'expectation':expectation,
                'expected_intent':scenario,'status':'NOT RUN','real_hand_verified':False,
                'actual_response':None,'observations':[]})
    return thumbs,transitions


def matrix():
    rows=[]
    for document,prefix in [('docs/23_hand-motion-completion-plan.md','H'),('docs/33_hand-control-correction-plan.md','V')]:
        for line in (ROOT/document).read_text(encoding='utf-8-sig').splitlines():
            columns=[c.strip() for c in line.split('|')]
            if len(columns)<5 or not re.match(rf'{prefix}-\d\d(?:\s|$)',columns[1]):continue
            identity=re.match(rf'{prefix}-\d\d',columns[1])[0]
            if any(row['case']==identity for row in rows):continue
            rows.append({'case':identity,'source':document,'original_condition':columns[2],
                         'original_expectation':columns[3],'status':'NOT RUN',
                         'real_hand_verified':False,'observations':[]})
    v05=[]
    for shape,side,distance,tilt,attempt in itertools.product(
            ('open_palm','thumb','point','two','three','fist'),('left','right'),
            ('distance1','distance2'),('tilt1','tilt2'),range(1,11)):
        v05.append({'case':'V-05','shape':shape,'side':side,'distance_condition':distance,
                    'tilt_condition':tilt,'attempt':attempt,'expected_intent':None,
                    'status':'NOT RUN','actual_response':None})
    thumbs,transitions=supplementary_trials()
    return {'source':'original H/V criteria plus explicitly supplementary pending conditions; NOT execution results',
            'cases':rows,'v05_clear_shape_trials':v05,
            'v05_supplementary_clear_shape_trials':thumbs,
            'v05_transition_unknown_trials':transitions,
            'preparation':{
                'original_clear_shape_contract':'6形×左右×距離2×傾き2×10提示＝480。元の行は変更しない',
                'supplementary_basis':'Thumb_Downと遷移・不明形・出入り・上下往復を追加。原文の回数や実手合格を変更しない',
                'guides':['docs/images/hand-menu-guide-2026-10-12-v2.png',
                          'docs/images/view-menu-test-guide-2026-10-12.png',
                          'docs/40_completion-operation-guide.md'],
                'condition_measurements':{'distance1_mm':None,'distance2_mm':None,
                                          'tilt1_degrees':None,'tilt2_degrees':None},
                'before_execution':['距離2条件・傾き2条件の実値、使用した手、甲／掌、照明、操作者匿名区分を記録',
                                    '実行ソース／モデル／構成hashを固定し、保持0.35秒・開始1.5秒の実効値を照合',
                                    '基準直径は本人指定の5mm。原文V-08の10mm表示比較も別条件で維持する',
                                    '試験専用シーン・台帳を使用。通常の仮C・記録は操作しない',
                                    '各試行前に前提状態を復元。停止した試行を成功にせず理由を記録',
                                    '映像は保存せず認識・状態・要求・結果・使用感だけを記録'],
                'actual_runtime_hash':None,'operator_id':None,'actual_started_at':None},
            'v07_long_trials':[{'input':mode,'required_duration_s':600,'actual_duration_s':None,'status':'NOT RUN'}
                               for mode in ('normal physical hand','staged synthetic replay')],
            'operator_feedback':{'opening_direction':None,'fatigue':None,'accepted_by_user':False}}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);args=parser.parse_args()
    value=matrix()
    if len(value['cases'])!=22 or len(value['v05_clear_shape_trials'])!=480:
        raise ValueError('original H12/V10 extraction failed; do not publish an incomplete matrix')
    with args.output.open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2)
