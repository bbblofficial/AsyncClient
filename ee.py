#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OryvexClient Fixer
Creates/updates start.bat, launcher.py, and .github/workflows/build.yml
Run from project root:  python fixer.py
"""
import os
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# ---------------------------------------------------------------------------
# File contents
# ---------------------------------------------------------------------------

LAUNCHER_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OryvexClient Launcher
Downloads Minecraft 1.8.8 + Forge + libraries + assets, then launches the game.
"""
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile

VERSION = "1.8.8"
FORGE_VERSION = "1.8.8-11.15.0.1655"
FORGE_UNIVERSAL_URL = (
    f"https://maven.minecraftforge.net/net/minecraftforge/forge/"
    f"{FORGE_VERSION}/forge-{FORGE_VERSION}-universal.jar"
)
MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
RESOURCES_URL = "https://resources.download.minecraft.net"

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "mc-data")
LIBS = os.path.join(DATA, "libraries")
ASSETS = os.path.join(DATA, "assets")
VERSIONS = os.path.join(DATA, "versions")
NATIVES = os.path.join(DATA, "natives")
MODS = os.path.join(ROOT, "mods")

USERNAME = "Player"
UUID = "00000000000000000000000000000000"
ACCESS_TOKEN = "0"


def log(msg):
    print(f"[Oryvex] {msg}", flush=True)


def sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest, sha1=None):
    if os.path.exists(dest) and sha1 and sha1_file(dest) == sha1:
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    log(f"Downloading {os.path.basename(dest)} ...")
    try:
        urllib.request.urlretrieve(url, tmp)
    except Exception as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise RuntimeError(f"Failed to download {url}: {e}")
    if sha1 and sha1_file(tmp) != sha1:
        os.remove(tmp)
        raise RuntimeError(f"SHA1 mismatch for {url}")
    if os.path.exists(dest):
        os.remove(dest)
    os.rename(tmp, dest)


def http_json(url):
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read().decode("utf-8"))


def get_version_json():
    log("Fetching version manifest ...")
    manifest = http_json(MANIFEST_URL)
    url = None
    for v in manifest["versions"]:
        if v["id"] == VERSION:
            url = v["url"]
            break
    if not url:
        raise RuntimeError(f"Minecraft {VERSION} not found in manifest")
    log("Fetching version JSON ...")
    return http_json(url)


def rules_allow(rules):
    if not rules:
        return True
    os_name = {"Windows": "windows", "Linux": "linux", "Darwin": "osx"}.get(
        platform.system(), "windows"
    )
    allowed = False
    for rule in rules:
        action = rule.get("action")
        r_os = rule.get("os", {}).get("name")
        if r_os is None or r_os == os_name:
            allowed = (action == "allow")
    return allowed


def maven_to_path(name):
    parts = name.split(":")
    group, artifact, version = parts[0], parts[1], parts[2]
    classifier = parts[3] if len(parts) > 3 else None
    ext = parts[4] if len(parts) > 4 else "jar"
    filename = f"{artifact}-{version}"
    if classifier:
        filename += f"-{classifier}"
    filename += f".{ext}"
    return "/".join(group.split(".")) + f"/{artifact}/{version}/{filename}"


def extract_natives(jar_path):
    os.makedirs(NATIVES, exist_ok=True)
    with zipfile.ZipFile(jar_path) as z:
        for name in z.namelist():
            if name.endswith((".dll", ".so", ".dylib", ".jnilib")):
                target = os.path.join(NATIVES, os.path.basename(name))
                if not os.path.exists(target):
                    with z.open(name) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)


def install_libraries(version_json):
    log("Installing libraries ...")
    os_name = {"Windows": "windows", "Linux": "linux", "Darwin": "osx"}.get(
        platform.system(), "windows"
    )
    for lib in version_json["libraries"]:
        if not rules_allow(lib.get("rules")):
            continue
        downloads = lib.get("downloads", {})
        artifact = downloads.get("artifact")
        if artifact:
            rel = maven_to_path(lib["name"])
            dest = os.path.join(LIBS, rel)
            download(artifact["url"], dest, artifact.get("sha1"))
        classifiers = downloads.get("classifiers", {})
        natives = lib.get("natives", {})
        native_key = natives.get(os_name)
        if native_key and native_key in classifiers:
            cls = classifiers[native_key]
            rel = maven_to_path(lib["name"] + ":" + native_key)
            dest = os.path.join(LIBS, rel)
            download(cls["url"], dest, cls.get("sha1"))
            extract_natives(dest)


