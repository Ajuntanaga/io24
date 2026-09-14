# DSP Amount internal-meter conclusion

Status: `MEASURED_CLASSIFIED_RESTORED`

Artifact: `live-report.json`

SHA-256: `7a98ebff0c782037adf58c1bd06e0e7ca6ec9e8cd3b2eaf679d6eeadd4b24c71`

Device: serial `AB7C22200355`, firmware bcdDevice `0128`

Clock: 96000 Hz, 512-frame period, 2048-frame buffer

Probe: Channel-2 EQ band 0, +15 dB high-shelf at 1 kHz, Q 0.7

Observation: simultaneous JaSt Input-2 and Main L/R meters, 240 frames per
amount; no playback or user listening.

| DSP Amount | Main/Input-2 median | Endpoint position |
|---:|---:|---:|
| 0% | 0.7079686 | 0.0000000 |
| 25% | 1.4887534 | 0.2472526 |
| 50% | 2.2607991 | 0.4917378 |
| 75% | 3.0927397 | 0.7551900 |
| 100% | 3.8658112 | 1.0000000 |

Classification: `LINEAR_METER_ENDPOINT_INTERPOLATION`.

Interpretation: `CONSISTENT_WITH_LINEAR_DRY_WET_NOT_ARCHITECTURE_PROOF`.
Functionally DSP Amount is a single dry-to-full-Fat-Channel blend. Exact zero
retains the dry signal, so this is not a send/output level. The experiment does
not establish whether the equivalent firmware implementation literally uses
parallel signal paths.

Restoration: exact-zero DSP Amount, EQ identity coefficients sent, Main
restored to 0.7599996, readable flags 449, gains unchanged, stereo link and
phantom off, processing order 0/1, mixer routes untouched, no errors. Battery
was 95% before and after.
