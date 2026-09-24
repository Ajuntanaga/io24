package dev.ajuntanaga.io24;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThrows;
import static org.junit.Assert.assertTrue;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

import org.junit.Test;

public final class Io24ProtocolTest {
    @Test
    public void gainAndPhantomEncodeAsExactAllowlistedScalarWrites() {
        assertArrayEquals(
                hex("2800010107000000"
                        + "507465536c70704100000000"
                        + "6172615014000000010000000300000000003442"),
                Io24Protocol.encode(Io24Command.setGain(2, 45.0f), 7));
        assertArrayEquals(
                hex("2800010108000000"
                        + "507465536c70704100000000"
                        + "6972615014000000000000000000000001000000"),
                Io24Protocol.encode(Io24Command.setPhantom(1, true), 8));
    }

    @Test
    public void allSimpleNativeControlsMapToTheirKnownWireFamilies() {
        assertScalar(Io24Command.setHeadphoneVolume(0.5f), false, 0, 1);
        assertScalar(Io24Command.setMainVolume(0.5f), false, 0, 2);
        assertScalar(Io24Command.setFxMix(2, 0.8f), false, 1, 4);
        assertScalar(Io24Command.setMonitorBlend(-0.5f), false, 0, 10);
        assertScalar(Io24Command.setOutputDelay(0.05f), false, 0, 14);
        assertScalar(Io24Command.setHighPass(2, true), true, 1, 5);
        assertScalar(Io24Command.setInputMute(1, true), true, 0, 7);
        assertScalar(Io24Command.setHeadphoneMute(true), true, 0, 6);
        assertScalar(Io24Command.setLinked(true), true, 0, 9);
        assertScalar(Io24Command.setPhoneSource(Io24State.PhoneSource.MIX_B),
                true, 0, 11);
        assertScalar(Io24Command.setVoiceFxInput(2), true, 0, 12);
        assertScalar(Io24Command.setOutputDelayBus(2), true, 0, 13);
        assertScalar(Io24Command.setPresetSlot(2, 3), true, 1, 16);
        assertScalar(Io24Command.setPresetEnabled(1, true), true, 0, 4);
    }

    @Test
    public void complexCommandCannotFallThroughToAGenericWireWriter() {
        assertThrows(
                IllegalArgumentException.class,
                () -> Io24Protocol.encode(
                        Io24Command.setVoiceFxParameter(
                                Io24State.VoiceFxModel.FILTERS,
                                "mix",
                                0.5f),
                        1));
    }

    @Test
    public void filterSelectionUsesTheFirmwareReplacementSequence() {
        Io24Protocol.Transaction transaction = Io24Protocol.encodeTransaction(
                Io24Command.setVoiceFxModel(Io24State.VoiceFxModel.FILTERS),
                Io24State.defaults(),
                254);

        assertEquals(3, transaction.writes().size());
        assertEquals(254, transaction.writes().get(0).uid());
        assertEquals(Io24Protocol.VOICE_FX_REPLACE_SETTLE_MS,
                transaction.writes().get(0).settleAfterMillis());
        assertEquals(255, transaction.writes().get(1).uid());
        assertEquals(1, transaction.writes().get(2).uid());
        assertEquals(2, transaction.nextUid());
        assertEquals(201, intAt(transaction.writes().get(0).frame(), 12));
        assertEquals(0x566f4678,
                intAt(transaction.writes().get(0).frame(), 20));
        assertEquals(4, intAt(transaction.writes().get(0).frame(), 32));
        assertEquals(0x626f7463,
                intAt(transaction.writes().get(2).frame(), 20));
    }

    @Test
    public void inactiveVoiceFxEditStaysSemanticUntilThatModelIsSelected() {
        Io24Protocol.Transaction transaction = Io24Protocol.encodeTransaction(
                Io24Command.setVoiceFxOn(
                        Io24State.VoiceFxModel.RING_MOD, true),
                Io24State.defaults(),
                4);

        assertTrue(transaction.writes().isEmpty());
        assertEquals(4, transaction.nextUid());
    }

    @Test
    public void mixerSendUsesBlock100BusAndSourceIds() {
        Io24Protocol.Transaction transaction = Io24Protocol.encodeTransaction(
                Io24Command.setMixerSend(
                        Io24State.Source.INPUT_2,
                        Io24State.Bus.MIX_B,
                        -12.0f),
                Io24State.defaults(),
                7);
        byte[] frame = transaction.writes().get(0).frame();

        assertEquals(100, intAt(frame, 12));
        assertEquals(2, intAt(frame, 16));
        assertEquals(0x50617261, intAt(frame, 20));
        assertEquals(4, intAt(frame, 32));
        assertEquals(-12.0f,
                ByteBuffer.wrap(frame).order(ByteOrder.LITTLE_ENDIAN)
                        .getFloat(36), 0.0f);
    }

