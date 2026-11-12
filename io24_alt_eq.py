#!/usr/bin/env python3
"""Exact UC 4.7.2 Passive and Vintage EQ support for the Linux Host.

The native circuit equations preserve UC's binary32 coefficient calculations.
No DLL, emulator, or disassembler is needed by the Host. Live routing remains
one seven-float ``Lfdf`` section at index 0 and three ``Bqdf`` sections at
indexes 1 through 3. The optional legacy oracle is retained for research.
"""

import cmath
import functools
import math
import os
from pathlib import Path

import io24_eq_native as native


PASSIVE_CLASS_ID = "{C0730CBB-5135-4558-9222-C40BDBA036ED}"
VINTAGE_CLASS_ID = "{E1C5E024-C5CD-473C-B08A-6EC177812E01}"
CLASS_IDS = {"passive": PASSIVE_CLASS_ID, "vintage": VINTAGE_CLASS_ID}
MODEL_BY_CLASS_ID = {value: key for key, value in CLASS_IDS.items()}

PASSIVE_LOW_HZ = (20.0, 30.0, 60.0, 100.0)
PASSIVE_HIGH_BOOST_HZ = (3000.0, 4000.0, 5000.0, 8000.0, 10000.0, 12000.0, 16000.0)
PASSIVE_HIGH_ATTEN_HZ = (5000.0, 10000.0, 20000.0)
VINTAGE_LOW_HZ = (35.0, 60.0, 110.0, 220.0)
VINTAGE_LOWMID_HZ = (360.0, 700.0, 1600.0)
VINTAGE_HIMID_HZ = (3200.0, 4800.0, 7200.0)

IDENTITY = (1.0, 0.0, 0.0, 0.0, 0.0)
WIDE_IDENTITY = IDENTITY + (0.0, 0.0)
NATIVE_RATES = (44100.0, 48000.0, 88200.0, 96000.0)

# Exact defaults and ordering from UC 4.7.2's embedded fatchannelxt.xml.
PASSIVE_DEFAULT = {
    "__classid": PASSIVE_CLASS_ID,
    "eqallon": 0,
    "bboost": 0.0,
    "batten": 0.0,
    "bfreq": 0,
    "mboost": 1.5,
    "bbwidth": 10.0,
    "mfreq": 4,
    "hatten": 1.5,
    "hsfreq": 2,
}
VINTAGE_DEFAULT = {
    "__classid": VINTAGE_CLASS_ID,
    "eqallon": 0,
    "lowgain": 0.0,
    "lowfreq": 1,
    "lowmidgain": 0.0,
    "lowmidfreq": 2,
    "himidgain": 0.0,
    "himidfreq": 2,
    "higain": 0.0,
}

DEFAULT_DLL = Path(os.environ.get(
    "XDG_CACHE_HOME", str(Path.home() / ".cache")
)) / "io24" / "re" / "dspusbdevice.dll"


class AlternateEqUnavailable(RuntimeError):
    """The exact retained UC designer dependency is unavailable."""


def default_eq(model, on=False):
    """Return a fresh exact UC semantic record for ``model``."""
    if model == "passive":
        result = dict(PASSIVE_DEFAULT)
    elif model == "vintage":
        result = dict(VINTAGE_DEFAULT)
    else:
        raise ValueError("alternate EQ model must be passive or vintage")
    result["eqallon"] = int(bool(on))
    return result


def model_of(eq):
    """Resolve a complete alternate model without guessing across classes."""
    if not isinstance(eq, dict):
        raise ValueError("alternate EQ must be an object")
    try:
        return MODEL_BY_CLASS_ID[eq.get("__classid")]
    except KeyError:
        raise ValueError("alternate EQ has an unknown class id")


def _number(eq, field, low, high, integer=False):
    if field not in eq or isinstance(eq[field], bool) and field != "eqallon":
        raise ValueError("%s EQ %s must be a finite number" %
                         (model_of(eq).title(), field))
    try:
        value = float(eq[field])
    except (TypeError, ValueError, OverflowError):
        raise ValueError("%s EQ %s must be a finite number" %
                         (model_of(eq).title(), field))
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError("%s EQ %s must be in [%g, %g]" %
                         (model_of(eq).title(), field, low, high))
    if integer and not value.is_integer():
        raise ValueError("%s EQ %s must be an integer switch index" %
                         (model_of(eq).title(), field))
    return int(value) if integer else value


