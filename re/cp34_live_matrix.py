#!/usr/bin/env python3
"""Hardware-free gates for the CP34 Linux factory Voice FX matrix.

This program reads local WAV/JSON fixtures only.  It never imports the io24
driver, opens an audio device, or performs a USB operation.
"""

import argparse
import hashlib
import io
import json
import math
import os
import struct
import sys
import wave


RATE = 48000
TARGET_TITLE = "Slap Echo"
EXPECTED_DELAY_S = 0.15
DELAY_TOLERANCE_S = 0.01
MIN_ECHO_DELTA_DB = 6.0
MIN_REVERB_DELTA_DB = 3.0
MIN_REVERB_LIKE_DELTA_DB = 3.0
MAX_DRY_ECHO_DB = -30.0
MIN_ACTIVE_ECHO_DB = -18.0
FLOOR_DB = -280.0
SLOT_CANDIDATES = frozenset({
    "ch1-slot1", "ch1-slot2", "ch2-slot1", "ch2-slot2",
})
STIMULUS_FRAMES = RATE * 4
STIMULUS_AMPLITUDE_I32 = 270352173
STIMULUS_POSITIONS = (19200, 52800, 86400, 120000, 153600)
ALLOWED_MAPPED_METHODS = frozenset({
    "set_send_db",
    "set_send_assigned",
    "set_bus_master",
    "set_pan",
    "set_fx_mix",
    "set_reverb",
    "set_gain",
    "set_hp_volume",
    "set_main_volume",
})
WRITE_ONLY_METHODS = frozenset({
    "set_send_db",
    "set_send_assigned",
    "set_bus_master",
    "set_pan",
    "set_reverb",
})
METHOD_KEYS = {
    "set_send_db": frozenset({"source", "bus", "gain_db"}),
    "set_send_assigned": frozenset({"source", "bus", "on"}),
    "set_bus_master": frozenset({"bus", "gain_db"}),
    "set_pan": frozenset({"source", "bus", "pan"}),
    "set_fx_mix": frozenset({"channel", "value"}),
    "set_reverb": frozenset({"on", "size", "mix", "hp_freq", "predelay"}),
    "set_gain": frozenset({"channel", "db"}),
    "set_hp_volume": frozenset({"value"}),
    "set_main_volume": frozenset({"value"}),
}
METHOD_IDENTITY_KEYS = {
    "set_send_db": ("source", "bus"),
    "set_send_assigned": ("source", "bus"),
    "set_bus_master": ("bus",),
    "set_pan": ("source", "bus"),
    "set_fx_mix": ("channel",),
    "set_gain": ("channel",),
}
REVERB_POSITIVE_CONTROL = {
    "on": True,
    "size": 0.9,
    "mix": 1.0,
    "hp_freq": 0.0,
    "predelay": 0.05,
}
MIXER_SOURCES = frozenset({
    "line/ch1", "line/ch2", "line/ch3",
    "return/ch1", "return/ch2", "return/ch3", "fxreturn/ch1",
})


def _db(value):
    return 20.0 * math.log10(value) if value > 1e-14 else FLOOR_DB


def _finite_between(value, minimum, maximum):
    return (isinstance(value, (int, float)) and not isinstance(value, bool) and
            math.isfinite(value) and minimum <= value <= maximum)


