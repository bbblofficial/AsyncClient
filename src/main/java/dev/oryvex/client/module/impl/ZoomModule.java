package dev.oryvex.client.module.impl;

import dev.oryvex.client.OryvexClient;
import dev.oryvex.client.module.Module;

public class ZoomModule extends Module {
    private boolean zooming;
    private float savedFov;
    private boolean savedSmooth;

    public ZoomModule() { super("Zoom", "Hold C to zoom in", true); }

    @Override public void onTick() {
        boolean want = enabled && mc.currentScreen == null && OryvexClient.zoomKey.isKeyDown();
        if (want && !zooming) {
            savedFov = mc.gameSettings.fovSetting;
            savedSmooth = mc.gameSettings.smoothCamera;
            zooming = true;
        }
        if (want) {
            mc.gameSettings.fovSetting = 30f;
            mc.gameSettings.smoothCamera = true;
        } else if (zooming) {
            mc.gameSettings.fovSetting = savedFov;
            mc.gameSettings.smoothCamera = savedSmooth;
            zooming = false;
        }
    }
}
