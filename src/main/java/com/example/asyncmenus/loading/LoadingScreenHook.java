package com.example.asyncmenus.loading;

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
