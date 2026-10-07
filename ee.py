#!/usr/bin/env python3
"""
fixer.py — repair the GeminiClient / Oryvex repo, install a custom
loading screen, and broadcast progress from every startup phase.

What it does
------------
1.  Backs the repo up to a timestamped .zip next to it.
2.  Deletes the broken duplicate mod  src/main/java/com/oryvex/.
3.  Adds a complete, phase-aware loading screen system:
        loading/LoadingPhase.java
        loading/LoadingScreenHook.java
        loading/CustomLoadingScreen.java
        loading/LoadingProgress.java
        loading/LoadingProgressHandler.java
        loading/TerrainLoadListener.java
        core/LoadingScreenTransformer.java
        core/AsyncMenusLoadingPlugin.java
4.  Rewrites  AsyncMenus.java  to install the hook on preInit and to
    register the progress handlers.
5.  Generates a placeholder logo PNG (or copies --custom-logo).
6.  Adds the FMLCorePlugin manifest attributes to build.gradle.
7.  Normalises .github/workflows/build.yml.
8.  Validates that no file still imports com.oryvex.*.

Usage
-----
    python fixer.py
    python fixer.py --repo "C:\\path\\to\\repo"
    python fixer.py --custom-logo my_logo.png
    python fixer.py --dry-run
    python fixer.py --no-backup
    python fixer.py --no-coremod        # skip the ASM transformer
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import shutil
import struct
import sys
import zipfile
import zlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BROKEN_PACKAGE_REL = Path("src/main/java/com/oryvex")

PKG_ROOT    = Path("src/main/java/com/example/asyncmenus")
LOADING_PKG = PKG_ROOT / "loading"
CORE_PKG    = PKG_ROOT / "core"

ASYNC_MENUS_REL = PKG_ROOT / "AsyncMenus.java"

TEXTURE_REL = Path(
    "src/main/resources/assets/asyncmenus/textures/gui/custom_loading.png"
)

WORKFLOW_REL = Path(".github/workflows/build.yml")
BUILD_GRADLE_REL = Path("build.gradle")

ARTIFACT_NAME    = "AsyncMenus-jar"
ARTIFACT_PATH    = "build/libs/*.jar"
ARTIFACT_EXCLUDE = "!build/libs/*-sources.jar"

CORE_PLUGIN_CLASS = "com.example.asyncmenus.core.AsyncMenusLoadingPlugin"

# ---------------------------------------------------------------------------
# Java sources
# ---------------------------------------------------------------------------

LOADING_PHASE_JAVA = r"""package com.example.asyncmenus.loading;

/** Every distinct startup / reload phase we report progress for. */
public enum LoadingPhase {
    MOD_CONSTRUCTION   ("Constructing mods",      5),
    PRE_INIT           ("Pre-initializing mods", 10),
    INIT               ("Initializing mods",     20),
    POST_INIT          ("Post-initializing mods",30),
    RESOURCE_LOAD      ("Loading resources",     45),
    START_GAME         ("Starting game",         60),
    TERRAIN            ("Building terrain",      75),
    JOINING_WORLD      ("Joining world",         85),
    RELOADING          ("Reloading resources",   50),
    DONE               ("Done",                 100);

    public final String label;
    public final int basePercent;

    LoadingPhase(String label, int basePercent) {
        this.label = label;
        this.basePercent = basePercent;
    }
}
"""

LOADING_PROGRESS_JAVA = r"""package com.example.asyncmenus.loading;

/**
 * Global, thread-safe progress bus. Any code can post a phase and a
 * sub-progress (0..1) inside that phase; the renderer on the client
 * thread reads the latest values.
 */
public final class LoadingProgress {

    private static volatile LoadingPhase phase = LoadingPhase.MOD_CONSTRUCTION;
    private static volatile float subProgress = 0f;
    private static volatile String customMessage = "";
    private static volatile boolean screenActive = false;

    private LoadingProgress() {}

    public static void setPhase(LoadingPhase p) {
        phase = p;
        subProgress = 0f;
        customMessage = "";
    }

    public static void setPhase(LoadingPhase p, float sub) {
        phase = p;
        subProgress = clamp(sub);
    }

    public static void setSub(float sub) {
        subProgress = clamp(sub);
    }

