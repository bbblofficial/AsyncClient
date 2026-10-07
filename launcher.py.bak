#!/usr/bin/env python3
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
