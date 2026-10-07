package com.example.asyncmenus;

import com.example.asyncmenus.loading.LoadingPhase;
import com.example.asyncmenus.loading.LoadingProgress;
import com.example.asyncmenus.loading.LoadingProgressHandler;
import com.example.asyncmenus.loading.LoadingScreenHook;
import com.example.asyncmenus.loading.TerrainLoadListener;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.event.FMLConstructionEvent;
import net.minecraftforge.fml.common.event.FMLInitializationEvent;
import net.minecraftforge.fml.common.event.FMLPostInitializationEvent;
import net.minecraftforge.fml.common.event.FMLPreInitializationEvent;

@Mod(modid = AsyncMenus.MODID, name = AsyncMenus.NAME, version = AsyncMenus.VERSION,
        clientSideOnly = true, acceptedMinecraftVersions = "[1.8.9]", useMetadata = true)
public class AsyncMenus {
    public static final String MODID = "asyncmenus";
    public static final String NAME = "Async Menus";
    public static final String VERSION = "1.0.0";

    @Mod.EventHandler
    public void construct(FMLConstructionEvent event) {
        LoadingProgress.setPhase(LoadingPhase.MOD_CONSTRUCTION, 0.5f);
    }

    @Mod.EventHandler
    public void preInit(FMLPreInitializationEvent event) {
        LoadingProgress.setPhase(LoadingPhase.PRE_INIT, 0.1f);

        LoadingScreenHook.install();

        // Only real Forge Event subclasses go on the EVENT_BUS:
        MinecraftForge.EVENT_BUS.register(new LoadingProgressHandler());
        MinecraftForge.EVENT_BUS.register(new TerrainLoadListener());
    }

    @Mod.EventHandler
    public void init(FMLInitializationEvent event) {
        LoadingProgress.setPhase(LoadingPhase.INIT, 0.1f);

        MinecraftForge.EVENT_BUS.register(new ResourcePackScreenHandler());
        MinecraftForge.EVENT_BUS.register(new ShaderPackPrefetcher());
    }

    @Mod.EventHandler
    public void postInit(FMLPostInitializationEvent event) {
        LoadingProgress.setPhase(LoadingPhase.POST_INIT, 0.1f);
    }
}
