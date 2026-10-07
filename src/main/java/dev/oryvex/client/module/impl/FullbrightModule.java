package dev.oryvex.client.module.impl;

import dev.oryvex.client.module.Module;

public class FullbrightModule extends Module {
    private boolean active;
    private float saved;

    public FullbrightModule() { super("Fullbright", "Maximum brightness", false); }

    @Override public void onTick() {
        if (enabled) {
            if (!active) { saved = mc.gameSettings.gammaSetting; active = true; }
            mc.gameSettings.gammaSetting = 100f;
        } else if (active) {
            mc.gameSettings.gammaSetting = saved;
            active = false;
        }
    }
}
