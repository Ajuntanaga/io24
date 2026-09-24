package dev.ajuntanaga.io24;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

import org.junit.Test;

public final class PresetsViewTest {
    @Test
    public void twoFrontPanelBlocksMapToTheCorrectAbsoluteDeviceSlots() {
        assertEquals(0, PresetsView.deviceSlotIndex(1, 0));
        assertEquals(1, PresetsView.deviceSlotIndex(1, 1));
        assertEquals(2, PresetsView.deviceSlotIndex(2, 0));
        assertEquals(3, PresetsView.deviceSlotIndex(2, 1));

        assertEquals(0, PresetsView.relativeBlockIndex(1, 0));
        assertEquals(1, PresetsView.relativeBlockIndex(1, 1));
        assertEquals(0, PresetsView.relativeBlockIndex(2, 2));
        assertEquals(1, PresetsView.relativeBlockIndex(2, 3));
    }

    @Test
    public void invalidPresetBlockCoordinatesAreRejected() {
        assertThrows(IllegalArgumentException.class,
                () -> PresetsView.deviceSlotIndex(0, 0));
        assertThrows(IllegalArgumentException.class,
                () -> PresetsView.deviceSlotIndex(1, 2));
    }
}