def validate_eq(eq):
    """Validate and normalize one complete UC alternate-EQ semantic record."""
    model = model_of(eq)
    if model == "passive":
        normalized = {
            "__classid": PASSIVE_CLASS_ID,
            "eqallon": _number(eq, "eqallon", 0, 1, True),
            "bboost": _number(eq, "bboost", 0, 10),
            "batten": _number(eq, "batten", 0, 10),
            "bfreq": _number(eq, "bfreq", 0, 3, True),
            "mboost": _number(eq, "mboost", 0, 10),
            "bbwidth": _number(eq, "bbwidth", 0, 10),
            "mfreq": _number(eq, "mfreq", 0, 6, True),
            "hatten": _number(eq, "hatten", 0, 10),
            "hsfreq": _number(eq, "hsfreq", 0, 2, True),
        }
    else:
        normalized = {
            "__classid": VINTAGE_CLASS_ID,
            "eqallon": _number(eq, "eqallon", 0, 1, True),
            "lowgain": _number(eq, "lowgain", -16, 16),
            "lowfreq": _number(eq, "lowfreq", 0, 3, True),
            "lowmidgain": _number(eq, "lowmidgain", -16, 16),
            "lowmidfreq": _number(eq, "lowmidfreq", 0, 2, True),
            "himidgain": _number(eq, "himidgain", -16, 16),
            "himidfreq": _number(eq, "himidfreq", 0, 2, True),
            "higain": _number(eq, "higain", -16, 16),
        }
    unknown = sorted(set(eq) - set(normalized))
    if unknown:
        raise ValueError("%s EQ has unknown field%s: %s" %
                         (model.title(), "s" if len(unknown) != 1 else "",
                          ", ".join(unknown)))
    return normalized


def resolve_dll(path=None):
    """Resolve a validated UC 4.7.2 designer artifact.

    An explicit path is strict.  Otherwise use the conventional user cache.
    Existing files are not assumed to be the right UC build: the bounded image
    parser must accept the candidate before it can become active.
    """
    explicit = path or os.environ.get("IO24_UC472_DSPUSBDEVICE")
    selected = Path(explicit or DEFAULT_DLL).expanduser().resolve()
    if not selected.is_file():
        detail = "%s is missing" % selected
    else:
        try:
            _image(str(selected))
        except AlternateEqUnavailable as error:
            detail = "%s: %s" % (selected, error)
        else:
            return selected
    raise AlternateEqUnavailable(
        "the optional legacy EQ oracle needs the pinned UC 4.7.2 "
        "dspusbdevice.dll; set IO24_UC472_DSPUSBDEVICE to your local copy"
        " (%s)" % detail)


@functools.lru_cache(maxsize=4)
def _image(path):
    import io24_uc472_vintage_eq as vintage
    try:
        return vintage.Image(path)
    except (OSError, vintage.AnalysisError) as error:
        raise AlternateEqUnavailable(str(error))


def designer_status(path=None):
    """Report native availability; ``path`` is retained for API compatibility."""
    return True, "native Passive/Vintage coefficient designers available"


def _rate(rate_hz):
    if isinstance(rate_hz, bool):
        raise ValueError("EQ sample rate must be a finite number")
    try:
        rate = float(rate_hz)
    except (TypeError, ValueError):
        raise ValueError("EQ sample rate must be a finite number")
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError("EQ sample rate must be positive")
    return rate


def live_design_key(eq, rate_hz=48000.0):
    """Immutable identity of the semantic state represented by live sections."""
    normalized = validate_eq(eq)
    return (_rate(rate_hz), tuple(normalized.items()))


