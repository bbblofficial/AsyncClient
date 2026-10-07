package com.example.asyncmenus.loading;

import net.minecraft.client.gui.GuiMainMenu;
import net.minecraftforge.client.event.GuiOpenEvent;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.fml.common.gameevent.TickEvent;
import net.minecraftforge.fml.relauncher.Side;
import net.minecraftforge.fml.relauncher.SideOnly;

/**
 * Handles only real Forge Event subclasses.
 *
 * FML lifecycle events (FMLPreInitializationEvent, FMLInitializationEvent,
 * FMLPostInitializationEvent, FMLConstructionEvent) are NOT subclasses of
 * net.minecraftforge.fml.common.eventhandler.Event, so they MUST be wired
 * via @Mod.EventHandler on the mod class rather than @SubscribeEvent here.
 */
@SideOnly(Side.CLIENT)
public class LoadingProgressHandler {

    @SubscribeEvent
    public void onClientTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        CustomLoadingScreen screen = LoadingScreenHook.getActiveScreen();
        if (screen == null || !LoadingProgress.isScreenActive()) return;
        try { screen.tick(); } catch (Throwable ignored) {}
    }

    @SubscribeEvent
    public void onGuiOpen(GuiOpenEvent e) {
        if (e.gui instanceof GuiMainMenu) {
            LoadingProgress.setPhase(LoadingPhase.DONE);
            LoadingProgress.setScreenActive(false);
        }
    }
}
