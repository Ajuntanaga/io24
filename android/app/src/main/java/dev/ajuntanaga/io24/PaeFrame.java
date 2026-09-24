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
    private static final int PARA = 0x50617261;
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
        return buildIntegerParameterWrite(
                uid, INPUT2_INDEX, INPUT_MUTE_WIRE_ID, muted ? 1 : 0);
    }

    static byte[] buildFloatParameterWrite(
            int uid,
            int index,
            int wireId,
            float value) {
        return buildParameterWrite(uid, PARA, index, wireId,
                Float.floatToRawIntBits(value));
    }

    static byte[] buildIntegerParameterWrite(
            int uid,
            int index,
            int wireId,
            int value) {
        return buildParameterWrite(uid, PARI, index, wireId, value);
    }

    /** Builds a native SetP frame for a validated coefficient/state blob. */
    static byte[] buildBlockWrite(
            int uid,
            int block,
            int blockIndex,
            byte[] blob) {
        requireUid(uid);
        if (block <= 0) {
            throw new IllegalArgumentException("Block identifier must be positive");
        }
        if (blockIndex < 0 || blockIndex > 2) {
            throw new IllegalArgumentException("Block index must be 0..2");
        }
        if (blob == null || blob.length < 12) {
            throw new IllegalArgumentException("Native blob must include its 12-byte header");
        }
        ByteBuffer body = ByteBuffer.wrap(blob).order(ByteOrder.LITTLE_ENDIAN);
        int declaredSize = body.getInt(4);
        if (declaredSize != blob.length) {
            throw new IllegalArgumentException(
                    "Native blob length does not match its header");
        }
        int frameSize = HEADER_SIZE + 12 + blob.length;
        if (frameSize > 0xffff) {
            throw new IllegalArgumentException("Native frame exceeds paesdk length limit");
        }
        ByteBuffer frame = ByteBuffer.allocate(frameSize)
                .order(ByteOrder.LITTLE_ENDIAN);
        frame.putShort((short) frameSize);
        frame.put((byte) 0x01);
        frame.put((byte) 0x01);
        frame.put((byte) uid);
        frame.put((byte) 0x00);
        frame.putShort((short) 0x0000);
        frame.putInt(SETP);
        frame.putInt(block);
        frame.putInt(blockIndex);
        frame.put(blob);
        return frame.array();
    }

    private static byte[] buildParameterWrite(
            int uid,
            int tag,
            int index,
            int wireId,
            int valueBits) {
        requireUid(uid);
        if (index < 0 || index > 1) {
            throw new IllegalArgumentException("Parameter index must be 0 or 1");
        }
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
        frame.putInt(tag);
        frame.putInt(PARAMETER_BLOB_SIZE);
        frame.putInt(index);
        frame.putInt(wireId);
        frame.putInt(valueBits);
        return frame.array();
    }

    /** Validates the empty synchronous reply emitted for a SetP request. */
    public static void parseSetReply(byte[] frame, int expectedUid)
            throws ProtocolException {
        requireUid(expectedUid);
        if (frame == null || frame.length != HEADER_SIZE) {
            throw new ProtocolException(
                    "SetP acknowledgement is not eight bytes");
        }
        ByteBuffer reply = ByteBuffer.wrap(frame).order(ByteOrder.LITTLE_ENDIAN);
        if (Short.toUnsignedInt(reply.getShort()) != HEADER_SIZE) {
            throw new ProtocolException(
                    "SetP acknowledgement length is invalid");
        }
        if (Byte.toUnsignedInt(reply.get()) != 0x01) {
            throw new ProtocolException("Unsupported protocol version");
        }
        if (Byte.toUnsignedInt(reply.get()) != 0x81) {
            throw new ProtocolException(
                    "SetP acknowledgement has the wrong direction");
        }
        if (Byte.toUnsignedInt(reply.get()) != expectedUid) {
            throw new ProtocolException(
                    "SetP acknowledgement UID does not match the write");
        }
        if (Byte.toUnsignedInt(reply.get()) != 0) {
            throw new ProtocolException(
                    "SetP acknowledgement reports an error");
        }
        if (Short.toUnsignedInt(reply.getShort()) != 0) {
            throw new ProtocolException(
                    "SetP acknowledgement reserved field is nonzero");
        }
    }

    /** Compatibility name retained for the original physical mute probe. */
    public static void parseInput2MuteReply(byte[] frame, int expectedUid)
            throws ProtocolException {
        parseSetReply(frame, expectedUid);
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
        byte[] stateValues = new byte[stateBytes];
        System.arraycopy(frame, STATE_VALUES_OFFSET, stateValues, 0, stateBytes);
        return new StateReply(
                uid,
                frame.length,
                stateSlotCount,
                input2Muted,
                stateValues);
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
        private final byte[] stateValues;

        StateReply(
                int uid,
                int responseLength,
                int stateSlotCount,
                boolean input2Muted,
                byte[] stateValues) {
            this.uid = uid;
            this.responseLength = responseLength;
            this.stateSlotCount = stateSlotCount;
            this.input2Muted = input2Muted;
            this.stateValues = stateValues.clone();
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

        public float floatSlot(int index) {
            requireSlot(index);
            return ByteBuffer.wrap(stateValues)
                    .order(ByteOrder.LITTLE_ENDIAN)
                    .getFloat(index * 4);
        }

        public int intSlot(int index) {
            requireSlot(index);
            return ByteBuffer.wrap(stateValues)
                    .order(ByteOrder.LITTLE_ENDIAN)
                    .getInt(index * 4);
        }

        private void requireSlot(int index) {
            if (index < 0 || index >= stateSlotCount) {
                throw new IllegalArgumentException(
                        "State slot must be 0.." + (stateSlotCount - 1));
            }
        }
    }

    public static final class ProtocolException extends Exception {
        ProtocolException(String message) {
            super(message);
        }
    }
}
