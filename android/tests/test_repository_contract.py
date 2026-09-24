import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _public_paths():
    values = []
    for line in (ROOT / "PUBLIC_FILES.txt").read_text().splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            values.append(value)
    return values


def _wrapper_properties():
    result = {}
    for line in (
        ROOT / "gradle/wrapper/gradle-wrapper.properties"
    ).read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value.replace("\\:", ":")
    return result


def test_toolchain_lock_matches_every_executable_reference():
    lock = json.loads((ROOT / "toolchain.lock.json").read_text())
    gradle = lock["gradle"]
    wrapper = _wrapper_properties()
    build = (ROOT / "build.gradle.kts").read_text()
    verify = (ROOT / "verify.sh").read_text()
    readme = (ROOT / "README.md").read_text()

    assert wrapper["distributionUrl"] == gradle["url"]
    assert wrapper["distributionSha256Sum"] == gradle["sha256"]
    assert gradle["archive"] in gradle["url"]
    assert (ROOT / "gradle/wrapper/gradle-wrapper.jar").is_file()
    assert hashlib.sha256(
        (ROOT / "gradle/wrapper/gradle-wrapper.jar").read_bytes()
    ).hexdigest() == gradle["wrapper_jar_sha256"]
    assert 'version "%s"' % lock["android_gradle_plugin"] in build
    assert "gradle-%s" % gradle["version"] in verify
    assert "Gradle %s" % gradle["version"] in readme
    assert "Android Gradle Plugin %s" % lock["android_gradle_plugin"] in readme
    assert "build-tools;36.0.0" in lock["android_sdk_packages"]
    assert "Build Tools 36.0.0" in readme
    assert '"build-tools;36.0.0"' in (
        ROOT / ".github/workflows/ci.yml"
    ).read_text()


def test_public_manifest_is_unique_complete_and_bounded():
    paths = _public_paths()

    assert len(paths) == len(set(paths))
    assert paths == sorted(paths)
    assert not [path for path in paths if Path(path).is_absolute()]
    assert not [path for path in paths if ".." in Path(path).parts]
    assert not [path for path in paths if not (ROOT / path).is_file()]
    assert not [
        path for path in paths
        if path.startswith((".gradle/", ".toolchain/", "build/", "app/build/"))
    ]
    for required in (
        ".github/workflows/ci.yml",
        ".github/workflows/codeql.yml",
        "app/src/main/java/dev/ajuntanaga/io24/MainActivity.java",
        "LICENSE",
        "README.md",
        "tests/test_android_contract.py",
    ):
        assert required in paths


def test_public_text_has_no_machine_identity_or_credentials():
    secret = re.compile(
        r"github_pat_[A-Za-z0-9_]+|ghp_[A-Za-z0-9]+|"
        r"BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY"
    )
    text_suffixes = {
        ".java", ".json", ".kts", ".md", ".properties", ".py", ".sh",
        ".xml", ".yml",
    }

    for value in _public_paths():
        path = ROOT / value
        if path.suffix not in text_suffixes and path.name not in {
            ".gitignore", "gradlew", "gradlew.bat", "PUBLIC_FILES.txt"
        }:
            continue
        text = path.read_text(errors="replace")
        assert "/" + "home/" not in text, value
        assert not secret.search(text), value


def test_github_workflows_are_hardware_free_and_sha_pinned():
    workflows = (
        ROOT / ".github/workflows/ci.yml",
        ROOT / ".github/workflows/codeql.yml",
    )
    for workflow in workflows:
        text = workflow.read_text()
        refs = re.findall(r"uses:\s*[^@\s]+@([^\s#]+)", text)
        assert "ubuntu-26.04" in text
        assert refs
        assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in refs)
        assert "adb " not in text
        assert "USB" not in text

    assert "languages: java-kotlin" in workflows[1].read_text()
    dependabot = (ROOT / ".github/dependabot.yml").read_text()
    assert "package-ecosystem: gradle" in dependabot
    assert "package-ecosystem: github-actions" in dependabot


def test_front_facing_docs_credit_oddbear_and_link_the_linux_host():
    readme = (ROOT / "README.md").read_text()

    assert "https://github.com/oddbear/Revelator.io24.Api" in readme
    assert "https://github.com/Ajuntanaga/io24" in readme
    assert "does not need the Linux laptop" in readme
    assert "There is no browser" not in readme
    for filename in ("README.md", "PUBLICATION.md", "CONTRIBUTING.md"):
        assert "—" not in (ROOT / filename).read_text()