    @Test
    public void mixerSoloRecomputesEverySourceOnTheSelectedBus() {
        Io24Protocol.Transaction transaction = Io24Protocol.encodeTransaction(
                Io24Command.setMixerSolo(
                        Io24State.Source.INPUT_1,
                        Io24State.Bus.MAIN,
                        true),
                Io24State.defaults(),
                1);

        assertEquals(Io24State.Source.values().length,
                transaction.writes().size());
        for (int index = 0; index < transaction.writes().size(); index++) {
            byte[] frame = transaction.writes().get(index).frame();
            float db = ByteBuffer.wrap(frame).order(ByteOrder.LITTLE_ENDIAN)
                    .getFloat(36);
            assertEquals(index == Io24State.Source.INPUT_1.ordinal()
                    ? 0.0f : -145.0f, db, 0.0f);
        }
    }

    @Test
    public void selectingDelayAt96kQuiescesHardwareAndKeepsSemanticIntent() {
        Io24State at96 = Io24State.defaults().buildUpon()
                .setSampleRateHz(96_000)
                .build();
        Io24Protocol.Transaction transaction = Io24Protocol.encodeTransaction(
                Io24Command.setVoiceFxModel(Io24State.VoiceFxModel.DELAY),
                at96,
                1);

        assertEquals(7, transaction.writes().size());
        assertEquals(0, intAt(transaction.writes().get(0).frame(), 32));
        assertEquals(0x676f6476,
                intAt(transaction.writes().get(6).frame(), 20));
    }

    @Test
    public void selectingDelayBeforeRateConfirmationAlsoQuiescesHardware() {
        Io24State unknown = Io24State.defaults();

        Io24Protocol.Transaction transaction = Io24Protocol.encodeTransaction(
                Io24Command.setVoiceFxModel(Io24State.VoiceFxModel.DELAY),
                unknown,
                1);

        assertFalse(unknown.sampleRateConfirmed());
        assertEquals(7, transaction.writes().size());
        assertEquals(0, intAt(transaction.writes().get(0).frame(), 32));
    }

    @Test
    public void deviceBlockSaveUsesTheExactMempStatDestination() {
        Io24Protocol.Transaction transaction = Io24Protocol.encodeTransaction(
                Io24Command.saveDeviceBlock(2, 1),
                Io24State.defaults(),
                17);
        byte[] frame = transaction.writes().get(0).frame();

        assertEquals(1, transaction.writes().size());
        assertEquals(2048, frame.length);
        assertEquals(17, transaction.writes().get(0).uid());
        assertEquals(0x53657450, intAt(frame, 8));
        assertEquals(0x4170706c, intAt(frame, 12));
        assertEquals(0x4d656d50, intAt(frame, 20));
        assertEquals(0x53746174, intAt(frame, 28));
        assertEquals(3, intAt(frame, 32));
        assertEquals(1028, Short.toUnsignedInt(
                ByteBuffer.wrap(frame).order(ByteOrder.LITTLE_ENDIAN)
                        .getShort(43)));
        assertEquals(1028, intAt(frame, 45));
        assertEquals(2, intAt(frame, 49));
        assertEquals(18, transaction.nextUid());
    }

    @Test
    public void entering96kQuiescesDelayAtTheOldRateBeforeStateChanges() {
        Io24State delayAt48 = Io24State.defaults().buildUpon()
                .setSelectedVoiceFx(Io24State.VoiceFxModel.DELAY)
                .setSampleRateHz(48_000)
                .build();

        Io24Protocol.Transaction transaction = Io24Protocol.encodeTransaction(
                Io24Command.setSampleRate(96_000), delayAt48, 1);

        assertEquals(7, transaction.writes().size());
        assertEquals(0, intAt(transaction.writes().get(0).frame(), 32));
        assertEquals(60, transaction.writes().get(0).settleAfterMillis());
        assertEquals(22, transaction.writes().get(6).settleAfterMillis());
        assertEquals(0x676f6476,
                intAt(transaction.writes().get(6).frame(), 20));
    }

    @Test
    public void entering882kUsesTheSameDelaySafetyTransaction() {
        Io24State delayAt48 = Io24State.defaults().buildUpon()
                .setSelectedVoiceFx(Io24State.VoiceFxModel.DELAY)
                .setSampleRateHz(48_000)
                .build();

        Io24Protocol.Transaction transaction = Io24Protocol.encodeTransaction(
                Io24Command.setSampleRate(88_200), delayAt48, 1);

        assertEquals(7, transaction.writes().size());
        assertEquals(0, intAt(transaction.writes().get(0).frame(), 32));
        assertEquals(60, transaction.writes().get(0).settleAfterMillis());
        assertEquals(22, transaction.writes().get(6).settleAfterMillis());
        assertEquals(0x676f6476,
                intAt(transaction.writes().get(6).frame(), 20));
    }

    @Test
    public void confirming48kNeverArmsDelayWithoutAnExplicitOnAction() {
        Io24State delayAt96 = Io24State.defaults().buildUpon()
                .setSelectedVoiceFx(Io24State.VoiceFxModel.DELAY)
                .setVoiceFxOn(Io24State.VoiceFxModel.DELAY, true)
                .setSampleRateHz(96_000)
                .build();

        Io24Protocol.Transaction transaction = Io24Protocol.encodeTransaction(
                Io24Command.setSampleRate(48_000), delayAt96, 1);

        assertEquals(7, transaction.writes().size());
        assertEquals(0, intAt(transaction.writes().get(0).frame(), 32));
        for (Io24Protocol.EncodedWrite write : transaction.writes()) {
            if (intAt(write.frame(), 20) == 0x566f4678) {
                assertFalse(intAt(write.frame(), 32) == 5);
            }
        }
    }

