import os
import pathlib
import re
import subprocess
import tempfile
import unittest
from urllib.parse import unquote, urlparse


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLIC_DOCS = (
    "README.md",
    "GUIDE.md",
    "PROTOCOL.md",
    "PUBLICATION.md",
    "CONTRIBUTING.md",
)
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def prose_without_fences(text):
    lines = []
    fence = None
    for line in text.splitlines():
        marker = line.lstrip()[:3]
        if marker in ("```", "~~~"):
            fence = None if fence == marker else marker
            continue
        if fence is None:
            lines.append(line)
    return "\n".join(lines)


class PublicationDocumentationTests(unittest.TestCase):
    def test_local_markdown_links_resolve(self):
        missing = []
        for filename in PUBLIC_DOCS:
            document = ROOT / filename
            text = prose_without_fences(document.read_text())
            for match in LINK.finditer(text):
                raw = match.group(1).strip()
                if raw.startswith("<") and raw.endswith(">"):
                    raw = raw[1:-1]
                raw = raw.split()[0]
                parsed = urlparse(raw)
                if not raw or raw.startswith("#") or parsed.scheme:
                    continue
                target = unquote(raw.split("#", 1)[0])
                if target and not (document.parent / target).exists():
                    line = text.count("\n", 0, match.start()) + 1
                    missing.append("%s:%d -> %s" % (filename, line, target))
        self.assertEqual(missing, [])

    def test_user_guides_describe_current_preset_and_voicefx_ui(self):
        readme = (ROOT / "README.md").read_text()
        guide = (ROOT / "GUIDE.md").read_text()

        for stale in (
                "stores a firmware-native Fat Channel candidate in either device block",
                "device-slots.json`) with status",
                "replace the LICENSE file with MIT",
                "project is useless without them"):
            self.assertNotIn(stale, readme)
        self.assertIn("device-presets.json", readme)
        self.assertIn("MemP/PrsM", readme)
        self.assertNotIn("**FX Model** row", guide)
        self.assertIn("**Model** row", guide)
        self.assertIn("**Voice FX input**", guide)
        self.assertIn("processingChannel", guide)
        self.assertIn("does not display a permanently disabled control", guide)
        self.assertIn("The io24's hardware Delay is never selected at 96 kHz",
                      readme)
        self.assertIn("Host processing at 96 kHz", (ROOT / "io24gtk.py").read_text())
        self.assertIn("USB 1-2", guide)
        self.assertNotIn("must expose all\nsix playback channels", guide)

    def test_github_facing_copy_is_plain_and_credits_prior_work(self):
        readme = (ROOT / "README.md").read_text()
        front_facing = ("README.md", "GUIDE.md", "PUBLICATION.md",
                        "CONTRIBUTING.md")

        self.assertIn(
            "https://github.com/oddbear/Revelator.io24.Api", readme)
        self.assertIn("There is no browser or phone", readme)
        for filename in front_facing:
            with self.subTest(filename=filename):
                self.assertNotIn("—", (ROOT / filename).read_text())

    def test_protocol_current_questions_do_not_repeat_superseded_fx_claim(self):
        protocol = (ROOT / "PROTOCOL.md").read_text()
        current = protocol.split("## 10. Current open questions", 1)[1].split(
            "## 11. References", 1)[0]

        self.assertIn("all six models", current.lower())
        self.assertIn("physical Input 1", current)
        self.assertNotIn("Block 201 (insert FX) does not respond at all", current)
        self.assertNotIn("autogainmode", current)

    def test_public_docs_do_not_expose_local_identity(self):
        for filename in PUBLIC_DOCS:
            text = (ROOT / filename).read_text()
            with self.subTest(filename=filename):
                self.assertNotIn("/home/", text)
                self.assertIsNone(re.search(
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
                    text,
                ))

    def test_publication_boundary_is_explicit(self):
        publication = (ROOT / "PUBLICATION.md").read_text()
        self.assertIn("fresh-history clean source import", publication)
        self.assertIn("re/uc_factory_presets.json", publication)
        self.assertIn("None of it is included", publication)
        self.assertIn("never a CI requirement", publication)
        self.assertIn("Ajuntanaga/io24", publication)

    def test_release_metadata_targets_intended_github_repository(self):
        metadata = (ROOT / "pyproject.toml").read_text()
        base = "https://github.com/Ajuntanaga/io24"

        self.assertIn("[project.urls]", metadata)
        self.assertIn('Homepage = "%s"' % base, metadata)
        self.assertIn('Repository = "%s"' % base, metadata)
        self.assertIn('Documentation = "%s#readme"' % base, metadata)
        self.assertIn('Issues = "%s/issues"' % base, metadata)
        self.assertIn(
            'description = "Native Linux control host for the PreSonus '
            'Revelator io24"', metadata)

    def test_public_release_has_no_browser_control_surface(self):
        self.assertFalse((ROOT / "io24web.py").exists())

        metadata = (ROOT / "pyproject.toml").read_text()
        self.assertNotIn("io24-web", metadata)
        self.assertNotIn("io24web", metadata)

        for filename in PUBLIC_DOCS:
            with self.subTest(filename=filename):
                self.assertNotIn(
                    "io24web", (ROOT / filename).read_text().lower())

    def test_debian_setup_uses_a_project_venv_and_lists_host_dependencies(self):
        readme = (ROOT / "README.md").read_text()
        contributing = (ROOT / "CONTRIBUTING.md").read_text()
        publication = (ROOT / "PUBLICATION.md").read_text()

        for package in (
                "build-essential", "pipewire-bin", "wireplumber",
                "python3-venv"):
            self.assertIn(package, readme)
        self.assertIn(
            "python3 -m venv --system-site-packages .venv", readme)
        self.assertIn(".venv/bin/python -m pip install .", readme)
        self.assertIn(".venv/bin/io24-mixer", readme)
        self.assertIn(".venv/bin/io24 status", readme)
        self.assertNotIn("\npython3 -m pip install .\n", readme)
        for document in (contributing, publication):
            self.assertIn(
                "python3 -m venv --system-site-packages .venv", document)
            self.assertIn(".venv/bin/python -m pip", document)

    def test_desktop_launcher_prefers_checkout_venv_then_system_python(self):
        source = (ROOT / "io24-mixer").read_text()

        with tempfile.TemporaryDirectory(prefix="io24-launcher-") as temp:
            stage = pathlib.Path(temp)
            app = stage / "project with spaces | pipe"
            app.mkdir()
            (app / "io24gtk.py").write_text("# test target\n")
            launcher = stage / "io24-mixer"
            launcher.write_text(source.replace("__APP_DIR__", str(app)))
            launcher.chmod(0o755)

            fallback_bin = stage / "fallback"
            fallback_bin.mkdir()
            fallback = fallback_bin / "python3"
            fallback.write_text(
                "#!/bin/sh\nprintf 'fallback:%s\\n' \"$*\"\n")
            fallback.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = "%s:%s" % (
                fallback_bin, environment.get("PATH", os.defpath))

            result = subprocess.run(
                [launcher, "--offline"], env=environment, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(
                result.stdout.strip(),
                "fallback:%s --offline" % (app / "io24gtk.py"))

            venv_python = app / ".venv" / "bin" / "python"
            venv_python.parent.mkdir(parents=True)
            venv_python.write_text(
                "#!/bin/sh\nprintf 'venv:%s\\n' \"$*\"\n")
            venv_python.chmod(0o755)

            result = subprocess.run(
                [launcher, "--offline"], env=environment, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(
                result.stdout.strip(),
                "venv:%s --offline" % (app / "io24gtk.py"))


if __name__ == "__main__":
    unittest.main()
