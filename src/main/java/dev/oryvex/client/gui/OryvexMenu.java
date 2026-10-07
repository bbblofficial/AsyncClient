package dev.oryvex.client.gui;

import dev.oryvex.client.OryvexClient;
import dev.oryvex.client.module.HudModule;
import dev.oryvex.client.module.Module;
import dev.oryvex.client.util.Render;
import dev.oryvex.client.util.Theme;
import net.minecraft.client.gui.GuiScreen;
import net.minecraft.client.renderer.GlStateManager;
import org.lwjgl.input.Keyboard;

import java.io.IOException;
import java.util.List;

/** Mod menu + HUD editor (drag enabled HUD elements around while it is open). */
public class OryvexMenu extends GuiScreen {
    private static final int W = 380, H = 252, GAP = 6, CARD_H = 30;

    private final GuiScreen parent;
    private int px, py;
    private HudModule dragging;
    private int offX, offY;

    public OryvexMenu(GuiScreen parent) {
        this.parent = parent;
    }

    @Override public void initGui() {
        px = (width - W) / 2;
        py = (height - H) / 2;
    }

    private int cardW() { return (W - 24 - GAP) / 2; }
    private int cardX(int i) { return px + 12 + (i % 2) * (cardW() + GAP); }
    private int cardY(int i) { return py + 46 + (i / 2) * (CARD_H + GAP); }

    @Override public void drawScreen(int mx, int my, float partial) {
        Render.vGradient(0, 0, width, height, 0x50000000, 0xB0000000);

        for (HudModule m : OryvexClient.modules.huds()) {
            if (!m.enabled) continue;
            Render.outline(m.x - 1, m.y - 1, m.getWidth() + 2, m.getHeight() + 2,
                    m == dragging ? Theme.ACCENT2 : Theme.ACCENT_DIM);
        }

        Render.roundedRect(px, py, W, H, 8, Theme.BG);

        GlStateManager.pushMatrix();
        GlStateManager.translate(px + 14, py + 12, 0);
        GlStateManager.scale(1.6f, 1.6f, 1f);
        fontRendererObj.drawStringWithShadow("ORYVEX", 0, 0, Theme.TEXT);
        GlStateManager.popMatrix();
        fontRendererObj.drawStringWithShadow("CLIENT", px + 14 + fontRendererObj.getStringWidth("ORYVEX") * 1.6f + 5, py + 17, Theme.ACCENT2);
        String ver = "v1.0.0  |  1.8.8";
        fontRendererObj.drawStringWithShadow(ver, px + W - 14 - fontRendererObj.getStringWidth(ver), py + 17, Theme.TEXT_DIM);
        Render.hGradient(px + 12, py + 34, W - 24, 2, Theme.ACCENT, Theme.ACCENT2);

        List<Module> list = OryvexClient.modules.all();
        for (int i = 0; i < list.size(); i++) {
            Module m = list.get(i);
            int cx = cardX(i), cy = cardY(i), cw = cardW();
            boolean hover = Render.inside(mx, my, cx, cy, cw, CARD_H);
            Render.roundedRect(cx, cy, cw, CARD_H, 5, hover ? Theme.CARD_HOVER : Theme.CARD);
            fontRendererObj.drawStringWithShadow(m.name, cx + 10, cy + 6, Theme.TEXT);
            fontRendererObj.drawString(fontRendererObj.trimStringToWidth(m.description, cw - 56), cx + 10, cy + 18, Theme.TEXT_DIM);

            int sw = 24, sh = 12;
            int sx = cx + cw - sw - 10, sy = cy + (CARD_H - sh) / 2;
            Render.roundedRect(sx, sy, sw, sh, 6, m.enabled ? Theme.ACCENT : 0xFF3A3A4A);
            int kx = m.enabled ? sx + sw - sh + 2 : sx + 2;
            Render.roundedRect(kx, sy + 2, sh - 4, sh - 4, 4, 0xFFFFFFFF);
        }

        String hint = "Drag HUD elements anywhere  |  " + Keyboard.getKeyName(OryvexClient.menuKey.getKeyCode()) + " to close";
        fontRendererObj.drawString(hint, px + (W - fontRendererObj.getStringWidth(hint)) / 2, py + H - 16, Theme.TEXT_DIM);
    }

    @Override protected void mouseClicked(int mx, int my, int button) throws IOException {
        super.mouseClicked(mx, my, button);
        if (button != 0) return;

        List<Module> list = OryvexClient.modules.all();
        for (int i = 0; i < list.size(); i++) {
            if (Render.inside(mx, my, cardX(i), cardY(i), cardW(), CARD_H)) {
                list.get(i).toggle();
                return;
            }
        }
        if (Render.inside(mx, my, px, py, W, H)) return;

        List<HudModule> huds = OryvexClient.modules.huds();
        for (int i = huds.size() - 1; i >= 0; i--) {
            HudModule m = huds.get(i);
            if (m.enabled && m.hit(mx, my)) {
                dragging = m;
                offX = mx - m.x;
                offY = my - m.y;
                return;
            }
        }
    }

    @Override protected void mouseClickMove(int mx, int my, int button, long time) {
        if (dragging == null) return;
        dragging.x = Math.max(0, Math.min(width - dragging.getWidth(), mx - offX));
        dragging.y = Math.max(0, Math.min(height - dragging.getHeight(), my - offY));
    }

    @Override protected void mouseReleased(int mx, int my, int state) {
        super.mouseReleased(mx, my, state);
        dragging = null;
    }

    @Override protected void keyTyped(char c, int key) throws IOException {
        if (key == Keyboard.KEY_ESCAPE || key == OryvexClient.menuKey.getKeyCode()) {
            mc.displayGuiScreen(parent);
            return;
        }
        super.keyTyped(c, key);
    }

    @Override public void onGuiClosed() {
        OryvexClient.modules.save();
    }

    @Override public boolean doesGuiPauseGame() { return false; }
}
