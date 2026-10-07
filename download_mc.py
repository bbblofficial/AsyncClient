#!/usr/bin/env python3
"""Download Minecraft 1.8.8 + Forge + all Forge libraries + vanilla libs (NO assets)."""
import hashlib, io, json, os, sys, urllib.request, zipfile

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

def get_lib_url(name, base="https://libraries.minecraft.net/"):
    """Build fallback URL for maven coordinate."""
    return base + maven_path(name)

def install_libs_from_json(vj, libs, forge=False):
    """Download all libraries from a version JSON."""
    count = 0
    for lib in vj.get("libraries", []):
        # skip native-only entries when not forge
        dl = lib.get("downloads", {})
        art = dl.get("artifact")
        if art and art.get("url"):
            url = art["url"]
            sha1 = art.get("sha1")
        else:
            # forge-style: build URL from maven
            name = lib["name"]
            url = get_lib_url(name)
            sha1 = None
        try:
            dest = os.path.join(libs, maven_path(lib["name"]))
            # handle natives
            for k, v in (dl.get("classifiers") or {}).items():
                if v.get("url"):
                    npath = maven_path(lib["name"] + ":" + k)
                    ndest = os.path.join(libs, npath)
                    download(v["url"], ndest, v.get("sha1"))
                    count += 1
            # skip if already exists
            if not os.path.exists(dest):
                download(url, dest, sha1)
                count += 1
        except Exception as e:
            log(f"  ! lib {lib['name']}: {e}")
    return count

def main(target):
    libs = os.path.join(target, "libraries")
    versions = os.path.join(target, "versions")

    # --- vanilla ---
    log("Fetching manifest ...")
    m = http_json(MANIFEST_URL)
    vurl = next(v["url"] for v in m["versions"] if v["id"] == VERSION)
    vj = http_json(vurl)

    c = vj["downloads"]["client"]
    log("Downloading client.jar ...")
    download(c["url"], os.path.join(versions, VERSION, f"{VERSION}.jar"), c.get("sha1"))

    log("Downloading vanilla libraries ...")
    n = install_libs_from_json(vj, libs)
    log(f"  -> {n} libs")

    # --- Forge installer ---
    log("Downloading Forge installer ...")
    installer_tmp = os.path.join(target, "_forge_installer.jar")
    download(FORGE_INSTALLER_URL, installer_tmp)

    log("Extracting Forge version.json ...")
    with zipfile.ZipFile(installer_tmp) as z:
        version_json_bytes = z.read("version.json")
    forge_vj = json.loads(version_json_bytes.decode("utf-8"))

    log("Downloading Forge libraries ...")
    n = install_libs_from_json(forge_vj, libs, forge=True)
    log(f"  -> {n} libs")

    # --- Forge universal jar ---
    log("Downloading Forge universal ...")
    download(FORGE_UNIVERSAL_URL,
             os.path.join(libs, "net/minecraftforge/forge",
                          FORGE_VERSION, f"forge-{FORGE_VERSION}-universal.jar"))

    # --- cleanup ---
    if os.path.exists(installer_tmp):
        os.remove(installer_tmp)

    log("Done (no assets — reused from user's .minecraft).")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python download_mc.py <target_dir>")
        sys.exit(1)
    main(sys.argv[1])