    @Test
    public void assigningVoiceFxToInput2WritesTheSourceThenRematerializesModel() {
        Io24Protocol.Transaction transaction = Io24Protocol.encodeTransaction(
                Io24Command.setVoiceFxInput(2), Io24State.defaults(), 10);
        byte[] source = transaction.writes().get(0).frame();

        assertEquals(8, transaction.writes().size());
        assertEquals(0x4170706c, intAt(source, 12));
        assertEquals(0x50617269, intAt(source, 20));
        assertEquals(0, intAt(source, 28));
        assertEquals(12, intAt(source, 32));
        assertEquals(1, intAt(source, 36));
        assertEquals(0x566f4678,
                intAt(transaction.writes().get(1).frame(), 20));
        assertEquals(0x676f6476,
                intAt(transaction.writes().get(7).frame(), 20));
    }

    @Test
    public void stateDecoderReadsFloatsPackedIntegersFlagsAndPhantomBytes()
            throws Exception {
        byte[] frame = stateReply(23);
        putFloat(frame, 4, 0.25f);
        putFloat(frame, 6, 0.5f);
        putInt(frame, 38, 3);
        putInt(frame, 39, 4);
        putInt(frame, 40, 2);
        putInt(frame, 41, 3);
        putInt(frame, 42, (1 << 2) | (1 << 3) | (1 << 6) | (1 << 12));
        putFloat(frame, 43, 0.65f);
        putFloat(frame, 44, 0.75f);
        putFloat(frame, 45, -0.25f);
        putFloat(frame, 46, 11.0f);
        putFloat(frame, 47, 22.0f);
        putInt(frame, 50, 0x00000101);

        PaeFrame.StateReply reply = PaeFrame.parseStateReply(frame, 23);
        Io24State state = Io24Protocol.decodeState(reply, Io24State.defaults());

        assertEquals(11.0f, state.input(1).gainDb(), 0.0f);
        assertEquals(22.0f, state.input(2).gainDb(), 0.0f);
        assertEquals(0.25f, state.input(1).level(), 0.0f);
        assertEquals(0.5f, state.input(2).level(), 0.0f);
        assertTrue(state.input(1).phantom());
        assertTrue(state.input(2).phantom());
        assertTrue(state.input(1).muted());
        assertFalse(state.input(2).muted());
        assertEquals(2, state.input(1).presetSlot());
        assertEquals(3, state.input(2).presetSlot());
        assertTrue(state.linked());
        assertTrue(state.headphoneMuted());
        assertEquals(0.65f, state.headphoneVolume(), 0.0f);
        assertEquals(0.75f, state.mainVolume(), 0.0f);
        assertEquals(-0.25f, state.monitorBlend(), 0.0f);
        assertEquals(1.0f, state.processing(1).get("preset_enabled"), 0.0f);
        assertEquals(0.0f, state.processing(2).get("preset_enabled"), 0.0f);
    }

    private static void assertScalar(
            Io24Command command,
            boolean integer,
            int expectedIndex,
            int expectedWireId) {
        byte[] frame = Io24Protocol.encode(command, 5);
        ByteBuffer reader = ByteBuffer.wrap(frame).order(ByteOrder.LITTLE_ENDIAN);
        assertEquals(40, Short.toUnsignedInt(reader.getShort(0)));
        assertEquals(integer ? 0x50617269 : 0x50617261, reader.getInt(20));
        assertEquals(expectedIndex, reader.getInt(28));
        assertEquals(expectedWireId, reader.getInt(32));
    }

    private static byte[] stateReply(int uid) {
        byte[] frame = PaeFrame.buildStateRead(uid);
        frame[3] = (byte) 0x81;
        ByteBuffer.wrap(frame).order(ByteOrder.LITTLE_ENDIAN)
                .putInt(8, 0x52706c79);
        return frame;
    }

    private static void putFloat(byte[] frame, int slot, float value) {
        ByteBuffer.wrap(frame).order(ByteOrder.LITTLE_ENDIAN)
                .putFloat(36 + slot * 4, value);
    }

    private static void putInt(byte[] frame, int slot, int value) {
        ByteBuffer.wrap(frame).order(ByteOrder.LITTLE_ENDIAN)
                .putInt(36 + slot * 4, value);
    }

    private static int intAt(byte[] value, int offset) {
        return ByteBuffer.wrap(value).order(ByteOrder.LITTLE_ENDIAN)
                .getInt(offset);
    }

    private static byte[] hex(String value) {
        byte[] result = new byte[value.length() / 2];
        for (int index = 0; index < result.length; index++) {
            result[index] = (byte) Integer.parseInt(
                    value.substring(index * 2, index * 2 + 2), 16);
        }
        return result;
    }
}
