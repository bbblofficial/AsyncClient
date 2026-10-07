#!/usr/bin/env python3
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
