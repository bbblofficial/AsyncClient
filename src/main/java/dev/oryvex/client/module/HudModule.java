package dev.oryvex.client.module;

import dev.oryvex.client.util.Render;
import dev.oryvex.client.util.Theme;

public abstract class HudModule extends Module {
    public int x, y;

    protected HudModule(String name, String description, boolean enabled, int x, int y) {
        super(name, description, enabled);
        this.x = x;
        this.y = y;
    }

    public abstract int getWidth();
    public abstract int getHeight();
    /** Draw the module at (x, y). */
    public abstract void render();

    protected void panel() {
        Render.roundedRect(x, y, getWidth(), getHeight(), 4, Theme.HUD_BG);
    }

    public boolean hit(int mx, int my) {
        return Render.inside(mx, my, x, y, getWidth(), getHeight());
    }
}
