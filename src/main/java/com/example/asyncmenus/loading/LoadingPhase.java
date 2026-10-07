package com.example.asyncmenus.loading;

/** Every distinct startup / reload phase we report progress for. */
public enum LoadingPhase {
    MOD_CONSTRUCTION   ("Constructing mods",       5),
    PRE_INIT           ("Pre-initializing mods",  10),
    INIT               ("Initializing mods",      20),
    POST_INIT          ("Post-initializing mods", 30),
    RESOURCE_LOAD      ("Loading resources",      45),
    START_GAME         ("Starting game",          60),
    TERRAIN            ("Building terrain",       75),
    JOINING_WORLD      ("Joining world",          85),
    RELOADING          ("Reloading resources",    50),
    DONE               ("Done",                  100);

    public final String label;
    public final int basePercent;

    LoadingPhase(String label, int basePercent) {
        this.label = label;
        this.basePercent = basePercent;
    }
}
