package com.example.asyncmenus.loading;

import net.minecraft.client.LoadingScreenRenderer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.FontRenderer;
import net.minecraft.client.gui.ScaledResolution;
import net.minecraft.client.renderer.GlStateManager;
import net.minecraft.client.renderer.Tessellator;
import net.minecraft.client.renderer.WorldRenderer;
import net.minecraft.client.renderer.vertex.DefaultVertexFormats;
import net.minecraft.util.ResourceLocation;
import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.GL11;

/**
 * Custom loading screen shown from the earliest possible frame until
 * the main menu / a world is ready. Draws whatever LoadingProgress
 * currently holds, so it works for every startup phase.
 */
public class CustomLoadingScreen extends LoadingScreenRenderer {

    private static final ResourceLocation LOGO =
            new ResourceLocation("asyncmenus", "textures/gui/custom_loading.png");

    private final Minecraft mc;

    public CustomLoadingScreen(Minecraft mc) {
        super(mc);
        this.mc = mc;
    }

    // --- LoadingScreenRenderer API used by vanilla --------------------

    @Override public void resetProgressAndMessage(String message) {
        LoadingProgress.setMessage(message);
        LoadingProgress.setPhase(LoadingPhase.START_GAME);
        render();
    }

    @Override public void displaySavingString(String message) {
        LoadingProgress.setMessage(message);
        render();
    }

    @Override public void setLoadingProgress(int progress) {
        LoadingProgress.setSub(progress / 100f);
        render();
    }

    @Override public void setDoneWorking() {
        LoadingProgress.setScreenActive(false);
    }

    // --- Called by the progress handler each client tick --------------

    /** Render one frame. Safe to call from the client thread only. */
    public void tick() {
        if (!LoadingProgress.isScreenActive()) return;
        render();
    }

    // -----------------------------------------------------------------

    private void render() {
        if (mc == null || !Display.isCreated()) return;

        ScaledResolution sr = new ScaledResolution(mc);
        int sw = sr.getScaledWidth();
        int sh = sr.getScaledHeight();

        GlStateManager.clearColor(0.06F, 0.06F, 0.08F, 1.0F);
        GlStateManager.clear(16640);

        GlStateManager.matrixMode(GL11.GL_PROJECTION);
        GlStateManager.loadIdentity();
        GlStateManager.ortho(0.0D, sw, sh, 0.0D, 1000.0D, 3000.0D);
        GlStateManager.matrixMode(GL11.GL_MODELVIEW);
        GlStateManager.loadIdentity();
        GlStateManager.translate(0.0F, 0.0F, -2000.0F);

        GlStateManager.disableLighting();
        GlStateManager.disableFog();
        GlStateManager.disableDepth();
        GlStateManager.enableTexture2D();
        GlStateManager.enableBlend();
        GlStateManager.color(1F, 1F, 1F, 1F);

        try {
            mc.getTextureManager().bindTexture(LOGO);
            int lw = 128, lh = 128;
            drawTexturedQuad((sw - lw) / 2, (sh - lh) / 2 - 50, lw, lh);
        } catch (Throwable ignored) {}

        FontRenderer fr = mc.fontRendererObj;

        LoadingPhase phase = LoadingProgress.getPhase();
        int percent = LoadingProgress.getPercent();
        String custom = LoadingProgress.getCustomMessage();

        String title = phase.label;
        fr.drawStringWithShadow(title,
                (sw - fr.getStringWidth(title)) / 2, sh / 2 + 50, 0xFFFFFF);

        if (!custom.isEmpty()) {
            fr.drawStringWithShadow(custom,
                    (sw - fr.getStringWidth(custom)) / 2, sh / 2 + 66, 0xAAAAAA);
        }

        String pctStr = percent + "%";
        fr.drawStringWithShadow(pctStr,
                (sw - fr.getStringWidth(pctStr)) / 2, sh / 2 + 82, 0xCCCCCC);

        int barW = 240, barH = 5;
        int barX = (sw - barW) / 2;
        int barY = sh / 2 + 100;

        drawRect(barX - 1, barY - 1, barX + barW + 1, barY + barH + 1, 0xFF333333);
        drawRect(barX, barY, barX + barW, barY + barH, 0xFF555555);
        if (percent > 0) {
            int fw = barW * percent / 100;
            drawRect(barX, barY, barX + fw, barY + barH, 0xFF4FC3F7);
        }

        Display.update();
    }

    private static void drawTexturedQuad(int x, int y, int w, int h) {
        Tessellator t = Tessellator.getInstance();
        WorldRenderer wr = t.getWorldRenderer();
        wr.begin(7, DefaultVertexFormats.POSITION_TEX);
        wr.pos(x,     y + h, 0).tex(0.0D, 1.0D).endVertex();
        wr.pos(x + w, y + h, 0).tex(1.0D, 1.0D).endVertex();
        wr.pos(x + w, y,     0).tex(1.0D, 0.0D).endVertex();
        wr.pos(x,     y,     0).tex(0.0D, 0.0D).endVertex();
        t.draw();
    }

    private static void drawRect(int l, int t, int r, int b, int color) {
        if (l < r) { int s = l; l = r; r = s; }
        if (t < b) { int s = t; t = b; b = s; }

        float a  = (color >> 24 & 0xFF) / 255.0F;
        float cr = (color >> 16 & 0xFF) / 255.0F;
        float cg = (color >>  8 & 0xFF) / 255.0F;
        float cb = (color       & 0xFF) / 255.0F;

        Tessellator tess = Tessellator.getInstance();
        WorldRenderer wr = tess.getWorldRenderer();
        GlStateManager.disableTexture2D();
        GlStateManager.color(cr, cg, cb, a);
        wr.begin(7, DefaultVertexFormats.POSITION);
        wr.pos(l, b, 0).endVertex();
        wr.pos(r, b, 0).endVertex();
        wr.pos(r, t, 0).endVertex();
        wr.pos(l, t, 0).endVertex();
        tess.draw();
        GlStateManager.enableTexture2D();
        GlStateManager.color(1F, 1F, 1F, 1F);
    }
}
