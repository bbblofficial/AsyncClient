#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OryvexClient Fixer v3
Small ZIP (~30MB): bundles client.jar + libraries + Forge, NO assets.
Assets are reused from user's .minecraft or downloaded on first run.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# ===========================================================================
# launcher.py — smart asset handling
# ===========================================================================
LAUNCHER_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OryvexClient Launcher (bundled client.jar + Forge, smart assets)."""
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
MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
RESOURCES_URL = "https://resources.download.minecraft.net"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")

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


def _req(url):
    return urllib.request.Request(url, headers={"User-Agent": UA})


def http_json(url):
    with urllib.request.urlopen(_req(url), timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


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
    with urllib.request.urlopen(_req(url), timeout=120) as resp, open(tmp, "wb") as f:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            f.write(chunk)
    if sha1 and sha1_file(tmp) != sha1:
        os.remove(tmp)
        raise RuntimeError(f"SHA1 mismatch: {url}")
    if os.path.exists(dest):
        os.remove(dest)
    os.rename(tmp, dest)


def find_java():
    jh = os.environ.get("JAVA_HOME")
    if jh:
        j = os.path.join(jh, "bin", "java.exe" if platform.system() == "Windows" else "java")
        if os.path.exists(j):
            return j
    j = shutil.which("java")
    if j:
        return j
    raise RuntimeError("Java not found. Install Java 8 or newer.")


def extract_natives():
    os.makedirs(NATIVES, exist_ok=True)
    n = 0
    for root, _, files in os.walk(LIBS):
        for f in files:
            if not f.endswith(".jar"):
                continue
            try:
                with zipfile.ZipFile(os.path.join(root, f)) as z:
                    for name in z.namelist():
                        if name.endswith((".dll", ".so", ".dylib", ".jnilib")):
                            t = os.path.join(NATIVES, os.path.basename(name))
                            if not os.path.exists(t):
                                with z.open(name) as src, open(t, "wb") as dst:
                                    shutil.copyfileobj(src, dst)
                                n += 1
            except zipfile.BadZipFile:
                pass
    if n:
        log(f"Extracted {n} natives.")


def ensure_assets():
    """If assets are missing, try user's .minecraft, then download."""
    index_path = os.path.join(ASSETS, "indexes", "1.8.json")
    if os.path.exists(index_path) and os.path.isdir(os.path.join(ASSETS, "objects")):
        # check it has files
        obj_dir = os.path.join(ASSETS, "objects")
        for _ in os.scandir(obj_dir):
            return  # has something
    # try user's .minecraft
    if platform.system() == "Windows":
        user_mc = os.path.join(os.environ.get("APPDATA", ""), ".minecraft")
    elif platform.system() == "Darwin":
        user_mc = os.path.expanduser("~/Library/Application Support/minecraft")
    else:
        user_mc = os.path.expanduser("~/.minecraft")
    user_assets = os.path.join(user_mc, "assets")
    if os.path.exists(os.path.join(user_assets, "indexes", "1.8.json")):
        log(f"Using existing assets from {user_assets}")
        # create symlink or use as-is via --assetsDir
        return user_assets
    # must download
    log("Assets not found. Downloading (~110MB, first run only) ...")
    manifest = http_json(MANIFEST_URL)
    vurl = next(v["url"] for v in manifest["versions"] if v["id"] == VERSION)
    vjson = http_json(vurl)
    ai = vjson["assetIndex"]
    os.makedirs(os.path.join(ASSETS, "indexes"), exist_ok=True)
    download(ai["url"], index_path, ai.get("sha1"))
    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)
    total = len(index["objects"])
    done = 0
    for name, obj in index["objects"].items():
        h = obj["hash"]
        dest = os.path.join(ASSETS, "objects", h[:2], h)
        if os.path.exists(dest):
            continue
        try:
            download(f"{RESOURCES_URL}/{h[:2]}/{h}", dest, h)
            done += 1
        except Exception as e:
            log(f"  ! {name}: {e}")
        if done % 200 == 0 and done:
            log(f"  ... {done}/{total}")
    log(f"Assets ready ({done} new).")
    return ASSETS


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
    return (";" if platform.system() == "Windows" else ":").join(entries)


