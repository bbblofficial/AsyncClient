package dev.oryvex.client.module.impl;

import dev.oryvex.client.module.TextHudModule;

import java.text.SimpleDateFormat;
import java.util.Date;

public class ClockModule extends TextHudModule {
    private final SimpleDateFormat format = new SimpleDateFormat("HH:mm");

    public ClockModule() { super("Clock", "Shows your local time", false, 6, 42); }
    @Override protected String label() { return "TIME"; }
    @Override protected String value() { return format.format(new Date()); }
}
