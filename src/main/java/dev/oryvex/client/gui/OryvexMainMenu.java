package dev.oryvex.client.gui;

import dev.oryvex.client.util.Render;
import dev.oryvex.client.util.Theme;
import net.minecraft.client.gui.GuiMultiplayer;
import net.minecraft.client.gui.GuiOptions;
import net.minecraft.client.gui.GuiScreen;
import net.minecraft.client.gui.GuiSelectWorld;
import net.minecraft.client.renderer.GlStateManager;
import net.minecraftforge.fml.client.GuiModList;

import java.awt.Color;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class OryvexMainMenu extends GuiScreen {
    private static final int PARTICLES = 60;

    private static class Btn {
        int x, y, w, h;
        String label;
        Runnable action;
    }

    private final List<Btn> buttons = new ArrayList<Btn>();
    private final float[] ppx = new float[PARTICLES];
    private final float[] ppy = new float[PARTICLES];
    private final float[] pspeed = new float[PARTICLES];
    private final int[] palpha = new int[PARTICLES];
    private long last = System.currentTimeMillis();

    private void add(int x, int y, int w, String label, Runnable action) {
        Btn b = new Btn();
        b.x = x; b.y = y; b.w = w; b.h = 22; b.label = label; b.action = action;
        buttons.add(b);
    }

    @Override public void initGui() {
        buttons.clear();
        Random r = new Random(1337);
        for (int i = 0; i < PARTICLES; i++) {
            ppx[i] = r.nextFloat() * width;
            ppy[i] = r.nextFloat() * height;
            pspeed[i] = 4 + r.nextFloat() * 16;
            palpha[i] = 40 + r.nextInt(90);
        }

        int bw = 200, cx = width / 2 - bw / 2, y = height / 2 - 24;
        add(cx, y, bw, "Singleplayer", () -> mc.displayGuiScreen(new GuiSelectWorld(this)));
        add(cx, y + 28, bw, "Multiplayer", () -> mc.displayGuiScreen(new GuiMultiplayer(this)));
        add(cx, y + 56, bw, "Client Settings", () -> mc.displayGuiScreen(new OryvexMenu(this)));
        add(cx, y + 84, 98, "Options", () -> mc.displayGuiScreen(new GuiOptions(this, mc.gameSettings)));
        add(cx + 102, y + 84, 98, "Mods", () -> mc.displayGuiScreen(new GuiModList(this)));
        add(cx, y + 112, bw, "Quit Game", () -> mc.shutdown());
    }

    @Override public void drawScreen(int mx, int my, float partial) {
        long now = System.currentTimeMillis();
        float dt = Math.min(0.1f, (now - last) / 1000f);
        last = now;
        float t = (now % 20000L) / 20000f;
        double wave = Math.sin(t * Math.PI * 2);

        int top = Color.HSBtoRGB((float) (0.72 + 0.04 * wave), 0.65f, 0.20f);
        int bottom = Color.HSBtoRGB((float) (0.56 - 0.03 * wave), 0.75f, 0.10f);
        Render.vGradient(0, 0, width, height, top, bottom);

        for (int i = 0; i < PARTICLES; i++) {
            ppy[i] -= pspeed[i] * dt;
            if (ppy[i] < 0) ppy[i] = height;
            drawRect((int) ppx[i], (int) ppy[i], (int) ppx[i] + 2, (int) ppy[i] + 2, Render.alpha(0xFFFFFF, palpha[i]));
        }

        // title
        GlStateManager.pushMatrix();
        GlStateManager.translate(width / 2f, height / 2f - 88, 0);
        GlStateManager.scale(4f, 4f, 1f);
        String title = "ORYVEX";
        fontRendererObj.drawStringWithShadow(title, -fontRendererObj.getStringWidth(title) / 2f, 0, Theme.TEXT);
        GlStateManager.popMatrix();
        Render.hGradient(width / 2 - 60, height / 2 - 48, 120, 2, Theme.ACCENT, Theme.ACCENT2);
        drawCenteredString(fontRendererObj, "C L I E N T   |   1 . 8 . 8", width / 2, height / 2 - 40, Theme.ACCENT2);

        for (Btn b : buttons) {
            boolean hover = Render.inside(mx, my, b.x, b.y, b.w, b.h);
            Render.roundedRect(b.x, b.y, b.w, b.h, 5, hover ? 0xE0302848 : 0xB0121218);
            if (hover) Render.roundedRect(b.x, b.y + 3, 3, b.h - 6, 1, Theme.ACCENT2);
            drawCenteredString(fontRendererObj, b.label, b.x + b.w / 2, b.y + 7, hover ? Theme.TEXT : 0xFFD0D0E0);
        }

        String foot = "OryvexClient v1.0.0  -  Not affiliated with Mojang AB";
        fontRendererObj.drawString(foot, 6, height - 12, Theme.TEXT_DIM);
    }

    @Override protected void mouseClicked(int mx, int my, int button) throws IOException {
        super.mouseClicked(mx, my, button);
        if (button != 0) return;
        for (Btn b : buttons) {
            if (Render.inside(mx, my, b.x, b.y, b.w, b.h)) {
                b.action.run();
                return;
            }
        }
    }

    @Override protected void keyTyped(char c, int key) throws IOException {
        // ESC does nothing on the main menu
    }

    @Override public boolean doesGuiPauseGame() { return false; }
}
