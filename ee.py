#!/usr/bin/env python3
"""
fixer.py — repair the GeminiClient / Oryvex repo and install a custom
Minecraft loading screen.

What this script does, in order
-------------------------------
1.  Backs the whole repository up to a timestamped .zip next to it.
2.  Deletes the broken duplicate mod  src/main/java/com/oryvex/  — this
    is the package whose AsyncResourcePackGui.java currently fails with
    "availableResourcePacks has private access in GuiScreenResourcePacks"
    and aborts :compileJava.
3.  Adds a custom loading screen that replaces the vanilla Mojang splash:
        src/main/java/com/example/asyncmenus/loading/CustomLoadingScreen.java
        src/main/java/com/example/asyncmenus/loading/LoadingScreenHook.java
4.  Rewrites src/main/java/com/example/asyncmenus/AsyncMenus.java so it
    installs the loading screen during FMLPreInitializationEvent and still
    registers the existing resource-pack handlers on FMLInitializationEvent.
5.  Generates a placeholder logo PNG at
        src/main/resources/assets/asyncmenus/textures/gui/custom_loading.png
    (unless you pass --custom-logo /path/to/your.png, in which case that
    file is copied instead).
6.  Normalises .github/workflows/build.yml (correct indentation for the
    Upload step, consistent artifact name/path).
7.  Sanity-checks that nothing under src/ still imports com.oryvex.*.

Usage
-----
    python fixer.py                          # run in-place next to the script
    python fixer.py --repo "C:\\path\\to\\repo"
    python fixer.py --custom-logo my_logo.png
    python fixer.py --dry-run
    python fixer.py --no-backup
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import shutil
import struct
import sys
import zipfile
import zlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths inside the repo
# ---------------------------------------------------------------------------

BROKEN_PACKAGE_REL = Path("src/main/java/com/oryvex")

PKG_ROOT            = Path("src/main/java/com/example/asyncmenus")
LOADING_PKG         = PKG_ROOT / "loading"
CUSTOM_LOADING_REL  = LOADING_PKG / "CustomLoadingScreen.java"
LOADING_HOOK_REL    = LOADING_PKG / "LoadingScreenHook.java"
ASYNC_MENUS_REL     = PKG_ROOT / "AsyncMenus.java"

TEXTURE_REL = Path(
    "src/main/resources/assets/asyncmenus/textures/gui/custom_loading.png"
)

WORKFLOW_REL = Path(".github/workflows/build.yml")

ARTIFACT_NAME    = "AsyncMenus-jar"
ARTIFACT_PATH    = "build/libs/*.jar"
ARTIFACT_EXCLUDE = "!build/libs/*-sources.jar"

# ---------------------------------------------------------------------------
# File contents
# ---------------------------------------------------------------------------

CUSTOM_LOADING_JAVA = r"""package com.example.asyncmenus.loading;

import net.minecraft.client.LoadingScreenRenderer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.FontRenderer;
import net.minecraft.client.gui.ScaledResolution;
import net.minecraft.client.renderer.GlStateManager;
import net.minecraft.client.renderer.Tessellator;
import net.minecraft.client.renderer.WorldRenderer;
import net.minecraft.client.renderer.vertex.DefaultVertexFormats;
import net.minecraft.util.ResourceLocation;
import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.GL11;

/**
 * Replaces vanilla's Mojang loading screen.
 * Extends LoadingScreenRenderer so it can be dropped into Minecraft.loadingScreen.
 */
public class CustomLoadingScreen extends LoadingScreenRenderer {

    /** Replace this PNG with your own logo. Put it under src/main/resources. */
    private static final ResourceLocation LOGO =
            new ResourceLocation("asyncmenus", "textures/gui/custom_loading.png");

    private final Minecraft mc;
    private String title = "";
    private String message = "";
    private int progress;

    public CustomLoadingScreen(Minecraft mc) {
        super(mc);
        this.mc = mc;
    }

