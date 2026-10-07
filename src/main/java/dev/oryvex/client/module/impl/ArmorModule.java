package dev.oryvex.client.module.impl;

import dev.oryvex.client.module.HudModule;
import net.minecraft.client.renderer.GlStateManager;
import net.minecraft.client.renderer.RenderHelper;
import net.minecraft.item.ItemStack;

public class ArmorModule extends HudModule {
    public ArmorModule() { super("Armor Status", "Armor durability", true, 6, 180); }

    @Override public int getWidth() { return 60; }
    @Override public int getHeight() { return 4 * 18 + 4; }

    @Override public void render() {
        panel();
        if (mc.thePlayer == null) return;
        for (int i = 0; i < 4; i++) {
            ItemStack stack = mc.thePlayer.inventory.armorItemInSlot(3 - i);
            if (stack == null) continue;
            int iy = y + 4 + i * 18;

            GlStateManager.pushMatrix();
            RenderHelper.enableGUIStandardItemLighting();
            mc.getRenderItem().renderItemAndEffectIntoGUI(stack, x + 4, iy);
            RenderHelper.disableStandardItemLighting();
            GlStateManager.popMatrix();
            GlStateManager.disableLighting();
            GlStateManager.enableBlend();

            if (stack.isItemStackDamageable()) {
                int left = stack.getMaxDamage() - stack.getItemDamage();
                float f = left / (float) stack.getMaxDamage();
                int c = f > 0.6f ? 0xFF55FF55 : (f > 0.3f ? 0xFFFFFF55 : 0xFFFF5555);
                mc.fontRendererObj.drawStringWithShadow(String.valueOf(left), x + 24, iy + 4, c);
            }
        }
        GlStateManager.color(1f, 1f, 1f, 1f);
    }
}