    public static void setMessage(String msg) {
        customMessage = msg == null ? "" : msg;
    }

    public static LoadingPhase getPhase()        { return phase; }
    public static float getSubProgress()         { return subProgress; }
    public static String getCustomMessage()      { return customMessage; }
    public static boolean isScreenActive()       { return screenActive; }
    public static void setScreenActive(boolean b) { screenActive = b; }

    /** Absolute 0..100 percent across all phases. */
    public static int getPercent() {
        LoadingPhase p = phase;
        LoadingPhase[] all = LoadingPhase.values();
        int nextBase = 100;
        for (int i = 0; i < all.length; i++) {
            if (all[i] == p) {
                nextBase = (i + 1 < all.length) ? all[i + 1].basePercent : 100;
                break;
            }
        }
        float span = nextBase - p.basePercent;
        return Math.max(0, Math.min(100,
                Math.round(p.basePercent + span * subProgress)));
    }

    private static float clamp(float f) {
        if (f < 0f) return 0f;
        if (f > 1f) return 1f;
        return f;
    }
}
"""

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
 * Custom loading screen shown from the earliest possible frame until
 * the main menu / a world is ready. Draws whatever LoadingProgress
 * currently holds, so it works for every startup phase.
 */
public class CustomLoadingScreen extends LoadingScreenRenderer {

    private static final ResourceLocation LOGO =
            new ResourceLocation("asyncmenus", "textures/gui/custom_loading.png");

    private final Minecraft mc;

    public CustomLoadingScreen(Minecraft mc) {
        super(mc);
        this.mc = mc;
    }

    // --- LoadingScreenRenderer API used by vanilla --------------------

    @Override public void resetProgressAndMessage(String message) {
        LoadingProgress.setMessage(message);
        LoadingProgress.setPhase(LoadingPhase.START_GAME);
        render();
    }

    @Override public void displaySavingString(String message) {
        LoadingProgress.setMessage(message);
        render();
    }

    @Override public void setLoadingProgress(int progress) {
        LoadingProgress.setSub(progress / 100f);
        render();
    }

    @Override public void setDoneWorking() {
        LoadingProgress.setScreenActive(false);
    }

    // --- Called by the progress handler each client tick --------------

    /** Render one frame. Safe to call from the client thread only. */
    public void tick() {
        if (!LoadingProgress.isScreenActive()) return;
        render();
    }

    // -----------------------------------------------------------------

    private void render() {
        if (mc == null || !Display.isCreated()) return;

        ScaledResolution sr = new ScaledResolution(mc);
        int sw = sr.getScaledWidth();
        int sh = sr.getScaledHeight();

        // Background
        GlStateManager.clearColor(0.06F, 0.06F, 0.08F, 1.0F);
        GlStateManager.clear(16640);

        // 2D projection
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
            drawTexturedQuad((sw - lw) / 2, (sh - lh) / 2 - 50, lw, lh);
        } catch (Throwable ignored) {}

        FontRenderer fr = mc.fontRendererObj;

        LoadingPhase phase = LoadingProgress.getPhase();
        int percent = LoadingProgress.getPercent();
        String custom = LoadingProgress.getCustomMessage();

        // Title (phase label)
        String title = phase.label;
        fr.drawStringWithShadow(title,
                (sw - fr.getStringWidth(title)) / 2, sh / 2 + 50, 0xFFFFFF);

        // Custom message from vanilla or mods
        if (!custom.isEmpty()) {
            fr.drawStringWithShadow(custom,
                    (sw - fr.getStringWidth(custom)) / 2, sh / 2 + 66, 0xAAAAAA);
        }

        // Percent
        String pctStr = percent + "%";
        fr.drawStringWithShadow(pctStr,
                (sw - fr.getStringWidth(pctStr)) / 2, sh / 2 + 82, 0xCCCCCC);

        // Progress bar
        int barW = 240, barH = 5;
        int barX = (sw - barW) / 2;
        int barY = sh / 2 + 100;

        drawRect(barX - 1, barY - 1, barX + barW + 1, barY + barH + 1, 0xFF333333);
        drawRect(barX, barY, barX + barW, barY + barH, 0xFF555555);
        if (percent > 0) {
            int fw = barW * percent / 100;
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

LOADING_SCREEN_HOOK_JAVA = r"""package com.example.asyncmenus.loading;

