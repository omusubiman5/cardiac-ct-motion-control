import time
from ui_bridge import MemoryChannel, CAPACITY, HEADER, valid_request, RecognizerUI


def test_incomplete_corrupt_and_oversized_memory_never_become_state():
    memory = bytearray(CAPACITY)
    channel = MemoryChannel('test', memory)
    assert channel.read() is None
    channel.write({'armed': True})
    assert channel.read() == {'armed': True}
    memory[HEADER.size] ^= 1
    assert channel.read() is None
    memory[:HEADER.size] = HEADER.pack(3, 10, 0)
    assert channel.read() is None
    memory[:HEADER.size] = HEADER.pack(4, CAPACITY, 0)
    assert channel.read() is None


def test_stale_future_unknown_or_invalid_request_cannot_control():
    now = 10.0
    for request in [{'id':'x','ts':7,'action':'arm'},
                    {'id':'x','ts':11,'action':'arm'},
                    {'id':'x','ts':10,'action':'exec'},
                    {'id':None,'ts':10,'action':'arm'}]:
        assert not valid_request(request, now)
    assert valid_request({'id':'x','ts':9,'action':'arm'}, now)


def test_same_mouse_request_cannot_fire_twice_and_unarmed_menu_is_inert():
    class Ops:
        armed = False
        calls = []
        def _send(self, action):
            self.calls.append(action)
    ui = RecognizerUI.__new__(RecognizerUI)
    ui.requests = MemoryChannel('test', bytearray(CAPACITY))
    ui.last_id = None
    ops = Ops()
    request = {'id':'one','ts':time.time(),'action':'arm'}
    ui.requests.write(request)
    ui.poll(ops)
    ui.poll(ops)
    assert ops.calls == ['arm']
    ui.requests.write({'id':'two','ts':time.time(),'action':'select'})
    ui.poll(ops)
    assert ops.calls == ['arm']


def test_missing_slicer_heartbeat_stops_worker_without_rearming():
    ui = RecognizerUI.__new__(RecognizerUI)
    ui.liveness = MemoryChannel('test', bytearray(CAPACITY))
    ui.last_panel_seen = time.time() - 11
    assert ui.panel_gone()
    ui.liveness.write({'ts':time.time()})
    assert not ui.panel_gone()


def test_closed_draft_menu_shows_main_overview_and_stopped_reason():
    from tests.test_op_controller import FakeClient, Clock
    from op_controller import OperationController
    from gesture_fsm import Shape
    client=FakeClient();client.last_state.update(draft=True,armed=False,mode='rotate')
    ops=OperationController(client,now=Clock(),panel_menu=True)
    ops.panel_menu.show('confirm');ops.menu_open=True
    ops.update(Shape.FIST,None)
    assert not ops.menu_open and not ops.panel_menu.opened
    ui=RecognizerUI.__new__(RecognizerUI)
    ui.state=MemoryChannel('test',bytearray(CAPACITY))
    ui.last_publish=0;ui.last_status=time.monotonic();ui.status_ms=0;ui.preview=False;ui.last_id=None
    ui.publish(ops,None,None)
    value=ui.state.read()
    assert value['page']=='main' and value['opened'] is False
    assert value['selected']==-1 and value['entries'][0]['key']=='view'
    assert '受付停止中' in value['reason']
    assert client.sent==[]
