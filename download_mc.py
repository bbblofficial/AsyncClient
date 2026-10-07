#!/usr/bin/env python3
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
