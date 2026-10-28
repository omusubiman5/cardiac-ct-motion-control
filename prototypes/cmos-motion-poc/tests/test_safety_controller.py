from safety_controller import (
    fresh_frame,
    ControllerState,
    Observation,
    SafetyController,
)


def test_start_frame_freshness_rejects_stale_future_and_nonfinite():
    assert fresh_frame(9.9, 10, .25)
    for timestamp in (9, 11, float('nan'), float('inf')):
        assert not fresh_frame(timestamp, 10, .25)
        controller = SafetyController(now=lambda:10)
        controller.arm()
        assert not controller.update(obs(timestamp)).allowed


def make_controller(now_list):
    iterator = iter(now_list)
    return SafetyController(
        max_frame_age=0.25,
        min_confidence=0.5,
        stability_frames=3,
        now=lambda: next(iterator),
    )


def obs(ts, hands=1, conf=0.9, valid=True):
    return Observation(
        hand_count=hands, timestamp=ts, confidence=conf, intent_valid=valid
    )


def test_disabled_until_armed():
    controller = SafetyController(now=lambda: 0.0)
    result = controller.update(obs(0.0))

    assert result.allowed is False
    assert controller.state is ControllerState.DISABLED


def test_stable_sequence_reaches_executing():
    times = [0.0] * 8
    controller = make_controller(times)
    controller.arm()

    controller.update(obs(0.0))  # READY -> TRACKING
    controller.update(obs(0.0))  # stable 2
    result = controller.update(obs(0.0))  # stable 3 -> EXECUTING

    assert controller.state is ControllerState.EXECUTING
    assert result.allowed is True


def test_multiple_hands_release_and_drop_to_ready():
    times = [0.0] * 8
    controller = make_controller(times)
    controller.arm()
    for _ in range(4):
        controller.update(obs(0.0))
    assert controller.state is ControllerState.EXECUTING

    result = controller.update(obs(0.0, hands=2))

    assert result.release is True
    assert result.allowed is False
    assert controller.state is ControllerState.READY


def test_stale_frame_releases_and_does_not_reexecute_on_reconnect():
    times = [0.0] * 8
    controller = make_controller(times)
    controller.arm()
    for _ in range(4):
        controller.update(obs(0.0))

    result = controller.update(obs(-1.0))  # stale
    assert result.release is True
    assert controller.state is ControllerState.READY

    # camera returning alone must not restore EXECUTING
    result = controller.update(obs(0.0))
    assert result.allowed is False
    assert controller.state is ControllerState.TRACKING


def test_ambiguous_intent_blocks_output():
    times = [0.0] * 8
    controller = make_controller(times)
    controller.arm()
    for _ in range(4):
        controller.update(obs(0.0))

    result = controller.update(obs(0.0, valid=False))

    assert result.allowed is False
    assert result.release is True


def test_fault_requires_manual_rearm():
    times = [0.0] * 8
    controller = make_controller(times)
    controller.arm()
    controller.fault("output exception")

    result = controller.update(obs(0.0))
    assert result.allowed is False
    assert controller.state is ControllerState.FAULT

    controller.arm()
    assert controller.state is ControllerState.READY