import net.minecraft.client.LoadingScreenRenderer;
import net.minecraft.client.Minecraft;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.lang.reflect.Field;

/**
 * Installs CustomLoadingScreen into Minecraft.loadingScreen as early
 * as possible (preInit). Also keeps a static reference so the tick
 * handler can force redraws while other startup work runs.
 */
public final class LoadingScreenHook {

    private static final Logger LOG = LogManager.getLogger("asyncmenus");
    private static CustomLoadingScreen activeScreen;
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
            if (f.get(mc) instanceof CustomLoadingScreen) {
                activeScreen = (CustomLoadingScreen) f.get(mc);
                return;
            }
            activeScreen = new CustomLoadingScreen(mc);
            f.set(mc, activeScreen);
            LoadingProgress.setScreenActive(true);
            LOG.info("Custom loading screen installed");
        } catch (Throwable t) {
            LOG.error("Could not install custom loading screen; vanilla will be used", t);
        }
    }

    public static CustomLoadingScreen getActiveScreen() { return activeScreen; }

    private static Field findField() throws NoSuchFieldException {
        try { return Minecraft.class.getDeclaredField("loadingScreen"); }  catch (NoSuchFieldException ignored) {}
        try { return Minecraft.class.getDeclaredField("field_71461_s"); } catch (NoSuchFieldException ignored) {}
        for (Field f : Minecraft.class.getDeclaredFields())
            if (f.getType() == LoadingScreenRenderer.class) return f;
        throw new NoSuchFieldException("Minecraft.loadingScreen not found");
    }
}
"""

LOADING_PROGRESS_HANDLER_JAVA = r"""package com.example.asyncmenus.loading;

import net.minecraftforge.fml.common.event.FMLConstructionEvent;
import net.minecraftforge.fml.common.event.FMLInitializationEvent;
import net.minecraftforge.fml.common.event.FMLPostInitializationEvent;
import net.minecraftforge.fml.common.event.FMLPreInitializationEvent;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.fml.common.gameevent.TickEvent;
import net.minecraftforge.client.event.GuiOpenEvent;
import net.minecraft.client.gui.GuiMainMenu;
import net.minecraftforge.fml.relauncher.Side;
import net.minecraftforge.fml.relauncher.SideOnly;

/**
 * Subscribes to Forge's startup events and pushes them into the global
 * LoadingProgress bus. Also forces a redraw each client tick while the
 * loading screen is active.
 */
@SideOnly(Side.CLIENT)
public class LoadingProgressHandler {

    private boolean showedPreInit;
    private boolean showedInit;
    private boolean showedPostInit;

    @SubscribeEvent
    public void onConstruct(FMLConstructionEvent e) {
        LoadingProgress.setPhase(LoadingPhase.MOD_CONSTRUCTION, 0.5f);
    }

    @SubscribeEvent
    public void onPreInit(FMLPreInitializationEvent e) {
        if (showedPreInit) return;
        showedPreInit = true;
        LoadingProgress.setPhase(LoadingPhase.PRE_INIT, 0.1f);
    }

    @SubscribeEvent
    public void onInit(FMLInitializationEvent e) {
        if (showedInit) return;
        showedInit = true;
        LoadingProgress.setPhase(LoadingPhase.INIT, 0.1f);
    }

    @SubscribeEvent
    public void onPostInit(FMLPostInitializationEvent e) {
        if (showedPostInit) return;
        showedPostInit = true;
        LoadingProgress.setPhase(LoadingPhase.POST_INIT, 0.1f);
    }

    /** Force a redraw each client tick while we own the screen. */
    @SubscribeEvent
    public void onClientTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        CustomLoadingScreen screen = LoadingScreenHook.getActiveScreen();
        if (screen == null || !LoadingProgress.isScreenActive()) return;
        try { screen.tick(); } catch (Throwable ignored) {}
    }

    /** Hide the overlay once the main menu appears. */
    @SubscribeEvent
    public void onGuiOpen(GuiOpenEvent e) {
        if (e.gui instanceof GuiMainMenu) {
            LoadingProgress.setPhase(LoadingPhase.DONE);
            LoadingProgress.setScreenActive(false);
        }
    }
}
"""

TERRAIN_LOAD_LISTENER_JAVA = r"""package com.example.asyncmenus.loading;

