package com.example.asyncmenus.loading;

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
