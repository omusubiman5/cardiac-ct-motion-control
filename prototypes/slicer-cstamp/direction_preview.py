"""Read-only placement-plane preview; no world geometry or scene mutation."""
import math

def preview_points(template, placement):
    c, s = math.cos(placement.in_plane_angle), math.sin(placement.in_plane_angle)
    return [(x*c-y*s, x*s+y*c) for x, y, _ in template.local_points(placement.path_dir)]
