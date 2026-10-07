# OryvexClient (Minecraft 1.8.8)

Forge-based PvP client with HUD modules (FPS, CPS, Coordinates, Keystrokes, Armor Status, Clock),
Toggle Sprint, Fullbright, Zoom, a custom main menu and a drag-and-drop HUD editor.

- **Right Shift** – open the client menu / HUD editor
- **C** (hold) – zoom

## Build on GitHub
Push this repo -> Actions -> *Build OryvexClient* -> download the **OryvexClient** artifact
(`client.jar` + `start.bat`).

## Install
Run `start.bat` (installs the bundled Forge 1.8.8 if missing and copies the jar to `.minecraft/mods`),
then start the **forge** profile in the Minecraft Launcher.

## Local build
Needs JDK 8 and Gradle 2.14.1: `gradle setupDecompWorkspace build`