import net.minecraftforge.client.event.GuiScreenEvent;
import net.minecraftforge.event.world.WorldEvent;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.fml.relauncher.Side;
import net.minecraftforge.fml.relauncher.SideOnly;

/**
 * Reports world/terrain progress so the loading screen can say
 * "Building terrain" / "Joining world" during world load.
 *
 * Also catches the ResourcePack reload via GuiScreenEvent when a
 * GuiScreenResourcePack is about to open.
 */
@SideOnly(Side.CLIENT)
public class TerrainLoadListener {

    @SubscribeEvent
    public void onWorldLoad(WorldEvent.Load e) {
        LoadingProgress.setScreenActive(true);
        LoadingProgress.setPhase(LoadingPhase.TERRAIN, 0.1f);
        LoadingProgress.setMessage("Downloading terrain");
    }

    @SubscribeEvent
    public void onWorldUnload(WorldEvent.Unload e) {
        // nothing to do yet; kept for symmetry
    }

    @SubscribeEvent
    public void onGuiInitPre(GuiScreenEvent.InitGuiEvent.Pre e) {
        if (e.gui == null) return;
        String name = e.gui.getClass().getSimpleName();
        if (name.equals("GuiDownloadTerrain") || name.equals("GuiWorldLoad")) {
            LoadingProgress.setScreenActive(true);
            LoadingProgress.setPhase(LoadingPhase.JOINING_WORLD, 0.2f);
            LoadingProgress.setMessage("Joining world");
        }
        if (name.equals("GuiScreenResourcePacks")) {
            LoadingProgress.setScreenActive(true);
            LoadingProgress.setPhase(LoadingPhase.RELOADING, 0.1f);
            LoadingProgress.setMessage("Scanning resource packs");
        }
    }
}
"""

ASYNC_MENUS_JAVA = r"""package com.example.asyncmenus;

import com.example.asyncmenus.loading.LoadingProgressHandler;
import com.example.asyncmenus.loading.LoadingScreenHook;
import com.example.asyncmenus.loading.TerrainLoadListener;
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
        // Install the loading screen before anything else.
        LoadingScreenHook.install();

        // Progress handlers: Forge bus for lifecycle events...
        MinecraftForge.EVENT_BUS.register(new LoadingProgressHandler());
        MinecraftForge.EVENT_BUS.register(new TerrainLoadListener());
    }

    @Mod.EventHandler
    public void init(FMLInitializationEvent event) {
        MinecraftForge.EVENT_BUS.register(new ResourcePackScreenHandler());
        MinecraftForge.EVENT_BUS.register(new ShaderPackPrefetcher());
    }
}
"""

LOADING_SCREEN_TRANSFORMER_JAVA = r"""package com.example.asyncmenus.core;

import net.minecraft.launchwrapper.IClassTransformer;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.*;

/**
 * Neutralises LoadingScreenRenderer.drawScreen() so vanilla never
 * paints the Mojang splash. Our own renderer takes over from preInit.
 *
 * Forge 1.8.9 ships ASM 5.0.3, so we target ASM5.
 */
public class LoadingScreenTransformer implements IClassTransformer {

    private static final String TARGET = "net.minecraft.client.LoadingScreenRenderer";

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (basicClass == null) return null;
        if (!TARGET.equals(transformedName) && !TARGET.equals(name)) return basicClass;

        ClassNode cn = new ClassNode();
        new ClassReader(basicClass).accept(cn, 0);

        for (MethodNode mn : cn.methods) {
            if ("drawScreen".equals(mn.name) || "func_73719_c".equals(mn.name)) {
                mn.instructions.clear();
                mn.tryCatchBlocks.clear();
                if (mn.localVariables != null) mn.localVariables.clear();

                InsnList ret = new InsnList();
                ret.add(new InsnNode(Opcodes.RETURN));
                mn.instructions.add(ret);

                mn.maxStack = 1;
                mn.maxLocals = 1;
            }
        }

        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cn.accept(cw);
        return cw.toByteArray();
    }
}
"""

LOADING_PLUGIN_JAVA = r"""package com.example.asyncmenus.core;

import net.minecraftforge.fml.relauncher.IFMLLoadingPlugin;

import java.util.Map;

