package dev.ajuntanaga.io24;

/** Immutable summary of one successful io24 state read. */
public final class ProbeResult {
    private final int protocolVersion;
    private final int maxCommandLength;
    private final int maxResponseLength;
    private final int responseLength;
    private final int stateSlotCount;
    private final boolean input2Muted;

    ProbeResult(
            int protocolVersion,
            int maxCommandLength,
            int maxResponseLength,
            int responseLength,
            int stateSlotCount,
            boolean input2Muted) {
        this.protocolVersion = protocolVersion;
        this.maxCommandLength = maxCommandLength;
        this.maxResponseLength = maxResponseLength;
        this.responseLength = responseLength;
        this.stateSlotCount = stateSlotCount;
        this.input2Muted = input2Muted;
    }

    public int protocolVersion() {
        return protocolVersion;
    }

    public int maxCommandLength() {
        return maxCommandLength;
    }

    public int maxResponseLength() {
        return maxResponseLength;
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
