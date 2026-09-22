package dev.ajuntanaga.io24;

/** Immutable summary of one successful read-only io24 probe. */
public final class ProbeResult {
    private final int protocolVersion;
    private final int maxCommandLength;
    private final int maxResponseLength;
    private final int responseLength;
    private final int stateSlotCount;

    ProbeResult(
            int protocolVersion,
            int maxCommandLength,
            int maxResponseLength,
            int responseLength,
            int stateSlotCount) {
        this.protocolVersion = protocolVersion;
        this.maxCommandLength = maxCommandLength;
        this.maxResponseLength = maxResponseLength;
        this.responseLength = responseLength;
        this.stateSlotCount = stateSlotCount;
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
}
