"""Loopback client for the typed command protocol (command_protocol.py).

Each command is one JSON line carrying v/session/seq/req/ts/params and
gets one JSON response line back. The client owns the session obtained
from ``hello``, a strictly increasing sequence, and unique request ids.

Fail-closed: any transport error closes the socket and returns
``{"ok": False, "reason": "transport ..."}``. A reconnect obtains a new
session and the server clears ``armed`` — reconnection alone never
resumes control, matching the dispatcher contract.
"""

from __future__ import annotations

import itertools
import json
import socket
import time
import uuid
import os
from typing import Callable
from input_lease import InputLease


class SlicerSessionClient:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 18944,
        timeout: float = 1.0,
        now: Callable[[], float] = time.time,
    ) -> None:
        if host != "127.0.0.1":
            raise ValueError("SlicerSessionClient is loopback-only")
        self.host = host
        self.port = port
        self.timeout = timeout
        self._now = now
        self._socket: socket.socket | None = None
        self._buffer = b""
        self.session: str | None = None
        self._seq = itertools.count(1)
        self._req = itertools.count(1)
        self.connected = False
        # last accepted server state for the overlay / controller
        self.last_state: dict = {}
        self.last_error = ""
        self.request_namespace = uuid.uuid4().hex
        self.last_request = None
        self.input_lease = InputLease(port)
        self.connection_generation = 0
        self.last_roundtrip_ms = None
        self.transport_drops = 0
        self.runtime_manifest = None
        self.runtime_hash = None
        self.trace_context = None
        self.last_trace = None
        self.trace_sink = None
        self.trace_error = None

    # --- lifecycle ----------------------------------------------------

    def connect(self) -> dict:
        """Open the socket and perform the hello handshake."""
        if self._socket is not None:
            self.close()
        self.input_lease.acquire()
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        except OSError:
            self.input_lease.release()
            raise
        sock.settimeout(self.timeout)
        self._socket = sock
        self._buffer = b""
        self._seq = itertools.count(1)
        try:
            response = self._roundtrip({"cmd": "hello", "v": 1, 'runtime_manifest': self.runtime_manifest})
        except OSError:
            self.close()
            raise
        if not response.get("ok"):
            self.close()
            return response
        self.connection_generation += 1
        self.session = response["session"]
        self.runtime_hash = response.get('runtime_hash')
        self.connected = True
        self.last_state = response.get("state", {})
        self.last_error = ""
        return response

    def close(self) -> None:
        self.input_lease.release()
        if self._socket is not None:
            try:
                self._socket.close()
            finally:
                self._socket = None
        self.session = None
        self.connected = False
        # Keep draft metadata, but never advertise a disconnected session as armed.
        self.last_state = {**self.last_state, 'armed': False}
        self._buffer = b""

    # --- commands -------------------------------------------------------

    def send(self, cmd: str, params: dict | None = None) -> dict:
        """Send one command, return the parsed response. On transport
        failure the socket is closed and a synthetic rejection is
        returned. The remote outcome is unknown; never retry an edit blindly."""
        if self._socket is None or self.session is None:
            try:
                hello = self.connect()
                if not hello.get('ok'):
                    self.last_error = str(hello.get('reason','hello rejected'))
                    return {'ok':False,'reason':self.last_error}
            except OSError as error:
                self.last_error = f"connect failed: {error}"
                return {"ok": False, "reason": self.last_error}
        envelope = {
            "v": 1,
            "session": self.session,
            "seq": next(self._seq),
            "req": f"{self.request_namespace}-{next(self._req):06d}",
            "cmd": cmd,
            "ts": self._now(),
            "params": params or {},
            "runtime_hash": self.runtime_hash,
            "trace": self.trace_context,
        }
        self.last_request = envelope['req']
        started_ns = time.perf_counter_ns()
        started = time.perf_counter()
        try:
            response = self._roundtrip(envelope)
            self.last_roundtrip_ms = (time.perf_counter()-started)*1000
            received_ns = time.perf_counter_ns()
            server = response.get('server_timing', {})
            server_ns = server.get('received_ns')
            self.last_trace = {'req':envelope['req'],'generation':self.connection_generation,
                               'frame':self.trace_context,'sent_ns':started_ns,'response_ns':received_ns,
                               'server':server,'clock_offset_interval_ns':
                               [server_ns-received_ns, server_ns-started_ns] if isinstance(server_ns,int) else None}
        except (OSError, json.JSONDecodeError) as error:
            self.last_roundtrip_ms = (time.perf_counter()-started)*1000
            self.transport_drops += 1
            self.last_error = f"transport: {error}"
            self.last_trace = {'req':envelope['req'],'generation':self.connection_generation,
                               'frame':self.trace_context,'sent_ns':started_ns,
                               'response_ns':time.perf_counter_ns(),'server':{},
                               'outcome':'unknown','error':self.last_error}
            self.close()
            self._record_trace(cmd, {'ok':False,'reason':self.last_error})
            return {"ok": False, "reason": self.last_error}
        if isinstance(response.get("state"), dict):
            self.last_state = response["state"]
        if not response.get('ok') and response.get('reason') in {
            'no session; send hello first', 'wrong session'
        }:
            # Local mouse handover intentionally invalidates the server session
            # without dropping TCP. Do not keep advertising the stale session,
            # and never replay the rejected edit/arm. The next status poll will
            # obtain a fresh hello; control still needs an explicit new start.
            self.last_error = response['reason']
            self.close()
            self._record_trace(cmd, response)
            return response
        self.last_error = ""
        self._record_trace(cmd, response)
        return response

    def _record_trace(self, cmd, response):
        if self.trace_sink is not None:
            try:
                self.trace_sink({'cmd':cmd,'response':{'ok':response.get('ok'),'reason':response.get('reason')},
                                 'latency_ms':self.last_roundtrip_ms,'trace':self.last_trace})
            except (OSError, ValueError) as error:
                self.trace_error = str(error)

    def _roundtrip(self, payload: dict) -> dict:
        assert self._socket is not None
        deadline = time.monotonic() + self.timeout
        self._socket.settimeout(self.timeout)
        self._socket.sendall((json.dumps(payload) + "\n").encode())
        while b"\n" not in self._buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise socket.timeout('response deadline exceeded')
            self._socket.settimeout(remaining)
            chunk = self._socket.recv(4096)
            if not chunk:
                raise OSError("connection closed by peer")
            self._buffer += chunk
            if len(self._buffer) > 65536:
                raise OSError('response exceeds protocol size limit')
        line, self._buffer = self._buffer.split(b"\n", 1)
        response = json.loads(line.decode("utf-8"))
        if not isinstance(response, dict):
            raise OSError('response must be an object')
        return response
