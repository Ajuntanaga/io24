package dev.ajuntanaga.io24;

import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

/** Deterministic flat-JSON semantic scene codec with no Android dependency. */
public final class PresetCodec {
    private static final int SCHEMA = 1;

    private PresetCodec() {
    }

    public static String encode(String name, Io24State state) {
        validateName(name);
        if (state == null) {
            throw new IllegalArgumentException("Scene state is required");
        }
        LinkedHashMap<String, Object> values = new LinkedHashMap<>();
        values.put("schema", SCHEMA);
        values.put("name", name);
        values.put("sample_rate_hz", state.sampleRateHz());
        values.put("main_volume", state.mainVolume());
        values.put("headphone_volume", state.headphoneVolume());
        values.put("headphone_muted", state.headphoneMuted());
        values.put("monitor_blend", state.monitorBlend());
        values.put("phone_source", state.phoneSource().name());
        values.put("linked", state.linked());
        values.put("output_delay_s", state.outputDelaySeconds());
        values.put("selected_voice_fx", state.selectedVoiceFx().name());
        values.put("voice_fx_input", state.voiceFxInput());

        for (int channel = 1; channel <= 2; channel++) {
            Io24State.Input input = state.input(channel);
            String prefix = "input." + channel + ".";
            values.put(prefix + "gain_db", input.gainDb());
            values.put(prefix + "phantom", input.phantom());
            values.put(prefix + "high_pass", input.highPass());
            values.put(prefix + "muted", input.muted());
            values.put(prefix + "fx_mix", input.fxMix());
            values.put(prefix + "preset_slot", input.presetSlot());
        }
        for (Io24State.Bus bus : Io24State.Bus.values()) {
            Io24State.BusState busState = state.bus(bus);
            String prefix = "bus." + bus.name() + ".";
            values.put(prefix + "master_db", busState.masterDb());
            values.put(prefix + "muted", busState.muted());
            values.put(prefix + "mirror_main", busState.mirrorsMain());
        }
        for (Io24State.Source source : Io24State.Source.values()) {
            for (Io24State.Bus bus : Io24State.Bus.values()) {
                Io24State.Send send = state.send(source, bus);
                String prefix = "send." + source.name() + "." + bus.name() + ".";
                values.put(prefix + "db", send.db());
                values.put(prefix + "assigned", send.assigned());
                values.put(prefix + "pan", send.pan());
                values.put(prefix + "muted", send.muted());
                values.put(prefix + "soloed", send.soloed());
            }
        }
        for (int channel = 1; channel <= 2; channel++) {
            for (Map.Entry<String, Float> entry
                    : state.processing(channel).entrySet()) {
                values.put("processing." + channel + "." + entry.getKey(),
                        entry.getValue());
            }
        }
        for (Io24State.VoiceFxModel model : Io24State.VoiceFxModel.values()) {
            Io24State.VoiceFxState effect = state.voiceFx(model);
            String prefix = "voice_fx." + model.name() + ".";
            values.put(prefix + "on", effect.on());
            for (Map.Entry<String, Float> entry
                    : effect.parameters().entrySet()) {
                values.put(prefix + entry.getKey(), entry.getValue());
            }
        }
        Io24State.ReverbState reverb = state.reverb();
        values.put("reverb.on", reverb.on());
        values.put("reverb.size", reverb.size());
        values.put("reverb.mix", reverb.mix());
        values.put("reverb.high_pass_hz", reverb.highPassHz());
        values.put("reverb.pre_delay_s", reverb.preDelaySeconds());
        return write(values);
    }

