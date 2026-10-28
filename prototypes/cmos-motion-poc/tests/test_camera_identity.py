from types import SimpleNamespace
import pytest
from camera_identity import identify_camera


def device(path='device-1',index=1,backend=700):
    return SimpleNamespace(path=path,index=index,backend=backend,name='synthetic camera',vid=18,pid=52)


def test_backend_index_and_device_path_are_all_bound_without_storing_raw_id():
    first=identify_camera(1,700,[device(),device('other',0,1400)])
    assert 'path' not in first and first['name']=='synthetic camera'
    assert first!=identify_camera(1,700,[device('device-2')])
    with pytest.raises(ValueError):identify_camera(1,1400,[device()])


def test_ambiguous_or_missing_device_does_not_fall_back_to_configured_name():
    with pytest.raises(ValueError):identify_camera(1,700,[device(),device()])
    with pytest.raises(ValueError):identify_camera(1,700,[device(None)])