def design_live_sections(eq, rate_hz=48000.0, dll_path=None):
    """Return UC's exact live packet order as ``(kind, index, coefficients)``.

    The result is ready for :class:`io24.Io24`: ``kind`` is ``wide`` for the
    seven-float Lfdf section and ``biquad`` for each five-float Bqdf section.
    A bypassed model is exact identity. ``dll_path`` is ignored for compatibility.
    """
    eq = validate_eq(eq)
    model = model_of(eq)
    rate = _rate(rate_hz)
    if not eq["eqallon"]:
        return (("wide", 0, WIDE_IDENTITY),
                ("biquad", 1, IDENTITY),
                ("biquad", 2, IDENTITY),
                ("biquad", 3, IDENTITY))

    if model == "passive":
        high = tuple(native.passive_high(
            eq["mfreq"], eq["mboost"], eq["hatten"], eq["hsfreq"],
            eq["bbwidth"], rate))
        low = tuple(native.passive_low(
            eq["bfreq"], eq["bboost"], eq["batten"], rate))
        return (("wide", 0, high), ("biquad", 1, low),
                ("biquad", 2, IDENTITY), ("biquad", 3, IDENTITY))

    low = tuple(native.vintage("low", eq["lowfreq"], eq["lowgain"], rate))
    high = tuple(native.vintage("high", 0, eq["higain"], rate))
    high_mid = tuple(native.vintage(
        "hi-mid", eq["himidfreq"], eq["himidgain"], rate))
    low_mid = tuple(native.vintage(
        "low-mid", eq["lowmidfreq"], eq["lowmidgain"], rate))
    return (("wide", 0, low), ("biquad", 1, high),
            ("biquad", 2, high_mid), ("biquad", 3, low_mid))


def _normalized_live_sections(sections):
    """Return a safe four-section live chain, or ``None`` if incomplete."""
    expected = (("wide", 0, 7), ("biquad", 1, 5),
                ("biquad", 2, 5), ("biquad", 3, 5))
    try:
        normalized = tuple(
            (str(kind), int(index), tuple(float(value)
                                         for value in coefficients))
            for kind, index, coefficients in sections)
    except (TypeError, ValueError, OverflowError):
        return None
    if len(normalized) != len(expected):
        return None
    for section, contract in zip(normalized, expected):
        kind, index, coefficients = section
        expected_kind, expected_index, expected_width = contract
        if kind != expected_kind or index != expected_index or \
                len(coefficients) != expected_width or \
                not all(math.isfinite(value) for value in coefficients):
            return None
    return normalized


def design_changed_live_sections(eq, field, previous_sections,
                                 rate_hz=48000.0, dll_path=None):
    """Recompute only the exact UC section affected by one semantic control.

    Passive has one coupled low section and one coupled high section. Vintage
    has four independent bands. Reusing the other already-exact sections makes
    graph feedback fast enough for pointer motion while remaining bit-for-bit
    identical to a complete :func:`design_live_sections` call.
    """
    eq = validate_eq(eq)
    model = model_of(eq)
    rate = _rate(rate_hz)
    previous = _normalized_live_sections(previous_sections)
    if field == "eqallon" or not eq["eqallon"] or previous is None:
        return design_live_sections(eq, rate, dll_path)

    if model == "passive":
        if field in ("bboost", "batten", "bfreq"):
            replacement_index = 1
            replacement = ("biquad", 1, tuple(native.passive_low(
                eq["bfreq"], eq["bboost"], eq["batten"], rate
            )))
        elif field in ("mboost", "bbwidth", "mfreq", "hatten", "hsfreq"):
            replacement_index = 0
            replacement = ("wide", 0, tuple(native.passive_high(
                eq["mfreq"], eq["mboost"], eq["hatten"],
                eq["hsfreq"], eq["bbwidth"], rate)))
        else:
            raise ValueError("unknown Passive EQ field %r" % field)
    else:
        routes = {
            "lowgain": (0, "wide", "low", "lowfreq", "lowgain"),
            "lowfreq": (0, "wide", "low", "lowfreq", "lowgain"),
            "higain": (1, "biquad", "high", None, "higain"),
            "himidgain": (2, "biquad", "hi-mid",
                           "himidfreq", "himidgain"),
            "himidfreq": (2, "biquad", "hi-mid",
                           "himidfreq", "himidgain"),
            "lowmidgain": (3, "biquad", "low-mid",
                            "lowmidfreq", "lowmidgain"),
            "lowmidfreq": (3, "biquad", "low-mid",
                            "lowmidfreq", "lowmidgain"),
        }
        try:
            replacement_index, kind, band, frequency_field, gain_field = \
                routes[field]
        except KeyError as error:
            raise ValueError("unknown Vintage EQ field %r" % field) from error
        frequency_index = 0 if frequency_field is None else eq[frequency_field]
        replacement = (kind, replacement_index, tuple(native.vintage(
            band, frequency_index, eq[gain_field], rate)))

    updated = list(previous)
    updated[replacement_index] = replacement
    return tuple(updated)


