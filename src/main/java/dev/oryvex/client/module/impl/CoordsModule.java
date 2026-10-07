package dev.oryvex.client.module.impl;

import dev.oryvex.client.module.HudModule;
import dev.oryvex.client.util.Theme;
import net.minecraft.util.MathHelper;

import java.util.Locale;

public class CoordsModule extends HudModule {
    private static final String[] DIRS = {"South", "West", "North", "East"};

    public CoordsModule() { super("Coordinates", "XYZ position and facing", true, 6, 60); }

    private String[] lines() {
        if (mc.thePlayer == null) return new String[]{"X: 0.0", "Y: 0.0", "Z: 0.0", "Facing: South"};
        int dir = MathHelper.floor_double((double) (mc.thePlayer.rotationYaw * 4.0F / 360.0F) + 0.5D) & 3;
        return new String[]{
                String.format(Locale.US, "X: %.1f", mc.thePlayer.posX),
                String.format(Locale.US, "Y: %.1f", mc.thePlayer.posY),
                String.format(Locale.US, "Z: %.1f", mc.thePlayer.posZ),
                "Facing: " + DIRS[dir]
        };
    }

    @Override public int getWidth() {
        int w = 70;
        for (String s : lines()) w = Math.max(w, mc.fontRendererObj.getStringWidth(s) + 12);
        return w;
    }

    @Override public int getHeight() { return 4 * 10 + 6; }

    @Override public void render() {
        panel();
        String[] l = lines();
        for (int i = 0; i < l.length; i++) {
            int c = i == 3 ? Theme.ACCENT2 : Theme.TEXT;
            mc.fontRendererObj.drawStringWithShadow(l[i], x + 6, y + 4 + i * 10, c);
        }
    }
}
