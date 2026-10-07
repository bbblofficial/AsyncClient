#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OryvexClient Fixer
Sets up everything so the GitHub Actions ZIP contains the full Minecraft.
Run from project root:  python fixer.py
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# ===========================================================================
# 1. launcher.py — uses bundled mc-data/, no downloads
# ===========================================================================

LAUNCHER_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OryvexClient Launcher (offline, bundled)."""
import os
import platform
import shutil
import subprocess
import sys
import zipfile

VERSION = "1.8.8"
FORGE_VERSION = "1.8.8-11.15.0.1655"

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


def extract_natives():
    os.makedirs(NATIVES, exist_ok=True)
    count = 0
    for root, _, files in os.walk(LIBS):
        for f in files:
            if not f.endswith(".jar"):
                continue
            jar = os.path.join(root, f)
            try:
                with zipfile.ZipFile(jar) as z:
                    for name in z.namelist():
                        if name.endswith((".dll", ".so", ".dylib", ".jnilib")):
                            target = os.path.join(NATIVES, os.path.basename(name))
                            if not os.path.exists(target):
                                with z.open(name) as src, open(target, "wb") as dst:
                                    shutil.copyfileobj(src, dst)
                                count += 1
            except zipfile.BadZipFile:
                pass
    if count:
        log(f"Extracted {count} native files.")


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


def launch():
    client_jar = os.path.join(VERSIONS, VERSION, f"{VERSION}.jar")
    forge_jar = os.path.join(LIBS, "net", "minecraftforge", "forge",
                             FORGE_VERSION, f"forge-{FORGE_VERSION}-universal.jar")

    if not os.path.exists(client_jar):
        raise RuntimeError(f"Missing {client_jar}. Re-extract the ZIP.")
    if not os.path.exists(forge_jar):
        raise RuntimeError(f"Missing {forge_jar}. Re-extract the ZIP.")

    extract_natives()

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


if __name__ == "__main__":
    try:
        launch()
    except Exception as e:
        log(f"ERROR: {e}")
        if platform.system() == "Windows":
            input("Press Enter to exit ...")
        sys.exit(1)
'''

# ===========================================================================
# 2. start.bat
# ===========================================================================

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
pause
exit /b 1
'''

# ===========================================================================
# 3. download_mc.py — runs in CI, fills dist/mc-data/
# ===========================================================================

DOWNLOAD_MC_PY = r'''#!/usr/bin/env python3
"""
Download Minecraft 1.8.8 + Forge + libraries + assets into a target directory.
Usage: python download_mc.py <target_dir>
"""
import hashlib
import json
import os
import platform
import sys
import urllib.request

VERSION = "1.8.8"
FORGE_VERSION = "1.8.8-11.15.0.1655"
FORGE_UNIVERSAL_URL = (
    f"https://maven.minecraftforge.net/net/minecraftforge/forge/"
    f"{FORGE_VERSION}/forge-{FORGE_VERSION}-universal.jar"
)
MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
RESOURCES_URL = "https://resources.download.minecraft.net"


def log(msg):
    print(f"[dl] {msg}", flush=True)


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
    urllib.request.urlretrieve(url, tmp)
    if sha1 and sha1_file(tmp) != sha1:
        os.remove(tmp)
        raise RuntimeError(f"SHA1 mismatch: {url}")
    if os.path.exists(dest):
        os.remove(dest)
    os.rename(tmp, dest)


def http_json(url):
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read().decode("utf-8"))


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


def main(target):
    libs = os.path.join(target, "libraries")
    assets = os.path.join(target, "assets")
    versions = os.path.join(target, "versions")

    log("Fetching version manifest ...")
    manifest = http_json(MANIFEST_URL)
    version_url = next(v["url"] for v in manifest["versions"] if v["id"] == VERSION)
    vjson = http_json(version_url)

    # --- client.jar ---
    client = vjson["downloads"]["client"]
    client_dest = os.path.join(versions, VERSION, f"{VERSION}.jar")
    log("Downloading client.jar ...")
    download(client["url"], client_dest, client.get("sha1"))

    # --- libraries (artifact + natives for all OSes) ---
    log("Downloading libraries ...")
    for lib in vjson["libraries"]:
        downloads = lib.get("downloads", {})
        artifact = downloads.get("artifact")
        if artifact:
            rel = maven_to_path(lib["name"])
            download(artifact["url"], os.path.join(libs, rel), artifact.get("sha1"))
        classifiers = downloads.get("classifiers", {})
        natives = lib.get("natives", {})
        for os_key in set(natives.values()):
            if os_key in classifiers:
                cls = classifiers[os_key]
                rel = maven_to_path(lib["name"] + ":" + os_key)
                download(cls["url"], os.path.join(libs, rel), cls.get("sha1"))

    # --- Forge ---
    log("Downloading Forge universal ...")
    forge_dest = os.path.join(libs, "net", "minecraftforge", "forge",
                              FORGE_VERSION, f"forge-{FORGE_VERSION}-universal.jar")
    download(FORGE_UNIVERSAL_URL, forge_dest)

    # --- assets ---
    asset_index = vjson.get("assetIndex")
    if asset_index:
        index_path = os.path.join(assets, "indexes", asset_index["id"] + ".json")
        log(f"Downloading asset index {asset_index['id']} ...")
        download(asset_index["url"], index_path, asset_index.get("sha1"))
        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)
        total = len(index["objects"])
        log(f"Downloading {total} assets ...")
        done = 0
        skipped = 0
        for name, obj in index["objects"].items():
            h = obj["hash"]
            prefix = h[:2]
            dest = os.path.join(assets, "objects", prefix, h)
            if os.path.exists(dest):
                skipped += 1
                continue
            url = f"{RESOURCES_URL}/{prefix}/{h}"
            try:
                download(url, dest, h)
                done += 1
            except Exception as e:
                log(f"  ! {name}: {e}")
            if (done + skipped) % 200 == 0:
                log(f"  ... {done + skipped}/{total}")
        log(f"Assets: {done} new, {skipped} cached.")

    log("Done.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python download_mc.py <target_dir>")
        sys.exit(1)
    main(sys.argv[1])
'''

# ===========================================================================
# 4. .github/workflows/build.yml
# ===========================================================================

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

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Download Minecraft 1.8.8 + Forge + assets
        run: |
          mkdir -p dist
          python3 download_mc.py dist/mc-data

      - name: Package
        run: |
          mkdir -p dist/mods
          JAR=$(ls build/libs/*.jar | grep -v -e sources -e dev | head -n 1)
          echo "Using $JAR"
          cp "$JAR" dist/mods/OryvexClient.jar
          cp start.bat dist/start.bat
          cp launcher.py dist/launcher.py
          echo "--- dist size ---"
          du -sh dist
          du -sh dist/mc-data/*

      - name: Create ZIP
        run: |
          cd dist
          zip -r -q ../OryvexClient.zip .
          cd ..
          ls -lh OryvexClient.zip

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: OryvexClient
          path: OryvexClient.zip
          compression-level: 0
          retention-days: 7
'''

GITIGNORE_ADDITIONS = """
# OryvexClient build artifacts
mc-data/
mods/
dist/
"""


# ===========================================================================
# Helpers
# ===========================================================================

def write(path, content, is_bat=False):
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)
        print(f"  backup {backup.relative_to(ROOT)}")
    if is_bat:
        content = content.replace("\r\n", "\n").replace("\n", "\r\n")
    path.write_text(content, encoding="utf-8", newline="")
    print(f"  write  {path.relative_to(ROOT)}  ({len(content)} bytes)")


def append_once(path, marker, content):
    path = path.resolve()
    if path.exists():
        existing = path.read_text(encoding="utf-8", errors="ignore")
        if marker in existing:
            print(f"  skip   {path.relative_to(ROOT)} (already patched)")
            return
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(content)
    print(f"  patch  {path.relative_to(ROOT)}")


def main():
    print("OryvexClient Fixer")
    print(f"Project root: {ROOT}\n")

    print("[1/5] launcher.py")
    write(ROOT / "launcher.py", LAUNCHER_PY)

    print("[2/5] start.bat")
    write(ROOT / "start.bat", START_BAT, is_bat=True)

    print("[3/5] download_mc.py")
    write(ROOT / "download_mc.py", DOWNLOAD_MC_PY)

    print("[4/5] .github/workflows/build.yml")
    write(ROOT / ".github" / "workflows" / "build.yml", WORKFLOW_YML)

    print("[5/5] .gitignore")
    append_once(ROOT / ".gitignore", "mc-data/", GITIGNORE_ADDITIONS)

    print("\nDone.")
    print("\nNext:")
    print("  git add .")
    print('  git commit -m "bundle minecraft into artifact"')
    print("  git push")
    print("\nThen Actions -> download OryvexClient.zip (~150-200 MB)")


if __name__ == "__main__":
    main()