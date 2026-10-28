from types import SimpleNamespace as N
from standard_gesture import decode_result
from standard_gesture import StandardObservation, operation_shape
from tests.test_gesture_fsm import make_landmarks
from gesture_fsm import Shape
import pytest

def observation(category, score=.9, **kwargs):
    return StandardObservation(1,make_landmarks(**kwargs),(),(),category,score,'Left',.99,1.)

@pytest.mark.parametrize('category,expected', [('Closed_Fist',Shape.FIST),('Thumb_Up',Shape.THUMB),('Thumb_Down',Shape.THUMB_DOWN),('ILoveYou',Shape.ILOVEYOU),('Victory',Shape.TWO)])
def test_standard_categories_control_discrete_intents(category,expected):
    assert operation_shape(observation(category))==expected

@pytest.mark.parametrize('category', ['Closed_Fist','Thumb_Up','Victory','ILoveYou'])
def test_low_score_does_not_fall_back_to_motion(category):
    assert operation_shape(observation(category,.2,index=True))==Shape.UNKNOWN

def _thumb_down_landmarks():
    lm = make_landmarks()
    lm[2] = type(lm[2])(0.44, 0.78)
    lm[3] = type(lm[3])(0.44, 0.90)
    lm[4] = type(lm[4])(0.44, 1.05)
    return lm

def _thumb_sideways_landmarks():
    # A straight extended thumb pointing mostly sideways/slightly down:
    # forward_ratio lands between the up and down bands (~-0.30).
    lm = make_landmarks()
    lm[2] = type(lm[2])(0.38, 0.50)
    lm[3] = type(lm[3])(0.38, 0.62)
    lm[4] = type(lm[4])(0.38, 0.75)
    return lm

def test_marginal_up_rescued_even_when_thumb_not_clearly_forward():
    # The model picks the direction; geometry only confirms a straight
    # extended thumb that is not clearly pointing down.
    obs = StandardObservation(1, _thumb_sideways_landmarks(), (), (),
                              'Thumb_Up', .6, 'Left', .99, 1.)
    assert operation_shape(obs) == Shape.THUMB

def test_sideways_thumb_is_not_a_thumb_down():
    obs = StandardObservation(1, _thumb_sideways_landmarks(), (), (),
                              'Thumb_Down', .6, 'Left', .99, 1.)
    assert operation_shape(obs) == Shape.UNKNOWN

@pytest.mark.parametrize('category,kwargs,expected', [
    ('ILoveYou', {'index': True, 'pinky': True, 'thumb_out': True}, Shape.ILOVEYOU),
    ('Victory', {'index': True, 'middle': True}, Shape.TWO),
])
def test_marginal_iloveyou_and_victory_rescued_by_finger_pattern(category, kwargs, expected):
    obs = StandardObservation(1, make_landmarks(**kwargs), (), (), category, .6, 'Left', .99, 1.)
    assert operation_shape(obs) == expected

@pytest.mark.parametrize('category,kwargs', [
    ('ILoveYou', {'index': True, 'middle': True}),   # model says ILY but pose is victory
    ('ILoveYou', {'index': True}),                    # only index out
    ('Victory', {'index': True}),                     # model says V but pose is point
    ('Victory', {}),                                  # model says V but pose is fist
])
def test_marginal_discrete_still_fails_closed_on_mismatch(category, kwargs):
    obs = StandardObservation(1, make_landmarks(**kwargs), (), (), category, .6, 'Left', .99, 1.)
    assert operation_shape(obs) == Shape.UNKNOWN

@pytest.mark.parametrize('category,kwargs,expected', [
    ('Closed_Fist', {}, Shape.FIST),
    ('Thumb_Up', {'thumb_out': True}, Shape.THUMB),
    ('Thumb_Down', {}, Shape.THUMB_DOWN),
])
def test_marginal_score_rescued_by_geometry(category, kwargs, expected):
    # A clear pose with a marginal model score is accepted when the
    # deterministic geometry verifier confirms the same shape.
    lm = _thumb_down_landmarks() if category == 'Thumb_Down' else make_landmarks(**kwargs)
    obs = StandardObservation(1, lm, (), (), category, .6, 'Left', .99, 1.)
    assert operation_shape(obs) == expected

