package com.example.asyncmenus;

import java.io.File;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.List;

import net.minecraft.client.gui.GuiResourcePackAvailable;
import net.minecraft.client.gui.GuiResourcePackSelected;
import net.minecraft.client.gui.GuiScreenResourcePacks;
import net.minecraft.client.resources.ResourcePackListEntry;
import net.minecraft.client.resources.ResourcePackRepository;
import net.minecraftforge.fml.relauncher.ReflectionHelper;
import org.apache.logging.log4j.LogManager;

/** Reflection access to the private members of vanilla's resource pack screen. */
final class PackScreenReflection {
    private static Field availableList, selectedList, availableGui, selectedGui;
    private static Constructor<ResourcePackRepository.Entry> entryCtor;
    private static boolean ok;

    static {
        try {
            // Dev (MCP) name first, then SRG name, then fall back to lookup by type/order.
            availableList = find(List.class, 0, "availableResourcePacks", "field_146966_g");
            selectedList = find(List.class, 1, "selectedResourcePacks", "field_146969_h");
            availableGui = find(GuiResourcePackAvailable.class, 0, "availableResourcePacksList", "field_146970_i");
            selectedGui = find(GuiResourcePackSelected.class, 0, "selectedResourcePacksList", "field_146967_r");
            entryCtor = ResourcePackRepository.Entry.class
                    .getDeclaredConstructor(ResourcePackRepository.class, File.class);
            entryCtor.setAccessible(true);
            ok = true;
        } catch (Throwable t) {
            LogManager.getLogger(AsyncMenus.MODID).error("Reflection setup failed; vanilla screen will be used", t);
        }
    }

    private PackScreenReflection() {}

    static boolean isAvailable() { return ok; }

    private static Field find(Class<?> type, int index, String... names) {
        try {
            return ReflectionHelper.findField(GuiScreenResourcePacks.class, names);
        } catch (RuntimeException ex) {
            int i = 0;
            for (Field f : GuiScreenResourcePacks.class.getDeclaredFields()) {
                if (f.getType() == type && i++ == index) {
                    f.setAccessible(true);
                    return f;
                }
            }
            throw ex;
        }
    }

    static void inject(GuiScreenResourcePacks screen,
                       List<ResourcePackListEntry> available, List<ResourcePackListEntry> selected,
                       GuiResourcePackAvailable availableUi, GuiResourcePackSelected selectedUi)
            throws IllegalAccessException {
        availableList.set(screen, available);
        selectedList.set(screen, selected);
        availableGui.set(screen, availableUi);
        selectedGui.set(screen, selectedUi);
    }

    static ResourcePackRepository.Entry newEntry(ResourcePackRepository repo, File file) throws Exception {
        return entryCtor.newInstance(repo, file);
    }
}
