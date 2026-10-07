package dev.oryvex.client.module.impl;

import dev.oryvex.client.module.HudModule;
import dev.oryvex.client.util.Render;
import dev.oryvex.client.util.Theme;
import net.minecraft.client.settings.KeyBinding;

public class KeystrokesModule extends HudModule {
    private static final int PRESSED = 0xC08B5CF6;

    public KeystrokesModule() { super("Keystrokes", "WASD and mouse buttons", true, 6, 110); }

    @Override public int getWidth() { return 64; }
    @Override public int getHeight() { return 64; }

    private void key(String label, KeyBinding kb, int kx, int ky, int w) {
        boolean down = kb.isKeyDown();
        Render.roundedRect(kx, ky, w, 20, 4, down ? PRESSED : Theme.HUD_BG);
        int tw = mc.fontRendererObj.getStringWidth(label);
        mc.fontRendererObj.drawStringWithShadow(label, kx + (w - tw) / 2f, ky + 6, Theme.TEXT);
    }

    @Override public void render() {
        key("W", mc.gameSettings.keyBindForward, x + 22, y, 20);
        key("A", mc.gameSettings.keyBindLeft, x, y + 22, 20);
        key("S", mc.gameSettings.keyBindBack, x + 22, y + 22, 20);
        key("D", mc.gameSettings.keyBindRight, x + 44, y + 22, 20);
        key("LMB", mc.gameSettings.keyBindAttack, x, y + 44, 31);
        key("RMB", mc.gameSettings.keyBindUseItem, x + 33, y + 44, 31);
    }
}
