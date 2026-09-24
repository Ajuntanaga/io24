package dev.ajuntanaga.io24;

import android.content.Context;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Atomic app-private scene storage. */
final class PresetStore {
    private final File directory;

    PresetStore(Context context) {
        directory = new File(context.getFilesDir(), "scenes");
    }

    synchronized void save(String name, Io24State state) throws IOException {
        ensureDirectory();
        File target = fileFor(name);
        File temporary = new File(directory, target.getName() + ".new");
        byte[] data = PresetCodec.encode(name, state).getBytes(StandardCharsets.UTF_8);
        try (FileOutputStream output = new FileOutputStream(temporary)) {
            output.write(data);
            output.getFD().sync();
        }
        if (target.exists() && !target.delete()) {
            throw new IOException("Could not replace existing scene");
        }
        if (!temporary.renameTo(target)) {
            throw new IOException("Could not finish saving scene");
        }
    }

    synchronized PresetCodec.Decoded load(String name) throws IOException {
        return PresetCodec.decode(read(fileFor(name)));
    }

    synchronized void delete(String name) throws IOException {
        File target = fileFor(name);
        if (target.exists() && !target.delete()) {
            throw new IOException("Could not delete scene");
        }
    }

    synchronized void rename(String oldName, String newName) throws IOException {
        PresetCodec.Decoded current = load(oldName);
        save(newName, current.state());
        if (!oldName.equals(newName)) {
            delete(oldName);
        }
    }

    synchronized List<String> names() throws IOException {
        if (!directory.exists()) {
            return Collections.emptyList();
        }
        File[] files = directory.listFiles((dir, name) -> name.endsWith(".json"));
        if (files == null) {
            throw new IOException("Could not list saved scenes");
        }
        List<String> names = new ArrayList<>();
        for (File file : files) {
            names.add(PresetCodec.decode(read(file)).name());
        }
        Collections.sort(names, String.CASE_INSENSITIVE_ORDER);
        return names;
    }

    synchronized PresetCodec.Decoded importJson(String json) throws IOException {
        PresetCodec.Decoded decoded = PresetCodec.decode(json);
        save(decoded.name(), decoded.state());
        return decoded;
    }

    private void ensureDirectory() throws IOException {
        if (!directory.exists() && !directory.mkdirs()) {
            throw new IOException("Could not create private scene storage");
        }
    }

    private File fileFor(String name) {
        return new File(directory, digest(name) + ".json");
    }

    private static String read(File file) throws IOException {
        if (!file.isFile() || file.length() > 1_000_000) {
            throw new IOException("Scene file is missing or too large");
        }
        byte[] data = new byte[(int) file.length()];
        try (FileInputStream input = new FileInputStream(file)) {
            int offset = 0;
            while (offset < data.length) {
                int count = input.read(data, offset, data.length - offset);
                if (count < 0) {
                    throw new IOException("Scene file ended early");
                }
                offset += count;
            }
        }
        return new String(data, StandardCharsets.UTF_8);
    }

    private static String digest(String value) {
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder result = new StringBuilder(hash.length * 2);
            for (byte item : hash) {
                result.append(String.format(java.util.Locale.US,
                        "%02x", item & 0xff));
            }
            return result.toString();
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 is unavailable", error);
        }
    }
}
