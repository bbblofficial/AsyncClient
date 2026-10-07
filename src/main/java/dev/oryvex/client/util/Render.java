package dev.oryvex.client.util;

import net.minecraft.client.gui.Gui;

public final class Render {
    private Render() {}

    private static int ch(int a, int b, int shift, float t) {
        int ca = (a >> shift) & 255;
        int cb = (b >> shift) & 255;
        return ((int) (ca + (cb - ca) * t)) & 255;
    }

    public static int lerp(int a, int b, float t) {
        t = Math.max(0f, Math.min(1f, t));
        return (ch(a, b, 24, t) << 24) | (ch(a, b, 16, t) << 16) | (ch(a, b, 8, t) << 8) | ch(a, b, 0, t);
    }

    public static int alpha(int rgb, int a) {
        return ((a & 255) << 24) | (rgb & 0xFFFFFF);
    }

    /** Rounded rectangle built from non-overlapping rects (safe for translucent colors). */
    public static void roundedRect(int x, int y, int w, int h, int r, int color) {
        r = Math.max(0, Math.min(r, Math.min(w, h) / 2));
        if (r == 0) {
            Gui.drawRect(x, y, x + w, y + h, color);
            return;
        }
        Gui.drawRect(x + r, y, x + w - r, y + h, color);
        Gui.drawRect(x, y + r, x + r, y + h - r, color);
        Gui.drawRect(x + w - r, y + r, x + w, y + h - r, color);
        for (int i = 0; i < r; i++) {
            double dy = r - i - 0.5;
            int inset = (int) Math.round(r - Math.sqrt(r * r - dy * dy));
            Gui.drawRect(x + inset, y + i, x + r, y + i + 1, color);
            Gui.drawRect(x + w - r, y + i, x + w - inset, y + i + 1, color);
            Gui.drawRect(x + inset, y + h - 1 - i, x + r, y + h - i, color);
            Gui.drawRect(x + w - r, y + h - 1 - i, x + w - inset, y + h - i, color);
        }
    }

    public static void outline(int x, int y, int w, int h, int color) {
        Gui.drawRect(x, y, x + w, y + 1, color);
        Gui.drawRect(x, y + h - 1, x + w, y + h, color);
        Gui.drawRect(x, y + 1, x + 1, y + h - 1, color);
        Gui.drawRect(x + w - 1, y + 1, x + w, y + h - 1, color);
    }

    public static void vGradient(int x, int y, int w, int h, int top, int bottom) {
        for (int i = 0; i < h; i++) {
            Gui.drawRect(x, y + i, x + w, y + i + 1, lerp(top, bottom, i / (float) h));
        }
    }

    public static void hGradient(int x, int y, int w, int h, int left, int right) {
        for (int i = 0; i < w; i++) {
            Gui.drawRect(x + i, y, x + i + 1, y + h, lerp(left, right, i / (float) w));
        }
    }

    public static boolean inside(int mx, int my, int x, int y, int w, int h) {
        return mx >= x && mx < x + w && my >= y && my < y + h;
    }
}
