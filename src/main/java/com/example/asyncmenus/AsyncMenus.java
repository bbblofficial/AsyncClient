package com.example.asyncmenus;

import com.example.asyncmenus.loading.LoadingScreenHook;
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
        LoadingScreenHook.install();
    }

    @Mod.EventHandler
    public void init(FMLInitializationEvent event) {
        MinecraftForge.EVENT_BUS.register(new ResourcePackScreenHandler());
        MinecraftForge.EVENT_BUS.register(new ShaderPackPrefetcher());
    }
}
