# io24 Android Read-Only Probe Implementation Plan

> **For agentic workers:** Implement inline, task by task. Preserve one writer,
> use test-first changes, and do not perform a live USB run without separate
> authorization.

**Goal:** Produce a minimal Android APK that performs one explicit, read-only
io24 control probe while leaving Android audio interfaces untouched.

**Architecture:** A pure-Java paesdk framing core feeds a narrow Android USB
transport. A single platform Activity handles permission and status without
third-party UI dependencies.

**Tech Stack:** Java 17, Android platform APIs, Gradle/Android Gradle Plugin,
JUnit 4, and the repository's Python safety-contract tests.

**Spec:** `android/DESIGN.md`

## Global constraints

- Match only USB `194f:0422`.
- Claim only interface 5, alternate setting 1, without forced driver detach.
- Endpoint addresses must be bulk OUT `0x01` and bulk IN `0x81`.
- Permit only vendor capability reads and one `GetP / Appl / JaSt` request.
- Never send `SetP`, touch interface 6, or request Android Internet permission.
- Do not access USB hardware during offline implementation or verification.

---

### Task 1: Protocol and safety contract

**Files:**

- Create: `tests/test_android_probe_contract.py`
- Create: `android/protocol/io24-read-state-v1.json`
- Create: `android/app/src/main/java/dev/ajuntanaga/io24/PaeFrame.java`
- Create: `android/app/src/test/java/dev/ajuntanaga/io24/PaeFrameTest.java`

**Interfaces:**

- Produces: `PaeFrame.buildStateRead(int)` and
  `PaeFrame.parseStateReply(byte[], int)`.

- [x] Write host and Java tests for the exact 2048-byte request, UID rules,
      response direction, declared lengths, and `Rply` tag.
- [x] Run the host test and observe RED because the Android sources are absent.
- [x] Implement the minimal framing core and protocol vector.
- [x] Run the host test and observe GREEN.

### Task 2: Android USB transport and UI

**Files:**

- Create: `android/settings.gradle.kts`
- Create: `android/build.gradle.kts`
- Create: `android/gradle.properties`
- Create: `android/app/build.gradle.kts`
- Create: `android/app/src/main/AndroidManifest.xml`
- Create: `android/app/src/main/res/xml/device_filter.xml`
- Create: `android/app/src/main/java/dev/ajuntanaga/io24/ProbeResult.java`
- Create: `android/app/src/main/java/dev/ajuntanaga/io24/Io24UsbProbe.java`
- Create: `android/app/src/main/java/dev/ajuntanaga/io24/MainActivity.java`

**Interfaces:**

- Consumes: `PaeFrame` from Task 1.
- Produces: an explicit Inspect/Disconnect flow and an open, interface-5-only
  connection suitable for the later audio-coexistence test.

- [x] Extend the host safety test for the manifest, device filter, interface,
      endpoint, and forbidden-write contract; observe RED.
- [x] Add the dependency-free Android project and transport.
- [x] Run the host safety test and observe GREEN.
- [x] Run Java unit tests and `assembleDebug` when the local Android toolchain is
      available.

### Task 3: Offline verification and gated phone trial

**Files:**

- Modify: `android/README.md`
- Create: `android/verify.sh`

**Interfaces:**

- Consumes: the completed Android project.
- Produces: one command for host contracts, Java tests, and APK assembly.

- [x] Verify host safety contracts with the repository Python environment.
- [x] Verify Java tests and debug APK assembly without network access.
- [x] Record the APK path and SHA-256 in `BUILD_REPORT.md`.
- [x] Stop before installation or USB access and request exact authorization for
      the phone trial.

### Task 4: Authorized phone and audio-coexistence trial

**Files:**

- Create: `android/LIVE_TEST_REPORT.md`
- Modify: `android/README.md`

**Interfaces:**

- Consumes: the debug APK and an explicit hardware authorization.
- Produces: device evidence that Android control and audio interfaces coexist.

- [x] Install the checksum-verified APK on the BLU 1660V.
- [x] Read protocol version 1 and the complete `GetP / Appl / JaSt` reply.
- [x] Retain control interface 5 while recording io24 input 2.
- [x] Play the recording through the io24 output.
- [x] Return to the controller and confirm it remains connected.
- [x] Release interface 5 with **Disconnect Control** and confirm the idle state.
