import json
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from session_client import SlicerSessionClient  # noqa: E402


def test_real_dispatcher_mouse_hand_roundtrip_rehandshakes_disarmed(server):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'slicer-cstamp' / 'tests'))
    from test_command_protocol import CommandDispatcher, FakeOps
    server.dispatcher = CommandDispatcher(FakeOps())
    client = SlicerSessionClient(port=server.port, timeout=2)
    try:
        assert client.connect()['ok']
        first_session = client.session
        assert client.send('arm')['ok']
        assert server.dispatcher.dispatch_local('claim_input', {'owner': 'mouse'}, input_method='mouse')['ok']
        assert server.dispatcher.session is None
        assert not client.send('status')['ok']
        assert not client.connected
        assert server.dispatcher.dispatch_local('claim_input', {'owner': 'hand'}, input_method='mouse')['ok']
        assert client.send('status')['ok']  # same polling path used by the real app
        assert client.connection_generation == 2 and client.session != first_session
        assert not client.last_state['armed'] and not server.dispatcher.armed
        assert sum(p.get('cmd') == 'arm' for p in server.requests) == 1
        assert client.send('arm')['ok']  # explicit new start, not a replay
        assert server.dispatcher.armed
    finally:
        client.close()


@pytest.mark.parametrize('reason', ['no session; send hello first', 'wrong session'])
def test_invalidated_server_session_closes_without_replaying_command(server, monkeypatch, reason):
    client = SlicerSessionClient(port=server.port, timeout=2)
    client.connect()
    client.send('arm')
    original_generation = client.connection_generation
    calls = []
    def rejected(payload):
        calls.append(payload)
        return {'ok': False, 'reason': reason}
    monkeypatch.setattr(client, '_roundtrip', rejected)
    result = client.send('commit', {'draft_id': 'do-not-replay'})
    assert not result['ok']
    assert [p['cmd'] for p in calls] == ['commit']
    assert client.session is None and not client.connected
    assert not client.last_state['armed']
    monkeypatch.undo()
    try:
        assert client.connect()['ok']
        assert client.connection_generation == original_generation + 1
        assert not client.last_state['armed']
        assert not any(p.get('cmd') == 'commit' for p in server.requests)
    finally:
        client.close()


def test_partial_response_cannot_extend_total_deadline():
    local, peer = socket.socketpair()
    client = SlicerSessionClient(timeout=.15)
    client._socket = local
    client.session = 'test'
    client.connected = True
    client.last_state = {'armed':True}
    def drip():
        try:
            peer.recv(4096)
            for _ in range(30):
                peer.sendall(b' ')
                time.sleep(.03)
        except OSError:
            pass
        finally:
            peer.close()
    sender = threading.Thread(target=drip, daemon=True)
    sender.start()
    started = time.monotonic()
    result = client.send('status')
    assert not result['ok'] and not client.connected
    assert time.monotonic()-started < .6
    assert not client.last_state['armed']
    sender.join(1)


def test_timeout_preserves_unknown_outcome_trace_and_clears_armed(server, monkeypatch):
    client = SlicerSessionClient(port=server.port)
    client.connect()
    client.send('arm')
    client.last_state['draft'] = True
    traces = []
    client.trace_sink = traces.append
    def fail(payload):
        raise socket.timeout('injected delayed response')
    monkeypatch.setattr(client, '_roundtrip', fail)
    result = client.send('commit', {'draft_id':'test'})
    assert not result['ok'] and not client.connected
    assert not client.last_state['armed'] and client.last_state['draft']
    assert traces[0]['trace']['req'] == client.last_request
    assert traces[0]['trace']['outcome'] == 'unknown'
    assert traces[0]['latency_ms'] >= 0
    assert client.transport_drops == 1


def test_rejected_hello_never_attempts_a_command_on_a_closed_socket(monkeypatch):
    client=SlicerSessionClient()
    monkeypatch.setattr(client,'connect',lambda:{'ok':False,'reason':'runtime changed'})
    assert client.send('arm')=={'ok':False,'reason':'runtime changed'}
    assert client.last_request is None


def test_trace_disk_failure_does_not_resend_a_successful_operation(server):
    client=SlicerSessionClient(port=server.port,timeout=2)
    def failed_sink(record):raise OSError('metadata disk failure')
    client.trace_sink=failed_sink
    try:
        result=client.send('arm')
        assert result['ok'] is True
        assert client.trace_error=='metadata disk failure'
        assert sum(r.get('cmd')=='arm' for r in server.requests)==1
    finally:client.close()


class FakeServer:
    """Minimal protocol server over a real loopback socket."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.requests = []
        self.dispatcher = None
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            conn.settimeout(10.0)
            buf = b""
            while True:
                try:
                    chunk = conn.recv(4096)
                except (OSError, socket.timeout):
                    break
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    data = json.loads(line.decode())
                    self.requests.append(data)
                    if self.dispatcher is not None:
                        response = self.dispatcher.handle_line(line)
                        conn.sendall((json.dumps(response) + '\n').encode())
                        continue
                    if data.get("cmd") == "hello":
                        conn.sendall(
                            b'{"ok": true, "session": "s-1",'
                            b' "state": {"armed": false}}\n'
                        )
                    else:
                        conn.sendall(
                            (json.dumps({
                                "ok": True, "req": data.get("req"),
                                "state": {"armed": True},
                            }) + "\n").encode()
                        )
            conn.close()

    def close(self):
        self.sock.close()


@pytest.fixture
def server():
    server = FakeServer()
    yield server
    server.close()


def test_hello_then_command_envelope(server):
    client = SlicerSessionClient(port=server.port, timeout=2.0)
    hello = client.connect()
    assert hello["ok"]
    assert client.session == "s-1"

    response = client.send("arm")
    assert response["ok"]
    sent = server.requests[-1]
    assert sent["v"] == 1
    assert sent["session"] == "s-1"
    assert sent["seq"] == 1
    assert sent["req"]
    assert isinstance(sent["ts"], float)
    assert sent["cmd"] == "arm"
    client.close()


def test_seq_increases(server):
    client = SlicerSessionClient(port=server.port, timeout=2.0)
    client.connect()
    client.send("status")
    client.send("status")
    seqs = [r["seq"] for r in server.requests[1:]]
    assert seqs == sorted(seqs) == [1, 2]
    client.close()


def test_transport_failure_is_fail_closed(server):
    client = SlicerSessionClient(port=server.port, timeout=2.0)
    client.connect()
    server.close()  # listener closed; existing conn still open
    # kill client-side view of the peer by stopping reads: emulate by
    # closing the socket server-side is not exposed, so simulate total
    # loss by connecting to a dead port after close
    client.close()
    client._socket = None
    client.session = None
    dead = SlicerSessionClient(port=1, timeout=0.2)
    response = dead.send("arm")
    assert response["ok"] is False
    assert "connect failed" in response["reason"]
    assert not dead.connected


def test_reconnect_gets_new_session_and_is_not_armed(server):
    client = SlicerSessionClient(port=server.port, timeout=2.0)
    client.connect()
    client.send("arm")
    assert client.last_state.get("armed") is True
    client.close()
    client.connect()
    # the client mirrors whatever the server reports; a fresh hello
    # always comes back disarmed from the dispatcher
    assert client.last_state.get("armed") is False
    client.close()
