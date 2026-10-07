package com.example.asyncmenus;

import java.io.File;
import java.io.FileFilter;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

import com.google.common.collect.Lists;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.*;
import net.minecraft.client.resources.*;
import net.minecraft.client.resources.I18n;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/** One open Resource Packs screen: owns the lists and the background loader. */
final class AsyncPackSession {
    private static final Logger LOG = LogManager.getLogger(AsyncMenus.MODID);
    private static final long DRAIN_BUDGET_NANOS = 3_000_000L; // max ~3 ms of UI work per frame

    private static final FileFilter PACK_FILTER = f ->
            (f.isFile() && f.getName().endsWith(".zip"))
                    || (f.isDirectory() && new File(f, "pack.mcmeta").isFile());

    private static final class Loaded {
        final ResourcePackRepository.Entry entry;
        final String name;
        Loaded(ResourcePackRepository.Entry entry, String name) { this.entry = entry; this.name = name; }
    }

    final GuiScreenResourcePacks screen;
    private final Minecraft mc = Minecraft.getMinecraft();
    private final List<ResourcePackListEntry> available = Lists.newArrayList();
    private final List<ResourcePackListEntry> selected = Lists.newArrayList();
    private final Map<ResourcePackListEntry, String> sortKeys = new HashMap<ResourcePackListEntry, String>();
    private final Queue<Loaded> ready = new ConcurrentLinkedQueue<Loaded>();
    private final AtomicInteger total = new AtomicInteger();
    private final AtomicInteger finished = new AtomicInteger();
    private volatile boolean scanDone;
    private volatile boolean cancelled;
    private ExecutorService pool;
    private boolean started;

    AsyncPackSession(GuiScreenResourcePacks screen) {
        this.screen = screen;
    }

    /** Called on every initGui (also on window resize). Lists persist; only the widgets are rebuilt. */
    void buildGui(List<GuiButton> buttons) throws Exception {
        if (!started) populateSelected();

        int w = screen.width, h = screen.height;
        GuiResourcePackAvailable left = new GuiResourcePackAvailable(mc, 200, h, available);
        left.setSlotXBoundsFromLeft(w / 2 - 4 - 200);
        left.registerScrollButtons(7, 8);
        GuiResourcePackSelected right = new GuiResourcePackSelected(mc, 200, h, selected);
        right.setSlotXBoundsFromLeft(w / 2 + 4);
        right.registerScrollButtons(7, 8);

        PackScreenReflection.inject(screen, available, selected, left, right);

        // Buttons last: if anything above throws, vanilla init can still run cleanly.
        buttons.add(new GuiOptionButton(2, w / 2 - 154, h - 48, I18n.format("resourcePack.openFolder")));
        buttons.add(new GuiOptionButton(1, w / 2 + 4, h - 48, I18n.format("gui.done")));

        if (!started) {
            started = true;
            startLoading();
        }
    }

    private void populateSelected() {
        ResourcePackRepository repo = mc.getResourcePackRepository();
        for (ResourcePackRepository.Entry e : Lists.reverse(repo.getRepositoryEntries())) {
            ResourcePackListEntryFound f = new ResourcePackListEntryFound(screen, e);
            selected.add(f);
            sortKeys.put(f, nameOf(e));
        }
        selected.add(new ResourcePackListEntryDefault(screen));
    }

    private void startLoading() {
        final ResourcePackRepository repo = mc.getResourcePackRepository();
        final File dir = repo.getDirResourcepacks();

        // Reuse packs vanilla already parsed (same name + type + lastModified).
        final Map<String, ResourcePackRepository.Entry> cache = new HashMap<String, ResourcePackRepository.Entry>();
        for (ResourcePackRepository.Entry e : repo.getRepositoryEntriesAll()) cache.put(e.toString(), e);
        final Set<String> selectedKeys = new HashSet<String>();
        for (ResourcePackRepository.Entry e : repo.getRepositoryEntries()) selectedKeys.add(e.toString());

        int threads = Math.max(2, Math.min(4, Runtime.getRuntime().availableProcessors()));
        pool = Executors.newFixedThreadPool(threads, r -> {
            Thread t = new Thread(r, "AsyncMenus-PackLoader");
            t.setDaemon(true);
            return t;
        });

        try {
            pool.submit(() -> {
                try {
                    File[] files = dir.listFiles(PACK_FILTER); // directory scan also happens off-thread
                    if (files == null) return;
                    total.addAndGet(files.length);
                    for (final File file : files) {
                        if (cancelled) return;
                        pool.submit(() -> loadOne(repo, file, cache, selectedKeys));
                    }
                } catch (RejectedExecutionException ignored) {
                } finally {
                    scanDone = true;
                }
            });
        } catch (RejectedExecutionException ignored) {
            scanDone = true;
        }
    }

    private void loadOne(ResourcePackRepository repo, File file,
                         Map<String, ResourcePackRepository.Entry> cache, Set<String> selectedKeys) {
        try {
            if (cancelled) return;
            ResourcePackRepository.Entry entry = PackScreenReflection.newEntry(repo, file);
            ResourcePackRepository.Entry cached = cache.get(entry.toString());
            if (cached != null) {
                entry = cached;
            } else {
                entry.updateResourcePack(); // heavy part: opens zip, reads pack.mcmeta + pack.png
            }
            if (cancelled || selectedKeys.contains(entry.toString())) return;
            ready.add(new Loaded(entry, file.getName()));
        } catch (Throwable t) {
            LOG.debug("Skipping unreadable resource pack {}", file, t); // vanilla also skips these
        } finally {
            finished.incrementAndGet();
        }
    }

    /** Render thread: move finished packs into the visible list, with a small per-frame time budget. */
    void drain() {
        long end = System.nanoTime() + DRAIN_BUDGET_NANOS;
        Loaded l;
        while (!cancelled && (l = ready.poll()) != null) {
            ResourcePackListEntryFound f = new ResourcePackListEntryFound(screen, l.entry);
            insertSorted(f, l.name);
            if (System.nanoTime() > end) break;
        }
    }

    private void insertSorted(ResourcePackListEntry e, String key) {
        sortKeys.put(e, key);
        int i = 0;
        while (i < available.size()) {
            String other = sortKeys.get(available.get(i));
            if (other != null && key.compareToIgnoreCase(other) < 0) break;
            i++;
        }
        available.add(i, e);
    }

    boolean isLoading() {
        return !cancelled && (!scanDone || finished.get() < total.get() || !ready.isEmpty());
    }

    void drawStatus() {
        if (!isLoading()) return;
        String msg = String.format("Loading packs... %d/%d", finished.get(), Math.max(total.get(), finished.get()));
        mc.fontRendererObj.drawStringWithShadow(msg,
                (screen.width - mc.fontRendererObj.getStringWidth(msg)) / 2f, screen.height - 20, 0xFFFFFF);
    }

    void cancel() {
        cancelled = true;
        ready.clear();
        if (pool != null) pool.shutdownNow();
    }

    private static String nameOf(ResourcePackRepository.Entry e) {
        try {
            return e.getResourcePackName();
        } catch (Exception ex) {
            return e.toString();
        }
    }
}