def design_native_coefficients(eq, dll_path=None):
    """Return the four-rate coefficient table used by a device block."""
    eq = validate_eq(eq)
    result = {}
    for rate in NATIVE_RATES:
        sections = design_live_sections(eq, rate)
        if model_of(eq) == "passive":
            result[rate] = {"low-mid": sections[1][2], "hi-mid": IDENTITY,
                            "high": IDENTITY, "wide": sections[0][2]}
        else:
            result[rate] = {"low-mid": sections[3][2], "hi-mid": sections[2][2],
                            "high": sections[1][2], "wide": sections[0][2]}
    return result


def section_response(section, frequency_hz, rate_hz):
    """Complex response of one UC wire-format section."""
    coefficients = tuple(section)
    if len(coefficients) not in (5, 7):
        raise ValueError("EQ section must contain five or seven coefficients")
    padded = coefficients + (0.0,) * (7 - len(coefficients))
    b0, na1, b1, na2, b2, na3, b3 = padded
    z = cmath.exp(-2j * math.pi * float(frequency_hz) / _rate(rate_hz))
    numerator = b0 + b1 * z + b2 * z ** 2 + b3 * z ** 3
    denominator = 1.0 - na1 * z - na2 * z ** 2 - na3 * z ** 3
    return numerator / denominator


def response_db(sections, frequency_hz, rate_hz):
    """Combined dB response for a result from :func:`design_live_sections`."""
    response = complex(1.0, 0.0)
    for _kind, _index, coefficients in sections:
        response *= section_response(coefficients, frequency_hz, rate_hz)
    magnitude = abs(response)
    return -180.0 if magnitude <= 1e-9 else 20.0 * math.log10(magnitude)


def _log_bell(frequency_hz, center_hz, width_octaves):
    distance = math.log(max(1e-6, frequency_hz) / center_hz, 2.0)
    width = max(.12, float(width_octaves))
    return math.exp(-.5 * (distance / width) ** 2)


def _low_shelf_weight(frequency_hz, center_hz):
    ratio = max(1e-9, float(frequency_hz)) / float(center_hz)
    return 1.0 / (1.0 + ratio ** 3.0)


def _high_shelf_weight(frequency_hz, center_hz):
    ratio = float(center_hz) / max(1e-9, float(frequency_hz))
    return 1.0 / (1.0 + ratio ** 3.0)


def preview_response_db(eq, frequency_hz, rate_hz=48000.0):
    """Fast parameter-driven curve used while exact DSP work is queued.

    This intentionally does not replace :func:`design_live_sections`; device
    writes still use the exact native coefficient designers. It gives the GTK
    graph immediate feedback while coefficient work is queued off the UI thread.
    Every semantic control has its own visible contribution.
    """
    eq = validate_eq(eq)
    _rate(rate_hz)
    frequency = max(1.0, float(frequency_hz))
    if not eq["eqallon"]:
        return 0.0
    if model_of(eq) == "passive":
        low_frequency = PASSIVE_LOW_HZ[eq["bfreq"]]
        high_frequency = PASSIVE_HIGH_BOOST_HZ[eq["mfreq"]]
        attenuation_frequency = PASSIVE_HIGH_ATTEN_HZ[eq["hsfreq"]]
        bandwidth = .32 + 1.45 * (eq["bbwidth"] / 10.0)
        response = (
            1.45 * eq["bboost"] * _low_shelf_weight(
                frequency, low_frequency * 2.1)
            - 1.15 * eq["batten"] * _low_shelf_weight(
                frequency, low_frequency * 3.2)
            + 1.45 * eq["mboost"] * _log_bell(
                frequency, high_frequency, bandwidth)
            - 1.18 * eq["hatten"] * _high_shelf_weight(
                frequency, attenuation_frequency)
        )
    else:
        response = (
            eq["lowgain"] * _low_shelf_weight(
                frequency, VINTAGE_LOW_HZ[eq["lowfreq"]] * 2.0)
            + eq["lowmidgain"] * _log_bell(
                frequency, VINTAGE_LOWMID_HZ[eq["lowmidfreq"]], 1.05)
            + eq["himidgain"] * _log_bell(
                frequency, VINTAGE_HIMID_HZ[eq["himidfreq"]], .82)
            + eq["higain"] * _high_shelf_weight(frequency, 9000.0)
        )
    return max(-36.0, min(36.0, float(response)))
