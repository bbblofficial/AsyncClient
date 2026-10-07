#!/usr/bin/env python3
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
