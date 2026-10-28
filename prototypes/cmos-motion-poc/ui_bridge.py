"""Ephemeral local UI transport; never creates a camera file or TCP client."""
import base64
import json
import mmap
import struct
import time
import zlib

CAPACITY = 512 * 1024
HEADER = struct.Struct('<III')
ACTIONS = {'arm', 'disarm', 'open', 'next', 'select', 'back', 'close', 'preview'}


class MemoryChannel:
    def __init__(self, name, memory=None):
        self.memory = memory if memory is not None else mmap.mmap(
            -1, CAPACITY, tagname='Local\\CardiacHandUI-v1-' + name)
        self.generation = 0

    def write(self, value):
        data = json.dumps(value, ensure_ascii=False).encode('utf-8')
        if len(data) > CAPACITY - HEADER.size:
            raise ValueError('UI payload exceeds capacity')
        self.generation += 2
        self.memory[:HEADER.size] = HEADER.pack(self.generation - 1, 0, 0)
        self.memory[HEADER.size:HEADER.size + len(data)] = data
        self.memory[:HEADER.size] = HEADER.pack(self.generation, len(data), zlib.crc32(data))

    def read(self):
        head = bytes(self.memory[:HEADER.size])
        generation, length, checksum = HEADER.unpack(head)
        if not generation or generation % 2 or not 0 < length <= CAPACITY - HEADER.size:
            return None
        data = bytes(self.memory[HEADER.size:HEADER.size + length])
        if head != bytes(self.memory[:HEADER.size]) or zlib.crc32(data) != checksum:
            return None
        try:
            value = json.loads(data)
            return value if isinstance(value, dict) else None
        except (ValueError, UnicodeError):
            return None

    def close(self):
        self.memory.close()


class RecognizerUI:
    def __init__(self):
        self.state = MemoryChannel('state')
        self.requests = MemoryChannel('requests')
        self.liveness = MemoryChannel('liveness')
        self.last_panel_seen = time.time()
        # Never replay a request from an earlier recognizer process.
        old = self.requests.read() or {}
        self.last_id = old.get('id')
        self.preview = False
        self.last_publish = 0.0
        self.last_status = 0.0
        self.status_ms = 0.0

    def panel_gone(self):
        value = self.liveness.read() or {}
        now = time.time()
        if 0 <= now - value.get('ts', 0) < 2.0:
            self.last_panel_seen = now
        return now - self.last_panel_seen > 10.0

    def poll(self, ops):
        request = self.requests.read()
        if not request or request.get('id') == self.last_id:
            return
        self.last_id = request.get('id')
        if not valid_request(request):
            return
        action = request['action']
        if action == 'preview':
            self.preview = request.get('enabled') is True
        elif action in {'arm', 'disarm'}:
            ops._send(action)
            if action == 'disarm':
                ops.panel_menu.close()
        elif ops.armed:
            menu = ops.panel_menu
            if action == 'open':
                menu.show('edit' if ops.draft else 'main')
                ops.last_accepted_at = ops._now()
            elif action == 'close':
                menu.close()
                ops.last_accepted_at = ops._now()
            elif menu.opened:
                if action == 'next':
                    menu.next()
                    ops.last_accepted_at = ops._now()
                elif action == 'back':
                    menu.back()
                    ops.last_accepted_at = ops._now()
                elif action == 'select':
                    ops._panel_select()
            ops.menu_open = menu.opened
            ops._reset_continuous()

    def publish(self, ops, cv2, frame):
        now = time.monotonic()
        if now - self.last_publish < 0.2:
            return
        self.last_publish = now
        # Same authoritative connection, no second hello/session reset.
        if now - self.last_status >= 1.0:
            previous = ops.last_response
            status_started = time.perf_counter()
            ops._send('status')
            self.status_ms = (time.perf_counter() - status_started) * 1000.0
            if ops.client.connected:
                ops.last_response = previous
            self.last_status = now
        from hand_menu import MAIN, EDIT
        menu = ops.panel_menu
        opened = menu.opened and ops.armed
        entries = menu.entries if opened else MAIN
        value = {'ts': time.time(), 'connected': ops.client.connected,
                 'armed': ops.armed, 'draft': ops.draft, 'mode': ops.mode,
                 'frozen': ops.draft_frozen,
                 'aim_valid': ops.aim_valid,
                 'layer': ops._state.get('layer', ''), 'opened': opened,
                 'page': menu.page if opened else 'main',
                 'selected': menu.index if opened else -1,
                 'entries': [{'key': e.key, 'label': e.label, 'detail': e.detail} for e in entries],
                 'shape': getattr(ops, 'recognition_shape', ops._shape).value,
                 'hold': ops._arm_hold.elapsed_s, 'hold_required': ops._arm_hold.hold_s,
                 'detail': getattr(ops, 'recognition_detail', ''),
                 'thumb_geometry': getattr(ops, 'thumb_geometry', None),
                 'input': {**getattr(ops, 'input_diagnostics', {}),
                           'generation':getattr(ops.client,'connection_generation',0),
                           'roundtrip_ms':getattr(ops.client,'last_roundtrip_ms',None),
                           'transport_drops':getattr(ops.client,'transport_drops',0)},
                 'reason': (("受付停止中：I Love You（親指・人差し指・小指）を1.5秒保持して再開。 " if not ops.armed else "")
                            + (menu.notice or ops.last_response.get('reason', '') or ops.notice)),
                 'confirmation': menu.confirm_snapshot if opened and menu.page == 'confirm' else None,
                 'plan_delta': ops.status_details.get('plan_delta'),
                 'plan_view': ops.status_details.get('plan_view'),
                 'audit':ops.status_details.get('pending_audit'),
                 'view_application': ops.status_details.get('view_application'),
                 'ack': self.last_id}
        if self.preview:
            ok, jpeg = cv2.imencode('.jpg', cv2.resize(frame, (320, 240)),
                                   [cv2.IMWRITE_JPEG_QUALITY, 65])
            if ok:
                value['preview'] = base64.b64encode(jpeg).decode('ascii')
        self.state.write(value)

    def close(self):
        self.state.write({'ts': time.time(), 'connected': False, 'armed': False,
                          'reason': '認識アプリが停止しました'})
        self.state.close()
        self.requests.close()
        self.liveness.close()


def valid_request(request, now=None):
    now = time.time() if now is None else now
    ts = request.get('ts')
    return (isinstance(request.get('id'), str) and len(request['id']) <= 64
            and request.get('action') in ACTIONS
            and isinstance(ts, (int, float)) and not isinstance(ts, bool)
            and 0 <= now - ts <= 2.0)