def launch():
    client_jar = os.path.join(VERSIONS, VERSION, f"{VERSION}.jar")
    forge_jar = os.path.join(LIBS, "net", "minecraftforge", "forge",
                             FORGE_VERSION, f"forge-{FORGE_VERSION}-universal.jar")
    if not os.path.exists(client_jar):
        raise RuntimeError(f"Missing {client_jar}")
    if not os.path.exists(forge_jar):
        raise RuntimeError(f"Missing {forge_jar}")

    assets_dir = ensure_assets() or ASSETS

    extract_natives()
    java = find_java()
    cp = build_classpath(client_jar, forge_jar)

    jvm = [
        java, "-Xmx2G", "-Xms512M",
        f"-Djava.library.path={NATIVES}",
        f"-Dorg.lwjgl.librarypath={NATIVES}",
        "-Dminecraft.launcher.brand=OryvexClient",
        "-Dminecraft.launcher.version=1.0.0",
        "-cp", cp,
    ]
    game = [
        "net.minecraft.launchwrapper.Launch",
        "--username", USERNAME,
        "--version", VERSION,
        "--gameDir", ROOT,
        "--assetsDir", assets_dir,
        "--assetIndex", "1.8",
        "--uuid", UUID,
        "--accessToken", ACCESS_TOKEN,
        "--userProperties", "{}",
        "--userType", "legacy",
        "--tweakClass", "net.minecraftforge.fml.common.launcher.FMLTweaker",
    ]
    log("Launching Minecraft ...")
    try:
        subprocess.run(jvm + game, cwd=ROOT)
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
# start.bat
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
# download_mc.py — NO assets
# ===========================================================================
DOWNLOAD_MC_PY = r'''#!/usr/bin/env python3
"""Download Minecraft 1.8.8 + Forge + libraries (NO assets)."""
import hashlib
import json
import os
import sys
import urllib.request

VERSION = "1.8.8"
FORGE_VERSION = "1.8.8-11.15.0.1655"
FORGE_URL = (f"https://maven.minecraftforge.net/net/minecraftforge/forge/"
             f"{FORGE_VERSION}/forge-{FORGE_VERSION}-universal.jar")
MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def log(m):
    print(f"[dl] {m}", flush=True)


def sha1_file(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def _req(u):
    return urllib.request.Request(u, headers={"User-Agent": UA})


def download(url, dest, sha1=None):
    if os.path.exists(dest) and sha1 and sha1_file(dest) == sha1:
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    with urllib.request.urlopen(_req(url), timeout=120) as r, open(tmp, "wb") as f:
        while True:
            c = r.read(65536)
            if not c:
                break
            f.write(c)
    if sha1 and sha1_file(tmp) != sha1:
        os.remove(tmp)
        raise RuntimeError(f"SHA1 mismatch: {url}")
    if os.path.exists(dest):
        os.remove(dest)
    os.rename(tmp, dest)


def http_json(u):
    with urllib.request.urlopen(_req(u), timeout=60) as r:
        return json.loads(r.read().decode())


def maven_path(n):
    p = n.split(":")
    g, a, v = p[0], p[1], p[2]
    cls = p[3] if len(p) > 3 else None
    ext = p[4] if len(p) > 4 else "jar"
    fn = f"{a}-{v}" + (f"-{cls}" if cls else "") + f".{ext}"
    return "/".join(g.split(".")) + f"/{a}/{v}/{fn}"


def main(target):
    libs = os.path.join(target, "libraries")
    versions = os.path.join(target, "versions")

    log("Fetching manifest ...")
    m = http_json(MANIFEST_URL)
    vurl = next(v["url"] for v in m["versions"] if v["id"] == VERSION)
    vj = http_json(vurl)

    c = vj["downloads"]["client"]
    log("Downloading client.jar ...")
    download(c["url"], os.path.join(versions, VERSION, f"{VERSION}.jar"), c.get("sha1"))

    log("Downloading libraries ...")
    for lib in vj["libraries"]:
        dl = lib.get("downloads", {})
        if dl.get("artifact"):
            download(dl["artifact"]["url"],
                     os.path.join(libs, maven_path(lib["name"])),
                     dl["artifact"].get("sha1"))
        for k in set(lib.get("natives", {}).values()):
            if k in dl.get("classifiers", {}):
                cl = dl["classifiers"][k]
                download(cl["url"],
                         os.path.join(libs, maven_path(lib["name"] + ":" + k)),
                         cl.get("sha1"))

    log("Downloading Forge universal ...")
    download(FORGE_URL,
             os.path.join(libs, "net/minecraftforge/forge",
                          FORGE_VERSION, f"forge-{FORGE_VERSION}-universal.jar"))

    log("Done (assets NOT downloaded — will be reused from user's .minecraft).")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python download_mc.py <target_dir>")
        sys.exit(1)
    main(sys.argv[1])
'''

# ===========================================================================
# workflow
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

      - name: Download Minecraft client + libraries + Forge
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
          du -sh dist

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

GITIGNORE_ADD = "\n# OryvexClient build artifacts\nmc-data/\nmods/\ndist/\n"


def write(path, content, is_bat=False):
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        b = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, b)
        print(f"  backup {b.relative_to(ROOT)}")
    if is_bat:
        content = content.replace("\r\n", "\n").replace("\n", "\r\n")
    path.write_text(content, encoding="utf-8", newline="")
    print(f"  write  {path.relative_to(ROOT)}  ({len(content)} bytes)")


def append_once(path, marker, content):
    path = path.resolve()
    if path.exists() and marker in path.read_text(encoding="utf-8", errors="ignore"):
        print(f"  skip   {path.relative_to(ROOT)}")
        return
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(content)
    print(f"  patch  {path.relative_to(ROOT)}")


def main():
    print("OryvexClient Fixer v3 (small ZIP, no assets)")
    print(f"Project root: {ROOT}\n")
    print("[1/5] launcher.py")
    write(ROOT / "launcher.py", LAUNCHER_PY)
    print("[2/5] start.bat")
    write(ROOT / "start.bat", START_BAT, is_bat=True)
    print("[3/5] download_mc.py")
    write(ROOT / "download_mc.py", DOWNLOAD_MC_PY)
    print("[4/5] workflow")
    write(ROOT / ".github" / "workflows" / "build.yml", WORKFLOW_YML)
    print("[5/5] .gitignore")
    append_once(ROOT / ".gitignore", "mc-data/", GITIGNORE_ADD)
    print("\nDone. ZIP will be ~25-35 MB.")


if __name__ == "__main__":
    main()