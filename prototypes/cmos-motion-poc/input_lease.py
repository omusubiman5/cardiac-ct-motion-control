"""Process lifetime lease for each live target port; shared by normal and replay clients."""
import os
import tempfile
from pathlib import Path


class InputLease:
    def __init__(self, port, directory=None):
        self.path = Path(directory or tempfile.gettempdir()) / f'cardiac-motion-input-{port}.lock'
        self.stream = None

    def acquire(self):
        if self.stream is not None:
            return
        stream = self.path.open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                if self.path.stat().st_size == 0:
                    stream.write(b'0'); stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            stream.close()
            raise OSError('normal/replay input is already active for this port')
        self.stream = stream

    def release(self):
        if self.stream is None:
            return
        stream, self.stream = self.stream, None
        try:
            if os.name == 'nt':
                import msvcrt
                stream.seek(0); msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
        finally:
            stream.close()
