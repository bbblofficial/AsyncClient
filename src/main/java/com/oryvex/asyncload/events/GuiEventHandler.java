package com.oryvex.asyncload.events;

import com.oryvex.asyncload.gui.AsyncResourcePackGui;
import net.minecraft.client.gui.GuiScreenResourcePacks;
import net.minecraftforge.client.event.GuiOpenEvent;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;

public class GuiEventHandler {

    @SubscribeEvent
    public void onGuiOpen(GuiOpenEvent event) {
        if (event.gui instanceof GuiScreenResourcePacks && !(event.gui instanceof AsyncResourcePackGui)) {
            GuiScreenResourcePacks original = (GuiScreenResourcePacks) event.gui;
            event.gui = new AsyncResourcePackGui(null);
        }
        
        if (event.gui != null && event.gui.getClass().getName().equals("net.optifine.gui.GuiShaders")) {
            // Future implementation for Shaders menu
        }
    }
}
