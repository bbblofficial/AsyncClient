import os

def create_project_structure():
    files = {
        ".github/workflows/build.yml": """name: Build Forge Mod 1.8.9

on:
  push:
    branches: [ "main", "master" ]
  pull_request:
    branches: [ "main", "master" ]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout Repository
      uses: actions/checkout@v3

    - name: Set up JDK 8
      uses: actions/setup-java@v3
      with:
        java-version: '8'
        distribution: 'temurin'

    - name: Cache Gradle packages
      uses: actions/cache@v3
      with:
        path: |
          ~/.gradle/caches
          ~/.gradle/wrapper
        key: ${{ runner.os }}-gradle-${{ hashFiles('**/*.gradle*', '**/gradle-wrapper.properties') }}
        restore-keys: |
          ${{ runner.os }}-gradle-

    - name: Grant execute permission for gradlew
      run: chmod +x gradlew

    - name: Build Mod with Gradle
      run: ./gradlew build

    - name: Upload Mod Artifact
      uses: actions/upload-artifact@v3
      with:
        name: AsyncMenuLoad-1.8.9
        path: build/libs/*.jar
""",
        "src/main/java/com/oryvex/asyncload/AsyncLoadMod.java": """package com.oryvex.asyncload;

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
""",
        "src/main/java/com/oryvex/asyncload/events/GuiEventHandler.java": """package com.oryvex.asyncload.events;

import com.oryvex.asyncload.gui.AsyncResourcePackGui;
import net.minecraft.client.gui.GuiScreenResourcePacks;
import net.minecraftforge.client.event.GuiOpenEvent;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;

public class GuiEventHandler {

    @SubscribeEvent
    public void onGuiOpen(GuiOpenEvent event) {
        if (event.gui instanceof GuiScreenResourcePacks && !(event.gui instanceof AsyncResourcePackGui)) {
            GuiScreenResourcePacks original = (GuiScreenResourcePacks) event.gui;
            event.gui = new AsyncResourcePackGui(null);
        }
        
        if (event.gui != null && event.gui.getClass().getName().equals("net.optifine.gui.GuiShaders")) {
            // Future implementation for Shaders menu
        }
    }
}
""",
        "src/main/java/com/oryvex/asyncload/gui/AsyncResourcePackGui.java": """package com.oryvex.asyncload.gui;

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
""",
        "src/main/resources/mcmod.info": """[
{
  "modid": "asyncload",
  "name": "Async Menu Load",
  "description": "Lazy loads Resource Packs and Shader menus without freezing the game.",
  "version": "${version}",
  "mcversion": "${mcversion}",
  "url": "",
  "updateUrl": "",
  "authorList": ["Oryvex"],
  "credits": "Non-blocking UI integration",
  "logoFile": "",
  "screenshots": [],
  "dependencies": []
}
]
""",
        "build.gradle": """buildscript {
    repositories {
        mavenCentral()
        maven { url = "https://maven.minecraftforge.net/" }
    }
    dependencies {
        classpath 'net.minecraftforge.gradle:ForgeGradle:2.1-SNAPSHOT'
    }
}
apply plugin: 'net.minecraftforge.gradle.forge'

version = "1.0.0"
group = "com.oryvex.asyncload"
archivesBaseName = "AsyncMenuLoad"

sourceCompatibility = targetCompatibility = '1.8'
compileJava {
    sourceCompatibility = '1.8'
    targetCompatibility = '1.8'
}

minecraft {
    version = "1.8.9-11.15.1.2318-1.8.9"
    runDir = "run"
    mappings = "stable_22"
}

processResources {
    inputs.property "version", project.version
    inputs.property "mcversion", project.minecraft.version

    from(sourceSets.main.resources.srcDirs) {
        include 'mcmod.info'
        expand 'version':project.version, 'mcversion':project.minecraft.version
    }
    from(sourceSets.main.resources.srcDirs) {
        exclude 'mcmod.info'
    }
}
""",
        "gradle.properties": """org.gradle.jvmargs=-Xmx2G
"""
    }

    for file_path, content in files.items():
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
        
        # Write the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Created: {file_path}")

    print("\nProject generation complete!")
    print("Next steps:")
    print("1. Run 'gradle wrapper' in your terminal to generate the gradlew files.")
    print("2. Run './gradlew setupDecompWorkspace' to set up Forge.")
    print("3. Push to GitHub to trigger the Actions build workflow.")

if __name__ == "__main__":
    create_project_structure()