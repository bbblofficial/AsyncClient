package dev.oryvex.client;

import dev.oryvex.client.gui.OryvexMainMenu;
import dev.oryvex.client.gui.OryvexMenu;
import dev.oryvex.client.module.HudModule;
import dev.oryvex.client.module.ModuleManager;
import dev.oryvex.client.module.impl.CpsModule;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiMainMenu;
import net.minecraft.client.renderer.GlStateManager;
import net.minecraft.client.settings.KeyBinding;
import net.minecraftforge.client.event.GuiOpenEvent;
import net.minecraftforge.client.event.MouseEvent;
import net.minecraftforge.client.event.RenderGameOverlayEvent;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.fml.client.registry.ClientRegistry;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.event.FMLInitializationEvent;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.fml.common.gameevent.TickEvent;
import org.lwjgl.input.Keyboard;
import org.lwjgl.opengl.Display;

@Mod(modid = OryvexClient.MODID, name = "OryvexClient", version = "1.0.0",
        clientSideOnly = true, acceptedMinecraftVersions = "[1.8.8]")
public class OryvexClient {
    public static final String MODID = "oryvexclient";

    public static KeyBinding menuKey;
    public static KeyBinding zoomKey;
    public static ModuleManager modules;

    private final Minecraft mc = Minecraft.getMinecraft();

    @Mod.EventHandler
    public void init(FMLInitializationEvent event) {
        menuKey = new KeyBinding("Open Menu", Keyboard.KEY_RSHIFT, "OryvexClient");
        zoomKey = new KeyBinding("Zoom", Keyboard.KEY_C, "OryvexClient");
        ClientRegistry.registerKeyBinding(menuKey);
        ClientRegistry.registerKeyBinding(zoomKey);

        modules = new ModuleManager();
        modules.load();

        Display.setTitle("OryvexClient 1.0.0 | Minecraft 1.8.8");
        MinecraftForge.EVENT_BUS.register(this);
    }

    @SubscribeEvent
    public void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        modules.tick();
        if (menuKey.isPressed() && mc.currentScreen == null) {
            mc.displayGuiScreen(new OryvexMenu(null));
        }
    }

    @SubscribeEvent
    public void onOverlay(RenderGameOverlayEvent.Post e) {
        if (e.type != RenderGameOverlayEvent.ElementType.ALL) return;
        if (mc.gameSettings.showDebugInfo) return;
        GlStateManager.enableBlend();
        for (HudModule m : modules.huds()) {
            if (m.enabled) m.render();
        }
        GlStateManager.color(1f, 1f, 1f, 1f);
    }

    @SubscribeEvent
    public void onMouse(MouseEvent e) {
        if (e.buttonstate) CpsModule.click(e.button);
    }

    @SubscribeEvent
    public void onGuiOpen(GuiOpenEvent e) {
        if (e.gui != null && e.gui.getClass() == GuiMainMenu.class) {
            e.gui = new OryvexMainMenu();
        }
    }
}