    public static Decoded decode(String json) {
        Map<String, String> values = new Parser(json).parse();
        int schema = integer(values, "schema");
        if (schema != SCHEMA) {
            throw new IllegalArgumentException(
                    "Unsupported scene schema " + schema);
        }
        String name = required(values, "name");
        validateName(name);
        Io24State.Builder builder = Io24State.defaults().buildUpon()
                .setConnection(
                        Io24State.ConnectionStatus.DISCONNECTED,
                        "Scene loaded on this phone",
                        false)
                .setRememberedSampleRateHz(integer(values, "sample_rate_hz"))
                .setMainVolume(decimal(values, "main_volume"))
                .setHeadphoneVolume(decimal(values, "headphone_volume"))
                .setHeadphoneMuted(toggle(values, "headphone_muted"))
                .setMonitorBlend(decimal(values, "monitor_blend"))
                .setPhoneSource(enumValue(
                        Io24State.PhoneSource.class,
                        required(values, "phone_source")))
                .setLinked(toggle(values, "linked"))
                .setOutputDelaySeconds(decimal(values, "output_delay_s"))
                .setSelectedVoiceFx(enumValue(
                        Io24State.VoiceFxModel.class,
                        required(values, "selected_voice_fx")))
                .setVoiceFxInput(integer(values, "voice_fx_input"));

        for (int channel = 1; channel <= 2; channel++) {
            String prefix = "input." + channel + ".";
            builder.setInputGain(channel, decimal(values, prefix + "gain_db"))
                    .setInputPhantom(channel, toggle(values, prefix + "phantom"))
                    .setInputHighPass(channel, toggle(values, prefix + "high_pass"))
                    .setInputMute(channel, toggle(values, prefix + "muted"))
                    .setInputFxMix(channel, decimal(values, prefix + "fx_mix"))
                    .setInputPresetSlot(
                            channel, integer(values, prefix + "preset_slot"));
        }
        for (Io24State.Bus bus : Io24State.Bus.values()) {
            String prefix = "bus." + bus.name() + ".";
            builder.setBus(
                    bus,
                    decimal(values, prefix + "master_db"),
                    toggle(values, prefix + "muted"),
                    toggle(values, prefix + "mirror_main"));
        }
        for (Io24State.Source source : Io24State.Source.values()) {
            for (Io24State.Bus bus : Io24State.Bus.values()) {
                String prefix = "send." + source.name() + "." + bus.name() + ".";
                builder.setMixerSend(
                                source,
                                bus,
                                decimal(values, prefix + "db"),
                                toggle(values, prefix + "assigned"),
                                decimal(values, prefix + "pan"))
                        .setMixerFlags(
                                source,
                                bus,
                                toggle(values, prefix + "muted"),
                                toggle(values, prefix + "soloed"));
            }
        }
        for (Map.Entry<String, String> entry : values.entrySet()) {
            String key = entry.getKey();
            if (!key.startsWith("processing.")) {
                continue;
            }
            int firstDot = key.indexOf('.', "processing.".length());
            if (firstDot < 0) {
                throw new IllegalArgumentException("Malformed processing field " + key);
            }
            int channel = parseInteger(
                    key.substring("processing.".length(), firstDot), key);
            builder.setProcessingParameter(
                    channel,
                    key.substring(firstDot + 1),
                    parseDecimal(entry.getValue(), key));
        }
        for (Io24State.VoiceFxModel model : Io24State.VoiceFxModel.values()) {
            String prefix = "voice_fx." + model.name() + ".";
            builder.setVoiceFxOn(model, toggle(values, prefix + "on"));
            for (String parameter
                    : Io24State.defaults().voiceFx(model).parameters().keySet()) {
                builder.setVoiceFxParameter(
                        model,
                        parameter,
                        decimal(values, prefix + parameter));
            }
        }
        builder.setReverb(
                toggle(values, "reverb.on"),
                decimal(values, "reverb.size"),
                decimal(values, "reverb.mix"),
                decimal(values, "reverb.high_pass_hz"),
                decimal(values, "reverb.pre_delay_s"));
        Io24State decoded = builder.build();
        // Exercise the same typed command validation used by a live apply.
        Io24ScenePlanner.commands(decoded);
        for (Io24State.Source source : Io24State.Source.values()) {
            for (Io24State.Bus bus : Io24State.Bus.values()) {
                Io24Command.setMixerPan(
                        source, bus, decoded.send(source, bus).pan());
            }
        }
        return new Decoded(name, decoded);
    }

    private static String write(LinkedHashMap<String, Object> values) {
        StringBuilder result = new StringBuilder(values.size() * 24);
        result.append('{');
        boolean first = true;
        for (Map.Entry<String, Object> entry : values.entrySet()) {
            if (!first) {
                result.append(',');
            }
            first = false;
            result.append('"').append(escape(entry.getKey())).append("\":");
            Object value = entry.getValue();
            if (value instanceof String) {
                result.append('"').append(escape((String) value)).append('"');
            } else if (value instanceof Boolean || value instanceof Integer) {
                result.append(value);
            } else if (value instanceof Float) {
                float number = (Float) value;
                if (!Float.isFinite(number)) {
                    throw new IllegalArgumentException("Scene values must be finite");
                }
                result.append(Float.toString(number));
            } else {
                throw new IllegalArgumentException("Unsupported scene value");
            }
        }
        return result.append('}').toString();
    }

    private static String escape(String value) {
        StringBuilder result = new StringBuilder(value.length());
        for (int index = 0; index < value.length(); index++) {
            char item = value.charAt(index);
            switch (item) {
                case '\\':
                    result.append("\\\\");
                    break;
                case '"':
                    result.append("\\\"");
                    break;
                case '\n':
                    result.append("\\n");
                    break;
                case '\r':
                    result.append("\\r");
                    break;
                case '\t':
                    result.append("\\t");
                    break;
                default:
                    if (item < 0x20) {
                        result.append(String.format(Locale.US, "\\u%04x", (int) item));
                    } else {
                        result.append(item);
                    }
            }
        }
        return result.toString();
    }

    private static void validateName(String value) {
        if (value == null || value.trim().isEmpty() || value.length() > 64) {
            throw new IllegalArgumentException(
                    "Scene name must be 1..64 characters");
        }
    }

