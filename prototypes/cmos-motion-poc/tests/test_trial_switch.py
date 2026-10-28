import json
import os
import time
from types import SimpleNamespace
import pytest
from trial_switch import TrialEndpoint


def test_pause_requires_current_nonce_and_confirmed_disarm(tmp_path):
    endpoint=TrialEndpoint(tmp_path,18944,1);calls=[]
    ops=SimpleNamespace(_send=lambda action:calls.append(action) or {'ok':True},
                        panel_menu=SimpleNamespace(close=lambda:calls.append('close')),
                        _reset_continuous=lambda:calls.append('reset'))
    endpoint.request.write_text(json.dumps({'id':'x','nonce':'wrong','pid':os.getpid(),'action':'pause','ts':time.time()}))
    with pytest.raises(ValueError):endpoint.poll(ops)
    assert calls==[]
    endpoint.request.write_text(json.dumps({'nonce':endpoint.nonce,'pid':os.getpid(),'action':'pause','ts':time.time()}))
    assert endpoint.poll(ops)
    assert calls==['disarm','close','reset']
    assert json.loads(endpoint.path.read_text())['phase']=='stopping'
    endpoint.stopped()
    assert json.loads(endpoint.path.read_text())['phase']=='paused'


def test_unconfirmed_stop_cannot_release_trial(tmp_path):
    endpoint=TrialEndpoint(tmp_path,18944,1)
    endpoint.request.write_text(json.dumps({'nonce':endpoint.nonce,'pid':os.getpid(),'action':'pause','ts':time.time()}))
    with pytest.raises(RuntimeError):endpoint.poll(SimpleNamespace(_send=lambda action:{'ok':False}))
    assert not endpoint.paused
    endpoint.stopped()
    assert json.loads(endpoint.path.read_text())['phase']=='stopped'
