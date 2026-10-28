from target_guard import StrictTargetGuard


SLICER_EXE = r"C:\Program Files\Slicer\Slicer.exe"


class FakeApi:
    def __init__(self, hwnd=100, pid=55, image=SLICER_EXE):
        self.hwnd = hwnd
        self.pid = pid
        self.image = image

    def foreground_hwnd(self):
        return self.hwnd

    def process_id_of(self, hwnd):
        return self.pid

    def image_path_of(self, pid):
        return self.image

    def window_class_of(self, hwnd):
        return "Qt5152QWindowIcon"


def test_allowed_process_is_approved():
    guard = StrictTargetGuard({SLICER_EXE}, FakeApi())

    allowed, reason = guard.check()

    assert allowed is True
    assert "target matched" in reason


def test_wrong_process_is_rejected():
    guard = StrictTargetGuard(
        {SLICER_EXE}, FakeApi(image=r"C:\Windows\notepad.exe")
    )

    allowed, reason = guard.check()

    assert allowed is False
    assert "not an allowed target" in reason


def test_no_foreground_window_is_rejected():
    guard = StrictTargetGuard({SLICER_EXE}, FakeApi(hwnd=0))

    allowed, reason = guard.check()

    assert allowed is False
    assert "no foreground window" in reason


def test_unknown_image_is_rejected():
    guard = StrictTargetGuard(
        {SLICER_EXE}, FakeApi(pid=55, image="")
    )

    allowed, reason = guard.check()

    assert allowed is False


def test_path_normalization_matches():
    guard = StrictTargetGuard(
        {r"c:/program files/slicer/slicer.exe"},
        FakeApi(image=r"C:\Program Files\Slicer\Slicer.exe"),
    )

    allowed, _ = guard.check()

    assert allowed is True
