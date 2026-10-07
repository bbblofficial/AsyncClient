package dev.oryvex.client.module.impl;

import dev.oryvex.client.module.TextHudModule;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

public class CpsModule extends TextHudModule {
    private static final List<Long> LEFT = new ArrayList<Long>();
    private static final List<Long> RIGHT = new ArrayList<Long>();

    public CpsModule() { super("CPS", "Clicks per second", true, 6, 24); }

    public static void click(int button) {
        long now = System.currentTimeMillis();
        if (button == 0) { LEFT.add(now); prune(LEFT); }
        else if (button == 1) { RIGHT.add(now); prune(RIGHT); }
    }

    private static int prune(List<Long> list) {
        long now = System.currentTimeMillis();
        Iterator<Long> it = list.iterator();
        while (it.hasNext()) {
            if (now - it.next() > 1000L) it.remove();
        }
        return list.size();
    }

    @Override protected String label() { return "CPS"; }
    @Override protected String value() { return prune(LEFT) + " | " + prune(RIGHT); }
}
