// Starter board: every cmux workspace as a tinted card.
//
// Header: "Good afternoon, {{NAME}}" and the date and time; under it
// who is working or waiting on the left and the total decisions on the right.
//
// Card, top to bottom:
//   title (card tinted in the workspace colour), blue unread count top right
//   the "Now" description (2 lines)
//   live line: "⚡ 12m · what it is doing" while an agent works,
//              "🙋 4m · Needs you" when a tab is stopped on a question box,
//              otherwise the plan bar ("Phase 1 of 4 · 4 of 12 steps done")
//   bottom row: two matching pills. Left: the most urgent signal (tap to go
//              there). Right: "Overview 3 ›" (3 = decisions inside).
// Glow: full (white) while stopped on a question box; soft (workspace colour)
// while something is unread; see glow().
// Signals, most urgent first: 🙋 needs you · 💬 asked you something · ⏳ usage limit · 📅 due soon ·
//   ✅ just finished · 🔀 open pull request · 💤 quiet.
// Data: ~/.claude/boards/ via ~/.claude/loop/board_sync.py (plan, decisions,
// ⏳ and 📅) and ~/.claude/loop/live_line.py (the live activity).
// Switch: right-click the sidebar button and pick starter-board or the standard one.
// Colours: change the six constants below to restyle the whole sidebar.

const BLUE = "#5b9cf6";   // unread count
const GREEN = "#22ab94";  // plan complete
const TEXT = "#f0f3fa";   // main text
const SOFT = "#d1d4dc";   // light grey for the quieter lines, still easy to read
const VIEWS = "{{HOME}}/.claude/boards/.views/";
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const clock = () => data.clock() ?? {};
const epoch = () => clock().epoch ?? 0;
const secs = (t) => (t > 1e12 ? t / 1000 : t || 0);  // tolerate ms or s timestamps

