package dev.oryvex.client.module;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import dev.oryvex.client.module.impl.*;
import net.minecraft.client.Minecraft;

import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.util.ArrayList;
import java.util.List;

public class ModuleManager {
    private final List<Module> modules = new ArrayList<Module>();

    public ModuleManager() {
        modules.add(new FpsModule());
        modules.add(new CpsModule());
        modules.add(new CoordsModule());
        modules.add(new KeystrokesModule());
        modules.add(new ArmorModule());
        modules.add(new ClockModule());
        modules.add(new ToggleSprintModule());
        modules.add(new FullbrightModule());
        modules.add(new ZoomModule());
    }

    public List<Module> all() { return modules; }

    public List<HudModule> huds() {
        List<HudModule> list = new ArrayList<HudModule>();
        for (Module m : modules) if (m instanceof HudModule) list.add((HudModule) m);
        return list;
    }

    public void tick() {
        for (Module m : modules) m.onTick();
    }

    private File file() {
        File f = new File(Minecraft.getMinecraft().mcDataDir, "config/oryvexclient.json");
        f.getParentFile().mkdirs();
        return f;
    }

    public void save() {
        try {
            JsonObject root = new JsonObject();
            for (Module m : modules) {
                JsonObject o = new JsonObject();
                o.addProperty("enabled", m.enabled);
                if (m instanceof HudModule) {
                    o.addProperty("x", ((HudModule) m).x);
                    o.addProperty("y", ((HudModule) m).y);
                }
                root.add(m.name, o);
            }
            Gson gson = new GsonBuilder().setPrettyPrinting().create();
            FileWriter w = new FileWriter(file());
            try { w.write(gson.toJson(root)); } finally { w.close(); }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void load() {
        File f = file();
        if (!f.exists()) return;
        try {
            FileReader r = new FileReader(f);
            JsonObject root;
            try { root = new JsonParser().parse(r).getAsJsonObject(); } finally { r.close(); }
            for (Module m : modules) {
                if (!root.has(m.name)) continue;
                JsonObject o = root.getAsJsonObject(m.name);
                if (o.has("enabled")) m.enabled = o.get("enabled").getAsBoolean();
                if (m instanceof HudModule) {
                    if (o.has("x")) ((HudModule) m).x = o.get("x").getAsInt();
                    if (o.has("y")) ((HudModule) m).y = o.get("y").getAsInt();
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