def install_assets(version_json):
    asset_index = version_json.get("assetIndex")
    if not asset_index:
        log("No asset index, skipping assets.")
        return
    index_path = os.path.join(ASSETS, "indexes", asset_index["id"] + ".json")
    download(asset_index["url"], index_path, asset_index.get("sha1"))
    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)
    log(f"Downloading {len(index['objects'])} assets ...")
    count = 0
    for name, obj in index["objects"].items():
        h = obj["hash"]
        prefix = h[:2]
        dest = os.path.join(ASSETS, "objects", prefix, h)
        if os.path.exists(dest):
            continue
        url = f"{RESOURCES_URL}/{prefix}/{h}"
        try:
            download(url, dest, h)
            count += 1
        except Exception as e:
            log(f"  ! Failed asset {name}: {e}")
    log(f"Assets ready ({count} new files).")


def install_client_jar(version_json):
    client = version_json["downloads"]["client"]
    dest = os.path.join(VERSIONS, VERSION, f"{VERSION}.jar")
    download(client["url"], dest, client.get("sha1"))
    return dest


def install_forge():
    dest = os.path.join(LIBS, "net", "minecraftforge", "forge",
                        FORGE_VERSION, f"forge-{FORGE_VERSION}-universal.jar")
    download(FORGE_UNIVERSAL_URL, dest)
    return dest


def build_classpath(client_jar, forge_jar):
    entries = [client_jar, forge_jar]
    for root, _, files in os.walk(LIBS):
        for f in files:
            if f.endswith(".jar"):
                entries.append(os.path.join(root, f))
    if os.path.isdir(MODS):
        for f in os.listdir(MODS):
            if f.endswith(".jar"):
                entries.append(os.path.join(MODS, f))
    sep = ";" if platform.system() == "Windows" else ":"
    return sep.join(entries)


def find_java():
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        java = os.path.join(java_home, "bin",
                            "java.exe" if platform.system() == "Windows" else "java")
        if os.path.exists(java):
            return java
    java = shutil.which("java")
    if java:
        return java
    raise RuntimeError("Java not found. Install Java 8 or newer.")


def launch(client_jar, forge_jar):
    java = find_java()
    cp = build_classpath(client_jar, forge_jar)
    jvm_args = [
        java, "-Xmx2G", "-Xms512M",
        f"-Djava.library.path={NATIVES}",
        f"-Dorg.lwjgl.librarypath={NATIVES}",
        "-Dminecraft.launcher.brand=OryvexClient",
        "-Dminecraft.launcher.version=1.0.0",
        "-cp", cp,
    ]
    game_args = [
        "net.minecraft.launchwrapper.Launch",
        "--username", USERNAME,
        "--version", VERSION,
        "--gameDir", ROOT,
        "--assetsDir", ASSETS,
        "--assetIndex", "1.8",
        "--uuid", UUID,
        "--accessToken", ACCESS_TOKEN,
        "--userProperties", "{}",
        "--userType", "legacy",
        "--tweakClass", "net.minecraftforge.fml.common.launcher.FMLTweaker",
    ]
    log("Launching Minecraft ...")
    try:
        subprocess.run(jvm_args + game_args, cwd=ROOT)
    except KeyboardInterrupt:
        pass


def main():
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(MODS, exist_ok=True)
    version_json = get_version_json()
    client_jar = os.path.join(VERSIONS, VERSION, f"{VERSION}.jar")
    if not os.path.exists(client_jar):
        client_jar = install_client_jar(version_json)
    install_libraries(version_json)
    if not os.path.exists(os.path.join(ASSETS, "indexes", "1.8.json")):
        install_assets(version_json)
    forge_jar = os.path.join(LIBS, "net", "minecraftforge", "forge",
                             FORGE_VERSION, f"forge-{FORGE_VERSION}-universal.jar")
    if not os.path.exists(forge_jar):
        forge_jar = install_forge()
    launch(client_jar, forge_jar)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"ERROR: {e}")
        if platform.system() == "Windows":
            input("Press Enter to exit ...")
        sys.exit(1)
