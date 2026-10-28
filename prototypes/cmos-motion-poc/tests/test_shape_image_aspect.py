"""Synthetic regression, not real-hand accuracy measurement."""
import math
import pytest
from tests.test_gesture_fsm import make_landmarks
from gesture_fsm import classify_shape, Shape
from motion_engine import Point

@pytest.mark.parametrize('aspect', [1, 16/9, 9/16, 4/3])
@pytest.mark.parametrize('angle', range(0,360,5))
@pytest.mark.parametrize('name,kwargs', [
    ('fist',{}), ('thumb',{'thumb_out':True}),
    ('point',{'index':True}), ('two',{'index':True,'middle':True}),
    ('three',{'index':True,'middle':True,'ring':True}),
    ('open_palm',{'index':True,'middle':True,'ring':True,'pinky':True}),
    ('pinch',{'index':True,'pinch':True}),
])
def test_same_physical_hand_across_rotation_and_aspect(aspect,angle,name,kwargs):
    a=math.radians(angle);c,s=math.cos(a),math.sin(a)
    # Canonical square geometry, rotate in equal units then encode as image x/y.
    lm={i:Point(.5+(c*(p.x-.5)-s*(p.y-.5))/aspect,
                .5+s*(p.x-.5)+c*(p.y-.5)) for i,p in make_landmarks(**kwargs).items()}
    assert classify_shape(lm,image_aspect=aspect)==Shape(name)

@pytest.mark.parametrize('angle',range(0,360,5))
def test_reported_side_of_fist_does_not_become_thumb(angle):
    lm=make_landmarks();lm[2],lm[3],lm[4]=Point(.4,.78),Point(.36,.735),Point(.32,.69)
    a=math.radians(angle);c,s=math.cos(a),math.sin(a);ratio=16/9
    rotated={i:Point(.5+(c*(p.x-.5)*ratio-s*(p.y-.5))/ratio,
                    .5+s*(p.x-.5)*ratio+c*(p.y-.5)) for i,p in lm.items()}
    assert classify_shape(rotated,image_aspect=ratio)==Shape.FIST
