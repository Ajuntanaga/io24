package dev.ajuntanaga.io24;

import android.hardware.usb.UsbConstants;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbEndpoint;
import android.hardware.usb.UsbInterface;
import android.hardware.usb.UsbManager;
import android.os.SystemClock;

import java.io.ByteArrayOutputStream;

/** Owns one explicit, bounded connection to io24 vendor interface 5. */
public final class Io24UsbProbe implements AutoCloseable {
    static final int VENDOR_ID = 0x194f;
    static final int PRODUCT_ID = 0x0422;
    static final int CONTROL_INTERFACE = 5;
    static final int CONTROL_ALTERNATE = 1;
    static final int ENDPOINT_OUT = 0x01;
    static final int ENDPOINT_IN = 0x81;

    private static final int VENDOR_INTERFACE_IN = 0xc1;
    private static final int REQUEST_PROTOCOL_VERSION = 0x00;
    private static final int REQUEST_MAX_LENGTH = 0x01;
    private static final int IO_TIMEOUT_MS = 2_000;
    private static final int RESPONSE_DEADLINE_MS = 1_600;
    private static final int ABSOLUTE_MAX_RESPONSE = 65_536;
    static final int MUTE_SETTLE_MS = 350;

    private final UsbManager usbManager;
    private UsbDeviceConnection connection;
    private UsbInterface claimedInterface;
    private UsbEndpoint endpointOut;
    private UsbEndpoint endpointIn;
    private int maxResponseLength;
    private int nextUid = 1;

    public Io24UsbProbe(UsbManager usbManager) {
        if (usbManager == null) {
            throw new IllegalArgumentException("UsbManager is required");
        }
        this.usbManager = usbManager;
    }

    public static UsbDevice findDevice(UsbManager usbManager) {
        if (usbManager == null) {
            return null;
        }
        for (UsbDevice device : usbManager.getDeviceList().values()) {
            if (matches(device)) {
                return device;
            }
        }
        return null;
    }

    public static boolean matches(UsbDevice device) {
        return device != null
                && device.getVendorId() == VENDOR_ID
                && device.getProductId() == PRODUCT_ID;
    }

    public synchronized ProbeResult connectAndRead(UsbDevice device)
            throws ProbeException {
        if (connection != null) {
            throw new ProbeException("The io24 control interface is already connected");
        }
        if (!matches(device)) {
            throw new ProbeException("The selected USB device is not a Revelator io24");
        }
        if (!usbManager.hasPermission(device)) {
            throw new ProbeException("Android USB permission has not been granted");
        }

        UsbInterface controlInterface = findControlInterface(device);
        UsbEndpoint endpointOut = findEndpoint(controlInterface, ENDPOINT_OUT);
        UsbEndpoint endpointIn = findEndpoint(controlInterface, ENDPOINT_IN);
        UsbDeviceConnection opened = usbManager.openDevice(device);
        if (opened == null) {
            throw new ProbeException("Android could not open the io24");
        }

        boolean claimed = false;
        try {
            claimed = opened.claimInterface(controlInterface, false);
            if (!claimed) {
                throw new ProbeException(
                        "Control interface 5 is unavailable; no driver was detached");
            }
            if (!opened.setInterface(controlInterface)) {
                throw new ProbeException("Could not select control alternate setting 1");
            }

            int protocolVersion = readCapability(
                    opened, REQUEST_PROTOCOL_VERSION, 0, 2);
            int maxCommandLength = readCapability(
                    opened, REQUEST_MAX_LENGTH, 0, 4);
            int maxResponseLength = readCapability(
                    opened, REQUEST_MAX_LENGTH, 1, 4);
            if (protocolVersion != 1) {
                throw new ProbeException(
                        "Unsupported io24 control protocol " + protocolVersion);
            }
            if (maxCommandLength < PaeFrame.STATE_FRAME_SIZE) {
                throw new ProbeException("Device command limit is too small");
            }
            if (maxResponseLength < 36
                    || maxResponseLength > ABSOLUTE_MAX_RESPONSE) {
                throw new ProbeException("Device response limit is invalid");
            }

            int uid = 1;
            byte[] request = PaeFrame.buildStateRead(uid);
            int written = opened.bulkTransfer(
                    endpointOut, request, request.length, IO_TIMEOUT_MS);
            if (written != request.length) {
                throw new ProbeException(
                        "State request was short: " + written + "/" + request.length);
            }
            byte[] response = readOneResponse(
                    opened, endpointIn, maxResponseLength);
            PaeFrame.StateReply state = PaeFrame.parseStateReply(response, uid);

            connection = opened;
            claimedInterface = controlInterface;
            this.endpointOut = endpointOut;
            this.endpointIn = endpointIn;
            this.maxResponseLength = maxResponseLength;
            nextUid = nextUid(uid);
            opened = null;
            claimed = false;
            return new ProbeResult(
                    protocolVersion,
                    maxCommandLength,
                    maxResponseLength,
                    state.responseLength(),
                    state.stateSlotCount(),
                    state.input2Muted());
        } catch (PaeFrame.ProtocolException error) {
            throw new ProbeException(error.getMessage(), error);
        } finally {
            if (opened != null) {
                if (claimed) {
                    opened.releaseInterface(controlInterface);
                }
                opened.close();
            }
        }
    }

    public synchronized boolean isConnected() {
        return connection != null;
    }

