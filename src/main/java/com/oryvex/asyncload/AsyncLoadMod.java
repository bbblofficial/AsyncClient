package com.oryvex.asyncload;

import com.oryvex.asyncload.events.GuiEventHandler;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.event.FMLInitializationEvent;

@Mod(modid = AsyncLoadMod.MODID, version = AsyncLoadMod.VERSION, name = AsyncLoadMod.NAME, acceptedMinecraftVersions = "[1.8.9]")
public class AsyncLoadMod {
    public static final String MODID = "asyncload";
    public static final String NAME = "Async Menu Load";
    public static final String VERSION = "1.0.0";

    @Mod.EventHandler
    public void init(FMLInitializationEvent event) {
        MinecraftForge.EVENT_BUS.register(new GuiEventHandler());
    }
}
