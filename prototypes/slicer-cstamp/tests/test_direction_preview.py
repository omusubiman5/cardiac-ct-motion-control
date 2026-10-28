import math
import pytest
from cstamp import CStampController
from direction_preview import preview_points

def test_preview_uses_real_size_and_angle_without_changing_placement():
    c=CStampController(); c.stamp((10,20,30),(0,0,1))
    c.rotate_opening(math.pi/2)
    c.tilt_plane(0,.7)
    before=c.draft
    points=preview_points(c.draft_template,c.draft.placement)
    radius=c.draft_template.radius
    assert all(math.hypot(x,y)==pytest.approx(radius) for x,y in points)
    local=c.draft_template.local_points(c.draft.placement.path_dir)[0]
    assert points[0]==pytest.approx((-local[1],local[0]))
    assert c.draft==before
