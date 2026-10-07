package com.oryvex.asyncload.gui;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiScreen;
import net.minecraft.client.gui.GuiScreenResourcePacks;
import net.minecraft.client.resources.ResourcePackListEntry;
import net.minecraft.client.resources.ResourcePackRepository;

import java.io.File;
import java.util.concurrent.ConcurrentLinkedQueue;

public class AsyncResourcePackGui extends GuiScreenResourcePacks {

    private final ConcurrentLinkedQueue<ResourcePackRepository.Entry> loadedPacksQueue = new ConcurrentLinkedQueue<>();
    private boolean isLoading = true;

    public AsyncResourcePackGui(GuiScreen parentScreenIn) {
        super(parentScreenIn);
    }

    @Override
    public void initGui() {
        super.initGui();
        this.availableResourcePacks.clear(); 
        startAsyncLoading();
    }

    private void startAsyncLoading() {
        Thread loadThread = new Thread(() -> {
            ResourcePackRepository repo = Minecraft.getMinecraft().getResourcePackRepository();
            repo.updateRepositoryEntriesAll(); 
            
            for (ResourcePackRepository.Entry entry : repo.getRepositoryEntriesAll()) {
                entry.updateResourcePack(); 
                loadedPacksQueue.add(entry);
            }
            isLoading = false;
        }, "Async-Pack-Loader");
        
        loadThread.setDaemon(true);
        loadThread.start();
    }

    @Override
    public void updateScreen() {
        super.updateScreen();
        
        int packsProcessedThisTick = 0;
        while (!loadedPacksQueue.isEmpty() && packsProcessedThisTick < 2) { 
            ResourcePackRepository.Entry entry = loadedPacksQueue.poll();
            if (entry != null) {
                // Implementation to add CustomPackEntry to this.availableResourcePacks goes here
            }
            packsProcessedThisTick++;
        }
    }

    @Override
    public void drawScreen(int mouseX, int mouseY, float partialTicks) {
        super.drawScreen(mouseX, mouseY, partialTicks);
        if (isLoading) {
            this.drawCenteredString(this.fontRendererObj, "Loading Packs Asynchronously...", this.width / 2, 20, 16777215);
        }
    }
}
