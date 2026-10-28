"""Metadata-only mapping of an OpenCV backend/index to its enumerated device."""
import hashlib


def identify_camera(index, backend, candidates=None):
    if candidates is None:
        from cv2_enumerate_cameras import enumerate_cameras
        candidates=enumerate_cameras(backend)
    matches=[c for c in candidates if c.index==index and c.backend==backend]
    if len(matches)!=1 or not isinstance(matches[0].path,str) or not matches[0].path:
        raise ValueError('camera device identity unavailable or ambiguous for this backend/index')
    camera=matches[0]
    return {'name':camera.name,'vid':camera.vid,'pid':camera.pid,
            'device_path_sha256':hashlib.sha256(camera.path.casefold().encode('utf-8')).hexdigest()}