    /**
     * Changes only Input 2 mute, waits at the old state boundary, then confirms
     * the result with a fresh full-state read.
     */
    public synchronized boolean setInput2Mute(boolean muted) throws ProbeException {
        if (connection == null || endpointOut == null || endpointIn == null) {
            throw new ProbeException("The io24 control interface is not connected");
        }

        int writeUid = claimUid();
        byte[] write = PaeFrame.buildInput2MuteWrite(writeUid, muted);
        writeFrame(connection, endpointOut, write, "Input 2 mute write");

        SystemClock.sleep(MUTE_SETTLE_MS);

        int readUid = claimUid();
        byte[] request = PaeFrame.buildStateRead(readUid);
        writeFrame(connection, endpointOut, request, "State verification request");
        byte[] response = readOneResponse(
                connection, endpointIn, maxResponseLength);
        try {
            PaeFrame.StateReply state = PaeFrame.parseStateReply(response, readUid);
            if (state.input2Muted() != muted) {
                throw new ProbeException(
                        "Fresh device state did not confirm the requested value");
            }
            return state.input2Muted();
        } catch (PaeFrame.ProtocolException error) {
            throw new ProbeException(error.getMessage(), error);
        }
    }

    @Override
    public synchronized void close() {
        if (connection == null) {
            return;
        }
        if (claimedInterface != null) {
            connection.releaseInterface(claimedInterface);
        }
        connection.close();
        connection = null;
        claimedInterface = null;
        endpointOut = null;
        endpointIn = null;
        maxResponseLength = 0;
        nextUid = 1;
    }

    private static UsbInterface findControlInterface(UsbDevice device)
            throws ProbeException {
        for (int index = 0; index < device.getInterfaceCount(); index++) {
            UsbInterface candidate = device.getInterface(index);
            if (candidate.getId() == CONTROL_INTERFACE
                    && candidate.getAlternateSetting() == CONTROL_ALTERNATE) {
                return candidate;
            }
        }
        throw new ProbeException("Control interface 5 alternate 1 was not found");
    }

    private static UsbEndpoint findEndpoint(UsbInterface controlInterface, int address)
            throws ProbeException {
        for (int index = 0; index < controlInterface.getEndpointCount(); index++) {
            UsbEndpoint candidate = controlInterface.getEndpoint(index);
            if (candidate.getAddress() == address
                    && candidate.getType() == UsbConstants.USB_ENDPOINT_XFER_BULK) {
                return candidate;
            }
        }
        throw new ProbeException(
                String.format("Bulk endpoint 0x%02x was not found", address));
    }

    private static int readCapability(
            UsbDeviceConnection connection,
            int request,
            int value,
            int length) throws ProbeException {
        byte[] buffer = new byte[length];
        int received = connection.controlTransfer(
                VENDOR_INTERFACE_IN,
                request,
                value,
                CONTROL_INTERFACE,
                buffer,
                length,
                IO_TIMEOUT_MS);
        if (received != length) {
            throw new ProbeException(
                    "Capability query was short: " + received + "/" + length);
        }
        int result = 0;
        for (int index = 0; index < length; index++) {
            result |= (buffer[index] & 0xff) << (index * 8);
        }
        return result;
    }

    private int claimUid() {
        int uid = nextUid;
        nextUid = nextUid(uid);
        return uid;
    }

    private static int nextUid(int uid) {
        return uid == 255 ? 1 : uid + 1;
    }

    private static void writeFrame(
            UsbDeviceConnection connection,
            UsbEndpoint endpointOut,
            byte[] frame,
            String label) throws ProbeException {
        int written = connection.bulkTransfer(
                endpointOut, frame, frame.length, IO_TIMEOUT_MS);
        if (written != frame.length) {
            throw new ProbeException(
                    label + " was short: " + written + "/" + frame.length);
        }
    }

    private static byte[] readOneResponse(
            UsbDeviceConnection connection,
            UsbEndpoint endpointIn,
            int maxResponseLength) throws ProbeException {
        ByteArrayOutputStream response = new ByteArrayOutputStream(maxResponseLength);
        byte[] chunk = new byte[Math.min(maxResponseLength, 2_048)];
        int expectedLength = -1;
        long deadline = SystemClock.elapsedRealtime() + RESPONSE_DEADLINE_MS;

        while (SystemClock.elapsedRealtime() < deadline) {
            int available = maxResponseLength - response.size();
            if (available <= 0) {
                throw new ProbeException("State reply filled the response limit");
            }
            int remaining = expectedLength > 0
                    ? expectedLength - response.size()
                    : available;
            if (remaining == 0) {
                break;
            }
            int timeout = (int) Math.max(
                    1, deadline - SystemClock.elapsedRealtime());
            int received = connection.bulkTransfer(
                    endpointIn,
                    chunk,
                    0,
                    Math.min(chunk.length, Math.min(remaining, available)),
                    timeout);
            if (received <= 0) {
                throw new ProbeException("Timed out waiting for the state reply");
            }
            response.write(chunk, 0, received);
            byte[] accumulated = response.toByteArray();
            if (expectedLength < 0 && accumulated.length >= 2) {
                expectedLength = (accumulated[0] & 0xff)
                        | ((accumulated[1] & 0xff) << 8);
                if (expectedLength < 8 || expectedLength > maxResponseLength) {
                    throw new ProbeException("State reply declares an invalid length");
                }
            }
            if (expectedLength > 0 && accumulated.length > expectedLength) {
                throw new ProbeException("State reply exceeded its declared length");
            }
            if (expectedLength > 0 && accumulated.length == expectedLength) {
                return accumulated;
            }
        }
        throw new ProbeException("State reply ended before its declared length");
    }

    public static final class ProbeException extends Exception {
        ProbeException(String message) {
            super(message);
        }

        ProbeException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
