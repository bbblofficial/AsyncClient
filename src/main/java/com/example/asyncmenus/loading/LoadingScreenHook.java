package com.example.asyncmenus.loading;

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