@pytest.mark.parametrize('category,kwargs', [
    ('Closed_Fist', {'index': True}),        # model says fist but index is out
    ('Thumb_Up', {}),                         # model says up but thumb is folded
    ('Thumb_Up', {'index': True}),            # model says up but pose is point
    ('Thumb_Down', {'thumb_out': True}),      # model says down but thumb points up
    ('Thumb_Down', {'index': True, 'middle': True, 'ring': True, 'pinky': True}),  # open palm
])
def test_marginal_score_still_fails_closed_on_mismatch(category, kwargs):
    obs = StandardObservation(1, make_landmarks(**kwargs), (), (), category, .6, 'Left', .99, 1.)
    assert operation_shape(obs) == Shape.UNKNOWN

def test_unknown_never_falls_back_to_legacy_fist_or_thumb():
    assert operation_shape(observation('None'))==Shape.UNKNOWN
    assert operation_shape(observation('None',thumb_out=True))==Shape.UNKNOWN

@pytest.mark.parametrize('kwargs,expected', [({'index':True},Shape.POINT),({'index':True,'middle':True,'ring':True,'pinky':True},Shape.OPEN_PALM),({'index':True,'pinch':True},Shape.PINCH),({'index':True,'middle':True,'ring':True},Shape.THREE)])
def test_existing_view_and_three_finger_routes(kwargs,expected):
    assert operation_shape(observation('None',**kwargs))==expected

def test_separate_gesture_and_handedness_scores_and_preserve_depth():
    p=N(x=.2,y=.3,z=-.1)
    r=N(hand_landmarks=[[p]],hand_world_landmarks=[[p]],
        gestures=[[N(category_name='Closed_Fist',score=.72)]],
        handedness=[[N(category_name='Left',score=.99)]])
    obs=decode_result(r,1.)
    assert obs.category=='Closed_Fist' and obs.gesture_score==.72
    assert obs.handedness_score==.99
    assert obs.image_landmarks_3d==((.2,.3,-.1),)
    assert obs.world_landmarks==((.2,.3,-.1),)

def test_no_hand_is_not_unrecognized_hand():
    assert decode_result(N(hand_landmarks=[]),1.).category=='No_Hand'
    r=N(hand_landmarks=[[]],hand_world_landmarks=[],gestures=[],handedness=[])
    assert decode_result(r,1.).category=='None'

def test_multiple_hands_do_not_select_first_hand():
    obs=decode_result(N(hand_landmarks=[[],[]]),1.)
    assert obs.category=='Multiple_Hands' and obs.landmarks is None

def test_menu_navigation_home_back_and_draft_cancel():
    from tests.test_op_controller import Clock, FakeClient, hold
    from op_controller import OperationController
    clock=Clock();client=FakeClient();client.last_state.update(armed=True,draft=True,mode='move')
    ops=OperationController(client,now=clock,panel_menu=True)
    # ILoveYou from any branch returns to the main menu, draft preserved
    hold(ops,clock,Shape.ILOVEYOU,1.)
    assert ops.panel_menu.opened and ops.panel_menu.page=='main' and ops.panel_menu.index==0
    hold(ops,clock,Shape.NONE,.5)
    # thumb up moves to the previous (wrapped, last) item
    hold(ops,clock,Shape.THUMB,1.)
    assert ops.panel_menu.index==len(ops.panel_menu.entries)-1
    hold(ops,clock,Shape.NONE,.5)
    # thumb down past the last entry backs out of the main menu
    hold(ops,clock,Shape.THUMB_DOWN,1.)
    assert not ops.panel_menu.opened
    hold(ops,clock,Shape.NONE,.5)
    # with the menu closed, thumb down cancels the draft and returns to view
    hold(ops,clock,Shape.THUMB_DOWN,1.)
    assert client.last_state['draft'] is False
    assert client.last_state['mode'] == 'view'
    assert [cmd for cmd,_ in client.sent] == ['cancel','select_mode']