    @Override public void resetProgressAndMessage(String message) { this.title = message; this.message = ""; render(); }
    @Override public void displaySavingString(String message)     { this.message = message;                  render(); }
    @Override public void setLoadingProgress(int progress)        { this.progress = progress;                render(); }
    @Override public void setDoneWorking()                        { /* stop drawing */ }

    // -----------------------------------------------------------------
    // Rendering
    // -----------------------------------------------------------------

    private void render() {
        if (mc == null || !Display.isCreated()) return;

        ScaledResolution sr = new ScaledResolution(mc);
        int sw = sr.getScaledWidth();
        int sh = sr.getScaledHeight();

        // Background
        GlStateManager.clearColor(0.06F, 0.06F, 0.08F, 1.0F);
        GlStateManager.clear(16640); // GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT

        // Orthographic 2D projection
        GlStateManager.matrixMode(GL11.GL_PROJECTION);
        GlStateManager.loadIdentity();
        GlStateManager.ortho(0.0D, sw, sh, 0.0D, 1000.0D, 3000.0D);
        GlStateManager.matrixMode(GL11.GL_MODELVIEW);
        GlStateManager.loadIdentity();
        GlStateManager.translate(0.0F, 0.0F, -2000.0F);

        GlStateManager.disableLighting();
        GlStateManager.disableFog();
        GlStateManager.disableDepth();
        GlStateManager.enableTexture2D();
        GlStateManager.enableBlend();
        GlStateManager.color(1F, 1F, 1F, 1F);

        // Logo
        try {
            mc.getTextureManager().bindTexture(LOGO);
            int lw = 128, lh = 128;
            drawTexturedQuad((sw - lw) / 2, (sh - lh) / 2 - 40, lw, lh);
        } catch (Throwable ignored) { /* missing texture - text only */ }

        FontRenderer fr = mc.fontRendererObj;

        if (!title.isEmpty())
            fr.drawStringWithShadow(title, (sw - fr.getStringWidth(title)) / 2, sh / 2 + 60, 0xFFFFFF);
        if (!message.isEmpty())
            fr.drawStringWithShadow(message, (sw - fr.getStringWidth(message)) / 2, sh / 2 + 76, 0xAAAAAA);

        // Progress bar
        int barW = 200, barH = 4;
        int barX = (sw - barW) / 2;
        int barY = sh / 2 + 100;

        drawRect(barX - 1, barY - 1, barX + barW + 1, barY + barH + 1, 0xFF333333);
        drawRect(barX, barY, barX + barW, barY + barH, 0xFF555555);
        if (progress > 0) {
            int fw = barW * Math.min(progress, 100) / 100;
            drawRect(barX, barY, barX + fw, barY + barH, 0xFF4FC3F7);
        }

        Display.update();
    }

    private static void drawTexturedQuad(int x, int y, int w, int h) {
        Tessellator t = Tessellator.getInstance();
        WorldRenderer wr = t.getWorldRenderer();
        wr.begin(7, DefaultVertexFormats.POSITION_TEX);
        wr.pos(x,     y + h, 0).tex(0.0D, 1.0D).endVertex();
        wr.pos(x + w, y + h, 0).tex(1.0D, 1.0D).endVertex();
        wr.pos(x + w, y,     0).tex(1.0D, 0.0D).endVertex();
        wr.pos(x,     y,     0).tex(0.0D, 0.0D).endVertex();
        t.draw();
    }

