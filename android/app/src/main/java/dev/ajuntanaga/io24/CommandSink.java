package dev.ajuntanaga.io24;

/** UI callback that accepts only validated controller commands. */
interface CommandSink {
    void dispatch(Io24Command command);
}
