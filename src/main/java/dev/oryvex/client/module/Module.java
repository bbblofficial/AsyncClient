package dev.oryvex.client.module;

import net.minecraft.client.Minecraft;

public abstract class Module {
    public final String name;
    public final String description;
    public boolean enabled;
    protected final Minecraft mc = Minecraft.getMinecraft();

    protected Module(String name, String description, boolean enabled) {
        this.name = name;
        this.description = description;
        this.enabled = enabled;
    }

    public void toggle() {
        enabled = !enabled;
    }

    /** Called every client tick (end phase). */
    public void onTick() {}
}