    private static void drawRect(int l, int t, int r, int b, int color) {
        if (l < r) { int s = l; l = r; r = s; }
        if (t < b) { int s = t; t = b; b = s; }

        float a  = (color >> 24 & 0xFF) / 255.0F;
        float cr = (color >> 16 & 0xFF) / 255.0F;
        float cg = (color >>  8 & 0xFF) / 255.0F;
        float cb = (color       & 0xFF) / 255.0F;

        Tessellator tess = Tessellator.getInstance();
        WorldRenderer wr = tess.getWorldRenderer();
        GlStateManager.disableTexture2D();
        GlStateManager.color(cr, cg, cb, a);
        wr.begin(7, DefaultVertexFormats.POSITION);
        wr.pos(l, b, 0).endVertex();
        wr.pos(r, b, 0).endVertex();
        wr.pos(r, t, 0).endVertex();
        wr.pos(l, t, 0).endVertex();
        tess.draw();
        GlStateManager.enableTexture2D();
        GlStateManager.color(1F, 1F, 1F, 1F);
    }
}
"""

LOADING_HOOK_JAVA = r"""package com.example.asyncmenus.loading;

import net.minecraft.client.LoadingScreenRenderer;
import net.minecraft.client.Minecraft;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.lang.reflect.Field;

/** Swaps the vanilla loading screen for CustomLoadingScreen. */
public final class LoadingScreenHook {

    private static final Logger LOG = LogManager.getLogger("asyncmenus");
    private static boolean installed;

    private LoadingScreenHook() {}

    public static void install() {
        if (installed) return;
        installed = true;

        Minecraft mc = Minecraft.getMinecraft();
        if (mc == null) {
            LOG.warn("Minecraft instance unavailable; custom loading screen not installed");
            return;
        }

        try {
            Field f = findField();
            f.setAccessible(true);
            if (f.get(mc) instanceof CustomLoadingScreen) return;

            f.set(mc, new CustomLoadingScreen(mc));
            LOG.info("Custom loading screen installed");
        } catch (Throwable t) {
            LOG.error("Could not install custom loading screen; vanilla will be used", t);
        }
    }

    private static Field findField() throws NoSuchFieldException {
        try { return Minecraft.class.getDeclaredField("loadingScreen"); }  catch (NoSuchFieldException ignored) {}
        try { return Minecraft.class.getDeclaredField("field_71461_s"); } catch (NoSuchFieldException ignored) {}

        // Last resort: first field whose type is LoadingScreenRenderer
        for (Field f : Minecraft.class.getDeclaredFields())
            if (f.getType() == LoadingScreenRenderer.class) return f;

        throw new NoSuchFieldException("Minecraft.loadingScreen not found");
    }
}
"""

ASYNC_MENUS_JAVA = r"""package com.example.asyncmenus;

import com.example.asyncmenus.loading.LoadingScreenHook;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.event.FMLInitializationEvent;
import net.minecraftforge.fml.common.event.FMLPreInitializationEvent;

@Mod(modid = AsyncMenus.MODID, name = AsyncMenus.NAME, version = AsyncMenus.VERSION,
        clientSideOnly = true, acceptedMinecraftVersions = "[1.8.9]", useMetadata = true)
public class AsyncMenus {
    public static final String MODID = "asyncmenus";
    public static final String NAME = "Async Menus";
    public static final String VERSION = "1.0.0";

    @Mod.EventHandler
    public void preInit(FMLPreInitializationEvent event) {
        LoadingScreenHook.install();
    }

    @Mod.EventHandler
    public void init(FMLInitializationEvent event) {
        MinecraftForge.EVENT_BUS.register(new ResourcePackScreenHandler());
        MinecraftForge.EVENT_BUS.register(new ShaderPackPrefetcher());
    }
}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def log(msg: str) -> None:
    print(f"[fixer] {msg}")


def warn(msg: str) -> None:
    print(f"[fixer] WARNING: {msg}", file=sys.stderr)


