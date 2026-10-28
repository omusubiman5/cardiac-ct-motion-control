import json

import pytest

from config import AppConfig


@pytest.mark.parametrize('field,value', [('camera_index',True), ('rotate_gain',float('nan')),
                                        ('tilt_deg_per_norm',float('inf')),('zoom_accel',False),
                                        ('mirror',1),('allowed_target_exes',['valid',8])])
def test_invalid_effective_values_fail_before_camera_start(field,value):
    with pytest.raises(ValueError):AppConfig(**{field:value}).validate()


def test_defaults_do_not_select_a_target_window():
    config = AppConfig.load(None)
    assert config.target_window_title == ""


def test_unknown_key_is_rejected(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"send_any_key": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown config keys"):
        AppConfig.load(path)


def test_invalid_camera_index_is_rejected(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"camera_index": -1}), encoding="utf-8")
    with pytest.raises(ValueError, match="camera_index"):
        AppConfig.load(path)

