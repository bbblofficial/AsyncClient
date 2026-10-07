package com.example.asyncmenus;

import java.io.File;
import java.util.Enumeration;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

import net.minecraft.client.Minecraft;
import net.minecraftforge.client.event.GuiOpenEvent;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;

/**
 * Warms the OS file cache for the shaderpacks folder in the background when the options screens open.
 * This does NOT make OptiFine's own shader list async; it only reduces the cost of its later synchronous scan.
 */
public class ShaderPackPrefetcher {
    private static final String[] OPTIFINE_MARKERS = {"net.optifine.shaders.Shaders", "shadersmod.client.Shaders"};

    private final boolean optifine = detectOptiFine();
    private final AtomicBoolean running = new AtomicBoolean();
    private volatile long lastRun;

    private boolean detectOptiFine() {
        for (String name : OPTIFINE_MARKERS) {
            try {
                Class.forName(name, false, getClass().getClassLoader());
                return true;
            } catch (Throwable ignored) {}
        }
        return false;
    }

    @SubscribeEvent
    public void onGuiOpen(GuiOpenEvent e) {
        if (!optifine || e.gui == null) return;
        String n = e.gui.getClass().getSimpleName();
        if (!n.equals("GuiOptions") && !n.equals("GuiVideoSettings")) return;

        long now = System.currentTimeMillis();
        if (now - lastRun < 30_000L || !running.compareAndSet(false, true)) return;
        lastRun = now;

        Thread t = new Thread(this::warm, "AsyncMenus-ShaderPrefetch");
        t.setDaemon(true);
        t.start();
    }

    private void warm() {
        try {
            File[] files = new File(Minecraft.getMinecraft().mcDataDir, "shaderpacks").listFiles();
            if (files == null) return;
            for (File f : files) {
                if (f.isFile() && f.getName().toLowerCase().endsWith(".zip")) {
                    try (ZipFile zip = new ZipFile(f)) {
                        Enumeration<? extends ZipEntry> en = zip.entries(); // reads the central directory
                        while (en.hasMoreElements()) en.nextElement();
                    } catch (Exception ignored) {}
                } else if (f.isDirectory()) {
                    new File(f, "shaders").list();
                }
            }
        } finally {
            running.set(false);
        }
    }
}
