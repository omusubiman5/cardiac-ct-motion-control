import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from view_commands import (  # noqa: E402
    MAX_DELTA,
    ViewCommandKind,
    parse_command,
)


def test_parse_rotate():
    cmd = parse_command('{"cmd": "rotate", "dx": 1.5, "dy": -0.5}')
    assert cmd is not None
    assert cmd.kind is ViewCommandKind.ROTATE
    assert cmd.dx == pytest.approx(1.5)
    assert cmd.dy == pytest.approx(-0.5)


def test_parse_pan():
    cmd = parse_command('{"cmd": "pan", "dx": 2, "dy": 3}')
    assert cmd is not None
    assert cmd.kind is ViewCommandKind.PAN


def test_parse_zoom():
    cmd = parse_command('{"cmd": "zoom", "ratio": 1.05}')
    assert cmd is not None
    assert cmd.kind is ViewCommandKind.ZOOM
    assert cmd.ratio == pytest.approx(1.05)


@pytest.mark.parametrize(
    "line",
    [
        '{"cmd": "keypress", "key": "a"}',        # keyboard is out of scope
        '{"cmd": "shell", "line": "dir"}',         # arbitrary commands
        '{"cmd": "rotate", "dx": "x", "dy": 0}',   # wrong type
        '{"cmd": "rotate", "dx": true, "dy": 0}',  # bool is not a number
        '{"cmd": "zoom", "ratio": 10}',            # over cap
        '{"cmd": "zoom", "ratio": 0.01}',          # under cap
        '{"cmd": "zoom"}',                          # missing field
        '{"cmd": "rotate", "dx": 1}',               # missing dy
        "not json",
        "[1, 2, 3]",
        '"rotate"',
        '{"cmd": "rotate", "dx": NaN, "dy": 0}',
        "",
    ],
)
def test_invalid_input_is_inert(line):
    assert parse_command(line) is None


def test_bytes_input_accepted():
    cmd = parse_command(b'{"cmd": "rotate", "dx": 1, "dy": 1}\n')
    assert cmd is not None


def test_oversized_line_rejected():
    line = '{"cmd": "rotate", "dx": 1, "dy": 1, "pad": "' + "x" * 5000 + '"}'
    assert parse_command(line) is None


def test_delta_cap_boundary():
    cmd = parse_command(
        f'{{"cmd": "pan", "dx": {MAX_DELTA}, "dy": {-MAX_DELTA}}}'
    )
    assert cmd is not None
    # Over-cap deltas are clamped, not rejected — a fast gesture frame
    # must lose magnitude, never the whole motion.
    cmd = parse_command(
        f'{{"cmd": "pan", "dx": {MAX_DELTA + 0.01}, "dy": 0}}'
    )
    assert cmd is not None and cmd.dx == MAX_DELTA
