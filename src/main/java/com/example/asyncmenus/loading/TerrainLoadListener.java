package com.example.asyncmenus.loading;

import net.minecraftforge.client.event.GuiScreenEvent;
import net.minecraftforge.event.world.WorldEvent;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.fml.relauncher.Side;
import net.minecraftforge.fml.relauncher.SideOnly;

/**
 * Reports world/terrain progress so the loading screen can say
 * "Building terrain" / "Joining world" during world load.
 *
 * Also catches the ResourcePack reload via GuiScreenEvent when a
 * GuiScreenResourcePack is about to open.
 */
@SideOnly(Side.CLIENT)
public class TerrainLoadListener {

    @SubscribeEvent
    public void onWorldLoad(WorldEvent.Load e) {
        LoadingProgress.setScreenActive(true);
        LoadingProgress.setPhase(LoadingPhase.TERRAIN, 0.1f);
        LoadingProgress.setMessage("Downloading terrain");
    }

    @SubscribeEvent
    public void onWorldUnload(WorldEvent.Unload e) {
        // nothing to do yet; kept for symmetry
    }

    @SubscribeEvent
    public void onGuiInitPre(GuiScreenEvent.InitGuiEvent.Pre e) {
        if (e.gui == null) return;
        String name = e.gui.getClass().getSimpleName();
        if (name.equals("GuiDownloadTerrain") || name.equals("GuiWorldLoad")) {
            LoadingProgress.setScreenActive(true);
            LoadingProgress.setPhase(LoadingPhase.JOINING_WORLD, 0.2f);
            LoadingProgress.setMessage("Joining world");
        }
        if (name.equals("GuiScreenResourcePacks")) {
            LoadingProgress.setScreenActive(true);
            LoadingProgress.setPhase(LoadingPhase.RELOADING, 0.1f);
            LoadingProgress.setMessage("Scanning resource packs");
        }
    }
}
