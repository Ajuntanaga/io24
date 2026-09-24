package dev.ajuntanaga.io24;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThrows;
import static org.junit.Assert.assertTrue;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.security.MessageDigest;

import org.junit.Test;

public final class PaeFrameTest {
    @Test
    public void stateReadMatchesTheProvenWireVector() throws Exception {
        byte[] frame = PaeFrame.buildStateRead(1);

        assertEquals(2048, frame.length);
        assertArrayEquals(hex(
                "0008010101000000507465476c70704100000000"
                        + "7453614aec0700000000000000000000"),
                slice(frame, 0, 36));
        assertEquals(
                "0cc107bdd645d9df161d4ede8355226c3c6f56166f9359a331d9e077a0230bb2",
                hex(MessageDigest.getInstance("SHA-256").digest(frame)));
    }

    @Test
    public void uidZeroIsRejected() {
        assertThrows(IllegalArgumentException.class, () -> PaeFrame.buildStateRead(0));
    }

    @Test
    public void matchingStateReplyReports503Slots() throws Exception {
        byte[] frame = PaeFrame.buildStateRead(9);
        frame[3] = (byte) 0x81;
        ByteBuffer.wrap(frame, 8, 4)
                .order(ByteOrder.LITTLE_ENDIAN)
                .putInt(0x52706c79);

        PaeFrame.StateReply result = PaeFrame.parseStateReply(frame, 9);

        assertEquals(9, result.uid());
        assertEquals(2048, result.responseLength());
        assertEquals(503, result.stateSlotCount());
    }

    @Test
    public void requestDirectionIsRejectedAsAReply() {
        byte[] frame = PaeFrame.buildStateRead(1);

        assertThrows(
                PaeFrame.ProtocolException.class,
                () -> PaeFrame.parseStateReply(frame, 1));
    }

    @Test
    public void input2MuteWriteMatchesTheProvenWireVector() {
        assertArrayEquals(
                hex("2800010111000000"
                        + "507465536c70704100000000"
                        + "6972615014000000010000000700000001000000"),
                PaeFrame.buildInput2MuteWrite(17, true));
        assertArrayEquals(
                hex("2800010112000000"
                        + "507465536c70704100000000"
                        + "6972615014000000010000000700000000000000"),
                PaeFrame.buildInput2MuteWrite(18, false));
    }

    @Test
    public void emptyInput2MuteReplyIsAcceptedForTheMatchingWrite() throws Exception {
        PaeFrame.parseInput2MuteReply(
                hex("0800018111000000"), 17);
    }

    @Test
    public void emptyInput2MuteReplyRejectsTheWrongUid() {
        assertThrows(
                PaeFrame.ProtocolException.class,
                () -> PaeFrame.parseInput2MuteReply(
                        hex("0800018112000000"), 17));
    }

    @Test
    public void emptyInput2MuteReplyRejectsARequestDirection() {
        assertThrows(
                PaeFrame.ProtocolException.class,
                () -> PaeFrame.parseInput2MuteReply(
                        hex("0800010111000000"), 17));
    }

    @Test
    public void nativeBlockWriteWrapsBlobWithoutChangingIt() {
        byte[] blob = hex(
                "78466f56100000000000000004000000");

        byte[] frame = PaeFrame.buildBlockWrite(33, 201, 0, blob);

        assertArrayEquals(hex(
                "2400010121000000"
                        + "50746553c900000000000000"
                        + "78466f56100000000000000004000000"), frame);
    }

    @Test
    public void nativeBlockWriteRejectsAnInconsistentBlobSize() {
        assertThrows(IllegalArgumentException.class, () ->
                PaeFrame.buildBlockWrite(1, 201, 0,
                        hex("78466f56140000000000000004000000")));
    }

    @Test
    public void stateReplyDecodesOnlyTheInput2MuteFlag() throws Exception {
        byte[] frame = stateReply(9);
        ByteBuffer.wrap(frame)
                .order(ByteOrder.LITTLE_ENDIAN)
                .putInt(36 + 42 * 4, 1 << 4);

        PaeFrame.StateReply muted = PaeFrame.parseStateReply(frame, 9);
        assertTrue(muted.input2Muted());

        ByteBuffer.wrap(frame)
                .order(ByteOrder.LITTLE_ENDIAN)
                .putInt(36 + 42 * 4, 1 << 3);
        PaeFrame.StateReply input1Only = PaeFrame.parseStateReply(frame, 9);
        assertFalse(input1Only.input2Muted());
    }

    private static byte[] stateReply(int uid) {
        byte[] frame = PaeFrame.buildStateRead(uid);
        frame[3] = (byte) 0x81;
        ByteBuffer.wrap(frame, 8, 4)
                .order(ByteOrder.LITTLE_ENDIAN)
                .putInt(0x52706c79);
        return frame;
    }

    private static byte[] slice(byte[] source, int start, int end) {
        byte[] result = new byte[end - start];
        System.arraycopy(source, start, result, 0, result.length);
        return result;
    }

    private static byte[] hex(String value) {
        byte[] result = new byte[value.length() / 2];
        for (int index = 0; index < result.length; index++) {
            result[index] = (byte) Integer.parseInt(
                    value.substring(index * 2, index * 2 + 2), 16);
        }
        return result;
    }

    private static String hex(byte[] value) {
        StringBuilder result = new StringBuilder(value.length * 2);
        for (byte item : value) {
            result.append(String.format("%02x", item & 0xff));
        }
        return result.toString();
    }
}
