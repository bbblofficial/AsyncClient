package dev.oryvex.client.module;

import dev.oryvex.client.util.Theme;

/** Small pill showing "LABEL value". */
public abstract class TextHudModule extends HudModule {
    protected TextHudModule(String name, String description, boolean enabled, int x, int y) {
        super(name, description, enabled, x, y);
    }

    protected abstract String label();
    protected abstract String value();

    @Override public int getWidth() {
        return 5 + mc.fontRendererObj.getStringWidth(label()) + 4 + mc.fontRendererObj.getStringWidth(value()) + 5;
    }

    @Override public int getHeight() { return 14; }

    @Override public void render() {
        panel();
        int lw = mc.fontRendererObj.getStringWidth(label());
        mc.fontRendererObj.drawStringWithShadow(label(), x + 5, y + 3, Theme.ACCENT2);
        mc.fontRendererObj.drawStringWithShadow(value(), x + 9 + lw, y + 3, Theme.TEXT);
    }
}