function agents(w) { return (w && w.agents) || []; }
// Waiting on you only when a thread is really stopped on a question
// (live_line.py counts AskUserQuestion and plan approvals as "🙋 N"). cmux also
// flags a thread that simply finished as "needs input"; that is not a question.
function askCount(w) {
  const l = (w && w.progress && w.progress.label) || "";
  const m = l.match(/(?:^| · )🙋 (\d+)/);
  return m ? parseInt(m[1], 10) : 0;
}
function asker(w) {
  if (!askCount(w)) return null;
  return agents(w).find((a) => a.status === "needs_input") || { status: "needs_input" };
}
// 💬: a thread finished by asking you something in plain text (live_line.py
// "💬 N"); stays until you reply in that thread.
function askedCount(w) {
  const m = ((w && w.progress && w.progress.label) || "").match(/(?:^| · )💬 (\d+)/);
  return m ? parseInt(m[1], 10) : 0;
}
function lastIdle(w) {
  return agents(w).filter((a) => a.status !== "working")
    .sort((a, b) => secs(b.lastActivityAt || 0) - secs(a.lastActivityAt || 0))[0] || null;
}
function askedSurface(w) {
  const m = ((w && w.progress && w.progress.label) || "").match(/(?:^| · )💬 \d+ ([0-9A-Fa-f-]{36})/);
  return m ? m[1] : "";
}
function askedSignal(w) {
  const n = askedCount(w);
  if (!n || asker(w)) return null;
  const sid = askedSurface(w);
  // Tap opens the tab that asked (its surface id rides in the label), else the newest idle tab.
  return { e: "💬", t: "asked you something" + (n > 1 ? ` (${n} tabs)` : ""), go: () => focusAgent(w, sid ? { surfaceId: sid } : lastIdle(w)) };
}
// The light: full glow while a thread is stopped on a question box (until he
// answers); soft glow while the workspace has something you have not opened yet
// (cmux's own unread marker, which clears when he opens the tab).
function glow(w) { return asker(w) ? "full" : w && w.unread ? "soft" : ""; }
function worker(w) { return agents(w).find((a) => a.status === "working"); }
// Busy if cmux says an agent is working OR our own live line hook reports an
// activity (it clears on Stop). Catches turns cmux misses, such as a thread
// resuming on its own when a background task finishes.
// A thread stopped by a usage limit is paused, not working: cmux keeps it
// "working" and the live line hook never got its Stop, so ⏳ wins over ⚡.
function paused(w) { return part(w, "⏳") !== ""; }
function busy(w) { return !paused(w) && (!!worker(w) || part(w, "⚡") !== ""); }
function parts(w) {
  const l = (w && w.progress && w.progress.label) || "";
  return l ? l.split(" · ") : [];
}
function part(w, prefix) {
  const p = parts(w).find((x) => x.indexOf(prefix) === 0);
  return p ? p.slice(prefix.length).trim() : "";
}
function decisions(w) {
  const p = parts(w).find((x) => /^\d+ decisions?$/.test(x));
  return p ? parseInt(p, 10) : 0;
}
function planLine(w) {
  return parts(w).filter((x) => /^(Phase |\d+ of \d+ steps)/.test(x)).join(" · ");
}
function planValue(w) { return (w && w.progress && w.progress.value) || 0; }
function tint(w, alpha) {
  const c = (w && w.color) || "";
  return /^#[0-9a-fA-F]{6}$/.test(c) ? c + alpha : "#7f7f7f" + alpha;
}
function ago(s) {
  s = Math.max(0, Math.floor(s));
  if (s < 60) return s + "s";
  const m = Math.floor(s / 60);
  if (m < 60) return m + "m";
  const h = Math.floor(m / 60);
  return h < 24 ? h + "h " + String(m % 60).padStart(2, "0") + "m" : Math.floor(h / 24) + " days";
}
function since(a) { return a && a.sinceEpoch ? ago(epoch() - secs(a.sinceEpoch)) : ""; }
function workLine(w) {
  if (!busy(w)) return "";
  const t = since(worker(w));
  return "⚡ " + (t ? t + " · " : "") + cap(part(w, "⚡") || "Working");
}
function liveText(w) {
  const q = asker(w);
  if (q) { const t = since(q); const n = askCount(w); return "🙋 " + (t ? t + " · " : "") + "Needs you" + (n > 1 ? ` (${n} tabs)` : ""); }
  if (paused(w)) return "⏳ Paused by the usage limit · " + cap(part(w, "⏳"));
  if (busy(w)) return workLine(w);
  // Nothing happening: the area's pulse, its one live reading (never money).
  return pulseText(w);
}
// Second live row: only when one tab waits on you while another is working.
function liveText2(w) { return asker(w) && busy(w) ? workLine(w) : ""; }
function liveColor(w) {
  if (asker(w)) return "primary";
  if (busy(w)) return TEXT;  // white, like every other line
  if (part(w, "▸")) return TEXT;
  return planValue(w) >= 1 ? GREEN : SOFT;
}
function showBar(w) { return !asker(w) && !busy(w) && planLine(w) !== ""; }
function slug(t) { return (t || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }

function focusAgent(w, a) {
  cmux("workspace.select", { workspace_id: w.id });
  if (a && a.surfaceId) {
    cmux("surface.focus", { surface_id: a.surfaceId, workspace_id: w.id });
    cmux("surface.trigger_flash", { surface_id: a.surfaceId, workspace_id: w.id });
  }
}
function open(w) { focusAgent(w, asker(w) || worker(w)); }
// Overview: jump to the page if it is already open in this workspace, never
// open a second copy.
function openDecisions(w) {
  cmux("workspace.select", { workspace_id: w.id });
  // file.open reuses the page if it is already open (markdown.open added a new pane each time).
  cmux("file.open", { path: VIEWS + slug(w.title) + ".md", workspace_id: w.id, focus: true });
}

// Jump to the tab a decision is answered in ("Planning tab (Main)"),
// searching every workspace; fall back to the Overview page.
function goToPlace(w, where) {
  const name = (where || "").replace(/\(.*\)/, "").replace(/\btab\b/i, "").trim().toLowerCase();
  if (name) {
    for (const ws of data.workspaces() ?? []) {
      const t = (ws.tabs || []).find((x) => (x.title || "").toLowerCase().indexOf(name) >= 0);
      if (t && (t.surfaceId || t.id)) {
        const id = t.surfaceId || t.id;
        cmux("workspace.select", { workspace_id: ws.id });
        cmux("surface.focus", { surface_id: id, workspace_id: ws.id });
        // Always visible feedback, even when that tab is the one already open.
        cmux("surface.trigger_flash", { surface_id: id, workspace_id: ws.id });
        return;
      }
    }
  }
  openDecisions(w);
}

function isPulse(w) { return !!w && !asker(w) && !busy(w) && !paused(w) && part(w, "▸") !== ""; }
function pulseText(w) {
  const p = part(w, "▸");
  return p ? p.split("•").map((x) => cap(x.trim())).join(" · ") : "";
}
// The bottom-left pill never repeats the live line: "waiting on your answer"
// already shows (with its time) on the line under the description.
function pillSignal(w) {
  const x = signal(w);
  if (x && x.e === "⏳") return null;  // already on the live line
  return x && x.e === "🙋" ? signal2(w) : x;
}
function pillText(w) {
  const x = pillSignal(w);
  return x ? `${x.e} ${cap(x.t)}` : "";
}
function ordered() {
  const ws = (data.workspaces() ?? []).slice();
  const t = (w) => secs(w.latestAt || 0);
  return ws.sort((a, b) => {
    if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1;
    if (a.pinned && b.pinned) return (a.index || 0) - (b.index || 0);
    return t(b) - t(a) || (a.index || 0) - (b.index || 0);
  });
}
// The single most urgent signal for a card, or null.
function signal(w) {
  if (!w) return null;
  const q = asker(w);
  if (q) return { e: "🙋", t: "needs you", go: () => focusAgent(w, q) };
  const ask = askedSignal(w);
  if (ask) return ask;
  const lim = part(w, "⏳");
  if (lim) return { e: "⏳", t: lim, go: () => cmux("workspace.select", { workspace_id: w.id }) };
  const due = part(w, "📅");
  if (due) {
    const [when, where] = due.split("→").map((x) => (x || "").trim());
    // Context first: the Needs you page says what is due and where to answer.
    return { e: "📅", t: when, go: () => openNeedsYou() };
  }

  const now = epoch();
  // ✅ only when nothing in this workspace is still working (the live line
  // already shows ⚡ then), and never for a tab whose newer session is busy.
  const busyTabs = new Set(agents(w).filter((a) => a.status === "working" || a.status === "needs_input").map((a) => a.surfaceId || a.panelId));
  const done = busy(w) || asker(w) ? null : agents(w).find((a) => a.status === "idle" && a.lastActivityAt
    && now - secs(a.lastActivityAt) < 1800 && !busyTabs.has(a.surfaceId || a.panelId));
  if (done) return { e: "✅", t: "done " + ago(now - secs(done.lastActivityAt)) + " ago", go: () => focusAgent(w, done) };
  if (w.pr && w.pr.status === "open") return { e: "🔀", t: "PR #" + w.pr.number, go: () => openURL(w.pr.url) };
  if (w.latestAt && now - secs(w.latestAt) > 5 * 86400) {
    return { e: "💤", t: "quiet " + ago(now - secs(w.latestAt)), go: () => cmux("workspace.select", { workspace_id: w.id }) };
  }
  return null;
}
function signal2(w) {
  if (!w) return null;
  const ask = askedSignal(w);
  if (ask) return ask;

  const lim = part(w, "⏳");
  if (lim) return { e: "⏳", t: lim, go: () => cmux("workspace.select", { workspace_id: w.id }) };
  const due = part(w, "📅");
  if (due) {
    const [when, where] = due.split("→").map((x) => (x || "").trim());
    // Context first: the Needs you page says what is due and where to answer.
    return { e: "📅", t: when, go: () => openNeedsYou() };
  }

  const now = epoch();
  // ✅ only when nothing in this workspace is still working (the live line
  // already shows ⚡ then), and never for a tab whose newer session is busy.
  const busyTabs = new Set(agents(w).filter((a) => a.status === "working" || a.status === "needs_input").map((a) => a.surfaceId || a.panelId));
  const done = busy(w) || asker(w) ? null : agents(w).find((a) => a.status === "idle" && a.lastActivityAt
    && now - secs(a.lastActivityAt) < 1800 && !busyTabs.has(a.surfaceId || a.panelId));
  if (done) return { e: "✅", t: "done " + ago(now - secs(done.lastActivityAt)) + " ago", go: () => focusAgent(w, done) };
  if (w.pr && w.pr.status === "open") return { e: "🔀", t: "PR #" + w.pr.number, go: () => openURL(w.pr.url) };
  if (w.latestAt && now - secs(w.latestAt) > 5 * 86400) {
    return { e: "💤", t: "quiet " + ago(now - secs(w.latestAt)), go: () => cmux("workspace.select", { workspace_id: w.id }) };
  }
  return null;
}

// Sentence case for the signal pills: "Due Sunday", "Your answer", "Done 5m ago".
function cap(t) { t = String(t || ""); return t.charAt(0).toUpperCase() + t.slice(1); }
function hour12(h) { return h % 12 === 0 ? 12 : h % 12; }
function timeLine() {
  const c = clock();
  if (c.hour === undefined) return "";
  // cmux counts weekdays from 1 (Sunday = 1), like Swift's Calendar.
  const wd = typeof c.weekday === "number" ? DAYS[(c.weekday + 6) % 7] : String(c.weekday || "").slice(0, 3);
  const d = c.epoch ? new Date(c.epoch * 1000) : null;
  const date = d ? ` ${d.getDate()} ${MONTHS[d.getMonth()]}` : "";
  const long = d ? `${["January","February","March","April","May","June","July","August","September","October","November","December"][d.getMonth()]} ${d.getDate()}` : wd;
  return `${wd} · ${long} · ${hour12(c.hour)}:${String(c.minute).padStart(2, "0")} ${c.hour < 12 ? "AM" : "PM"}`;
}
function greeting() {
  const h = clock().hour;
  if (h === undefined) return "Hello, {{NAME}}";
  if (h < 5) return "Late night, {{NAME}}";
  if (h < 12) return "Good morning, {{NAME}}";
  if (h < 17) return "Good afternoon, {{NAME}}";
  return "Good evening, {{NAME}}";
}
// Header counts, each a tap target: 🙋 and ⚡ jump to the tab; the rest open
// the Needs you page (what is due, what is paused).
const NEEDS_YOU = "{{HOME}}/.claude/boards/.views/needs-you.md";
function openNeedsYou() {
  const ws = (data.workspaces() ?? []).find((w) => w.selected) || (data.workspaces() ?? [])[0];
  if (!ws) return;
  cmux("file.open", { path: NEEDS_YOU, workspace_id: ws.id, focus: true });
}
function firstWith(test) {
  for (const w of data.workspaces() ?? []) { const a = test(w); if (a) return [w, a]; }
  return null;
}
function counts() {
  let q = 0, k = 0, due = 0, bd = 0, lim = 0;
  for (const w of data.workspaces() ?? []) {
    if (asker(w)) q += 1;
    if (busy(w)) k += 1;
    if (part(w, "⏳")) lim += 1;
    const d = part(w, "📅");
    if (d) { const m = d.match(/\+(\d+)/); due += 1 + (m ? parseInt(m[1], 10) : 0); }
  }
  return { q, k, due, bd, lim };
}
const HEADER_ITEMS = [
  { text: (c) => (c.q ? `🙋 Waiting ${c.q}` : ""), go: () => { const f = firstWith(asker); if (f) focusAgent(f[0], f[1]); } },
  { text: (c) => (c.k ? `⚡ Working ${c.k}` : ""), go: () => { const f = firstWith(worker); if (f) focusAgent(f[0], f[1]); } },
  { text: (c) => (c.lim ? `⏳ Paused ${c.lim}` : ""), go: () => openNeedsYou() },
  { text: (c) => (c.due ? `📅 Due ${c.due}` : ""), go: () => openNeedsYou() },
];
// Header summary: only what can change what you do next.
function activeLine() {
  let q = 0, k = 0, due = 0, bd = 0, lim = 0;
  for (const w of data.workspaces() ?? []) {
    if (asker(w)) q += 1;
    if (busy(w)) k += 1;
    if (part(w, "📅")) due += 1;
    if (part(w, "⏳")) lim += 1;
  }
  const out = [];
  if (q) out.push(`🙋 ${q} waiting`);
  if (k) out.push(`⚡ ${k} working`);
  if (lim) out.push(`⏳ ${lim} paused`);
  if (due) out.push(`📅 ${due} due soon`);
  return out.length ? out.join(" · ") : "All clear";
}
function decisionTotal() {
  let d = 0;
  for (const w of data.workspaces() ?? []) d += decisions(w);
  return d ? `${d} decisions` : "";
}

sidebar(() =>
  VStack({ spacing: 6 }, [
    // Header: greeting and date/time on top; activity and decisions under it.
    // Header, top to bottom: the date and time (small, top right), the
    // greeting, then what is going on.
    HStack({ spacing: 0 }, [
      Spacer({ minLength: 0 }),
      Text(() => timeLine()).font(10).weight("medium").color(SOFT).lineLimit(1),
    ]),
    HStack({ spacing: 0 }, [
      Text(() => greeting()).font(15).weight("bold").color(TEXT).lineLimit(1),
      Spacer({ minLength: 0 }),
    ]).paddingVertical(2),
    // Under the date: each count is its own tap target.
    HStack({ spacing: 0 }, [
      ...HEADER_ITEMS.map((it, i) =>
        Text(() => it.text(counts()))
          .font(10).weight("regular").color(TEXT).lineLimit(1)
          .paddingTrailing(() => (it.text(counts()) ? 10 : 0))
          .onTap(() => it.go())),
      Text(() => (HEADER_ITEMS.some((it) => it.text(counts())) ? "" : "All clear"))
        .font(10).weight("regular").color(SOFT),
      Spacer({ minLength: 0 }),
    ]).paddingVertical(4),
    Divider(),
    // Pinned workspaces first (in their pinned order), then the most recently
    // active at the top. Right-click a card to pin or unpin it.
    ForEach(
      { items: () => ordered(), key: (w) => w.id },
      (w) =>
        VStack({ spacing: 5 }, [
          // Spacing 0 so hidden items leave no gap: the right edge stays flush.
          HStack({ spacing: 0 }, [
            Text(() => (w() && w().title) || "").font(14).weight("bold").lineLimit(1),
            Spacer({ minLength: 0 }),
            // Top right: only the blue unread count (replies you have not read).
            Text(() => (w() && w().unread ? `${w().unread}` : ""))
              .font(10).bold().color("white")
              .paddingHorizontal(() => (w() && w().unread ? 5 : 0))
              .background(() => (w() && w().unread ? BLUE : null)).cornerRadius(7)
              .paddingLeading(() => (w() && w().unread ? 6 : 0)),
          ]),
          HStack({ spacing: 0 }, [
            Text(() => (w() && w().description) || "")
              .font(11).weight("medium").color(TEXT).lineLimit(2),
            Spacer({ minLength: 0 }),
          ]),
          // Live line, its own row under the description: what an agent is
          // doing right now, or how long it has waited on you. Zero height when idle.
          // When nothing is happening this line is the area's pulse, drawn as a
          // "live reading" chip: a dot in the workspace colour and a stronger
          // wash of that colour, so it never looks like a signal or an action.
          HStack({ spacing: 0 }, [
            HStack({ spacing: 0 }, [
              Text(() => (isPulse(w()) ? "●" : "")).font(8).color(() => tint(w(), "FF"))
                .paddingTrailing(() => (isPulse(w()) ? 5 : 0)),
              Text(() => liveText(w())).font(9).weight(() => (isPulse(w()) ? "semibold" : "medium"))
                .color(() => liveColor(w())).lineLimit(1).truncation("tail"),
            ])
              .paddingHorizontal(() => (isPulse(w()) ? 7 : 0))
              .paddingVertical(() => (isPulse(w()) ? 3 : 0))
              .background(() => (isPulse(w()) ? tint(w(), "40") : null)).cornerRadius(10),
            Spacer({ minLength: 0 }).frame({ width: 0 }),
          ])
            .frame({ height: () => (liveText(w()) ? (isPulse(w()) ? 19 : 13) : 0) })
            .opacity(() => (liveText(w()) ? 1 : 0))
            .paddingVertical(() => (liveText(w()) ? 1 : 0)),
          HStack({ spacing: 0 }, [
            Text(() => liveText2(w())).font(9).weight("medium").color(TEXT).lineLimit(1).truncation("tail"),
            Spacer({ minLength: 0 }).frame({ width: 0 }),
          ])
            .frame({ height: () => (liveText2(w()) ? 13 : 0) })
            .opacity(() => (liveText2(w()) ? 1 : 0)),
          // Bottom row: two matching pills. Left: the most urgent signal (tap to
          // go there). Right: Overview with the decisions count inside it.
          HStack({ spacing: 0 }, [
            // Bottom left: what needs you, when something does; otherwise the
            // area's pulse (its one live line). Truncates before Overview.
            Text(() => pillText(w()))
              .font(8).weight("semibold").color(TEXT).lineLimit(1).truncation("tail")
              .paddingHorizontal(() => (pillText(w()) ? 7 : 0))
              .paddingVertical(() => (pillText(w()) ? 3 : 0))
              .background(() => (pillText(w()) ? "#ffffff1a" : null)).cornerRadius(6)
              .hoverBackground("#ffffff2a")
              .onTap(() => { const x = pillSignal(w()); if (x) x.go(); else open(w()); }),
            Spacer({ minLength: 6 }),
            HStack({ spacing: 0 }, [
              Text("Overview").font(8).weight("semibold").color(SOFT).lineLimit(1),
              Text(() => (decisions(w()) ? `${decisions(w())}` : ""))
                .font(8).weight("heavy").color(TEXT)
                .paddingLeading(() => (decisions(w()) ? 6 : 0)),
              Text("›").font(8).weight("semibold").color(SOFT).lineLimit(1).paddingLeading(5),
            ])
              .frame({ minWidth: 76 })
              .paddingHorizontal(4).paddingVertical(3)
              .hoverBackground("#ffffff1a").cornerRadius(6)
              .onTap(() => openDecisions(w())),
          ]),
        ])
          .paddingHorizontal(10).paddingVertical(10)
          // Lit means go back in there. Full glow: stopped on a question box
          // (white outline, until answered). Soft glow: something new not yet
          // opened (white outline too, clears when opened).
          .background(() => tint(w(), glow(w()) === "full" ? "73" : glow(w()) === "soft" || (w() && w().selected) ? "59" : "33"))
          .borderColor(() => (glow(w()) ? TEXT : null))
          .borderWidth(() => (glow(w()) ? 1.5 : 0))
          .cornerRadius(10)
          .hoverBackground("#ffffff12")
          .frame({ maxWidth: "infinity" })
          .onTap(() => open(w()))
          .contextMenu([
            Button(() => (w() && w().pinned ? "Unpin" : "Pin to top"), () =>
              cmux("workspace.action", { workspace_id: w().id, action: w().pinned ? "unpin" : "pin" })),
          ])
    ),
  ]).paddingHorizontal(6)
);
