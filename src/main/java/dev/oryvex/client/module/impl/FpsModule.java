package dev.oryvex.client.module.impl;

import dev.oryvex.client.module.TextHudModule;
import net.minecraft.client.Minecraft;

public class FpsModule extends TextHudModule {
    public FpsModule() { super("FPS", "Shows your frame rate", true, 6, 6); }
    @Override protected String label() { return "FPS"; }
    @Override protected String value() { return String.valueOf(Minecraft.getDebugFPS()); }
}