'''

START_BAT = r'''@echo off
setlocal
title OryvexClient Launcher
cd /d "%~dp0"

echo ==========================================
echo    OryvexClient  -  Minecraft 1.8.8
echo ==========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 goto nopython
    set "PY=py"
) else (
    set "PY=python"
)

"%PY%" launcher.py
if errorlevel 1 (
    echo.
    echo Launcher exited with an error.
    pause
)
exit /b 0

:nopython
echo Python 3 is required but was not found.
echo Download it from https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during install.
pause
exit /b 1
'''

WORKFLOW_YML = r'''name: Build OryvexClient

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 8
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: 8

      - name: Cache Gradle
        uses: actions/cache@v4
        with:
          path: |
            ~/.gradle/caches
            ~/.gradle/wrapper
          key: gradle-${{ hashFiles('build.gradle') }}

      - name: Install Gradle 2.14.1
        run: |
          wget -q https://services.gradle.org/distributions/gradle-2.14.1-bin.zip
          unzip -q gradle-2.14.1-bin.zip -d "$HOME"

      - name: Build mod
        run: $HOME/gradle-2.14.1/bin/gradle setupCIWorkspace build --no-daemon --stacktrace

      - name: Package
        run: |
          mkdir -p dist/mods
          JAR=$(ls build/libs/*.jar | grep -v -e sources -e dev | head -n 1)
          echo "Using $JAR"
          cp "$JAR" dist/mods/OryvexClient.jar
          cp start.bat dist/start.bat
          cp launcher.py dist/launcher.py
          ls -lh dist dist/mods

      - name: Create ZIP
        run: |
          cd dist
          zip -r ../OryvexClient.zip .
          cd ..
          ls -lh OryvexClient.zip

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: OryvexClient
          path: OryvexClient.zip
'''

GITIGNORE_ADDITIONS = """
# OryvexClient launcher data
mc-data/
mods/
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write(path: Path, content: str, force: bool = True):
    """Write content to path, backing up existing file."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        print(f"  skip  {path.relative_to(ROOT)} (exists)")
        return
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)
        print(f"  backup {backup.relative_to(ROOT)}")
    # normalize line endings to \r\n for bat, \n for others
    if path.suffix == ".bat":
        content = content.replace("\r\n", "\n").replace("\n", "\r\n")
    path.write_text(content, encoding="utf-8", newline="")
    print(f"  write  {path.relative_to(ROOT)} ({len(content)} bytes)")


def append_once(path: Path, marker: str, content: str):
    """Append content to file only if marker not already present."""
    path = path.resolve()
    if path.exists():
        existing = path.read_text(encoding="utf-8", errors="ignore")
        if marker in existing:
            print(f"  skip  {path.relative_to(ROOT)} (already patched)")
            return
    else:
        existing = ""
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(content)
    print(f"  patch  {path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"OryvexClient Fixer")
    print(f"Project root: {ROOT}")
    print()

    print("[1/4] Writing launcher.py")
    write(ROOT / "launcher.py", LAUNCHER_PY)

    print("[2/4] Writing start.bat")
    write(ROOT / "start.bat", START_BAT)

    print("[3/4] Writing .github/workflows/build.yml")
    write(ROOT / ".github" / "workflows" / "build.yml", WORKFLOW_YML)

    print("[4/4] Patching .gitignore")
    append_once(ROOT / ".gitignore", "mc-data/", GITIGNORE_ADDITIONS)

    print()
    print("Done.")
    print()
    print("Next steps:")
    print("  1. git add .")
    print('  2. git commit -m "feat: python launcher + fixed workflow"')
    print("  3. git push")
    print("  4. Download OryvexClient.zip from Actions")
    print()
    print("To test locally (Windows):")
    print("  start.bat")
    print("To test locally (Linux/Mac):")
    print("  python3 launcher.py")


if __name__ == "__main__":
    main()