package dev.ajuntanaga.io24;

/** Immutable result of one serialized controller command. */
public final class CommandResult {
    private final Io24State state;
    private final Io24Command.Proof proof;
    private final String message;

    public CommandResult(
            Io24State state,
            Io24Command.Proof proof,
            String message) {
        if (state == null || proof == null) {
            throw new IllegalArgumentException("State and proof are required");
        }
        this.state = state;
        this.proof = proof;
        this.message = message == null ? "" : message;
    }

    public Io24State state() {
        return state;
    }

    public Io24Command.Proof proof() {
        return proof;
    }

    public String message() {
        return message;
    }
}
