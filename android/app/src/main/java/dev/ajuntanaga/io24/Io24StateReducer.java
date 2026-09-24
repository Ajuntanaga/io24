package dev.ajuntanaga.io24;

/** Pure reducer used for simulated, write-only, and local controller state. */
final class Io24StateReducer {
    private Io24StateReducer() {
    }

    static Io24State apply(Io24State state, Io24Command command) {
        if (state == null || command == null) {
            throw new IllegalArgumentException("State and command are required");
        }
        Io24State.Builder builder = state.buildUpon();
        switch (command.kind()) {
            case SET_GAIN:
                builder.setInputGain(command.channel(), command.value());
                break;
            case SET_PHANTOM:
                builder.setInputPhantom(command.channel(), command.toggle());
                break;
            case SET_HIGH_PASS:
                builder.setInputHighPass(command.channel(), command.toggle());
                break;
            case SET_INPUT_MUTE:
                builder.setInputMute(command.channel(), command.toggle());
                break;
            case SET_FX_MIX:
                builder.setInputFxMix(command.channel(), command.value());
                break;
            case SET_LINK:
                builder.setLinked(command.toggle());
                break;
            case SET_MUTE_SYNC:
                builder.setProcessingParameter(
                        1, "mute_sync", command.toggle() ? 1.0f : 0.0f);
                break;
            case SET_MAIN_VOLUME:
                builder.setMainVolume(command.value());
                break;
            case SET_HEADPHONE_VOLUME:
                builder.setHeadphoneVolume(command.value());
                break;
            case SET_HEADPHONE_MUTE:
                builder.setHeadphoneMuted(command.toggle());
                break;
            case SET_MONITOR_BLEND:
                builder.setMonitorBlend(command.value());
                break;
            case SET_PHONE_SOURCE:
                builder.setPhoneSource(command.phoneSource());
                break;
            case SET_PROCESSING_CHANNEL:
            case SET_VOICE_FX_INPUT:
                builder.setVoiceFxInput(command.channel());
                break;
            case SET_OUTPUT_DELAY:
                builder.setOutputDelaySeconds(command.value());
                break;
            case SET_OUTPUT_DELAY_BUS:
                builder.setProcessingParameter(
                        1, "output_delay_bus", command.value());
                break;
            case SET_SAMPLE_RATE:
                builder.setSampleRateHz(Math.round(command.value()));
                if (state.selectedVoiceFx() == Io24State.VoiceFxModel.DELAY) {
                    // A rate confirmation never arms model 5. The user must
                    // explicitly turn Delay on after confirming a safe rate.
                    builder.setVoiceFxOn(Io24State.VoiceFxModel.DELAY, false);
                }
                break;
            case SET_MIXER_SEND:
                setSend(builder, state, command, command.value(), null, null);
                break;
            case SET_MIXER_ASSIGN:
                setSend(builder, state, command, null, command.toggle(), null);
                break;
            case SET_MIXER_PAN:
                setSend(builder, state, command, null, null, command.value());
                break;
            case SET_MIXER_MUTE:
                for (Io24State.Bus bus : Io24State.Bus.values()) {
                    Io24State.Send send = state.send(command.source(), bus);
                    builder.setMixerFlags(
                            command.source(), bus, command.toggle(), send.soloed());
                }
                break;
            case SET_MIXER_SOLO:
                Io24State.Send solo = state.send(command.source(), command.bus());
                builder.setMixerFlags(
                        command.source(), command.bus(), solo.muted(),
                        command.toggle());
                break;
            case SET_BUS_MASTER:
                Io24State.BusState masterBus = state.bus(command.bus());
                builder.setBus(
                        command.bus(), command.value(), masterBus.muted(),
                        masterBus.mirrorsMain());
                break;
            case SET_BUS_MUTE:
                Io24State.BusState muteBus = state.bus(command.bus());
                builder.setBus(
                        command.bus(), muteBus.masterDb(), command.toggle(),
                        muteBus.mirrorsMain());
                break;
            case SET_MIRROR_MAIN:
                Io24State.BusState mirrorBus = state.bus(command.bus());
                builder.setBus(
                        command.bus(), mirrorBus.masterDb(), mirrorBus.muted(),
                        false);
                break;
            case SET_PROCESSING_PARAMETER:
                builder.setProcessingParameter(
                        command.channel(), command.parameter(), command.value());
                break;
            case SET_VOICE_FX_MODEL:
                builder.setSelectedVoiceFx(command.model());
                break;
            case SET_VOICE_FX_ON:
                builder.setVoiceFxOn(command.model(), command.toggle());
                break;
            case SET_VOICE_FX_PARAMETER:
                builder.setVoiceFxParameter(
                        command.model(), command.parameter(), command.value());
                break;
            case SET_REVERB:
                builder.setReverb(
                        command.toggle(),
                        command.values().get("size"),
                        command.values().get("mix"),
                        command.values().get("high_pass_hz"),
                        command.values().get("pre_delay_s"));
                break;
            case SET_PRESET_SLOT:
                builder.setInputPresetSlot(
                        command.channel(), Math.round(command.value()));
                break;
            case SET_PRESET_ENABLED:
                builder.setProcessingParameter(
                        command.channel(), "preset_enabled",
                        command.toggle() ? 1.0f : 0.0f);
                break;
            case SAVE_DEVICE_BLOCK:
            case SAVE_LOCAL_SCENE:
            case LOAD_LOCAL_SCENE:
                break;
            default:
                throw new IllegalArgumentException(
                        "Unsupported state command " + command.kind());
        }
        builder.setLastProof(proofLabel(command.proof()));
        return builder.build();
    }

    private static void setSend(
            Io24State.Builder builder,
            Io24State state,
            Io24Command command,
            Float db,
            Boolean assigned,
            Float pan) {
        Io24State.Send old = state.send(command.source(), command.bus());
        builder.setMixerSend(
                command.source(),
                command.bus(),
                db == null ? old.db() : db,
                assigned == null ? old.assigned() : assigned,
                pan == null ? old.pan() : pan);
    }

    static String proofLabel(Io24Command.Proof proof) {
        switch (proof) {
            case READBACK:
                return "Confirmed by fresh io24 state";
            case SENT:
                return "Sent; this device field has no readback";
            case LOCAL:
                return "Stored on this phone";
            case HOST_ONLY:
                return "Processed on this phone";
            default:
                return proof.name();
        }
    }
}
