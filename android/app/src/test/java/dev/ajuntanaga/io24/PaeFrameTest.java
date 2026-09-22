package dev.ajuntanaga.io24;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

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