@IFMLLoadingPlugin.MCVersion("1.8.9")
@IFMLLoadingPlugin.TransformerExclusions({"com.example.asyncmenus.core"})
public class AsyncMenusLoadingPlugin implements IFMLLoadingPlugin {

    @Override public String[] getASMTransformerClass() {
        return new String[]{ LoadingScreenTransformer.class.getName() };
    }
    @Override public String getModContainerClass()           { return null; }
    @Override public String getSetupClass()                  { return null; }
    @Override public void   injectData(Map<String,Object> d) {}
    @Override public String getAccessTransformerClass()      { return null; }
}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def log(m: str) -> None:
    print(f"[fixer] {m}")


def warn(m: str) -> None:
    print(f"[fixer] WARNING: {m}", file=sys.stderr)


def die(m: str, code: int = 1) -> None:
    print(f"[fixer] ERROR: {m}", file=sys.stderr)
    sys.exit(code)


def is_repo_root(p: Path) -> bool:
    return (p / "build.gradle").is_file()


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for c in [cur, *cur.parents]:
        if is_repo_root(c):
            return c
    die(f"no build.gradle found above {start}")
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
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            if path.read_text(encoding="utf-8") == content:
                log(f"already up-to-date: {path.name}")
                return False
        except OSError:
            pass
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
    except OSError:
        pass
    return True


# ---------------------------------------------------------------------------
# Placeholder PNG
# ---------------------------------------------------------------------------


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    payload = tag + data
    return (struct.pack(">I", len(data)) + payload
            + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF))


def make_placeholder_png(w: int = 128, h: int = 128) -> bytes:
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            t = (x + y) / (w + h)
            r = int(20 + 40 * t)
            g = int(80 + 100 * t)
            b = int(160 + 80 * t)
            cx, cy = w / 2.0, h / 2.0
            dx, dy = abs(x - cx) / cx, abs(y - cy) / cy
            a = 0 if (dx > 0.88 and dy > 0.88) else 255
            raw += bytes((r, g, b, a))
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 9)
    return sig + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b"")


def install_texture(repo: Path, custom: Path | None, dry_run: bool) -> None:
    dst = repo / TEXTURE_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    if custom is not None:
        if not custom.is_file():
            die(f"--custom-logo not found: {custom}")
        if dst.exists() and dst.read_bytes() == custom.read_bytes():
            log(f"logo already in place: {TEXTURE_REL}")
            return
        log(f"copying logo -> {TEXTURE_REL}")
        if not dry_run:
            shutil.copyfile(custom, dst)
        return
    if dst.exists():
        log(f"logo already present: {TEXTURE_REL}")
        return
    log(f"generating placeholder logo: {TEXTURE_REL}")
    if not dry_run:
        dst.write_bytes(make_placeholder_png())


# ---------------------------------------------------------------------------
# build.gradle — add coremod manifest attributes
# ---------------------------------------------------------------------------


