package com.example.asyncmenus.loading;

/**
 * Global, thread-safe progress bus. Any code can post a phase and a
 * sub-progress (0..1) inside that phase; the renderer on the client
 * thread reads the latest values.
 */
public final class LoadingProgress {

    private static volatile LoadingPhase phase = LoadingPhase.MOD_CONSTRUCTION;
    private static volatile float subProgress = 0f;
    private static volatile String customMessage = "";
    private static volatile boolean screenActive = false;

    private LoadingProgress() {}

    public static void setPhase(LoadingPhase p) {
        phase = p;
        subProgress = 0f;
        customMessage = "";
    }

    public static void setPhase(LoadingPhase p, float sub) {
        phase = p;
        subProgress = clamp(sub);
    }

    public static void setSub(float sub)        { subProgress = clamp(sub); }
    public static void setMessage(String msg)   { customMessage = msg == null ? "" : msg; }

    public static LoadingPhase getPhase()       { return phase; }
    public static float getSubProgress()        { return subProgress; }
    public static String getCustomMessage()     { return customMessage; }
    public static boolean isScreenActive()      { return screenActive; }
    public static void setScreenActive(boolean b){ screenActive = b; }

    /** Absolute 0..100 percent across all phases. */
    public static int getPercent() {
        LoadingPhase p = phase;
        LoadingPhase[] all = LoadingPhase.values();
        int nextBase = 100;
        for (int i = 0; i < all.length; i++) {
            if (all[i] == p) {
                nextBase = (i + 1 < all.length) ? all[i + 1].basePercent : 100;
                break;
            }
        }
        float span = nextBase - p.basePercent;
        return Math.max(0, Math.min(100,
                Math.round(p.basePercent + span * subProgress)));
    }

    private static float clamp(float f) {
        if (f < 0f) return 0f;
        if (f > 1f) return 1f;
        return f;
    }
}
