package dev.ajuntanaga.io24;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Converts semantic scene state into ordered typed controller commands. */
final class Io24ScenePlanner {
    private Io24ScenePlanner() {
    }

    static List<Io24Command> commands(Io24State target) {
        List<Io24Command> result = new ArrayList<>();
        for (int channel = 1; channel <= 2; channel++) {
            Io24State.Input input = target.input(channel);
            result.add(Io24Command.setGain(channel, input.gainDb()));
            result.add(Io24Command.setPhantom(channel, input.phantom()));
            result.add(Io24Command.setHighPass(channel, input.highPass()));
            result.add(Io24Command.setInputMute(channel, input.muted()));
            result.add(Io24Command.setFxMix(channel, input.fxMix()));
            result.add(Io24Command.setPresetEnabled(
                    channel,
                    value(target.processing(channel), "preset_enabled", 1) >= 0.5f));
            for (Map.Entry<String, Float> entry
                    : target.processing(channel).entrySet()) {
                if (!entry.getKey().equals("preset_enabled")
                        && !entry.getKey().equals("source_input")
                        && !entry.getKey().equals("main_hardware_muted")
                        && !entry.getKey().equals("mute_sync")
                        && !entry.getKey().equals("output_delay_bus")) {
                    result.add(Io24Command.setProcessingParameter(
                            channel, entry.getKey(), entry.getValue()));
                }
            }
        }
        result.add(Io24Command.setLinked(target.linked()));
        result.add(Io24Command.setMainVolume(target.mainVolume()));
        result.add(Io24Command.setHeadphoneVolume(target.headphoneVolume()));
        result.add(Io24Command.setHeadphoneMute(target.headphoneMuted()));
        result.add(Io24Command.setMonitorBlend(target.monitorBlend()));
        result.add(Io24Command.setPhoneSource(target.phoneSource()));
        result.add(Io24Command.setOutputDelay(target.outputDelaySeconds()));
        result.add(Io24Command.setOutputDelayBus(Math.round(
                value(target.processing(1), "output_delay_bus", 0))));
        result.add(Io24Command.setMuteSync(
                value(target.processing(1), "mute_sync", 0) >= 0.5f));
        result.add(Io24Command.setVoiceFxInput(target.voiceFxInput()));
        for (Io24State.Bus bus : Io24State.Bus.values()) {
            Io24State.BusState busState = target.bus(bus);
            result.add(Io24Command.setBusMaster(bus, busState.masterDb()));
            result.add(Io24Command.setBusMute(bus, busState.muted()));
            if (bus != Io24State.Bus.MAIN) {
                result.add(Io24Command.setMirrorMain(bus, busState.mirrorsMain()));
            }
            for (Io24State.Source source : Io24State.Source.values()) {
                Io24State.Send send = target.send(source, bus);
                result.add(Io24Command.setMixerSend(source, bus, send.db()));
                result.add(Io24Command.setMixerAssigned(
                        source, bus, send.assigned()));
                result.add(Io24Command.setMixerSolo(source, bus, send.soloed()));
            }
        }
        for (Io24State.Source source : Io24State.Source.values()) {
            result.add(Io24Command.setMixerMute(
                    source,
                    target.send(source, Io24State.Bus.MAIN).muted()));
        }
        for (Io24State.VoiceFxModel model : Io24State.VoiceFxModel.values()) {
            Io24State.VoiceFxState effect = target.voiceFx(model);
            result.add(Io24Command.setVoiceFxOn(model, effect.on()));
            for (Map.Entry<String, Float> entry : effect.parameters().entrySet()) {
                if (!entry.getKey().equals("voiced")) {
                    result.add(Io24Command.setVoiceFxParameter(
                            model, entry.getKey(), entry.getValue()));
                }
            }
        }
        result.add(Io24Command.setVoiceFxModel(target.selectedVoiceFx()));
        Io24State.ReverbState reverb = target.reverb();
        result.add(Io24Command.setReverb(
                reverb.on(), reverb.size(), reverb.mix(),
                reverb.highPassHz(), reverb.preDelaySeconds()));
        return result;
    }

    private static float value(
            Map<String, Float> values,
            String key,
            float fallback) {
        Float value = values.get(key);
        return value == null ? fallback : value;
    }
}
