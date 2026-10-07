#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OryvexClient Fixer v5
- skips native-only libs (no artifact)
- reads Forge installer's install_profile.json
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# ===========================================================================
# launcher.py  (unchanged from v3/v4)
# ===========================================================================
LAUNCHER_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OryvexClient Launcher."""
import hashlib, json, os, platform, shutil, subprocess, sys
import urllib.request, zipfile

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


def log(m): print(f"[Oryvex] {m}", flush=True)
def _req(u): return urllib.request.Request(u, headers={"User-Agent": UA})

def http_json(u):
    with urllib.request.urlopen(_req(u), timeout=60) as r:
        return json.loads(r.read().decode())

def sha1_file(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()

def download(url, dest, sha1=None):
    if os.path.exists(dest) and sha1 and sha1_file(dest) == sha1:
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    with urllib.request.urlopen(_req(url), timeout=120) as r, open(tmp, "wb") as f:
        while True:
            c = r.read(65536)
            if not c: break
            f.write(c)
    if sha1 and sha1_file(tmp) != sha1:
        os.remove(tmp); raise RuntimeError(f"SHA1 mismatch: {url}")
    if os.path.exists(dest): os.remove(dest)
    os.rename(tmp, dest)

def find_java():
    jh = os.environ.get("JAVA_HOME")
    if jh:
        j = os.path.join(jh, "bin", "java.exe" if platform.system() == "Windows" else "java")
        if os.path.exists(j): return j
    j = shutil.which("java")
    if j: return j
    raise RuntimeError("Java not found. Install Java 8 or newer.")

def extract_natives():
    os.makedirs(NATIVES, exist_ok=True)
    for root, _, files in os.walk(LIBS):
        for f in files:
            if not f.endswith(".jar"): continue
            try:
                with zipfile.ZipFile(os.path.join(root, f)) as z:
                    for name in z.namelist():
                        if name.endswith((".dll", ".so", ".dylib", ".jnilib")):
                            t = os.path.join(NATIVES, os.path.basename(name))
                            if not os.path.exists(t):
                                with z.open(name) as s, open(t, "wb") as d:
                                    shutil.copyfileobj(s, d)
            except zipfile.BadZipFile:
                pass

def ensure_assets():
    index_path = os.path.join(ASSETS, "indexes", "1.8.json")
    obj_dir = os.path.join(ASSETS, "objects")
    if os.path.exists(index_path) and os.path.isdir(obj_dir):
        for _ in os.scandir(obj_dir):
            return ASSETS
    if platform.system() == "Windows":
        user_mc = os.path.join(os.environ.get("APPDATA", ""), ".minecraft")
    elif platform.system() == "Darwin":
        user_mc = os.path.expanduser("~/Library/Application Support/minecraft")
    else:
        user_mc = os.path.expanduser("~/.minecraft")
    ua = os.path.join(user_mc, "assets")
    if os.path.exists(os.path.join(ua, "indexes", "1.8.json")):
        log(f"Using assets from {ua}")
        return ua
    log("Assets missing. Downloading (~110MB) ...")
    m = http_json(MANIFEST_URL)
    vurl = next(v["url"] for v in m["versions"] if v["id"] == VERSION)
    vj = http_json(vurl)
    ai = vj["assetIndex"]
    os.makedirs(os.path.join(ASSETS, "indexes"), exist_ok=True)
    download(ai["url"], index_path, ai.get("sha1"))
    with open(index_path, encoding="utf-8") as f:
        idx = json.load(f)
    for n, o in idx["objects"].items():
        h = o["hash"]
        d = os.path.join(ASSETS, "objects", h[:2], h)
        if os.path.exists(d): continue
        try: download(f"{RESOURCES_URL}/{h[:2]}/{h}", d, h)
        except Exception as e: log(f"  ! {n}: {e}")
    return ASSETS

def build_cp(client_jar, forge_jar):
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
    forge_jar = os.path.join(LIBS, "net/minecraftforge/forge",
                             FORGE_VERSION, f"forge-{FORGE_VERSION}-universal.jar")
    if not os.path.exists(client_jar): raise RuntimeError(f"Missing {client_jar}")
    if not os.path.exists(forge_jar): raise RuntimeError(f"Missing {forge_jar}")
    assets = ensure_assets() or ASSETS
    extract_natives()
    java = find_java()
    cp = build_cp(client_jar, forge_jar)
    jvm = [java, "-Xmx2G", "-Xms512M",
           f"-Djava.library.path={NATIVES}",
           f"-Dorg.lwjgl.librarypath={NATIVES}",
           "-Dminecraft.launcher.brand=OryvexClient",
           "-Dminecraft.launcher.version=1.0.0",
           "-cp", cp]
    game = ["net.minecraft.launchwrapper.Launch",
            "--username", USERNAME, "--version", VERSION,
            "--gameDir", ROOT, "--assetsDir", assets, "--assetIndex", "1.8",
            "--uuid", UUID, "--accessToken", ACCESS_TOKEN,
            "--userProperties", "{}", "--userType", "legacy",
            "--tweakClass", "net.minecraftforge.fml.common.launcher.FMLTweaker"]
    log("Launching Minecraft ...")
    try: subprocess.run(jvm + game, cwd=ROOT)
    except KeyboardInterrupt: pass

if __name__ == "__main__":
    try:
        launch()
    except Exception as e:
        log(f"ERROR: {e}")
        if platform.system() == "Windows": input("Press Enter to exit ...")
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
# download_mc.py  — FIXED
# ===========================================================================
DOWNLOAD_MC_PY = r'''#!/usr/bin/env python3
"""Download Minecraft 1.8.8 + Forge + all libraries (NO assets)."""
import hashlib, json, os, sys, urllib.request, zipfile

VERSION = "1.8.8"
FORGE_VERSION = "1.8.8-11.15.0.1655"
FORGE_INSTALLER_URL = (f"https://maven.minecraftforge.net/net/minecraftforge/forge/"
                       f"{FORGE_VERSION}/forge-{FORGE_VERSION}-installer.jar")
FORGE_UNIVERSAL_URL = (f"https://maven.minecraftforge.net/net/minecraftforge/forge/"
                       f"{FORGE_VERSION}/forge-{FORGE_VERSION}-universal.jar")
MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def log(m): print(f"[dl] {m}", flush=True)
def _req(u): return urllib.request.Request(u, headers={"User-Agent": UA})

def sha1_file(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()

def download(url, dest, sha1=None):
    if os.path.exists(dest) and sha1 and sha1_file(dest) == sha1:
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    with urllib.request.urlopen(_req(url), timeout=120) as r, open(tmp, "wb") as f:
        while True:
            c = r.read(65536)
            if not c: break
            f.write(c)
    if sha1 and sha1_file(tmp) != sha1:
        os.remove(tmp); raise RuntimeError(f"SHA1 mismatch: {url}")
    if os.path.exists(dest): os.remove(dest)
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

def install_libs_from_json(vj, libs):
    """Download all libraries that have an artifact URL + all natives."""
    count = 0
    skipped = 0
    for lib in vj.get("libraries", []):
        dl = lib.get("downloads") or {}

        # 1) main artifact (only if the JSON provides it)
        art = dl.get("artifact")
        if art and art.get("url"):
            try:
                dest = os.path.join(libs, maven_path(lib["name"]))
                if not os.path.exists(dest):
                    download(art["url"], dest, art.get("sha1"))
                    count += 1
            except Exception as e:
                log(f"  ! artifact {lib['name']}: {e}")
        else:
            # No artifact in JSON -> it's a native-only or forge-style lib.
            # Try maven fallback ONLY if the lib has no natives field
            # (otherwise the artifact genuinely doesn't exist).
            if not lib.get("natives"):
                name = lib["name"]
                url = "https://libraries.minecraft.net/" + maven_path(name)
                try:
                    dest = os.path.join(libs, maven_path(name))
                    if not os.path.exists(dest):
                        download(url, dest)
                        count += 1
                except Exception:
                    skipped += 1  # forge libs also served from forge maven below

        # 2) natives (classifiers)
        for k, v in (dl.get("classifiers") or {}).items():
            if not v.get("url"): continue
            try:
                ndest = os.path.join(libs, maven_path(lib["name"] + ":" + k))
                if not os.path.exists(ndest):
                    download(v["url"], ndest, v.get("sha1"))
                    count += 1
            except Exception as e:
                log(f"  ! native {lib['name']}:{k}: {e}")

    return count, skipped

def install_forge_libs(forge_vj, libs):
    """Forge versionInfo libraries usually have no downloads object;
    we build URLs from maven coordinates via maven.minecraftforge.net."""
    count = 0
    for lib in forge_vj.get("libraries", []):
        name = lib["name"]
        dl = lib.get("downloads") or {}
        # prefer explicit URL if present
        art = dl.get("artifact")
        urls = []
        if art and art.get("url"):
            urls.append((art["url"], art.get("sha1")))
        else:
            # forge libs are on maven.minecraftforge.net (and also on
            # libraries.minecraft.net for the vanilla ones)
            urls.append(("https://maven.minecraftforge.net/" + maven_path(name), None))
            urls.append(("https://libraries.minecraft.net/" + maven_path(name), None))

        dest = os.path.join(libs, maven_path(name))
        if os.path.exists(dest):
            continue

        ok = False
        for url, sha in urls:
            try:
                download(url, dest, sha)
                ok = True
                break
            except Exception:
                continue
        if ok:
            count += 1
        else:
            log(f"  ! forge lib missing: {name}")

        # natives inside forge libs (rare)
        for k, v in (dl.get("classifiers") or {}).items():
            if not v.get("url"): continue
            try:
                ndest = os.path.join(libs, maven_path(name + ":" + k))
                if not os.path.exists(ndest):
                    download(v["url"], ndest, v.get("sha1"))
                    count += 1
            except Exception as e:
                log(f"  ! native {name}:{k}: {e}")
    return count

def main(target):
    libs = os.path.join(target, "libraries")
    versions = os.path.join(target, "versions")

    # ---------- vanilla ----------
    log("Fetching manifest ...")
    m = http_json(MANIFEST_URL)
    vurl = next(v["url"] for v in m["versions"] if v["id"] == VERSION)
    vj = http_json(vurl)

    c = vj["downloads"]["client"]
    log("Downloading client.jar ...")
    download(c["url"], os.path.join(versions, VERSION, f"{VERSION}.jar"), c.get("sha1"))

    log("Downloading vanilla libraries ...")
    n, s = install_libs_from_json(vj, libs)
    log(f"  -> {n} downloaded, {s} skipped")

    # ---------- forge ----------
    log("Downloading Forge installer ...")
    installer_tmp = os.path.join(target, "_forge_installer.jar")
    download(FORGE_INSTALLER_URL, installer_tmp)

    log("Extracting Forge install_profile.json ...")
    with zipfile.ZipFile(installer_tmp) as z:
        names = z.namelist()
        forge_vj = None
        if "install_profile.json" in names:
            profile = json.loads(z.read("install_profile.json").decode("utf-8"))
            # newer installers nest a full version JSON under "versionInfo"
            if isinstance(profile.get("versionInfo"), dict):
                forge_vj = profile["versionInfo"]
            # older ones put it under "version"
            elif isinstance(profile.get("version"), dict):
                forge_vj = profile["version"]
        if forge_vj is None and "version.json" in names:
            forge_vj = json.loads(z.read("version.json").decode("utf-8"))
        if forge_vj is None:
            raise RuntimeError(
                "Could not find Forge version JSON inside installer. "
                f"Files: {names[:20]}"
            )

    log(f"Found Forge version: {forge_vj.get('id')} "
        f"({len(forge_vj.get('libraries', []))} libs)")

    log("Downloading Forge libraries ...")
    n = install_forge_libs(forge_vj, libs)
    log(f"  -> {n} downloaded")

    # ---------- Forge universal jar ----------
    log("Downloading Forge universal ...")
    download(FORGE_UNIVERSAL_URL,
             os.path.join(libs, "net/minecraftforge/forge",
                          FORGE_VERSION, f"forge-{FORGE_VERSION}-universal.jar"))

    # cleanup
    if os.path.exists(installer_tmp):
        os.remove(installer_tmp)

    log("Done (no assets — reused from user's .minecraft).")

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

      - name: Download Minecraft + Forge + libs
        run: |
          mkdir -p dist
          python3 download_mc.py dist/mc-data

      - name: Verify critical libs
        run: |
          echo "--- checking launchwrapper ---"
          find dist/mc-data/libraries -name "*launchwrapper*"
          echo "--- checking asm ---"
          find dist/mc-data/libraries -name "*asm-all*"
          echo "--- checking forge universal ---"
          find dist/mc-data/libraries -name "*forge*universal*"
          echo "--- total ---"
          du -sh dist

      - name: Package
        run: |
          mkdir -p dist/mods
          JAR=$(ls build/libs/*.jar | grep -v -e sources -e dev | head -n 1)
          cp "$JAR" dist/mods/OryvexClient.jar
          cp start.bat dist/start.bat
          cp launcher.py dist/launcher.py

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

GITIGNORE_ADD = "\n# OryvexClient build artifacts\nmc-data/\nmods/\ndist/\n_forge_installer.jar\n"


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
    print("OryvexClient Fixer v5")
    print(f"Project root: {ROOT}\n")
    print("[1/5] launcher.py");     write(ROOT / "launcher.py", LAUNCHER_PY)
    print("[2/5] start.bat");       write(ROOT / "start.bat", START_BAT, is_bat=True)
    print("[3/5] download_mc.py");  write(ROOT / "download_mc.py", DOWNLOAD_MC_PY)
    print("[4/5] workflow");        write(ROOT / ".github" / "workflows" / "build.yml", WORKFLOW_YML)
    print("[5/5] .gitignore");      append_once(ROOT / ".gitignore", "mc-data/", GITIGNORE_ADD)
    print("\nDone.")


if __name__ == "__main__":
    main()