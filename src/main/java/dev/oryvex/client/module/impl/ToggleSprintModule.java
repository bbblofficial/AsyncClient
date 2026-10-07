package dev.oryvex.client.module.impl;

import dev.oryvex.client.module.Module;

public class ToggleSprintModule extends Module {
    public ToggleSprintModule() { super("Toggle Sprint", "Auto-sprint while moving", true); }

    @Override public void onTick() {
        if (!enabled || mc.thePlayer == null || mc.currentScreen != null) return;
        if (mc.gameSettings.keyBindForward.isKeyDown()
                && !mc.thePlayer.isSneaking()
                && !mc.thePlayer.isUsingItem()
                && !mc.thePlayer.isCollidedHorizontally
                && mc.thePlayer.getFoodStats().getFoodLevel() > 6) {
            mc.thePlayer.setSprinting(true);
        }
    }
}
