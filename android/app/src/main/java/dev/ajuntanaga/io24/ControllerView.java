package dev.ajuntanaga.io24;

import android.view.View;

/** One state-rendered destination in the controller shell. */
interface ControllerView {
    View view();

    void render(Io24State state);
}