def _read_mono_wav_bytes(raw_bytes, path_label):
    with wave.open(io.BytesIO(raw_bytes), "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        rate = handle.getframerate()
        frames = handle.getnframes()
        raw = handle.readframes(frames)
    if channels != 1:
        raise ValueError("%s: expected mono derivative, got %d channels" %
                         (path_label, channels))
    if rate != RATE:
        raise ValueError("%s: expected %d Hz, got %d" %
                         (path_label, RATE, rate))
    if width == 4:
        values = struct.unpack("<%di" % frames, raw)
        scale = 2147483648.0
    elif width == 2:
        values = struct.unpack("<%dh" % frames, raw)
        scale = 32768.0
    else:
        raise ValueError("%s: expected 16-bit or 32-bit PCM" % path_label)
    return [value / scale for value in values]


def _read_mono_wav(path):
    with open(path, "rb") as handle:
        raw_bytes = handle.read()
    return _read_mono_wav_bytes(raw_bytes, path)


def _direct_arrivals(samples):
    peak = max((abs(value) for value in samples), default=0.0)
    if peak <= 1e-8:
        raise ValueError("capture contains no usable impulse")
    threshold = peak * 0.75
    separation = int(RATE * 0.4)
    arrivals = []
    cursor = 0
    while cursor < len(samples):
        if abs(samples[cursor]) >= threshold:
            arrivals.append(cursor)
            cursor += separation
        else:
            cursor += 1
    if len(arrivals) < 5:
        raise ValueError("capture contains fewer than five isolated impulses")
    return arrivals


def _rms(samples):
    return math.sqrt(sum(value * value for value in samples) / len(samples))


def _capture_metrics_bytes(raw_bytes, path_label):
    samples = _read_mono_wav_bytes(raw_bytes, path_label)
    peak = max(abs(value) for value in samples)
    if peak >= 0.98:
        raise ValueError("%s: capture clips at %.6f" % (path_label, peak))
    arrivals = _direct_arrivals(samples)
    delay = int(EXPECTED_DELAY_S * RATE)
    tolerance = int(DELAY_TOLERANCE_S * RATE)
    ratios = []
    late_ratios = []
    for origin in arrivals:
        lo = origin + delay - tolerance
        hi = min(len(samples), origin + delay + tolerance + 1)
        if lo < 0 or hi <= lo:
            continue
        direct = max(abs(value) for value in
                     samples[max(0, origin - 8):origin + 9])
        echo = max(abs(value) for value in samples[lo:hi])
        ratios.append(echo / direct if direct else 0.0)
        late_lo = origin + int(0.02 * RATE)
        late_hi = min(len(samples), origin + int(0.13 * RATE) + 1)
        late = max(abs(value) for value in samples[late_lo:late_hi])
        late_ratios.append(late / direct if direct else 0.0)
    if len(ratios) < 5:
        raise ValueError("%s: incomplete 150 ms observation windows" % path_label)
    ratios.sort()
    ratio = ratios[len(ratios) // 2]
    late_ratios.sort()
    late_ratio = late_ratios[len(late_ratios) // 2]
    return {
        "path": path_label,
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "impulses": len(arrivals),
        "arrival_offsets_samples": [value - arrivals[0] for value in arrivals],
        "peak": peak,
        "rms_db": _db(_rms(samples)),
        "echo_ratio_db": _db(ratio),
        "late_ratio_db": _db(late_ratio),
    }


def _capture_metrics(path):
    with open(path, "rb") as handle:
        raw_bytes = handle.read()
    return _capture_metrics_bytes(raw_bytes, path)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_stimulus(path):
    if os.path.exists(path):
        raise ValueError("output already exists")
    samples = bytearray(STIMULUS_FRAMES * 4)
    for position in STIMULUS_POSITIONS:
        struct.pack_into("<i", samples, position * 4, STIMULUS_AMPLITUDE_I32)
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(4)
        handle.setframerate(RATE)
        handle.writeframes(bytes(samples))
    return {
        "schema": "cp34-impulse-stimulus-v1",
        "status": "GENERATED",
        "path": path,
        "sha256": _sha256(path),
        "channels": 1,
        "sample_width_bytes": 4,
        "rate": RATE,
        "frames": STIMULUS_FRAMES,
        "peak_i32": STIMULUS_AMPLITUDE_I32,
    }


def analyze(dry_paths, active_paths, reverb_path, target_title,
            audible_attested=False):
    if target_title != TARGET_TITLE:
        raise ValueError("target title must be exactly %r" % TARGET_TITLE)
    if len(dry_paths) != 2 or len(active_paths) != 2:
        raise ValueError("exactly two dry and two active captures are required")

    dry = [_capture_metrics(path) for path in dry_paths]
    active = [_capture_metrics(path) for path in active_paths]
    reverb = _capture_metrics(reverb_path)
    dry_rms = sum(10.0 ** (row["rms_db"] / 20.0) for row in dry) / len(dry)
    reverb_rms_delta = reverb["rms_db"] - _db(dry_rms)
    worst_dry_late = max(row["late_ratio_db"] for row in dry)
    reverb_delta = reverb["late_ratio_db"] - worst_dry_late
    worst_dry_echo = max(row["echo_ratio_db"] for row in dry)
    for row in active:
        row["echo_delta_db"] = row["echo_ratio_db"] - worst_dry_echo

    reasons = []
    if not audible_attested:
        reasons.append("audible result was not attested")
    if len({row["impulses"] for row in dry + active + [reverb]}) != 1:
        reasons.append("impulse counts differ across captures")
    else:
        reference_timing = dry[0]["arrival_offsets_samples"]
        timing_tolerance = int(0.002 * RATE)
        if any(
            any(abs(got - expected) > timing_tolerance
                for got, expected in zip(row["arrival_offsets_samples"],
                                         reference_timing))
            for row in dry[1:] + active + [reverb]
        ):
            reasons.append("impulse timing differs across captures")
    if reverb["late_ratio_db"] < MIN_ACTIVE_ECHO_DB:
        reasons.append("reverb positive control has no late energy")
    if reverb_delta < MIN_REVERB_DELTA_DB:
        reasons.append("reverb positive control is below 3 dB")
    if worst_dry_echo > MAX_DRY_ECHO_DB:
        reasons.append("dry reference already contains a 150 ms repeat")
    for index, row in enumerate(active, 1):
        if row["echo_ratio_db"] < MIN_ACTIVE_ECHO_DB:
            reasons.append("active capture %d has no usable 150 ms repeat" % index)
        if row["echo_delta_db"] < MIN_ECHO_DELTA_DB:
            reasons.append("active capture %d is less than 6 dB above dry" % index)

    return {
        "schema": "cp34-audio-ab-v1",
        "status": "PASS" if not reasons else "INCONCLUSIVE",
        "target_title": target_title,
        "audible_attested": bool(audible_attested),
        "expected_delay_s": EXPECTED_DELAY_S,
        "reverb_delta_db": reverb_delta,
        "reverb_rms_delta_db": reverb_rms_delta,
        "dry": dry,
        "active": active,
        "reverb": reverb,
        "reasons": reasons,
    }


def analyze_slot(dry_paths, active_paths, candidate, audible_attested=False):
    dry_inputs = []
    active_inputs = []
    for path in dry_paths:
        with open(path, "rb") as handle:
            dry_inputs.append((path, handle.read()))
    for path in active_paths:
        with open(path, "rb") as handle:
            active_inputs.append((path, handle.read()))
    return analyze_slot_bytes(
        dry_inputs, active_inputs, candidate,
        audible_attested=audible_attested,
    )


def analyze_slot_bytes(dry_inputs, active_inputs, candidate,
                       audible_attested=False):
    """Analyze immutable labeled WAV bytes using the canonical slot algorithm."""
    if candidate not in SLOT_CANDIDATES:
        raise ValueError("unsupported slot candidate %r" % candidate)
    if len(dry_inputs) != 2 or len(active_inputs) != 2:
        raise ValueError("exactly two dry and two active captures are required")

    dry = [_capture_metrics_bytes(raw_bytes, path_label)
           for path_label, raw_bytes in dry_inputs]
    active = [_capture_metrics_bytes(raw_bytes, path_label)
              for path_label, raw_bytes in active_inputs]
    captures = dry + active
    worst_dry_echo = max(row["echo_ratio_db"] for row in dry)
    worst_dry_late = max(row["late_ratio_db"] for row in dry)
    for row in active:
        row["echo_delta_db"] = row["echo_ratio_db"] - worst_dry_echo
        row["late_delta_db"] = row["late_ratio_db"] - worst_dry_late
    impulse_counts_match = len({row["impulses"] for row in captures}) == 1
    reference_timing = dry[0]["arrival_offsets_samples"]
    timing_tolerance = int(0.002 * RATE)
    impulse_timing_matches = impulse_counts_match and not any(
        any(abs(got - expected) > timing_tolerance
            for got, expected in zip(row["arrival_offsets_samples"],
                                     reference_timing))
        for row in captures[1:]
    )
    reverb_like_observed = impulse_timing_matches and all(
        row["late_ratio_db"] >= MIN_ACTIVE_ECHO_DB and
        row["late_delta_db"] >= MIN_REVERB_LIKE_DELTA_DB
        for row in active
    )

    reasons = []
    if not audible_attested:
        reasons.append("audible result was not attested")
    if not impulse_counts_match:
        reasons.append("impulse counts differ across captures")
    elif not impulse_timing_matches:
        reasons.append("impulse timing differs across captures")
    if worst_dry_echo > MAX_DRY_ECHO_DB:
        reasons.append("dry reference already contains a 150 ms repeat")
    for index, row in enumerate(active, 1):
        if row["echo_ratio_db"] < MIN_ACTIVE_ECHO_DB:
            reasons.append("active capture %d has no usable 150 ms repeat" % index)
        if row["echo_delta_db"] < MIN_ECHO_DELTA_DB:
            reasons.append("active capture %d is less than 6 dB above dry" % index)

    if reverb_like_observed:
        classification = "NON_SPECIFIC_LATE_TAIL"
        reasons.append(
            "repeatable late tail observed; source and loaded effect model are unresolved",
        )
    elif not reasons:
        classification = "REPEAT_150MS_SIGNATURE"
    else:
        classification = "NO_DISTINCTIVE_SIGNATURE"

    return {
        "schema": "cp34-slot-survey-audio-v1",
        "status": "SIGNATURE_PRESENT"
                  if classification == "REPEAT_150MS_SIGNATURE" and not reasons
                  else "INCONCLUSIVE",
        "classification": classification,
        "reverb_like_observed": reverb_like_observed,
        "candidate": candidate,
        "model_identity": "UNRESOLVED",
        "title_verified": False,
        "live_ready": False,
        "restoration_verified": False,
        "audible_attested": bool(audible_attested),
        "expected_delay_s": EXPECTED_DELAY_S,
        "dry": dry,
        "active": active,
        "reasons": reasons,
    }


def validate_ledger(path):
    with open(path) as handle:
        ledger = json.load(handle)
    if not isinstance(ledger, dict):
        raise ValueError("ledger root must be an object")
    reasons = []
    if ledger.get("schema") != "cp34-restoration-ledger-v1":
        reasons.append("unsupported restoration-ledger schema")
    if ledger.get("target_title") != TARGET_TITLE:
        reasons.append("target title must be exactly %r" % TARGET_TITLE)
    if not isinstance(ledger.get("run_id"), str) or not ledger["run_id"].strip():
        reasons.append("run_id is required")
    if (not isinstance(ledger.get("device_serial"), str) or
            not ledger["device_serial"].strip()):
        reasons.append("device_serial is required")
    shadow_hash = ledger.get("shadow", {}).get("sha256")
    if (not isinstance(shadow_hash, str) or len(shadow_hash) != 64 or
            any(character not in "0123456789abcdef"
                for character in shadow_hash)):
        reasons.append("shadow.sha256 must be 64 lowercase hex digits")
    actions = ledger.get("actions")
    if not isinstance(actions, list) or not actions:
        reasons.append("restoration ledger has no actions")
        actions = []
    action_rows = []
    for index, action in enumerate(actions, 1):
        if not isinstance(action, dict):
            reasons.append("action #%d must be an object" % index)
            continue
        action_rows.append((index, action))
    if (any(action.get("write_only") for _, action in action_rows) and
            ledger.get("shadow", {}).get("current_attested") is not True):
        reasons.append("write-only actions require a current-attested shadow")
    if sum(action.get("method") == "set_reverb"
           for _, action in action_rows) != 1:
        reasons.append("ledger requires exactly one reverb positive control")
    if sum(action.get("id") == "front-panel-enable" and
           action.get("kind") == "manual_front_panel"
           for _, action in action_rows) != 1:
        reasons.append("ledger requires one front-panel-enable action")
    seen_ids = set()
    for index, action in action_rows:
        action_id = action.get("id") or "#%d" % index
        mapped_kinds = ("mapped_write", "clamp_probe")
        if action.get("kind") not in (*mapped_kinds, "manual_front_panel"):
            reasons.append(
                "action %s has unknown kind %s" %
                (action_id, action.get("kind")),
            )
        if action_id in seen_ids:
            reasons.append("duplicate action id %s" % action_id)
        seen_ids.add(action_id)
        if not action.get("inverse"):
            reasons.append("action %s has no inverse" % action_id)
        if (action.get("kind") in mapped_kinds and
                (not isinstance(action.get("forward"), dict) or
                 not isinstance(action.get("inverse"), dict))):
            label = "mapped" if action.get("kind") == "mapped_write" else "clamp"
            reasons.append(
                "%s action %s needs object forward and inverse" %
                (label, action_id),
            )
        if (action.get("kind") in mapped_kinds and
                isinstance(action.get("forward"), dict) and
                isinstance(action.get("inverse"), dict) and
                action.get("method") in METHOD_KEYS):
            allowed_keys = METHOD_KEYS[action["method"]]
            for direction in ("forward", "inverse"):
                unexpected = sorted(set(action[direction]) - allowed_keys)
                missing = sorted(allowed_keys - set(action[direction]))
                if unexpected:
                    reasons.append(
                        "action %s %s has unexpected keys: %s" %
                        (action_id, direction, ", ".join(unexpected)),
                    )
                if missing:
                    reasons.append(
                        "action %s %s is missing keys: %s" %
                        (action_id, direction, ", ".join(missing)),
                    )
            identity_keys = METHOD_IDENTITY_KEYS.get(action["method"], ())
            if any(action["forward"].get(key) != action["inverse"].get(key)
                   for key in identity_keys):
                reasons.append(
                    "action %s inverse addresses a different control" %
                    action_id,
                )
            if ("bus" in allowed_keys and
                    (action["forward"].get("bus") != "mixa" or
                     action["inverse"].get("bus") != "mixa")):
                reasons.append("action %s must use bus mixa" % action_id)
            if action["method"] == "set_reverb":
                for direction in ("forward", "inverse"):
                    values = action[direction]
                    checks = {
                        "on": isinstance(values.get("on"), bool),
                        "size": _finite_between(values.get("size"), 0.0, 1.0),
                        "mix": _finite_between(values.get("mix"), 0.0, 1.0),
                        "hp_freq": _finite_between(values.get("hp_freq"),
                                                   0.0, 500.0),
                        "predelay": _finite_between(values.get("predelay"),
                                                    0.0001, 0.25),
                    }
                    for name, valid in checks.items():
                        if not valid:
                            reasons.append(
                                "action %s %s has invalid %s" %
                                (action_id, direction, name),
                            )
            if action["method"] == "set_send_db":
                for direction in ("forward", "inverse"):
                    values = action[direction]
                    if values.get("source") not in MIXER_SOURCES:
                        reasons.append(
                            "action %s %s has invalid source" %
                            (action_id, direction),
                        )
                    gain_db = values.get("gain_db")
                    is_clamp_forward = (
                        action.get("kind") == "clamp_probe" and
                        direction == "forward"
                    )
                    if (gain_db is not None and not is_clamp_forward and
                            not _finite_between(gain_db, -144.0, 10.0)):
                        reasons.append(
                            "action %s %s has invalid gain_db" %
                            (action_id, direction),
                        )
                if action.get("kind") == "clamp_probe":
                    requested = action["forward"].get("gain_db")
                    expected = action.get("expected_wire_db")
                    if (not isinstance(requested, (int, float)) or
                            isinstance(requested, bool) or
                            not math.isfinite(requested) or
                            -144.0 <= requested <= 10.0):
                        reasons.append(
                            "action %s clamp probe needs out-of-range gain_db" %
                            action_id,
                        )
                    else:
                        clamped = max(-144.0, min(10.0, float(requested)))
                        if expected != clamped:
                            reasons.append(
                                "action %s clamp expected_wire_db does not match" %
                                action_id,
                            )
            elif action.get("kind") == "clamp_probe":
                reasons.append(
                    "action %s clamp probe must use set_send_db" % action_id,
                )
            if action["method"] == "set_gain":
                for direction in ("forward", "inverse"):
                    values = action[direction]
                    if (type(values.get("channel")) is not int or
                            values["channel"] not in (1, 2)):
                        reasons.append(
                            "action %s %s has invalid channel" %
                            (action_id, direction),
                        )
                    if not _finite_between(values.get("db"), 0.0, 60.0):
                        reasons.append(
                            "action %s %s has invalid db" %
                            (action_id, direction),
                        )
            if action["method"] == "set_fx_mix":
                for direction in ("forward", "inverse"):
                    values = action[direction]
                    if (type(values.get("channel")) is not int or
                            values["channel"] not in (1, 2)):
                        reasons.append(
                            "action %s %s has invalid channel" %
                            (action_id, direction),
                        )
                    if not _finite_between(values.get("value"), 0.0, 1.0):
                        reasons.append(
                            "action %s %s has invalid value" %
                            (action_id, direction),
                        )
            if (action["method"] == "set_reverb" and
                    action["forward"] != REVERB_POSITIVE_CONTROL):
                reasons.append(
                    "reverb positive control parameters do not match the matrix",
                )
        if (action.get("kind") == "manual_front_panel" and
                (not isinstance(action.get("forward"), str) or
                 not action["forward"].strip() or
                 not isinstance(action.get("inverse"), str) or
                 not action["inverse"].strip())):
            reasons.append(
                "manual action %s needs text forward and inverse" %
                action_id,
            )
        if action.get("write_only"):
            expected_source = "shadow:" + str(
                ledger.get("shadow", {}).get("sha256", ""),
            )
            if action.get("baseline_source") != expected_source:
                reasons.append(
                    "action %s baseline does not match the pinned shadow" %
                    action_id,
                )
        if (action.get("kind") in mapped_kinds and
                action.get("method") not in ALLOWED_MAPPED_METHODS):
            reasons.append(
                "action %s uses prohibited method %s" %
                (action_id, action.get("method")),
            )
        if (action.get("method") in WRITE_ONLY_METHODS and
                action.get("write_only") is not True):
            reasons.append(
                "action %s method %s is write-only" %
                (action_id, action.get("method")),
            )
    return {
        "schema": "cp34-restoration-ledger-validation-v1",
        "status": "VALID" if not reasons else "INVALID",
        "actions": len(actions),
        "sha256": _sha256(path),
        "reasons": reasons,
    }


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    audio = subparsers.add_parser("analyze")
    audio.add_argument("--target-title", required=True)
    audio.add_argument("--audible-attested", action="store_true")
    audio.add_argument("--dry", action="append", default=[])
    audio.add_argument("--active", action="append", default=[])
    audio.add_argument("--reverb", required=True)
    slot_audio = subparsers.add_parser("analyze-slot")
    slot_audio.add_argument("--candidate", required=True)
    slot_audio.add_argument("--audible-attested", action="store_true")
    slot_audio.add_argument("--dry", action="append", default=[])
    slot_audio.add_argument("--active", action="append", default=[])
    ledger = subparsers.add_parser("validate-ledger")
    ledger.add_argument("path")
    stimulus = subparsers.add_parser("generate-stimulus")
    stimulus.add_argument("path")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.command == "analyze":
            report = analyze(args.dry, args.active, args.reverb,
                             args.target_title, args.audible_attested)
        elif args.command == "analyze-slot":
            report = analyze_slot(args.dry, args.active, args.candidate,
                                  args.audible_attested)
        elif args.command == "validate-ledger":
            report = validate_ledger(args.path)
        else:
            report = generate_stimulus(args.path)
    except (OSError, ValueError, json.JSONDecodeError, wave.Error) as error:
        report = {
            "schema": "cp34-offline-gate-error-v1",
            "status": "INVALID" if args.command == "validate-ledger"
                      else "INCONCLUSIVE",
            "reasons": [str(error)],
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in (
        "PASS", "SIGNATURE_PRESENT", "VALID", "GENERATED",
    ) else 2


if __name__ == "__main__":
    sys.exit(main())