def die(msg: str, code: int = 1) -> None:
    print(f"[fixer] ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def is_repo_root(p: Path) -> bool:
    return (p / "build.gradle").is_file()


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for c in [cur, *cur.parents]:
        if is_repo_root(c):
            return c
    die(f"could not find a repository (no build.gradle) above {start}")
    raise SystemExit(1)


def backup_repo(repo: Path) -> Path:
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = repo.parent / f"{repo.name}-backup-{stamp}.zip"
    log(f"backing up to {out}")
    skip = {".git", "build", "run", ".gradle", ".idea", "out", "bin"}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in skip]
            for name in files:
                p = Path(root) / name
                if p.resolve() == out.resolve():
                    continue
                zf.write(p, p.relative_to(repo))
    log(f"backup written ({out.stat().st_size // 1024} KiB)")
    return out


def write_text(path: Path, content: str, dry_run: bool) -> bool:
    """Write *content* to *path*. Returns True if anything changed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8")
        except OSError:
            existing = None
        if existing == content:
            log(f"already up-to-date: {path.name}")
            return False
    log(f"writing {path}")
    if not dry_run:
        path.write_text(content, encoding="utf-8")
    return True


def remove_broken_package(repo: Path, dry_run: bool) -> bool:
    target = repo / BROKEN_PACKAGE_REL
    if not target.exists():
        log(f"already clean: {BROKEN_PACKAGE_REL}")
        return False
    log(f"removing broken duplicate mod: {BROKEN_PACKAGE_REL}")
    if dry_run:
        return True
    shutil.rmtree(target)
    com_dir = target.parent
    try:
        if com_dir.is_dir() and not any(com_dir.iterdir()):
            com_dir.rmdir()
            log(f"pruned empty directory: {com_dir.relative_to(repo)}")
    except OSError:
        pass
    return True


# ---------------------------------------------------------------------------
# Placeholder logo PNG
# ---------------------------------------------------------------------------


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    payload = tag + data
    return (
        struct.pack(">I", len(data))
        + payload
        + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
    )


def make_placeholder_png(w: int = 128, h: int = 128) -> bytes:
    """Return a small RGBA PNG: a diagonal blue gradient with cut corners."""
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter type 0
        for x in range(w):
            t = (x + y) / (w + h)              # 0..1 along the diagonal
            r = int(20 + 40 * t)
            g = int(80 + 100 * t)
            b = int(160 + 80 * t)

            # cut the four corners by making them transparent
            cx, cy = w / 2.0, h / 2.0
            dx, dy = abs(x - cx) / cx, abs(y - cy) / cy
            a = 0 if (dx > 0.88 and dy > 0.88) else 255
            raw += bytes((r, g, b, a))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)  # 8-bit RGBA
    idat = zlib.compress(bytes(raw), 9)
    return sig + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b"")


def install_texture(repo: Path, custom_logo: Path | None, dry_run: bool) -> None:
    dst = repo / TEXTURE_REL
    dst.parent.mkdir(parents=True, exist_ok=True)

    if custom_logo is not None:
        if not custom_logo.is_file():
            die(f"--custom-logo not found: {custom_logo}")
        if dst.exists() and dst.read_bytes() == custom_logo.read_bytes():
            log(f"logo already in place: {TEXTURE_REL}")
            return
        log(f"copying custom logo {custom_logo} -> {TEXTURE_REL}")
        if not dry_run:
            shutil.copyfile(custom_logo, dst)
        return

    if dst.exists():
        log(f"logo already present, leaving alone: {TEXTURE_REL}")
        return

    log(f"generating placeholder logo: {TEXTURE_REL}")
    if not dry_run:
        dst.write_bytes(make_placeholder_png())


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


def rewrite_workflow(repo: Path, dry_run: bool) -> bool:
    wf = repo / WORKFLOW_REL
    if not wf.is_file():
        warn(f"workflow not found: {WORKFLOW_REL} (skipping)")
        return False

    original = wf.read_text(encoding="utf-8")

    # Match the entire "Upload jar" step (name + following indented lines)
    # and replace it wholesale, fixing both its indent and its contents.
    step_re = re.compile(
        r"(?P<indent>[ \t]*)-[ \t]*name:[ \t]*Upload jar[ \t]*\r?\n"
        r"(?P<body>(?:[ \t]+[^\n]*\r?\n)+)",
        re.MULTILINE,
    )

    desired = (
        "      - name: Upload jar\n"
        "        uses: actions/upload-artifact@v4\n"
        "        with:\n"
        f"          name: {ARTIFACT_NAME}\n"
        "          path: |\n"
        f"            {ARTIFACT_PATH}\n"
        f"            {ARTIFACT_EXCLUDE}\n"
        "          if-no-files-found: error\n"
    )

    m = step_re.search(original)
    if not m:
        warn("could not locate the 'Upload jar' step; workflow left untouched")
        return False

    new = original[: m.start()] + desired + original[m.end():]

    if new == original:
        log("workflow already correct")
        return False

    log(f"rewriting {WORKFLOW_REL}")
    if not dry_run:
        wf.write_text(new, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

import re  # noqa: E402  (kept near use for clarity)

STALE_REF = re.compile(r"\bcom\.oryvex\b")


def find_stale_refs(repo: Path) -> list[Path]:
    out: list[Path] = []
    src = repo / "src"
    if not src.is_dir():
        return out
    for p in src.rglob("*"):
        if p.suffix.lower() not in {".java", ".kt", ".groovy", ".scala"}:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if STALE_REF.search(text):
            out.append(p)
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Fix the GeminiClient/Oryvex repo so `gradle build` succeeds, "
            "and install a custom Minecraft loading screen."
        ),
    )
    p.add_argument("--repo", type=Path, default=None,
                   help="repository root (default: nearest parent of this script with build.gradle)")
    p.add_argument("--custom-logo", type=Path, default=None,
                   help="PNG to install as the loading screen logo (default: generated placeholder)")
    p.add_argument("--no-backup", action="store_true",
                   help="skip the .zip backup")
    p.add_argument("--dry-run", action="store_true",
                   help="report planned changes, write nothing")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.repo is not None:
        repo = args.repo.resolve()
        if not is_repo_root(repo):
            die(f"{repo} does not look like a repository (no build.gradle)")
    else:
        repo = find_repo_root(Path(__file__).resolve().parent)

    log(f"repository: {repo}")
    if args.dry_run:
        log("DRY RUN — nothing will be written")

    if not args.no_backup and not args.dry_run:
        backup_repo(repo)
    elif args.no_backup:
        log("backup disabled")

    removed_pkg = remove_broken_package(repo, args.dry_run)

    changed_custom = write_text(repo / CUSTOM_LOADING_REL, CUSTOM_LOADING_JAVA, args.dry_run)
    changed_hook   = write_text(repo / LOADING_HOOK_REL,   LOADING_HOOK_JAVA,   args.dry_run)
    changed_mod    = write_text(repo / ASYNC_MENUS_REL,    ASYNC_MENUS_JAVA,    args.dry_run)

    install_texture(repo, args.custom_logo, args.dry_run)

    changed_wf = rewrite_workflow(repo, args.dry_run)

    offenders = find_stale_refs(repo)
    if offenders:
        warn("the following files still reference 'com.oryvex':")
        for p in offenders:
            print(f"    {p.relative_to(repo)}", file=sys.stderr)
    else:
        log("no stale 'com.oryvex' references remain")

    print()
    log("summary")
    log(f"  broken package removed        : {removed_pkg}")
    log(f"  CustomLoadingScreen.java      : {'written' if changed_custom else 'unchanged'}")
    log(f"  LoadingScreenHook.java        : {'written' if changed_hook else 'unchanged'}")
    log(f"  AsyncMenus.java               : {'written' if changed_mod else 'unchanged'}")
    log(f"  workflow                      : {'rewritten' if changed_wf else 'unchanged'}")
    log(f"  stale 'com.oryvex' references : {len(offenders)}")

    if args.dry_run:
        log("re-run without --dry-run to apply")

    return 0 if not offenders else 2


if __name__ == "__main__":
    sys.exit(main())