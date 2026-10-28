from __future__ import annotations

import argparse
import hashlib
import os
import platform
import json
import sys
import time
from pathlib import Path

from config import AppConfig
from input_lease import InputLease
from gesture_fsm import Shape, classify_shape, thumb_geometry
from hand_landmarker import (
    HandObservation,
    LegacyHandRecognizer,
    TasksHandRecognizer,
)
from motion_engine import (
    Gesture,
    MotionAction,
    MotionEngine,
    Point,
    classify_gesture,
)
from mouse_relay import PreviewMouseRelay, WindowsMouseRelay
from op_controller import OperationController
from safety_controller import (
    fresh_frame,
    ControllerState,
    Observation,
    SafetyController,
)
from session_client import SlicerSessionClient
from target_guard import StrictTargetGuard


WINDOW_NAME = "Cardiac 3D Motion PoC"

# MediaPipe 21-landmark skeleton edges for the debug overlay.
HAND_EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CMOS camera hand-motion PoC for cardiac 3D view control"
    )
    parser.add_argument("--config", type=Path, help="JSON configuration file")
    parser.add_argument("--camera-index", type=int, help="override camera index")
    parser.add_argument('--prepare-configuration', type=Path, help='observe actual camera/model configuration into a NEW metadata file and exit without control')
    parser.add_argument('--trial-log', type=Path, help='metadata-only command trace JSONL, use a new file per trial')
    parser.add_argument(
        "--enable-input",
        action="store_true",
        help="send mouse input only to the configured foreground window",
    )
    parser.add_argument(
        "--slicer-connect",
        action="store_true",
        help="send typed view commands to the Slicer loopback server",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = AppConfig.load(args.config)
        if args.camera_index is not None:
            values = config.public_dict()
            values["camera_index"] = args.camera_index
            config = AppConfig(**values)
            config.validate()
        output_mode = config.output_mode
        if args.enable_input:
            output_mode = "mouse"
        if args.slicer_connect:
            output_mode = "slicer"
        session_client = None
        ops = None
        if output_mode == "mouse":
            if not config.allowed_target_exes:
                raise ValueError(
                    "allowed_target_exes is required with mouse output"
                )
            bridge = WindowsMouseRelay(
                config,
                StrictTargetGuard(set(config.allowed_target_exes)),
            )
        elif output_mode == "slicer":
            session_client = SlicerSessionClient(
                port=config.slicer_port,
                # Loopback commands stay synchronous; a network-share
                # payload makes the server's per-request verification IO
                # slower than the 1s default deadline.
                timeout=10.0,
            )
            ops = OperationController(
                session_client,
                panel_menu=True,
                gesture_hold_s=config.gesture_hold_s,
                arm_hold_s=config.arm_hold_s,
                rotate_deg_per_norm=config.rotate_deg_per_norm,
                rotate_deadzone=config.rotate_deadzone,
                pan_px_per_norm=config.pan_px_per_norm,
                zoom_ratio_per_norm=config.zoom_ratio_per_norm,
                wheel_zoom_ratio=config.wheel_zoom_ratio,
                aim_rate_hz=config.aim_rate_hz,
                opening_deg_per_norm=config.opening_deg_per_norm,
                tilt_deg_per_norm=config.tilt_deg_per_norm,
                loss_grace_s=config.loss_grace_s,
                zoom_config=__import__('zoom_engine').ZoomConfig(
                    deadzone=config.zoom_deadzone, accel=config.zoom_accel,
                    max_velocity=config.zoom_max_velocity, min_ratio=config.zoom_min_ratio,
                    max_ratio=config.zoom_max_ratio, release_tau=config.zoom_release_tau),
            )
            bridge = None
        else:
            bridge = PreviewMouseRelay()
    except (OSError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    try:
        import cv2
        import mediapipe as mp  # noqa: F401
    except ImportError as exc:
        print(
            f"Missing dependency: {exc}. Run .\\setup.ps1 first.",
            file=sys.stderr,
        )
        return 3

    backend = {
        "dshow": cv2.CAP_DSHOW,
        "msmf": cv2.CAP_MSMF,
        "any": cv2.CAP_ANY,
    }.get(config.camera_backend.casefold())
    if backend is None:
        print("camera_backend must be dshow, msmf, or any", file=sys.stderr)
        return 2

    camera_lease = InputLease('camera-'+str(config.camera_index))
    try:
        camera_lease.acquire()
        if session_client is not None:
            session_client.input_lease.acquire()
    except OSError as error:
        camera_lease.release()
        print(str(error),file=sys.stderr)
        return 2
    capture = cv2.VideoCapture(config.camera_index, backend)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera_width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera_height)
    if not capture.isOpened():
        capture.release()
        camera_lease.release()
        if session_client is not None: session_client.close()
        print(
            f"Camera {config.camera_index} could not be opened. Connect a USB CMOS camera "
            "or select another --camera-index.",
            file=sys.stderr,
        )
        return 4

    if session_client is not None:
        try:
            sampled, sample = capture.read()
            if not sampled:
                raise ValueError('camera actual dimensions could not be observed')
            model = Path(config.model_path)
            settings = config.public_dict()
            settings['output_mode'] = output_mode
            from camera_identity import identify_camera
            actual_backend=int(capture.get(cv2.CAP_PROP_BACKEND))
            identity=identify_camera(config.camera_index,actual_backend)
            session_client.runtime_manifest = {
                'settings': settings,
                'camera': {'index':config.camera_index, 'backend':capture.getBackendName(),
                           'width':int(sample.shape[1]), 'height':int(sample.shape[0]), **identity},
                'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),
                'python_version':platform.python_version(), 'windows_version':platform.platform(),
                'software_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in Path(__file__).resolve().parent.glob('*.py')},
            }
            if args.prepare_configuration:
                with args.prepare_configuration.open('x', encoding='utf-8') as stream:
                    json.dump(session_client.runtime_manifest, stream, ensure_ascii=False, indent=2, allow_nan=False)
                capture.release()
                camera_lease.release()
                session_client.close()
                return 0
            if args.trial_log:
                # Reserve a distinct run; never append one trial into a previous run.
                with args.trial_log.open('x', encoding='utf-8'):
                    pass
                def trace_sink(record):
                    with args.trial_log.open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n')
                session_client.trace_sink = trace_sink
            hello = session_client.connect()
            if not hello.get('ok'):
                raise ValueError('Slicer configuration rejected: '+str(hello.get('reason')))
        except (OSError, ValueError, ImportError) as error:
            session_client.close()
            capture.release()
            camera_lease.release()
            print(str(error), file=sys.stderr)
            return 2

    engine = MotionEngine(config)
    engine.enabled = True  # output is gated solely by SafetyController
    controller = SafetyController(
        min_confidence=config.min_detection_confidence,
    )
    if output_mode == "slicer":
        # the local controller is only the per-frame recognition gate;
        # protocol armed state lives on the server and is entered via
        # the dedicated I Love You hold (or Space as physical input)
        controller.arm()
    last_action: MotionAction | None = None
    last_status = "disabled"
    last_reason = "disabled"
    last_accepted_at: float | None = None
    failed_reads = 0
    previous_time = time.perf_counter()
    armed_since: float | None = None
    fps = 0.0
    diagnostic_at = 0.0
    sent_commands = 0

    model_path = Path(config.model_path)
    if not model_path.is_absolute():
        model_path = Path(__file__).resolve().parent / model_path

    if config.recognizer in {"tasks", "standard"}:
        if not model_path.is_file():
            print(
                f"Hand landmarker model missing: {model_path}. "
                "Install the pinned asset or set recognizer=legacy.",
                file=sys.stderr,
            )
            capture.release()
            cv2.destroyAllWindows()
            return 6
        if config.recognizer == 'standard':
            from standard_gesture import StandardGestureRecognizer
            recognizer = StandardGestureRecognizer(str(model_path),
                min_detection_confidence=config.min_detection_confidence,
                min_tracking_confidence=config.min_tracking_confidence)
        else:
            recognizer = TasksHandRecognizer(str(model_path), num_hands=2,
                min_detection_confidence=config.min_detection_confidence,
                min_tracking_confidence=config.min_tracking_confidence)
    else:
        recognizer = LegacyHandRecognizer(
            num_hands=2,
            min_detection_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        )

    # discrete mouse-wheel input on the preview window is converted to
    # the same continuous-ratio zoom command as a pinch (FR-022)
    wheel_ticks = {"count": 0}

    def _on_mouse(event, _x, _y, flags, _userdata):
        if event == cv2.EVENT_MOUSEWHEEL:
            wheel_ticks["count"] += 1 if flags > 0 else -1

    if ops is None:
        cv2.namedWindow(WINDOW_NAME)
        cv2.setMouseCallback(WINDOW_NAME, _on_mouse)
    hud = None
    unified_ui = None
    trial_endpoint = None
    if ops is not None:
        from ui_bridge import RecognizerUI
        unified_ui = RecognizerUI()
        from trial_switch import TrialEndpoint
        trial_endpoint = TrialEndpoint(Path(os.environ.get('CSTAMP_WORKSPACE_ROOT',Path(__file__).resolve().parents[2])) / 'work/input-switch',
                                       session_client.port, config.camera_index)

    try:
        frame_id = 0
        while True:
            if trial_endpoint is not None and trial_endpoint.poll(ops):
                return 0
            if unified_ui is not None:
                if unified_ui.panel_gone():
                    print('Slicer UI heartbeat lost; recognizer stopped.', flush=True)
                    return 0
                session_client.trace_context = None
                unified_ui.poll(ops)
            capture_started = time.perf_counter()
            ok, frame = capture.read()
            frame_id += 1
            acquired_ns = time.perf_counter_ns()
            capture_ms = (time.perf_counter() - capture_started) * 1000.0
            if not ok:
                failed_reads += 1
                gate = controller.fault("camera read failed")
                last_reason = gate.reason
                engine.reset_tracking()
                if bridge is not None:
                    bridge.release_all()
                if ops is not None:
                    ops.recognition_lost("camera read failed")
                    ops.on_transport_lost()
                if failed_reads >= 10:
                    print(
                        "Camera stream was lost; input was disabled.",
                        file=sys.stderr,
                    )
                    return 5
                continue
            failed_reads = 0

            if config.mirror:
                frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            now = time.monotonic()
            inference_started = time.perf_counter()
            obs = recognizer.recognize(rgb, timestamp=now)
            recognized_ns = time.perf_counter_ns()
            inference_ms = (time.perf_counter() - inference_started) * 1000.0
            if output_mode == "slicer":
                ops.input_diagnostics = {'width':int(frame.shape[1]), 'height':int(frame.shape[0]),
                                         'capture_ms':round(capture_ms,1),
                                         'inference_ms':round(inference_ms,1), 'fps':round(fps,1),
                                         'ui_status_ms':round(unified_ui.status_ms,1)}
                shape = (
                    classify_shape(
                        obs.landmarks,
                        config.pinch_threshold,
                        config.thumb_ratio,
                        image_aspect=frame.shape[1] / frame.shape[0],
                    )
                    if obs.landmarks is not None
                    else Shape.NONE
                )
                gesture = _legacy_gesture_of(shape)
                if config.recognizer == 'standard':
                    from standard_gesture import operation_shape
                    shape = operation_shape(obs, image_aspect=frame.shape[1]/frame.shape[0],
                        pinch_threshold=config.pinch_threshold, thumb_ratio=config.thumb_ratio,
                        min_gesture_score=config.min_gesture_confidence)
                    gesture = _legacy_gesture_of(shape)
                valid_obs = (
                    obs.landmarks is not None
                    and obs.hand_count == 1
                    and fresh_frame(obs.timestamp, time.monotonic(), controller.max_frame_age)
                    and obs.confidence >= config.min_detection_confidence
                    and shape not in (Shape.NONE, Shape.UNKNOWN)
                )
                ops.recognition_shape = shape
                ops.thumb_geometry = thumb_geometry(obs.landmarks, image_aspect=frame.shape[1] / frame.shape[0])
                ops.recognition_detail = (
                    f"手：{obs.hand_count}　信頼度：{obs.confidence:.2f}"
                    + ("" if valid_obs else "　開始条件を満たしていません")
                )
                if config.recognizer == 'standard':
                    ops.recognition_detail = (
                        f"標準：{obs.category}　手形スコア：{obs.gesture_score:.2f}"
                        + ("\n親指上：前へ　親指下：次へ・戻る　グー：決定" if ops.menu_open else "\n🤟：メニュー　親指上：C呼出　グー：決定")
                        + ("" if valid_obs else "　開始条件を満たしていません")
                    )
                gate = controller.update(
                    Observation(
                        hand_count=obs.hand_count,
                        timestamp=obs.timestamp,
                        confidence=obs.confidence,
                        intent_valid=shape not in (
                            Shape.NONE, Shape.UNKNOWN,
                        ),
                    )
                )
                # dispatcher.armed is the protocol authority; the local
                # gate is a per-frame recognition quality check only
                if ops.armed:
                    send_shape, send_lm = (
                        (shape, obs.landmarks)
                        if gate.allowed
                        else (Shape.NONE, None)
                    )
                else:
                    # dedicated arm path: needs a single valid hand but
                    # not yet EXECUTING stability
                    send_shape, send_lm = (
                        (shape, obs.landmarks) if valid_obs
                        else (Shape.NONE, None)
                    )
                if not valid_obs:
                    ops.recognition_lost('hand absent, ambiguous, or below confidence threshold')
                ops.hand_absent = obs.hand_count == 0
                session_client.trace_context = {'frame_id':frame_id,'acquired_ns':acquired_ns,
                                                'recognized_ns':recognized_ns,
                                                'gate_ns':time.perf_counter_ns()}
                request_before = session_client.last_request
                responses = ops.update(send_shape, send_lm)
                generated = session_client.last_request != request_before
                if generated:
                    ops.last_delivery = {'frame_id': frame_id, 'shape': shape.value,
                        'command': ops.last_command, 'req': session_client.last_request,
                        'ok': ops.last_response.get('ok'), 'reason': ops.last_response.get('reason', ''),
                        'trace': session_client.last_trace,
                        'view_application': ops.last_response.get('result', {}).get('view_application')}
                blocked = ''
                if not ops.armed:
                    blocked = '受付停止中'
                elif not gate.allowed:
                    blocked = gate.reason
                elif ops.menu_open:
                    blocked = 'メニュー操作中'
                elif not generated:
                    blocked = '移動量待ち／現在モードに割当なし'
                ops.input_diagnostics['pipeline'] = {
                    'frame_id': frame_id, 'recognized_shape': shape.value,
                    'gate_allowed': gate.allowed, 'gate_reason': gate.reason,
                    'mode': ops.mode, 'command_generated': generated, 'blocked': blocked,
                    'last_delivery': getattr(ops, 'last_delivery', None)}
                if session_client.trace_error:
                    ops._send('disarm')
                    print('Trial metadata unavailable: '+session_client.trace_error,file=sys.stderr)
                    return 6
                if wheel_ticks["count"]:
                    # wheel -> same SMOOTH_ZOOM ratio path (FR-022)
                    zoom_response = ops.zoom_step(
                        wheel_ticks["count"]
                    )
                    if zoom_response is not None:
                        responses.append(zoom_response)
                    wheel_ticks["count"] = 0
                if any(r.get("ok") for r in responses):
                    last_accepted_at = now
                    sent_commands += sum(
                        1 for r in responses if r.get("ok")
                    )
                if (
                    ops.armed
                    and ops.last_accepted_at is not None
                    and now - ops.last_accepted_at > config.input_timeout_s
                ):
                    ops._send("disarm")
                    last_accepted_at = None
                action = None
                status = _OpsStatus(ops)
                last_reason = ops.last_response.get(
                    "reason", gate.reason
                )
                if not ops.armed and not ops.last_response.get("reason"):
                    last_reason = "not armed: hold ONE I Love You for 1.5s"
            else:
                gesture = (
                    classify_gesture(obs.landmarks, config.pinch_threshold)
                    if obs.landmarks is not None
                    else Gesture.NONE
                )
                shape = Shape.NONE
                gate = controller.update(
                    Observation(
                        hand_count=obs.hand_count,
                        timestamp=obs.timestamp,
                        confidence=obs.confidence,
                        intent_valid=gesture is not Gesture.NONE,
                    )
                )
                if (
                    armed_since is not None
                    and now - armed_since > config.input_timeout_s
                ):
                    gate = controller.disarm()
                    armed_since = None
                    gate = controller.update(
                        Observation(
                            obs.hand_count, now, obs.confidence, False
                        )
                    )
                last_reason = gate.reason

                if gate.release or not gate.allowed:
                    engine.reset_tracking()
                    action = None
                else:
                    action = engine.update(obs.landmarks)
                status = bridge.apply(action)
                if status.applied:
                    sent_commands += 1
            diagnostic_now = time.monotonic()
            if diagnostic_now - diagnostic_at >= 1.0:
                print(
                    f"motion state={output_state(controller, ops)} mode={output_mode} "
                    f"hands={obs.hand_count} gesture={gesture.value} "
                    f"shape={shape.value} "
                    f"confidence={obs.confidence:.3f} "
                    f"arm_hold_s={ops._arm_hold.elapsed_s if ops is not None else 0.0:.2f} "
                    f"thumb={getattr(ops, 'thumb_geometry', None)!r} "
                    f"input={getattr(ops, 'input_diagnostics', None)!r} "
                    f"age_ms={(diagnostic_now - obs.timestamp) * 1000:.1f} "
                    f"gate={last_reason!r} action={format_action(action)!r} "
                    f"output={status.message!r} sent_total={sent_commands}",
                    flush=True,
                )
                diagnostic_at = diagnostic_now
            last_action = action or last_action
            last_status = status.message

            frame_now = time.perf_counter()
            delta = max(frame_now - previous_time, 1e-6)
            previous_time = frame_now
            instantaneous_fps = 1.0 / delta
            fps = (
                instantaneous_fps
                if fps == 0.0
                else 0.1 * instantaneous_fps + 0.9 * fps
            )

            if obs.landmarks:
                draw_hand(cv2, frame, obs.landmarks)
            draw_overlay(
                cv2,
                frame,
                controller,
                gesture,
                action,
                last_action,
                last_status,
                last_reason,
                obs.hand_count,
                fps,
                output_mode != "preview",
                ops=ops,
            )
            if unified_ui is not None:
                unified_ui.publish(ops, cv2, frame)
            else:
                cv2.imshow(WINDOW_NAME, frame)
            if hud is not None:
                hud.update(ops)

            key = cv2.waitKey(1) & 0xFF if unified_ui is None else -1
            if key in (27, ord("q"), ord("Q")):
                return 0
            if key == 32:
                if output_mode == "slicer":
                    # physical input alternative (FR-001): same contract,
                    # goes through the session like hand input
                    ops._send("disarm" if ops.armed else "arm")
                    last_accepted_at = time.monotonic()
                elif controller.state in (
                    ControllerState.DISABLED,
                    ControllerState.FAULT,
                ):
                    controller.arm()
                    armed_since = time.monotonic()
                    last_reason = "armed"
                else:
                    controller.disarm()
                    armed_since = None
                    last_reason = "disabled"
                if output_mode != "slicer":
                    engine.reset_tracking()
                    bridge.release_all()
                last_action = None
    finally:
        camera_lease.release()
        if unified_ui is not None:
            unified_ui.close()
        if hud is not None:
            hud.close()
        controller.disarm()
        if session_client is not None:
            session_client.close()
        elif bridge is not None:
            bridge.release_all()
        recognizer.close()
        capture.release()
        cv2.destroyAllWindows()
        if trial_endpoint is not None:
            trial_endpoint.stopped()


def draw_hand(cv2, frame, landmarks: dict[int, Point]) -> None:
    height, width = frame.shape[:2]
    for start, end in HAND_EDGES:
        a = landmarks.get(start)
        b = landmarks.get(end)
        if a is None or b is None:
            continue
        cv2.line(
            frame,
            (int(a.x * width), int(a.y * height)),
            (int(b.x * width), int(b.y * height)),
            (80, 200, 80),
            2,
            cv2.LINE_AA,
        )
    for point in landmarks.values():
        cv2.circle(
            frame,
            (int(point.x * width), int(point.y * height)),
            3,
            (60, 160, 255),
            -1,
            cv2.LINE_AA,
        )


def draw_overlay(
    cv2,
    frame,
    controller: SafetyController,
    gesture: Gesture,
    action: MotionAction | None,
    last_action: MotionAction | None,
    status: str,
    reason: str,
    hand_count: int,
    fps: float,
    real_input: bool,
    ops: OperationController | None = None,
) -> None:
    armed = ops.armed if ops is not None else controller.state is not ControllerState.DISABLED
    state_color = (40, 220, 40) if armed else (60, 60, 230)
    mode = "ACTIVE OUTPUT" if real_input else "PREVIEW ONLY"
    lines = [
        (f"{output_state(controller, ops).upper()} / {mode}", state_color),
        (f"gesture: {gesture.value}  hands: {hand_count}  fps: {fps:.1f}", (255, 255, 255)),
        (format_action(action or last_action), (255, 220, 60)),
        (status, (200, 200, 200)),
        (f"gate: {reason}", (200, 200, 200)),
    ]
    if ops is not None:
        st = ops.client.last_state
        conn = "linked" if ops.client.connected else "no link"
        lines.append((f"hand shape: {ops._shape.value}", (255, 255, 255)))
        lines.append((
            f"slicer: {conn} armed={st.get('armed')} "
            f"mode={st.get('mode')} layer={st.get('layer')} "
            f"draft={st.get('draft')}",
            (40, 220, 220),
        ))
        if ops.menu_open:
            lines.append((
                f"menu {ops.menu_index + 1}/{len(ops.menu_lines)}: "
                + (ops.menu_lines[ops.menu_index % len(ops.menu_lines)] if ops.menu_lines else "empty"),
                (255, 180, 40),
            ))
        lines.append((
            "ILY hold=arm/menu  thumbUp=C/prev  thumbDown=next/cancel  "
            "fist=decide  3f=reset",
            (220, 220, 220),
        ))
    else:
        lines.append(("SPACE: arm/disarm    Q/ESC: quit", (220, 220, 220)))
        lines.append(("open hand=rotate  index only=pan  pinch+vertical=zoom", (220, 220, 220)))
    lines.append(("Q/ESC: quit", (220, 220, 220)))
    y = 32
    for text, color in lines:
        cv2.putText(frame, text, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)
        y += 30


def _legacy_gesture_of(shape: Shape) -> Gesture:
    """Map a Shape onto the old Gesture enum for overlay display."""
    return {
        Shape.OPEN_PALM: Gesture.ROTATE,
        Shape.POINT: Gesture.PAN,
        Shape.PINCH: Gesture.ZOOM,
    }.get(shape, Gesture.NONE)


class _OpsStatus:
    """BridgeStatus-compatible view of the last protocol response."""

    def __init__(self, ops: OperationController) -> None:
        response = ops.last_response or {}
        state = ops.client.last_state
        self.applied = bool(response.get("ok"))
        self.message = (
            f"armed={state.get('armed')} mode={state.get('mode')} "
            f"layer={state.get('layer')} draft={state.get('draft')} "
            f"cmd={ops.last_command or 'none'} menu={ops.menu_open} "
            f"selected={ops.panel_menu.index if ops.panel_menu else ops.menu_index} "
            f"page={ops.panel_menu.page if ops.panel_menu else 'legacy'} "
            f"{response.get('reason', '')}"
        )


def output_state(controller: SafetyController, ops: OperationController | None) -> str:
    if ops is not None:
        if not ops.client.connected:
            return "disconnected"
        if not ops.armed:
            return "disabled"
    return controller.state.value


def format_action(action: MotionAction | None) -> str:
    if action is None:
        return "action: none"
    if action.kind is Gesture.ZOOM:
        return f"action: zoom {action.amount:+d}"
    return f"action: {action.kind.value} dx={action.dx:+d} dy={action.dy:+d}"


if __name__ == "__main__":
    raise SystemExit(main())

