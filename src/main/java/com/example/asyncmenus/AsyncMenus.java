package com.example.asyncmenus;

import com.example.asyncmenus.loading.LoadingProgressHandler;
import com.example.asyncmenus.loading.LoadingScreenHook;
import com.example.asyncmenus.loading.TerrainLoadListener;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.event.FMLInitializationEvent;
import net.minecraftforge.fml.common.event.FMLPreInitializationEvent;

@Mod(modid = AsyncMenus.MODID, name = AsyncMenus.NAME, version = AsyncMenus.VERSION,
        clientSideOnly = true, acceptedMinecraftVersions = "[1.8.9]", useMetadata = true)
public class AsyncMenus {
    public static final String MODID = "asyncmenus";
    public static final String NAME = "Async Menus";
    public static final String VERSION = "1.0.0";

    @Mod.EventHandler
    public void preInit(FMLPreInitializationEvent event) {
        // Install the loading screen before anything else.
        LoadingScreenHook.install();

        // Progress handlers: Forge bus for lifecycle events...
        MinecraftForge.EVENT_BUS.register(new LoadingProgressHandler());
        MinecraftForge.EVENT_BUS.register(new TerrainLoadListener());
    }

    @Mod.EventHandler
    public void init(FMLInitializationEvent event) {
        MinecraftForge.EVENT_BUS.register(new ResourcePackScreenHandler());
        MinecraftForge.EVENT_BUS.register(new ShaderPackPrefetcher());
    }
}
