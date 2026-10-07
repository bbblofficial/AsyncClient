package com.example.asyncmenus;

import net.minecraft.client.gui.GuiScreenResourcePacks;
import net.minecraftforge.client.event.GuiOpenEvent;
import net.minecraftforge.client.event.GuiScreenEvent;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

public class ResourcePackScreenHandler {
    private static final Logger LOG = LogManager.getLogger(AsyncMenus.MODID);
    private AsyncPackSession session;

    @SubscribeEvent
    public void onInitPre(GuiScreenEvent.InitGuiEvent.Pre e) {
        // Exact class match: subclasses from other mods are left untouched.
        if (e.gui == null || e.gui.getClass() != GuiScreenResourcePacks.class) return;
        if (!PackScreenReflection.isAvailable()) return;

        GuiScreenResourcePacks screen = (GuiScreenResourcePacks) e.gui;
        try {
            if (session == null || session.screen != screen) {
                closeSession();
                session = new AsyncPackSession(screen);
            }
            session.buildGui(e.buttonList);
            e.setCanceled(true); // skip vanilla's blocking initGui
        } catch (Throwable t) {
            LOG.error("Async resource pack screen failed, falling back to vanilla", t);
            closeSession(); // event not cancelled -> vanilla initGui runs
        }
    }

    @SubscribeEvent
    public void onGuiOpen(GuiOpenEvent e) {
        if (session != null && e.gui != session.screen) closeSession();
    }

    @SubscribeEvent
    public void onDrawPre(GuiScreenEvent.DrawScreenEvent.Pre e) {
        if (session != null && e.gui == session.screen) session.drain();
    }

    @SubscribeEvent
    public void onDrawPost(GuiScreenEvent.DrawScreenEvent.Post e) {
        if (session != null && e.gui == session.screen) session.drawStatus();
    }

    private void closeSession() {
        if (session != null) {
            session.cancel();
            session = null;
        }
    }
}
