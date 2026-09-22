package dev.ajuntanaga.io24;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

/** Bounded paesdk framing for the Revelator io24 control interface. */
public final class PaeFrame {
    private static final int HEADER_SIZE = 8;
    private static final int GETP = 0x47657450;
    private static final int SETP = 0x53657450;
    private static final int APPL = 0x4170706c;
    private static final int JAST = 0x4a615374;
    private static final int PARI = 0x50617269;
    private static final int RPLY = 0x52706c79;
    private static final int STATE_BLOB_SIZE = 0x7ec;
    private static final int STATE_PAYLOAD_SIZE = 12 + STATE_BLOB_SIZE;
    private static final int STATE_VALUES_OFFSET = 36;
    private static final int STATE_FLAGS_SLOT = 42;
    private static final int INPUT2_MUTE_BIT = 4;
    private static final int INPUT2_INDEX = 1;
    private static final int INPUT_MUTE_WIRE_ID = 7;
    private static final int PARAMETER_BLOB_SIZE = 0x14;
    public static final int STATE_FRAME_SIZE = HEADER_SIZE + STATE_PAYLOAD_SIZE;
    public static final int INPUT2_MUTE_FRAME_SIZE = 40;

    private PaeFrame() {
    }

    public static byte[] buildStateRead(int uid) {
        requireUid(uid);
        ByteBuffer frame = ByteBuffer.allocate(STATE_FRAME_SIZE)
                .order(ByteOrder.LITTLE_ENDIAN);
        frame.putShort((short) STATE_FRAME_SIZE);
        frame.put((byte) 0x01); // protocol
        frame.put((byte) 0x01); // request
        frame.put((byte) uid);
        frame.put((byte) 0x00); // status
        frame.putShort((short) 0x0000);
        frame.putInt(GETP);
        frame.putInt(APPL);
        frame.putInt(0); // application block index
        frame.putInt(JAST);
        frame.putInt(STATE_BLOB_SIZE);
        frame.putInt(0); // blob index
        frame.putInt(0); // parameter id
        return frame.array();
    }

    /** Builds the only write supported by this milestone: input 2 mute on/off. */
    public static byte[] buildInput2MuteWrite(int uid, boolean muted) {
        requireUid(uid);
        ByteBuffer frame = ByteBuffer.allocate(INPUT2_MUTE_FRAME_SIZE)
                .order(ByteOrder.LITTLE_ENDIAN);
        frame.putShort((short) INPUT2_MUTE_FRAME_SIZE);
        frame.put((byte) 0x01); // protocol
        frame.put((byte) 0x01); // request
        frame.put((byte) uid);
        frame.put((byte) 0x00); // status
        frame.putShort((short) 0x0000);
        frame.putInt(SETP);
        frame.putInt(APPL);
        frame.putInt(0); // application block index
        frame.putInt(PARI);
        frame.putInt(PARAMETER_BLOB_SIZE);
        frame.putInt(INPUT2_INDEX);
        frame.putInt(INPUT_MUTE_WIRE_ID);
        frame.putInt(muted ? 1 : 0);
        return frame.array();
    }

    public static StateReply parseStateReply(byte[] frame, int expectedUid)
            throws ProtocolException {
        requireUid(expectedUid);
        if (frame == null || frame.length < 36) {
            throw new ProtocolException("Reply is shorter than the state header");
        }
        ByteBuffer reply = ByteBuffer.wrap(frame).order(ByteOrder.LITTLE_ENDIAN);
        int declaredLength = Short.toUnsignedInt(reply.getShort());
        if (declaredLength != frame.length) {
            throw new ProtocolException("Reply length does not match its header");
        }
        if (Byte.toUnsignedInt(reply.get()) != 0x01) {
            throw new ProtocolException("Unsupported protocol version");
        }
        if (Byte.toUnsignedInt(reply.get()) != 0x81) {
            throw new ProtocolException("Reply has the wrong message direction");
        }
        int uid = Byte.toUnsignedInt(reply.get());
        if (uid != expectedUid) {
            throw new ProtocolException("Reply UID does not match the request");
        }
        if (Byte.toUnsignedInt(reply.get()) != 0) {
            throw new ProtocolException("Device returned a nonzero status");
        }
        if (Short.toUnsignedInt(reply.getShort()) != 0) {
            throw new ProtocolException("Reply reserved field is nonzero");
        }
        if (reply.getInt() != RPLY) {
            throw new ProtocolException("Reply tag is not Rply");
        }
        if (reply.getInt() != APPL || reply.getInt() != 0) {
            throw new ProtocolException("Reply addresses a different block");
        }
        if (reply.getInt() != JAST) {
            throw new ProtocolException("Reply blob is not JaSt");
        }
        int blobSize = reply.getInt();
        if (blobSize < 16 || 12 + blobSize != frame.length - HEADER_SIZE) {
            throw new ProtocolException("Reply blob length is invalid");
        }
        if (reply.getInt() != 0 || reply.getInt() != 0) {
            throw new ProtocolException("Reply blob index or parameter is nonzero");
        }
        int stateBytes = blobSize - 16;
        if (stateBytes % 4 != 0) {
            throw new ProtocolException("Reply state is not float-aligned");
        }
        int stateSlotCount = stateBytes / 4;
        if (stateSlotCount <= STATE_FLAGS_SLOT) {
            throw new ProtocolException("Reply is missing the state flags slot");
        }
        int flags = ByteBuffer.wrap(frame)
                .order(ByteOrder.LITTLE_ENDIAN)
                .getInt(STATE_VALUES_OFFSET + STATE_FLAGS_SLOT * 4);
        boolean input2Muted = (flags & (1 << INPUT2_MUTE_BIT)) != 0;
        return new StateReply(uid, frame.length, stateSlotCount, input2Muted);
    }

    private static void requireUid(int uid) {
        if (uid < 1 || uid > 255) {
            throw new IllegalArgumentException("UID must be in the range 1..255");
        }
    }

    public static final class StateReply {
        private final int uid;
        private final int responseLength;
        private final int stateSlotCount;
        private final boolean input2Muted;

        StateReply(
                int uid,
                int responseLength,
                int stateSlotCount,
                boolean input2Muted) {
            this.uid = uid;
            this.responseLength = responseLength;
            this.stateSlotCount = stateSlotCount;
            this.input2Muted = input2Muted;
        }

        public int uid() {
            return uid;
        }

        public int responseLength() {
            return responseLength;
        }

        public int stateSlotCount() {
            return stateSlotCount;
        }

        public boolean input2Muted() {
            return input2Muted;
        }
    }

    public static final class ProtocolException extends Exception {
        ProtocolException(String message) {
            super(message);
        }
    }
}