    private static String required(Map<String, String> values, String key) {
        String result = values.get(key);
        if (result == null) {
            throw new IllegalArgumentException("Scene is missing " + key);
        }
        return result;
    }

    private static int integer(Map<String, String> values, String key) {
        return parseInteger(required(values, key), key);
    }

    private static int parseInteger(String value, String key) {
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException error) {
            throw new IllegalArgumentException(key + " must be an integer", error);
        }
    }

    private static float decimal(Map<String, String> values, String key) {
        return parseDecimal(required(values, key), key);
    }

    private static float parseDecimal(String value, String key) {
        try {
            float result = Float.parseFloat(value);
            if (!Float.isFinite(result)) {
                throw new NumberFormatException("not finite");
            }
            return result;
        } catch (NumberFormatException error) {
            throw new IllegalArgumentException(key + " must be a finite number", error);
        }
    }

    private static boolean toggle(Map<String, String> values, String key) {
        String value = required(values, key);
        if (value.equals("true")) {
            return true;
        }
        if (value.equals("false")) {
            return false;
        }
        throw new IllegalArgumentException(key + " must be true or false");
    }

    private static <T extends Enum<T>> T enumValue(Class<T> type, String value) {
        try {
            return Enum.valueOf(type, value);
        } catch (IllegalArgumentException error) {
            throw new IllegalArgumentException(
                    "Unknown " + type.getSimpleName() + " " + value, error);
        }
    }

    public static final class Decoded {
        private final String name;
        private final Io24State state;

        private Decoded(String name, Io24State state) {
            this.name = name;
            this.state = state;
        }

        public String name() {
            return name;
        }

        public Io24State state() {
            return state;
        }
    }

    private static final class Parser {
        private final String source;
        private int offset;

        Parser(String source) {
            this.source = source == null ? "" : source;
        }

        Map<String, String> parse() {
            LinkedHashMap<String, String> values = new LinkedHashMap<>();
            whitespace();
            expect('{');
            whitespace();
            if (take('}')) {
                return values;
            }
            while (true) {
                whitespace();
                String key = string();
                whitespace();
                expect(':');
                whitespace();
                String value = source.charAt(offset) == '"' ? string() : literal();
                if (values.put(key, value) != null) {
                    throw problem("Duplicate field " + key);
                }
                whitespace();
                if (take('}')) {
                    break;
                }
                expect(',');
            }
            whitespace();
            if (offset != source.length()) {
                throw problem("Trailing content");
            }
            return values;
        }

        private String string() {
            expect('"');
            StringBuilder result = new StringBuilder();
            while (offset < source.length()) {
                char item = source.charAt(offset++);
                if (item == '"') {
                    return result.toString();
                }
                if (item != '\\') {
                    if (item < 0x20) {
                        throw problem("Control character in string");
                    }
                    result.append(item);
                    continue;
                }
                if (offset >= source.length()) {
                    throw problem("Unfinished escape");
                }
                char escaped = source.charAt(offset++);
                switch (escaped) {
                    case '"':
                    case '\\':
                    case '/':
                        result.append(escaped);
                        break;
                    case 'n':
                        result.append('\n');
                        break;
                    case 'r':
                        result.append('\r');
                        break;
                    case 't':
                        result.append('\t');
                        break;
                    case 'u':
                        if (offset + 4 > source.length()) {
                            throw problem("Unfinished unicode escape");
                        }
                        try {
                            result.append((char) Integer.parseInt(
                                    source.substring(offset, offset + 4), 16));
                        } catch (NumberFormatException error) {
                            throw problem("Invalid unicode escape");
                        }
                        offset += 4;
                        break;
                    default:
                        throw problem("Unsupported escape");
                }
            }
            throw problem("Unfinished string");
        }

        private String literal() {
            int start = offset;
            while (offset < source.length()) {
                char item = source.charAt(offset);
                if (item == ',' || item == '}' || Character.isWhitespace(item)) {
                    break;
                }
                offset++;
            }
            if (start == offset) {
                throw problem("Value is missing");
            }
            String result = source.substring(start, offset);
            if (!result.equals("true") && !result.equals("false")) {
                try {
                    double number = Double.parseDouble(result);
                    if (!Double.isFinite(number)) {
                        throw new NumberFormatException("not finite");
                    }
                } catch (NumberFormatException error) {
                    throw problem("Invalid literal " + result);
                }
            }
            return result;
        }

        private void whitespace() {
            while (offset < source.length()
                    && Character.isWhitespace(source.charAt(offset))) {
                offset++;
            }
        }

        private boolean take(char expected) {
            if (offset < source.length() && source.charAt(offset) == expected) {
                offset++;
                return true;
            }
            return false;
        }

        private void expect(char expected) {
            if (!take(expected)) {
                throw problem("Expected " + expected);
            }
        }

        private IllegalArgumentException problem(String message) {
            return new IllegalArgumentException(
                    "Malformed scene JSON at " + offset + ": " + message);
        }
    }
}
