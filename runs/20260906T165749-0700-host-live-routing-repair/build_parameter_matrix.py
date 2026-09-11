#!/usr/bin/env python3
"""Build the atomic io24 parameter-verification ledger.

This is a plan generator, not a device runner.  It opens no USB or audio
device and performs no writes.  Every generated row starts PENDING; a separate
evidence runner must supply a permitted terminal status, evidence links, and a
completed restoration record.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent

TERMINAL_STATUSES = (
    "PASS_READBACK",
    "PASS_AUDIO",
    "PASS_FRONT_PANEL",
    "PASS_HOST",
    "PASS_PERSISTENCE",
    "FAIL",
    "INCONCLUSIVE",
    "NOT_APPLICABLE",
)

PROFILES = {
    "readback_scalar": {
        "trials": 2,
        "sequence": "baseline -> low -> nominal -> high -> low-clamp -> high-clamp -> baseline",
        "oracle": "exact integer/bit, or expected float32/declared device quantization",
        "guard": "non-target readable state unchanged; audio remains below -6 dBFS",
        "restoration": "restore the captured readable value and prove it read back",
        "terminal_pass": "PASS_READBACK",
    },
    "readback_toggle": {
        "trials": 2,
        "sequence": "captured state -> opposite -> captured state",
        "oracle": "exact JaSt bit/value plus the declared front-panel indication when one exists",
        "guard": "other channel and unrelated flag bits unchanged",
        "restoration": "restore captured state and prove exact bit/value",
        "terminal_pass": "PASS_READBACK",
    },
    "readback_enum": {
        "trials": 2,
        "sequence": "visit each safe declared member, then captured member",
        "oracle": "exact integer readback of the selector; selector readback is not evidence that stored content was recalled into the audio path",
        "guard": "no unexplained cross-channel slot or processing displacement; a declared expected_side_effect is not a violation",
        "restoration": "restore captured member and prove exact readback, including reversal of any declared side effect",
        "terminal_pass": "PASS_READBACK",
    },
    "write_only_audio_scalar": {
        "trials": 2,
        "sequence": "randomized A/B/A brackets at low, nominal, high and clamp boundaries",
        "oracle": "predeclared objective level, spectrum, timing, or transfer-function metric",
        "guard": "same-path positive control passes; target peak below -6 dBFS; other bus/channel isolated",
        "restoration": "send the captured inverse and require baseline audio equivalence",
        "terminal_pass": "PASS_AUDIO",
        "transport_label": "WRITE_SENT_NOT_READABLE",
    },
    "write_only_audio_toggle": {
        "trials": 2,
        "sequence": "A(off)/B(on)/A(off), with labels concealed from offline analysis",
        "oracle": "predeclared objective signal-domain difference; USB completion is insufficient",
        "guard": "same-path positive control and non-target isolation both pass",
        "restoration": "return to captured state and require baseline audio equivalence",
        "terminal_pass": "PASS_AUDIO",
        "transport_label": "WRITE_SENT_NOT_READABLE",
    },
    "front_panel_write_only": {
        "trials": 2,
        "sequence": "command each declared mode, exercise the physical button, restore",
        "oracle": "front-panel indication and resulting safe readable transitions agree with the mode",
        "guard": "never select a channel into the other channel's slot pair",
        "restoration": "restore the captured/declared project mode",
        "terminal_pass": "PASS_FRONT_PANEL",
        "transport_label": "WRITE_SENT_NOT_READABLE",
    },
    "dsp_audio_scalar": {
        "trials": 2,
        "sequence": "randomized bypass/value/bypass brackets at safe low, nominal, high and clamp points",
        "oracle": "measured response matches the exact serialized coefficient/payload prediction",
        "guard": "other physical channel delta <= 0.25 dB and target peak below -6 dBFS",
        "restoration": "replay exact inverse payload and require baseline equivalence",
        "terminal_pass": "PASS_AUDIO",
        "transport_label": "WRITE_SENT_NOT_READABLE",
    },
    "dsp_audio_toggle": {
        "trials": 2,
        "sequence": "bypass/on/bypass with a discriminating fixed stimulus",
        "oracle": "objective transfer-function or dynamics change matches the selected block",
        "guard": "positive control passes and other channel stays within 0.25 dB of baseline",
        "restoration": "restore captured/bypass state and require baseline equivalence",
        "terminal_pass": "PASS_AUDIO",
        "transport_label": "WRITE_SENT_NOT_READABLE",
    },
    "dsp_audio_enum": {
        "trials": 2,
        "sequence": "randomized member order with bypass between members",
        "oracle": "each member has its predeclared, mutually discriminating audio signature",
        "guard": "selector/model write occurs before state; no stale-model parameters are sent",
        "restoration": "restore prior member/state and require baseline equivalence",
        "terminal_pass": "PASS_AUDIO",
        "transport_label": "WRITE_SENT_NOT_READABLE",
    },
    "mixer_level": {
        "trials": 2,
        "sequence": "off -> -60 -> -24 -> 0 -> +6 -> low/high clamp -> off",
        "oracle": "captured level tracks requested delta within 0.35 dB and only on the selected bus",
        "clamp_oracle": "an out-of-range request must reach its clamped wire bound (-144.0 dB low or +10.0 dB high); -144.0 remains measurable and is not the -145.0 off sentinel",
        "guard": "Mix A appears only on USB 3-4; Mix B only on USB 5-6; no feedback path",
        "restoration": "restore known prior level/assignment or park the route off",
        "terminal_pass": "PASS_AUDIO",
        "transport_label": "WRITE_SENT_NOT_READABLE",
    },
    "mixer_assignment": {
        "trials": 2,
        "sequence": "known level -> assigned -> unassigned -> assigned",
        "oracle": "unassign reaches off sentinel; reassign returns the retained level within 0.35 dB",
        "guard": "all other source/bus cells remain isolated",
        "restoration": "restore prior assignment and level, or park off",
        "terminal_pass": "PASS_AUDIO",
        "transport_label": "WRITE_SENT_NOT_READABLE",
    },
    "host_mapping": {
        "trials": 2,
        "sequence": "instrumented fake -> local process -> live objective confirmation when audio-affecting",
        "oracle": "exact downstream calls/state, silent programmatic adoption, and expected live result",
        "guard": "no hidden USB write from synchronization or page construction",
        "restoration": "restore Host state and downstream controls",
        "terminal_pass": "PASS_HOST",
    },
    "host_process": {
        "trials": 2,
        "sequence": "start/change/observe/stop/restart",
        "oracle": "process identity, requested live state, clean exit, and no orphan",
        "guard": "no unrelated PipeWire/ALSA owner is stopped or reconfigured",
        "restoration": "clear forced setting and stop only the test-owned process",
        "terminal_pass": "PASS_HOST",
    },
    "telemetry": {
        "trials": 2,
        "sequence": "known negative control -> known positive control -> negative control",
        "oracle": "reported value follows the independently measured stimulus with correct channel mapping",
        "guard": "read-only path emits zero control writes",
        "restoration": "remove stimulus; no state write required",
        "terminal_pass": "PASS_READBACK",
    },
    "serializer": {
        "trials": 2,
        "sequence": "boundary/default/representative vectors serialized independently",
        "oracle": "byte-exact framing, float32 arithmetic, ordering, clamping, and inverse fixture",
        "guard": "hardware-free; malformed/non-finite input is rejected before transport",
        "restoration": "not applicable; no live write",
        "terminal_pass": "PASS_HOST",
    },
    "persistence": {
        "trials": 2,
        "sequence": "save -> dislodge -> recall with Host closed -> disconnect -> non-computer cold power -> recall",
        "oracle": "distinctive Fat Channel/effect signature is audible with no Host write in the observation window",
        "guard": "only Channel 2 global slot 3 is overwritten; Channel 1 slot bodies and global slot 0 untouched",
        "restoration": "restore selectors/enables/routing; slot-3 overwrite remains explicitly documented",
        "terminal_pass": "PASS_PERSISTENCE",
    },
    "component_reconcile": {
        "trials": 1,
        "sequence": "map declaration to exactly one operational row or one evidence-backed exclusion",
        "oracle": "exact UC 4.7.2 component path, flags, type/range, runtime binding and io24 applicability",
        "guard": "no descriptor ID is treated as a wire ID without an independently decoded bridge",
        "restoration": "not applicable; static only",
        "terminal_pass": "NOT_APPLICABLE",
    },
    "catalog_reconcile": {
        "trials": 1,
        "sequence": "identify table/model, recover omitted fields, map or classify duplicates/read-only entries",
        "oracle": "exact source address/table and one unambiguous operational or exclusion disposition",
        "guard": "catalog evidence authorizes no device write",
        "restoration": "not applicable; static only",
        "terminal_pass": "NOT_APPLICABLE",
    },
    "implementation_gap": {
        "trials": 1,
        "sequence": "prove applicability -> implement exact binding -> run the appropriate live profile",
        "oracle": "cannot pass while absent, guessed, silently dropped, or represented by the wrong model",
        "guard": "no guessed coefficients or unknown/unmapped device write",
        "restoration": "defined by the eventual operational profile",
        "terminal_pass": "PASS_HOST",
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _component_paramlists() -> dict[str, list[dict[str, str]]]:
    """Parse ParamList declarations from the retained component-model text.

    The retained file contains extraction prelude bytes before its XML document,
    so an XML parser is intentionally not used here.  The bounded regex consumes
    only complete ParamList elements and their Param start tags.
    """
    text = (ROOT / "re/uc_component_model/dspusb_component_model.xml").read_text()
    lists: dict[str, list[dict[str, str]]] = {}
    for match in re.finditer(
            r'<uc:ParamList\s+([^>]*\bid="[^"]+"[^>]*)>(.*?)</uc:ParamList>',
            text, re.S):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', match.group(1)))
        params = []
        for p in re.finditer(r'<uc:Param\s+([^>]*)/\s*>', match.group(2), re.S):
            params.append(dict(re.findall(r'(\w+)="([^"]*)"', p.group(1))))
        lists[attrs["id"]] = params
    return lists


def build() -> dict:
    rows: list[dict] = []
    ids: set[str] = set()

    def add(row_id: str, phase: str, family: str, parameter: str,
            profile: str, *, scope: dict | None = None,
            stimuli: list | None = None, api: tuple[str, ...] = (),
            source: tuple[str, ...] = (), requires: tuple[str, ...] = (),
            blockers: tuple[str, ...] = (), note: str | None = None,
            prior_evidence: tuple[str, ...] = (),
            expected_side_effect: str | None = None) -> None:
        if row_id in ids:
            raise ValueError("duplicate matrix id %s" % row_id)
        if profile not in PROFILES:
            raise ValueError("unknown profile %s" % profile)
        ids.add(row_id)
        row = {
            "id": row_id,
            "phase": phase,
            "family": family,
            "parameter": parameter,
            "scope": scope or {},
            "profile": profile,
            "stimuli": stimuli or [],
            "api": list(api),
            "source": list(source),
            "requires": list(requires),
            "blockers": list(blockers),
            "result": {
                "status": "PENDING",
                "attempts": [],
                "evidence": [],
                "restored": False,
                "restoration_evidence": [],
            },
        }
        if note:
            row["note"] = note
        if prior_evidence:
            row["prior_evidence"] = list(prior_evidence)
        if expected_side_effect:
            row["expected_side_effect"] = expected_side_effect
        rows.append(row)

    # P1/P3: direct application controls and their readable state.
    direct = (
        ("headphones_volume", "hpVolume", "readback_scalar",
         [0.0, 0.25, 0.75, 1.0, -0.1, 1.1], ("set_hp_volume",)),
        ("main_volume", "mainVolume", "readback_scalar",
         [0.0, 0.25, 0.75, 1.0, -0.1, 1.1], ("set_main_volume",)),
        ("monitor_blend", "monitorMix", "readback_scalar",
         [-1.0, 0.0, 1.0, -1.1, 1.1], ("set_monitor_mix",)),
        ("output_delay", "outputDelay", "write_only_audio_scalar",
         [0.0, 0.05, 0.173, 0.5, -0.1, 0.7], ("set_output_delay", "output_delay_off")),
        ("output_delay_bus", "outputDelayBus", "write_only_audio_scalar",
         ["off", "mixa", "mixb"], ("set_output_delay_bus",)),
        ("headphones_mute", "hpOutputMute", "readback_toggle",
         [False, True], ("set_hp_mute",)),
        ("channel_link", "channelLink", "readback_toggle",
         [False, True], ("set_channel_link",)),
        ("preset_mode", "presetMode", "front_panel_write_only",
         [0, 1, 2], ("set_preset_mode",)),
    )
    for ident, param, profile, stimuli, api in direct:
        add("native.global." + ident, "P3", "native_control", param, profile,
            stimuli=stimuli, api=api, source=("io24.py", "firmware JaSt/dispatcher"),
            requires=("exclusive_usb", "battery_above_10"))

    for ch in (1, 2):
        per_channel = (
            ("gain", "input%dGain" % ch, "readback_scalar",
             [0.0, 24.0, 48.0, 60.0, -1.0, 61.0], ("set_gain",)),
            ("phantom", "input%dPhantomPower" % ch, "readback_toggle",
             [False, True], ("set_phantom",)),
            ("input_mute", "input%dMute" % ch, "readback_toggle",
             [False, True], ("set_mute",)),
            ("low_cut_enable", "input%dHighPassFilter" % ch,
             "write_only_audio_toggle", [False, True], ("set_highpass",)),
            ("processing_mix", "input%dFxMix" % ch,
             "write_only_audio_scalar", [0.0, 0.25, 0.75, 1.0, -0.1, 1.1],
             ("set_fx_mix", "set_preset_enabled", "set_preset_button_mode",
              "preset_enabled")),
            ("processing_channel", "input%dProcessingChannel" % ch,
             "readback_enum", [1, 2], ("set_processing_channel",)),
            ("preset_slot", "input%dSlotIndex" % ch, "readback_enum",
             [0, 1] if ch == 1 else [2, 3], ("set_preset_slot",)),
        )
        for ident, param, profile, stimuli, api in per_channel:
            note = None
            expected_side_effect = None
            if ident == "processing_mix":
                note = ("One firmware scalar: exact zero bypasses the channel; "
                        "set_preset_enabled is only its Boolean 0/1 alias. "
                        "JaSt reports zero versus nonzero, not the exact mix.")
                expected_side_effect = \
                    "disabled flag set only at exact zero"
            elif ident == "preset_slot":
                note = ("Writing the slot index alone produced no audio change "
                        "in three separate 2026-08 tests. PASS_READBACK is a "
                        "selector claim only; recall is proved solely by the "
                        "device_persistence rows.")
            elif ident == "processing_channel":
                expected_side_effect = (
                    "firmware 1.28 (0x2e77a..0x2e7bb) replays Pari/16 for "
                    "indexes 0 and 1 with their values exchanged after a "
                    "Pari/12 change; restore the inverse Pari/12 and confirm "
                    "both slot indexes returned")
            add("native.channel%d.%s" % (ch, ident), "P3", "native_control",
                param, profile, scope={"channel": ch}, stimuli=stimuli, api=api,
                source=("io24.py", "firmware JaSt/dispatcher"),
                requires=("exclusive_usb", "battery_above_10"), note=note,
                expected_side_effect=expected_side_effect)

    add("native.voicefx_owner_alias", "P5", "native_control",
        "VoiceFX physical-channel ownership", "readback_enum",
        stimuli=[1, 2], api=("set_voicefx_channel", "processing_channel"),
        source=("io24.py", "UC 4.7.2 processingChannel branch"),
        requires=("exclusive_usb", "battery_above_10"))
    add("native.main_physical_mute", "P3", "telemetry",
        "mainPhysicalMute", "telemetry", stimuli=[False, True],
        source=("JaSt slot 42 bit 1",),
        note="Read-only physical button; Linux Host must not pretend it can write it.")
    add("native.unknown_flag_bit13", "P1", "telemetry",
        "JaSt slot 42 bit 13 / Pari wire 15", "component_reconcile",
        source=("io24.py KNOWN_PARI",), blockers=("purpose_unknown_no_live_write",),
        note="Accounted for, but full authorization does not turn an unknown control into a safe parameter.")
    add("native.global.headphones_source", "P3", "native_control",
        "global/phonesSrc", "write_only_audio_scalar",
        stimuli=["main", "mixa", "mixb"], api=("set_phones_source",),
        source=("UC 4.7.2 global/phonesSrc route",
                "firmware special Pari wire 11 handler 0x6004e6b4"),
        requires=("deterministic_audio_rig@batch",),
        note="Write-only: Host shadow plus objective source-isolation capture; never claim JaSt readback.")

    # P3: the complete backend mixer keyspace.  line/ch3 is deliberately kept
    # visible as an applicability question because Michael/io24 exposes two
    # analog input components while the generic backend retained source id 6.
    mixer_sources = (
        "line/ch1", "line/ch2", "line/ch3", "return/ch1", "return/ch2",
        "return/ch3", "fxreturn/ch1",
    )
    mixer_buses = ("main", "mixa", "mixb")
    for source_name in mixer_sources:
        for bus in mixer_buses:
            blockers = ("prove_line_ch3_io24_applicability",) if source_name == "line/ch3" else ()
            for field, profile, api, stimuli in (
                    ("level_db", "mixer_level", ("set_send_db", "set_mix_db", "set_mix_norm", "mix_off"),
                     [None, -60.0, -24.0, 0.0, 6.0, -200.0, 20.0]),
                    ("assigned", "mixer_assignment", ("set_send_assigned",), [False, True])):
                add("mixer.%s.%s.%s" % (_safe_id(source_name), bus, field),
                    "P3", "mixer_cell", field, profile,
                    scope={"source": source_name, "bus": bus}, stimuli=stimuli,
                    api=api, source=("io24.py block 100",),
                    requires=("deterministic_audio_rig@batch",), blockers=blockers)
    for bus in mixer_buses:
        add("mixer.%s.master" % bus, "P3", "mixer_master", "master trim",
            "host_mapping", scope={"bus": bus}, stimuli=[-12.0, 0.0, 6.0],
            api=("set_bus_master", "bus_master"), source=("io24.py send fold",),
            requires=("all_bus_sends_materialized", "deterministic_audio_rig@batch"))
    for pair in ("line/ch1+line/ch2", "return/ch1+return/ch2"):
        for bus in mixer_buses:
            add("mixer.%s.%s.balance" % (_safe_id(pair), bus), "P3",
                "mixer_balance", "stereo pair balance", "host_mapping",
                scope={"pair": pair, "bus": bus}, stimuli=[0.0, 0.5, 1.0],
                api=("set_pan", "set_pair_pan", "pan", "pan_gain", "pan_db"),
                source=("UC 4.7.2 pan law", "io24.py"),
                requires=("deterministic_stereo_audio_rig",))
    for bus in ("mixa", "mixb"):
        add("mixer.%s.mirror_main" % bus, "P3", "mixer_mapping",
            "one-shot mirror main", "host_mapping", scope={"bus": bus},
            stimuli=["known_sparse_main", "known_full_main"], api=("mirror_main",),
            source=("io24.py",), requires=("all_bus_sends_materialized",))
    for bus in mixer_buses:
        add("mixer.%s.solo" % bus, "P3", "mixer_mapping", "host solo",
            "host_mapping", scope={"bus": bus},
            stimuli=["one_source", "two_sources", "release", "clear_all"],
            api=("set_solo", "clear_solo", "soloed"),
            source=("io24.py send fold",),
            requires=("all_bus_sends_materialized", "deterministic_audio_rig@batch"))

    # P4: Fat Channel.  Every field gets a per-physical-channel row.  Builder
    # instance 0, instance 1, and the default both-instance path are obligations
    # of each dynamics row rather than hidden extra parameters.
    eq_fields = {
        "enabled": [False, True],
        "shape": ["off", "peaking", "lowshelf", "highshelf", "hp", "lp"],
        "frequency_hz": [20.0, 120.0, 1000.0, 5000.0, 18000.0],
        "gain_db": [-15.0, 0.0, 9.0, 15.0],
        "q": [0.1, 0.7, 2.0, 10.0],
    }
    gate_fields = {
        "on": [False, True], "threshold_db": [-84.0, -40.0, 0.0],
        "range_db": [-84.0, -60.0, 0.0],
        "attack_s": [0.00002, 0.005, 0.5],
        "release_s": [0.05, 0.3, 2.0],
        "keyfilter_hz": [40.0, 730.0, 16000.0],
        "expander": [False, True], "keylisten": [False, True],
    }
    compressor_common = {
        "on": [False, True], "model": [0, 1, 2],
        "keyfilter_hz": [40.0, 730.0, 16000.0], "keylisten": [False, True],
    }
    compressor_models = {
        "standard": {
            "threshold_db": [-56.0, -24.0, 0.0], "ratio": [1.0, 4.0, 20.0],
            "attack_s": [0.0002, 0.02, 0.15],
            "release_s": [0.0025, 0.15, 0.9], "gain_db": [0.0, 6.0, 28.0],
            "softknee": [False, True], "automode": [False, True],
        },
        "tube": {"peak": [0.0, 50.0, 100.0], "gain": [0.0, 40.0, 100.0],
                 "limit_mode": [False, True]},
        "fet": {"input_db": [-56.0, -43.0, -20.0, 0.0],
                "output_db": [-56.0, -12.0, 0.0],
                "attack_s": [0.000021, 0.0001, 0.0008],
                "release_s": [0.05, 0.25, 1.1],
                "ratio_index": [0, 1, 2, 3, 4]},
    }
    alternate_eq = {
        "passive": {
            "eqallon": [False, True], "bboost": [0.0, 5.0, 10.0],
            "batten": [0.0, 5.0, 10.0],
            "bfreq": ["vendor_literal_20kHz", "30", "60", "100"],
            "mboost": [0.0, 5.0, 10.0], "bbwidth": [0.0, 5.0, 10.0],
            "mfreq": [3000, 4000, 5000, 8000, 10000, 12000, 16000],
            "hatten": [0.0, 5.0, 10.0], "hsfreq": [5000, 10000, 20000],
        },
        "vintage": {
            "eqallon": [False, True], "lowgain": [-16.0, 0.0, 16.0],
            "lowfreq": [35, 60, 110, 220],
            "lowmidgain": [-16.0, 0.0, 16.0],
            "lowmidfreq": [360, 700, 1600],
            "himidgain": [-16.0, 0.0, 16.0],
            "himidfreq": [3200, 4800, 7200],
            "higain": [-16.0, 0.0, 16.0],
        },
    }
    for ch in (1, 2):
        add("fat.channel%d.low_cut_frequency" % ch, "P4", "fat_low_cut",
            "frequency_hz", "dsp_audio_scalar", scope={"channel": ch},
            stimuli=[24.0, 40.0, 300.0, 1000.0, 0.0, 1200.0],
            api=("set_highpass_freq", "highpass_coeffs"),
            source=("io24.py filt/Bqdf",), requires=("deterministic_audio_rig@batch",))
        add("fat.channel%d.eq_global_enabled" % ch, "P4", "fat_eq",
            "eqallon host mapping", "host_mapping", scope={"channel": ch},
            stimuli=[False, True], api=("eq_off",),
            source=("UC factory record", "io24_presets.py"),
            requires=("deterministic_audio_rig@batch",))
        for band in range(4):
            for field, stimuli in eq_fields.items():
                add("fat.channel%d.eq.band%d.%s" % (ch, band, field), "P4",
                    "fat_eq", field, "dsp_audio_enum" if field in ("enabled", "shape")
                    else "dsp_audio_scalar",
                    scope={"channel": ch, "band": band}, stimuli=stimuli,
                    api=("set_eq_band",),
                    source=("UC 4.7.2 Standard selector 9", "io24.py eq/Bqdf"),
                    requires=("deterministic_audio_rig@batch",))
        for field, stimuli in gate_fields.items():
            add("fat.channel%d.gate.%s" % (ch, field), "P4", "fat_gate",
                field, "dsp_audio_toggle" if field in ("on", "expander", "keylisten")
                else "dsp_audio_scalar", scope={"channel": ch}, stimuli=stimuli,
                api=("set_gate", "gate_off"), source=("io24_dsp.py gate blob",),
                requires=("deterministic_audio_rig@batch",))
        for field, stimuli in compressor_common.items():
            add("fat.channel%d.compressor.%s" % (ch, field), "P4",
                "fat_compressor", field,
                "dsp_audio_enum" if field == "model" else
                "dsp_audio_toggle" if field in ("on", "keylisten") else "dsp_audio_scalar",
                scope={"channel": ch}, stimuli=stimuli,
                api=("set_compressor", "compressor_off"),
                source=("io24_dsp.py cpxt",), requires=("deterministic_audio_rig@batch",))
        for model, fields in compressor_models.items():
            for field, stimuli in fields.items():
                add("fat.channel%d.compressor.%s.%s" % (ch, model, field),
                    "P4", "fat_compressor", field,
                    "dsp_audio_toggle" if isinstance(stimuli[0], bool) else
                    "dsp_audio_enum" if field == "ratio_index" else "dsp_audio_scalar",
                    scope={"channel": ch, "model": model}, stimuli=stimuli,
                    api=("set_compressor",), source=("io24_dsp.py cpxt_%s" % model,),
                    requires=("deterministic_audio_rig@batch",))
        for field, stimuli in {
                "on": [False, True], "threshold_db": [-40.0, -28.0, 0.0],
                "release_s": [0.05, 0.4, 2.0]}.items():
            add("fat.channel%d.limiter.%s" % (ch, field), "P4", "fat_limiter",
                field, "dsp_audio_toggle" if field == "on" else "dsp_audio_scalar",
                scope={"channel": ch}, stimuli=stimuli, api=("set_limiter",),
                source=("io24_dsp.py limiter",), requires=("deterministic_audio_rig@batch",))
        add("fat.channel%d.order" % ch, "P4", "fat_order",
            "compressor/EQ order", "dsp_audio_enum", scope={"channel": ch},
            stimuli=["compressor_then_eq", "eq_then_compressor"],
            api=("set_comp_eq_order",), source=("io24.py opt/Pari",),
            requires=("non_commutative_audio_fixture",))
        add("fat.channel%d.eq_model" % ch, "P4", "fat_eq_model",
            "mutable EQ model", "implementation_gap", scope={"channel": ch},
            stimuli=["standard", "passive", "vintage"],
            source=("UC 4.7.2 fatchannelxt.xml",),
            blockers=("alternate_eq_exact_builder_pending",))
        for model, fields in alternate_eq.items():
            for field, stimuli in fields.items():
                blockers = ["alternate_eq_exact_builder_pending"]
                if model == "passive" and field == "bfreq":
                    blockers.append("vendor_20kHz_literal_requires_resolution")
                add("fat.channel%d.eq.%s.%s" % (ch, model, field), "P4",
                    "fat_eq_alternate", field,
                    "implementation_gap", scope={"channel": ch, "model": model},
                    stimuli=stimuli, source=("UC 4.7.2 fatchannelxt.xml",),
                    blockers=tuple(blockers))
        for block in ("gate", "compressor", "limiter"):
            add("fat.channel%d.%s.instance_targeting" % (ch, block), "P1",
                "serializer_targeting", "DSP sub-instance 0/1/both", "serializer",
                scope={"channel": ch, "block": block}, stimuli=[0, 1, "both"],
                source=("io24.py", "io24_dsp.py"))

    # P5: shared reverb. Sends and returns are not duplicated here; dependency
    # IDs tie their engine tests to the already atomic native/mixer rows.
    for field, stimuli in {
            "on": [False, True], "size": [0.0, 0.5, 1.0],
            "mix": [0.0, 0.5, 1.0], "hp_freq": [0.0, 200.0, 500.0],
            "predelay": [0.0001, 0.02, 0.25]}.items():
        add("reverb.engine.%s" % field, "P5", "shared_reverb", field,
            "dsp_audio_toggle" if field == "on" else "dsp_audio_scalar",
            stimuli=stimuli, api=("set_reverb", "reverb_off"),
            source=("io24.py block 202", "io24_meters.py vrvb"),
            requires=("native.channel1.processing_mix", "native.channel2.processing_mix",
                      "mixer.fxreturn_ch1.main.level_db",
                      "mixer.fxreturn_ch1.main.assigned", "deterministic_audio_rig@batch"))
    add("reverb.character", "P5", "shared_reverb_host", "character mapping",
        "host_mapping", stimuli=["Custom", "Room", "Plate", "Spring", "Hall", "Cathedral"],
        source=("io24gtk.py REVERB_TYPES",), requires=("reverb.engine.size", "reverb.engine.hp_freq", "reverb.engine.predelay"))
    add("reverb.movement.enabled", "P5", "shared_reverb_host", "movement",
        "host_mapping", stimuli=[False, True], source=("io24gtk.py",),
        requires=("reverb.engine.size",))
    add("reverb.movement.depth", "P5", "shared_reverb_host", "movement depth",
        "host_mapping", stimuli=[0.0, 0.05, 0.12], source=("io24gtk.py",),
        requires=("reverb.movement.enabled",))
    add("reverb.serializer", "P1", "serializer", "vrvb derived coefficient payload",
        "serializer", stimuli=["off", "defaults", "boundaries", "48k", "96k"],
        source=("io24_meters.py", "UC 4.7.2 host builder"))

    # P5: every VoiceFX model and transmitted user field, for each possible
    # physical owner.  Model selection and derived initializer blobs are their
    # own rows so payload acceptance cannot masquerade as audible processing.
    voicefx_fields = {
        "transformer": {"on": [False, True], "lows": [0.0, 0.5, 1.0],
                        "width": [0.0, 0.5, 1.0], "mix": [0.0, 0.5, 1.0]},
        "detuner": {"on": [False, True], "detune": list(range(9)),
                    "mix": [0.0, 0.5, 1.0]},
        "vocoder": {"on": [False, True], "vol": [0.0, 0.5, 1.0],
                    "carrier_type": [0, 1, 2], "carrier_freq": [50.0, 100.0, 500.0],
                    "mix": [0.0, 0.5, 1.0]},
        "ringmod": {"on": [False, True], "carrier_hz": [0.1, 30.0, 2000.0],
                    "carrier2": [False, True], "carrier2_hz": [0.1, 50.0, 2000.0],
                    "dist": [0.0, 0.5, 1.0], "vol": [0.0, 0.5, 1.0],
                    "mix": [0.0, 0.5, 1.0]},
        "filters": {"on": [False, True], "pitch": [0.0, 0.5, 1.0],
                    "regeneration": [0.0, 0.5, 1.0], "damping": [0.0, 0.5, 1.0],
                    "distortion": [0.0, 0.5, 1.0], "volume": [0.0, 0.5, 1.0],
                    "mix": [0.0, 0.5, 1.0]},
        "delay": {"on": [False, True], "time_s": [0.0001, 0.125, 0.25],
                  "feedback": [0.0, 0.5, 1.0], "mix": [0.0, 0.5, 1.0]},
    }
    for owner in (1, 2):
        add("voicefx.owner%d.model_selector" % owner, "P5", "voicefx_selector",
            "fxmodel", "dsp_audio_enum", scope={"owner": owner},
            stimuli=list(voicefx_fields), api=("set_fx",),
            source=("io24_fx.py", "UC parameter 450"),
            requires=("native.voicefx_owner_alias", "deterministic_audio_rig@batch"))
        add("voicefx.owner%d.model_before_state" % owner, "P1", "serializer_order",
            "model-before-state ordering", "serializer", scope={"owner": owner},
            stimuli=list(voicefx_fields), api=("apply_voicefx_snapshot", "send_fx"),
            source=("io24.py", "UC 4.7.2 model factory"))
        for model, fields in voicefx_fields.items():
            for field, stimuli in fields.items():
                if field in ("on", "carrier2"):
                    profile = "dsp_audio_toggle"
                elif field in ("carrier_type", "detune"):
                    profile = "dsp_audio_enum"
                else:
                    profile = "dsp_audio_scalar"
                add("voicefx.owner%d.%s.%s" % (owner, model, field), "P5",
                    "voicefx", field, profile, scope={"owner": owner, "model": model},
                    stimuli=stimuli, api=("set_fx", "configure_voice_fx_intent"),
                    source=("io24_fx.py", "UC 4.7.2 voicefx.xml"),
                    requires=("native.voicefx_owner_alias", "deterministic_audio_rig@batch",
                              "reverb.engine.on"),
                    prior_evidence=(
                        "2026-08-11 fx_gate_probe: block 201 measured inaudible "
                        "(-0.3 dB) with block-202 reverb as same-path positive "
                        "control (+6.0 dB); two runs agreed and preset recall "
                        "did not open the gate",
                    ))
            add("voicefx.owner%d.%s.serializer" % (owner, model), "P1",
                "serializer", "%s complete payload" % model, "serializer",
                scope={"owner": owner, "model": model},
                stimuli=["off", "default", "boundaries", "48k", "96k"],
                source=("io24_fx.py", "UC 4.7.2 host builder"))
        add("voicefx.owner%d.vocoder.avoiced" % owner, "P1", "telemetry",
            "avoiced read-only detector", "component_reconcile",
            scope={"owner": owner, "model": "vocoder"},
            source=("UC 4.7.2 RobotVoiceA",),
            blockers=("no_device_readback_route_established",))

    # P6: state, preset, factory-loader, reconnect, and disconnected acceptance.
    state_rows = (
        ("snapshot", "Host shadow snapshot", "host_mapping", ("snapshot",)),
        ("host_preset_save", "Host JSON save", "host_mapping", ("save_preset",)),
        ("host_preset_load", "Host JSON load", "host_mapping", ("load_preset",)),
        ("startup_save", "startup snapshot save", "host_mapping", ("save_startup",)),
        ("startup_apply", "startup snapshot apply", "host_mapping", ("apply_startup",)),
        ("shadow_reapply", "explicit cached-control replay", "host_mapping", ("reapply_shadow",)),
        ("shadow_forget", "explicit cached-control forget", "host_mapping", ("clear_shadow",)),
        ("shadow_normalization", "legacy alias/one-leg-pan migration", "host_mapping", ()),
        ("slot_before_dsp", "slot-before-DSP replay order", "serializer", ()),
        ("offline_attach", "offline open and later attach", "host_process", ()),
        ("hot_reconnect", "hot disconnect/reconnect gate", "host_process", ()),
        ("gtk_silent_adoption", "programmatic UI adoption emits no writes", "host_mapping", ()),
        ("factory_target", "factory preset target channel", "host_mapping", ()),
        ("factory_all_records", "all included factory records parse without silent field loss", "serializer", ()),
        ("hotkey_ch1", "Channel 1 Host Hot Key snapshot override", "host_mapping",
         ("HostHotKeySession.assign", "HostHotKeySession.capture",
          "HostHotKeySession.press")),
        ("hotkey_ch2", "Channel 2 Host Hot Key snapshot override", "host_mapping",
         ("HostHotKeySession.assign", "HostHotKeySession.capture",
          "HostHotKeySession.press")),
        ("hotkey_release", "Host Hot Key release restores normal snapshot", "host_mapping",
         ("HostHotKeySession.release",)),
        ("refuse_unproved_fx_gate", "unproved direct VoiceFX gate remains refused", "serializer", ("fx_on", "fx_off")),
    )
    for ident, parameter, profile, api in state_rows:
        blockers = ()
        add("state." + ident, "P6", "host_state", parameter, profile,
            api=api, source=("io24.py", "io24gtk.py"), blockers=blockers)
    add("state.channel2_slot3_write", "P6", "device_preset",
        "complete tagged record write to global slot 3", "persistence",
        scope={"channel": 2, "global_slot": 3},
        api=("save_device_slot", "save_uc_device_slot", "save_known_device_slot",
             "save_native_model0_voicefx_slot"),
        source=("io24.py MemP/Stat",),
        requires=("all_target_state_rows_pass", "battery_above_10"),
        blockers=("memp_receiver_ambiguity_unresolved_live",),
        note=("The only live MemP-tagged SetP observation (2026-08-10) "
              "resolved to a cache-invalidation handler at firmware 0x3c064 "
              "with no payload. The distinct CP34 {0,0}/0x420bc/0x531e0 "
              "receiver remains statically derived and unconfirmed live."))
    prior_voicefx_negative = (
        "2026-08-11 fx_gate_probe: block 201 measured inaudible (-0.3 dB) "
        "with block-202 reverb as same-path positive control (+6.0 dB); two "
        "runs agreed and preset recall did not open the gate",
    )
    persistence_note = ("A dry result is a valid negative only when the "
                        "same-path positive control passed immediately before "
                        "disconnect.")
    for model in voicefx_fields:
        add("persistence.channel2.%s" % model, "P6", "device_persistence",
            "%s standalone recall" % model, "persistence",
            scope={"channel": 2, "global_slot": 3, "model": model},
            source=("MemP/Stat", "front-panel recall"),
            requires=("state.channel2_slot3_write", "voicefx.owner2.%s.on" % model),
            note=persistence_note, prior_evidence=prior_voicefx_negative)
    add("persistence.channel2.shared_reverb", "P6", "device_persistence",
        "shared reverb standalone recall", "persistence",
        scope={"channel": 2, "global_slot": 3},
        source=("block 202", "front-panel recall"),
        requires=("state.channel2_slot3_write", "reverb.engine.on"),
        note=persistence_note, prior_evidence=prior_voicefx_negative)
    add("state.custom_firmware_deferred", "P7", "deferred_api",
        "paired custom-firmware lane controls", "component_reconcile",
        api=("save_paired_doubler_private_reverb",),
        source=("io24.py",), blockers=("post_initial_github_publication_only",))

    # P7: host-owned device settings, telemetry, and multiband parameters.
    add("host.sample_rate", "P7", "host_device", "PipeWire sample rate",
        "host_process", stimuli=[44100, 48000, 88200, 96000],
        source=("io24gtk.py", "UAC2 descriptors"))
    add("host.quantum", "P7", "host_device", "PipeWire quantum",
        "host_process", stimuli=[32, 64, 128, 256, 512, 1024, 2048],
        source=("io24gtk.py",))
    for field in ("rate", "period_size", "buffer_size", "format", "channels"):
        add("host.live_stream.%s" % field, "P7", "host_telemetry", field,
            "telemetry", source=("io24gtk.py ALSA live stream",))
    for field in ("usb_identity", "serial", "firmware", "channel_names"):
        api = ("channel_name", "channel_names") if field == "channel_names" else ()
        add("host.identity.%s" % field, "P0", "host_telemetry", field,
            "telemetry", api=api, source=("USB descriptor", "io24.py"))
    for field in ("input_levels", "main_levels", "mixa_levels", "mixb_levels",
                  "gate_reduction", "compressor_reduction", "limiter_reduction"):
        add("host.meter.%s" % field, "P3", "host_telemetry", field,
            "telemetry", api=("read_state", "read_params", "read_reduction"),
            source=("JaSt", "DSP reduction query"))
    for field in ("page_start", "page_pause", "stall_watchdog", "reattach"):
        add("host.spectrum.%s" % field, "P7", "host_process", field,
            "host_process", source=("io24gtk.py Spectrum",))
    add("host.device_close", "P0", "host_process", "exclusive handle close",
        "host_process", api=("close",), source=("io24.py",))
    add("host.raw_state_float_decoder", "P1", "serializer", "JaSt float decoder",
        "serializer", api=("floats",), source=("io24.py",))
    add("host.raw_setter_boundary", "P1", "serializer",
        "mapped-only set_param boundary", "serializer", api=("set_param",),
        source=("io24.py KNOWN_PARA/KNOWN_PARI",),
        blockers=("unknown_unmapped_writes_forbidden",))
    add("host.raw_biquad_boundary", "P1", "serializer",
        "stable finite Bqdf boundary", "serializer", api=("set_biquad",),
        source=("io24.py",))
    add("host.bus_shadow_queries", "P1", "host_state",
        "send/pan/bus shadow query methods", "host_mapping",
        api=("send_db", "has_send_level", "send_assigned", "bus_summary"),
        source=("io24.py",))

    add("multiband.enabled", "P7", "multiband", "PipeWire chain enabled",
        "host_process", stimuli=[False, True], api=("start", "stop", "running"),
        source=("io24_mbc.py",), requires=("pipewire_available", "sc3_available"))
    for i, stimuli in enumerate(([40, 150, 400], [300, 800, 2500], [2000, 4500, 12000])):
        add("multiband.crossover%d" % i, "P7", "multiband", "crossover %d" % i,
            "host_mapping", stimuli=stimuli, api=("set_controls",),
            source=("io24_mbc.py Linkwitz-Riley graph",), requires=("multiband.enabled",))
    mb_fields = {
        "character": ["standard", "tube", "fet"],
        "threshold_db": [-40.0, -20.0, 0.0], "ratio": [1.0, 4.0, 20.0],
        "knee_db": [0.0, 6.0, 12.0], "attack_ms": [1.0, 20.0, 100.0],
        "release_ms": [10.0, 200.0, 800.0], "makeup_db": [0.0, 6.0, 24.0],
        "auto_makeup": [False, True], "limit_mode": [False, True],
        "key_filter_enabled": [False, True], "key_frequency_hz": [30.0, 1000.0, 16000.0],
        "key_listen": [False, True],
    }
    for band in ("low", "lowmid", "highmid", "high"):
        for field, stimuli in mb_fields.items():
            add("multiband.%s.%s" % (band, field), "P7", "multiband", field,
                "host_mapping", scope={"band": band}, stimuli=stimuli,
                api=("set_controls",), source=("io24gtk.py", "io24_mbc.py"),
                requires=("multiband.enabled",))

    # Static reconciliation: every retained 117-entry descriptor and every
    # relevant component-model route gets an individual ledger row.  These are
    # not counted as operational passes merely because a same-named Host control
    # exists; P1 must link or exclude them one by one.
    catalog = json.loads((ROOT / "re/io24_params.json").read_text())
    for index, entry in enumerate(catalog):
        add("catalog.%03d.%s" % (index, _safe_id(entry["name"])), "P1",
            "vendor_descriptor", entry["name"], "catalog_reconcile",
            scope={"catalog_index": index, **entry},
            source=("re/io24_params.json",),
            note="Legacy extraction field labels are provisional; exact UC 4.7.2 XML/table wins on disagreement.")

    lists = _component_paramlists()
    component_routes: list[tuple[str, tuple[str, ...]]] = [
        ("global", ("Global", "DesktopGlobal")),
    ]
    for ch in (1, 2):
        component_routes.append(("line/ch%d" % ch,
                                 ("Channel", "InputChannel", "AnalogInputChannel", "MicLineInputChannel")))
        component_routes.append(("line/ch%d/presets" % ch, ("ChannelPresets",)))
        component_routes.append(("line/ch%d/cache" % ch, ("PresetCache",)))
        component_routes.append(("line/ch%d/voicefxopt" % ch, ("InsertFXSelector",)))
    for ch in (1, 2, 3):
        component_routes.append(("return/ch%d" % ch, ("Channel", "InputChannel")))
    component_routes.append(("fxreturn/ch1", ("Channel", "InputChannel")))
    for route in ("main/ch1", "aux/ch1", "aux/ch2"):
        component_routes.append((route, ("Channel", "OutputChannel")))
    for route, paramlists in component_routes:
        seen: set[str] = set()
        for paramlist in paramlists:
            if paramlist not in lists:
                raise ValueError("missing component ParamList %s" % paramlist)
            for entry in lists[paramlist]:
                name = entry.get("id", "")
                if not name or name in seen:
                    continue
                seen.add(name)
                add("component.%s.%s" % (_safe_id(route), _safe_id(name)), "P1",
                    "component_route", route + "/" + name, "component_reconcile",
                    scope={"route": route, "paramlist": paramlist, **entry},
                    source=("re/uc_component_model/dspusb_component_model.xml",))

    rows.sort(key=lambda r: r["id"])
    api_index: dict[str, list[str]] = {}
    for row in rows:
        for name in row["api"]:
            api_index.setdefault(name, []).append(row["id"])
    source_paths = (
        "io24.py", "io24gtk.py", "io24d.py", "io24_scene.py", "ucnet_shim.py",
        "io24_dsp.py", "io24_fx.py", "io24_mbc.py", "io24_presets.py",
        "re/io24_params.json",
        "re/uc_component_model/dspusb_component_model.xml",
        "re/uc_component_model/dsp_fx_params.xml",
    )
    matrix = {
        "schema": "io24-atomic-parameter-verification-matrix-v1",
        "plan_timestamp": "2026-09-06",
        "target": {"model": "PreSonus Revelator io24", "usb_id": "194f:0422",
                   "serial": "AB7C22200355", "firmware_bcd": "0x0128"},
        "authority": {
            "authorized": ["bounded USB control", "bounded ALSA playback/capture",
                           "Linux Host launch/restart/cache", "Channel 2 global slot 3 overwrite",
                           "disconnect and non-computer cold-power acceptance test"],
            "forbidden": ["Wine or .wine-io24", "firmware", "DFU", "reset",
                          "network", "unknown/unmapped writes", "Channel 1 slot-body writes",
                          "global slot 0 overwrite"],
            "stop_conditions": ["battery <= 10 percent", "identity drift", "bootloader 194f:0405",
                                "clipping", "feedback", "USB/audio timeout", "restoration mismatch"],
            "preconditions": {
                "cold_start_before_measurement_session": "cold power cycle at the device end and confirm 194f:0422 / bcdDevice 0x0128 before measurement",
                "deterministic_audio_rig@batch": "same-path positive control must pass at batch open and close; a mismatch makes every row in that batch INCONCLUSIVE",
            },
            "stop_recovery": {
                "bootloader_194f_0405": "stop all work; cold power cycle at the device end, wait about 15 seconds, and confirm kernel USB disconnect; DFU reports Upload Unsupported and is never a repair path",
            },
        },
        "terminal_statuses": list(TERMINAL_STATUSES),
        "profiles": PROFILES,
        "source_sha256": {name: _sha256(ROOT / name) for name in source_paths},
        "coverage": {
            "total_rows": len(rows),
            "by_phase": dict(sorted(Counter(r["phase"] for r in rows).items())),
            "by_family": dict(sorted(Counter(r["family"] for r in rows).items())),
            "by_profile": dict(sorted(Counter(r["profile"] for r in rows).items())),
            "vendor_descriptor_rows": len(catalog),
            "component_route_rows": sum(r["family"] == "component_route" for r in rows),
            "mixer_cell_rows": sum(r["family"] == "mixer_cell" for r in rows),
            "voicefx_parameter_rows": sum(r["family"] == "voicefx" for r in rows),
            "fat_channel_parameter_rows": sum(r["family"].startswith("fat_") for r in rows),
            "multiband_parameter_rows": sum(r["family"] == "multiband" for r in rows),
        },
        "api_index": dict(sorted(api_index.items())),
        "rows": rows,
    }
    return matrix


def _safe_public_api() -> set[str]:
    """Public control/state API names that the matrix must account for."""
    names: set[str] = set()
    for filename, clsname in (("io24.py", "Io24"), ("io24_mbc.py", "Chain")):
        tree = ast.parse((ROOT / filename).read_text(), filename)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == clsname)
        for node in cls.body:
            if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
                continue
            if (node.name.startswith(("set_", "save_", "load_", "read_", "clear_", "reapply_"))
                    or node.name in {
                        "close", "floats", "output_delay_off", "processing_channel",
                        "channel_name", "channel_names", "compressor_off", "gate_off",
                        "pan", "send_db", "has_send_level", "send_assigned", "bus_master",
                        "pan_gain", "pan_db", "mirror_main", "mix_off", "bus_summary",
                        "snapshot", "apply_startup", "send_fx", "apply_voicefx_snapshot",
                        "configure_voice_fx_intent", "fx_on", "fx_off", "preset_enabled",
                        "reverb_off", "eq_off", "running", "start", "stop",
                        "soloed",
                    }):
                names.add(node.name)
    return names


def validate(matrix: dict) -> None:
    rows = matrix["rows"]
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate row id")
    if any(row["result"]["status"] != "PENDING" for row in rows):
        raise SystemExit("a plan row contains a claimed result")
    if matrix["coverage"]["vendor_descriptor_rows"] != 117:
        raise SystemExit("vendor descriptor catalog is not 117 rows")
    missing = _safe_public_api() - set(matrix["api_index"])
    if missing:
        raise SystemExit("public APIs absent from matrix: " + ", ".join(sorted(missing)))
    if any(row["profile"] not in matrix["profiles"] for row in rows):
        raise SystemExit("unknown profile in row")
    if any(row["result"]["restored"] for row in rows):
        raise SystemExit("a plan row incorrectly claims restoration")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    matrix = build()
    validate(matrix)
    if args.summary:
        print(json.dumps(matrix["coverage"], indent=2, sort_keys=True))
    else:
        text = json.dumps(matrix, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.write_text(text)
        else:
            print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
