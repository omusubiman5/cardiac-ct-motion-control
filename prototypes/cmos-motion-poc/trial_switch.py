"""Metadata-only cooperative stop. Never transfers an armed session."""
import json
import os
import secrets
import sys
import time
from pathlib import Path


class TrialEndpoint:
    def __init__(self, directory, port, camera):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.nonce = secrets.token_hex(16)
        self.path = self.directory / f'normal-{os.getpid()}.json'
        self.request = self.directory / f'pause-{self.nonce}.json'
        self.paused = False
        self.metadata = {'pid': os.getpid(), 'nonce': self.nonce, 'port': port,
                         'camera': camera, 'cwd': os.getcwd(),
                         'argv': [sys.executable, str(Path(sys.argv[0]).resolve()), *sys.argv[1:]],
                         'phase': 'normal', 'created_ts': time.time()}
        self._write()

    def _write(self):
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.metadata), encoding='utf-8')
        os.replace(temporary, self.path)

    def poll(self, ops):
        if not self.request.exists():
            return False
        request = json.loads(self.request.read_text(encoding='utf-8'))
        if (request.get('nonce') != self.nonce or request.get('pid') != os.getpid()
                or request.get('action') != 'pause' or type(request.get('ts')) not in (int, float)
                or not 0 <= time.time() - request['ts'] <= 10):
            raise ValueError('invalid or stale trial pause request')
        response = ops._send('disarm')
        if not response.get('ok'):
            raise RuntimeError('normal server did not confirm disarm')
        ops.panel_menu.close()
        ops._reset_continuous()
        self.paused = True
        self.metadata.update(phase='stopping', armed=False)
        self._write()
        return True

    def stopped(self):
        self.metadata.update(phase='paused' if self.paused else 'stopped', armed=False)
        self._write()
