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
 * Replaces vanilla's Mojang loading screen.
 * Extends LoadingScreenRenderer so it can be dropped into Minecraft.loadingScreen.
 */
public class CustomLoadingScreen extends LoadingScreenRenderer {

    /** Replace this PNG with your own logo. Put it under src/main/resources. */
    private static final ResourceLocation LOGO =
            new ResourceLocation("asyncmenus", "textures/gui/custom_loading.png");

    private final Minecraft mc;
    private String title = "";
    private String message = "";
    private int progress;

    public CustomLoadingScreen(Minecraft mc) {
        super(mc);
        this.mc = mc;
    }

    @Override public void resetProgressAndMessage(String message) { this.title = message; this.message = ""; render(); }
    @Override public void displaySavingString(String message)     { this.message = message;                  render(); }
    @Override public void setLoadingProgress(int progress)        { this.progress = progress;                render(); }
    @Override public void setDoneWorking()                        { /* stop drawing */ }

    // -----------------------------------------------------------------
    // Rendering
    // -----------------------------------------------------------------

    private void render() {
        if (mc == null || !Display.isCreated()) return;

        ScaledResolution sr = new ScaledResolution(mc);
        int sw = sr.getScaledWidth();
        int sh = sr.getScaledHeight();

        // Background
        GlStateManager.clearColor(0.06F, 0.06F, 0.08F, 1.0F);
        GlStateManager.clear(16640); // GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT

        // Orthographic 2D projection
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

        // Logo
        try {
            mc.getTextureManager().bindTexture(LOGO);
            int lw = 128, lh = 128;
            drawTexturedQuad((sw - lw) / 2, (sh - lh) / 2 - 40, lw, lh);
        } catch (Throwable ignored) { /* missing texture - text only */ }

        FontRenderer fr = mc.fontRendererObj;

        if (!title.isEmpty())
            fr.drawStringWithShadow(title, (sw - fr.getStringWidth(title)) / 2, sh / 2 + 60, 0xFFFFFF);
        if (!message.isEmpty())
            fr.drawStringWithShadow(message, (sw - fr.getStringWidth(message)) / 2, sh / 2 + 76, 0xAAAAAA);

        // Progress bar
        int barW = 200, barH = 4;
        int barX = (sw - barW) / 2;
        int barY = sh / 2 + 100;

        drawRect(barX - 1, barY - 1, barX + barW + 1, barY + barH + 1, 0xFF333333);
        drawRect(barX, barY, barX + barW, barY + barH, 0xFF555555);
        if (progress > 0) {
            int fw = barW * Math.min(progress, 100) / 100;
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