def patch_build_gradle(repo: Path, dry_run: bool, enable_coremod: bool) -> bool:
    """Ensure a `jar { manifest { ... } }` block exists if coremod is on."""
    if not enable_coremod:
        log("skipping build.gradle coremod patch (--no-coremod)")
        return False

    path = repo / BUILD_GRADLE_REL
    if not path.is_file():
        warn("build.gradle not found; skipping coremod manifest patch")
        return False

    text = path.read_text(encoding="utf-8")

    # Already present?
    if CORE_PLUGIN_CLASS in text:
        log("build.gradle already declares the coremod")
        return False

    block = (
        "\n"
        "jar {\n"
        "    manifest {\n"
        f"        attributes(\n"
        f"            'FMLCorePlugin': '{CORE_PLUGIN_CLASS}',\n"
        f"            'FMLCorePluginContainsFMLMod': 'true'\n"
        "        )\n"
        "    }\n"
        "}\n"
    )

    log("appending coremod manifest block to build.gradle")
    if not dry_run:
        path.write_text(text.rstrip() + "\n" + block, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


def rewrite_workflow(repo: Path, dry_run: bool) -> bool:
    wf = repo / WORKFLOW_REL
    if not wf.is_file():
        warn(f"workflow not found: {WORKFLOW_REL}")
        return False

    original = wf.read_text(encoding="utf-8")

    step_re = re.compile(
        r"(?P<indent>[ \t]*)-[ \t]*name:[ \t]*Upload jar[ \t]*\r?\n"
        r"(?P<body>(?:[ \t]+[^\n]*\r?\n)+)",
        re.MULTILINE,
    )
    m = step_re.search(original)
    if not m:
        warn("could not locate 'Upload jar' step; workflow untouched")
        return False

    indent = m.group("indent")
    desired = (
        f"{indent}- name: Upload jar\n"
        f"{indent}  uses: actions/upload-artifact@v4\n"
        f"{indent}  with:\n"
        f"{indent}    name: {ARTIFACT_NAME}\n"
        f"{indent}    path: |\n"
        f"{indent}      {ARTIFACT_PATH}\n"
        f"{indent}      {ARTIFACT_EXCLUDE}\n"
        f"{indent}    if-no-files-found: error\n"
    )

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
            if STALE_REF.search(p.read_text(encoding="utf-8", errors="replace")):
                out.append(p)
        except OSError:
            pass
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fix the repo and install a full-startup loading screen.",
    )
    p.add_argument("--repo", type=Path, default=None)
    p.add_argument("--custom-logo", type=Path, default=None)
    p.add_argument("--no-backup", action="store_true")
    p.add_argument("--no-coremod", action="store_true",
                   help="skip the ASM transformer / FMLCorePlugin patch")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.repo is not None:
        repo = args.repo.resolve()
        if not is_repo_root(repo):
            die(f"{repo} has no build.gradle")
    else:
        repo = find_repo_root(Path(__file__).resolve().parent)

    log(f"repository: {repo}")
    if args.dry_run:
        log("DRY RUN — nothing will be written")

    if not args.no_backup and not args.dry_run:
        backup_repo(repo)
    elif args.no_backup:
        log("backup disabled")

    removed = remove_broken_package(repo, args.dry_run)

    # Loading system
    writes = {
        "LoadingPhase.java":           (LOADING_PKG / "LoadingPhase.java",            LOADING_PHASE_JAVA),
        "LoadingProgress.java":        (LOADING_PKG / "LoadingProgress.java",         LOADING_PROGRESS_JAVA),
        "CustomLoadingScreen.java":    (LOADING_PKG / "CustomLoadingScreen.java",     CUSTOM_LOADING_JAVA),
        "LoadingScreenHook.java":      (LOADING_PKG / "LoadingScreenHook.java",       LOADING_SCREEN_HOOK_JAVA),
        "LoadingProgressHandler.java": (LOADING_PKG / "LoadingProgressHandler.java",  LOADING_PROGRESS_HANDLER_JAVA),
        "TerrainLoadListener.java":    (LOADING_PKG / "TerrainLoadListener.java",     TERRAIN_LOAD_LISTENER_JAVA),
    }

    # Coremod (optional)
    if not args.no_coremod:
        writes["LoadingScreenTransformer.java"] = (
            CORE_PKG / "LoadingScreenTransformer.java", LOADING_SCREEN_TRANSFORMER_JAVA)
        writes["AsyncMenusLoadingPlugin.java"] = (
            CORE_PKG / "AsyncMenusLoadingPlugin.java",  LOADING_PLUGIN_JAVA)

    # Mod entry point (always)
    writes["AsyncMenus.java"] = (ASYNC_MENUS_REL, ASYNC_MENUS_JAVA)

    changed = 0
    for _, (path, content) in writes.items():
        if write_text(repo / path, content, args.dry_run):
            changed += 1

    install_texture(repo, args.custom_logo, args.dry_run)

    changed_gradle = patch_build_gradle(repo, args.dry_run, not args.no_coremod)
    changed_wf     = rewrite_workflow(repo, args.dry_run)

    offenders = find_stale_refs(repo)
    if offenders:
        warn("files still referencing 'com.oryvex':")
        for p in offenders:
            print(f"    {p.relative_to(repo)}", file=sys.stderr)

    print()
    log("summary")
    log(f"  broken package removed : {removed}")
    log(f"  java files written     : {changed}")
    log(f"  build.gradle patched   : {changed_gradle}")
    log(f"  workflow rewritten     : {changed_wf}")
    log(f"  coremod enabled        : {not args.no_coremod}")
    log(f"  stale references       : {len(offenders)}")

    return 0 if not offenders else 2


if __name__ == "__main__":
    sys.exit(main())