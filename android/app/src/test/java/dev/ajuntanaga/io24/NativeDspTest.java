package dev.ajuntanaga.io24;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThrows;

import java.security.MessageDigest;
import java.util.Arrays;
import java.util.List;

import org.junit.Test;

public final class NativeDspTest {
    @Test
    public void voiceFxDefaultsMatchTheUcDerivedBuilders() throws Exception {
        Io24State state = Io24State.defaults();

        List<byte[]> transformer = NativeDsp.voiceFxMaterialization(
                Io24State.VoiceFxModel.TRANSFORMER,
                state.voiceFx(Io24State.VoiceFxModel.TRANSFORMER),
                48_000);
        assertEquals(5, transformer.size());
        assertDigest("454f632854716e6c718dc2a81fac8f0b3303183b4d2a458d6a3395299ba9c184",
                transformer.get(0));
        assertDigest("209726f219c590831586e9c681181eeaddf1855abe77fcc43de788c6448f01c9",
                transformer.get(2));
        assertDigest("f0396b4b352cf21b5807080246f518a6af61e7a79eee531c3cc115ce4f47622f",
                transformer.get(4));

        assertDigest("879712c7994ab555c49ddae7b67c1a388db89928c38794c57d0579261af45d61",
                materialized(state, Io24State.VoiceFxModel.DETUNER).get(0));
        assertDigest("add0fb3a4bbeb228901719728e1bea994c4f208c1e669635e49eb9f4d9f69853",
                materialized(state, Io24State.VoiceFxModel.DETUNER).get(1));
        assertDigest("5a5ecfac051fb16546067d8450b8f856c503d840788ee6da5df82d5d067b00ac",
                materialized(state, Io24State.VoiceFxModel.VOCODER).get(0));
        assertDigest("2472b5bd614c77731d7dd10102e6755f8a1901a9ba5464be13050d29c56f5f4c",
                materialized(state, Io24State.VoiceFxModel.VOCODER).get(1));
        assertDigest("b4726c6deee9c7e592d01be7812e07446f8b034e0380f5c45867709aed9b989d",
                materialized(state, Io24State.VoiceFxModel.RING_MOD).get(0));
        assertDigest("44a853e68e4db1e22cb3740a12c3953e9811fc8e882b8db92038431360f4bcb9",
                materialized(state, Io24State.VoiceFxModel.FILTERS).get(0));
        assertDigest("0686f288aee658cc1778de1b0161ddc13bffddd17a6750f712d269ba9d8850c0",
                materialized(state, Io24State.VoiceFxModel.DELAY).get(0));
    }

    @Test
    public void sharedReverbMatchesTheProvenBlock202Vector() throws Exception {
        assertDigest("e0b111444e68e7d65974df2cc8a90b0726bf589ef524e9e3d0c9b3f29707c0cc",
                NativeDsp.reverb(Io24State.defaults().reverb(), 48_000));
    }

    @Test
    public void nativeDelayBuilderRejectsBothUnacceptedHighRates() {
        Io24State state = Io24State.defaults();
        for (int rate : new int[] {88_200, 96_000}) {
            assertThrows(IllegalArgumentException.class, () ->
                    NativeDsp.voiceFxMaterialization(
                            Io24State.VoiceFxModel.DELAY,
                            state.voiceFx(Io24State.VoiceFxModel.DELAY),
                            rate));
        }
    }

    @Test
    public void everySharedReverbControlChangesItsNativeBlock202Record() {
        byte[] baseline = NativeDsp.reverb(
                Io24State.defaults().reverb(), 48_000);
        Io24State.ReverbState[] edits = {
                Io24State.defaults().buildUpon()
                        .setReverb(true, 0.5f, 0.3f, 200.0f, 0.02f)
                        .build().reverb(),
                Io24State.defaults().buildUpon()
                        .setReverb(false, 0.8f, 0.3f, 200.0f, 0.02f)
                        .build().reverb(),
                Io24State.defaults().buildUpon()
                        .setReverb(false, 0.5f, 0.7f, 200.0f, 0.02f)
                        .build().reverb(),
                Io24State.defaults().buildUpon()
                        .setReverb(false, 0.5f, 0.3f, 320.0f, 0.02f)
                        .build().reverb(),
                Io24State.defaults().buildUpon()
                        .setReverb(false, 0.5f, 0.3f, 200.0f, 0.06f)
                        .build().reverb(),
        };
        for (Io24State.ReverbState edit : edits) {
            assertFalse(Arrays.equals(
                    baseline, NativeDsp.reverb(edit, 48_000)));
        }
    }

    @Test
    public void standardDynamicsMatchTheUcDerivedBuilders() throws Exception {
        Io24State state = Io24State.defaults();
        assertDigest("c2da4b9032350d827c3f9eae457c1436ae75801a90b194455103fbdb99e44309",
                NativeDsp.gate(state.processing(1), 48_000).get(0));
        assertDigest("d4951a935a34df73d85b7182deda280cd7228ac416d10cbdf5340efa6c617d2c",
                NativeDsp.standardCompressor(state.processing(1)).get(0));
    }

    @Test
    public void standardEqLimiterAndHighPassMatchUcDerivedVectors()
            throws Exception {
        Io24State.Builder builder = Io24State.defaults().buildUpon()
                .setProcessingParameter(1, "eq_on", 1)
                .setProcessingParameter(1, "eq_low_freq", 80)
                .setProcessingParameter(1, "eq_low_gain", 6)
                .setProcessingParameter(1, "eq_lowmid_freq", 400)
                .setProcessingParameter(1, "eq_lowmid_gain", -3)
                .setProcessingParameter(1, "eq_himid_freq", 2500)
                .setProcessingParameter(1, "eq_himid_gain", 4)
                .setProcessingParameter(1, "eq_high_freq", 10000)
                .setProcessingParameter(1, "eq_high_gain", 6)
                .setProcessingParameter(1, "limiter_on", 1)
                .setProcessingParameter(1, "limiter_threshold", -1);
        Io24State state = builder.build();
        List<byte[]> eq = NativeDsp.standardEq(state.processing(1), 48_000);

        assertDigest("0b45da4914b51c77736dd16def37f698609a45d004011c83c180ede0c29bab88",
                eq.get(0));
        assertDigest("72b238a856a66fa2448692761815b91fc2633eee1c97c72ea5bbead38e75751f",
                eq.get(1));
        assertDigest("5d0fef4a404d1a27c5ac39318a29c361168935709c382b94bb5ed405099a45b8",
                eq.get(2));
        assertDigest("2d64ccb8899e6973b75488050edcb2aedbe8d8ff29e578ea8d9fd806c416bda3",
                eq.get(3));
        assertDigest("591e26c745ce313b63e629bcf50add027ffed3a84f55e366e0f9525797818093",
                NativeDsp.limiter(state.processing(1), 48_000).get(0));
        assertDigest("60e5324fb50f944e20abac1e0172164f493b08f100d6cddcaa5516a809828f78",
                NativeDsp.highPassFilter(true, 80, 48_000));
    }

    private static List<byte[]> materialized(
            Io24State state,
            Io24State.VoiceFxModel model) {
        return NativeDsp.voiceFxMaterialization(
                model, state.voiceFx(model), 48_000);
    }

    private static void assertDigest(String expected, byte[] value)
            throws Exception {
        assertEquals(expected, hex(
                MessageDigest.getInstance("SHA-256").digest(value)));
    }

    private static String hex(byte[] value) {
        StringBuilder result = new StringBuilder(value.length * 2);
        for (byte item : value) {
            result.append(String.format("%02x", item & 0xff));
        }
        return result.toString();
    }

}
