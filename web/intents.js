/* HomeBase intent parser: turns a spoken or typed sentence into one MCP tool call.
 * Deterministic on purpose (no LLM): fast, free, and identical on every demo take.
 * parseIntent(text, {family: ["Maya", ...], today: "YYYY-MM-DD"})
 *   -> {tool, args} | {special: "reset"} | {error: "..."} | {help: true}
 */
(function (root) {
  "use strict";

  const pad = (n) => String(n).padStart(2, "0");
  const cap = (s) => s.trim().replace(/^./, (c) => c.toUpperCase());

  function parseTime(text) {
    const patterns = [
      /\b(?:at|by|around|from|@)\s+(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?(?!\d)/i,
      /\b(\d{1,2}):(\d{2})\s*(a\.?m\.?|p\.?m\.?)?/i,
      /\b(\d{1,2})()\s*(a\.?m\.?|p\.?m\.?)(?![a-z])/i,
    ];
    for (const re of patterns) {
      const m = text.match(re);
      if (!m) continue;
      let h = parseInt(m[1], 10);
      const min = m[2] ? parseInt(m[2], 10) : 0;
      const ap = m[3] ? m[3].toLowerCase().replace(/\./g, "") : "";
      if (h > 23 || min > 59) continue;
      if (ap === "pm" && h < 12) h += 12;
      else if (ap === "am" && h === 12) h = 0;
      else if (!ap && h >= 1 && h <= 7) h += 12; // "at 5" in a family planner means 5 pm
      return { h, m: min, match: m[0] };
    }
    return null;
  }

  function addMinutes(h, m, add) {
    const total = Math.min(h * 60 + m + add, 23 * 60 + 59);
    return { h: Math.floor(total / 60), m: total % 60 };
  }

  const stamp = (day, t) => `${day}T${pad(t.h)}:${pad(t.m)}`;

  function findMember(text, names) {
    for (const n of names) {
      if (new RegExp(`\\b${n}(?:'s)?\\b`, "i").test(text)) return n;
    }
    return null;
  }

  function plusDays(day, n) {
    const d = new Date(day + "T12:00:00");
    d.setDate(d.getDate() + n);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }

  function parseDuration(text) {
    let m = text.match(/\bfor\s+(\d+(?:\.\d+)?)\s*(hours?|hrs?|minutes?|mins?)\b/i);
    if (m) {
      const n = parseFloat(m[1]);
      return { minutes: /^h/i.test(m[2]) ? Math.round(n * 60) : Math.round(n), match: m[0] };
    }
    m = text.match(/\bfor\s+an?\s+(hour|half hour)\b/i);
    if (m) return { minutes: /half/i.test(m[1]) ? 30 : 60, match: m[0] };
    return null;
  }

  function splitQty(raw) {
    let item = raw.trim().replace(/[.!?]+$/, "");
    let qty = "1";
    let m = item.match(/^(a dozen|dozen)\s+(.+)/i);
    if (m) return { qty: "12", item: cap(m[2]) };
    m = item.match(/^(\d+(?:\.\d+)?\s*(?:kg|g|l|litres?|liters?|ml|lbs?|packs?|bottles?|cartons?)?)\s+(?:of\s+)?(.+)/i);
    if (m) return { qty: m[1].trim(), item: cap(m[2]) };
    item = item.replace(/^(some|a|an|the)\s+/i, "");
    return { qty, item: cap(item) };
  }

  function parseIntent(text, ctx) {
    const family = (ctx && ctx.family) || [];
    const today = (ctx && ctx.today) || new Date().toISOString().slice(0, 10);
    const raw = (text || "").trim();
    if (!raw) return { help: true };
    const l = raw.toLowerCase().replace(/^(hey |ok |okay )?(alexa|homebase)[,!. ]*/i, "").replace(/[.!?]+$/, "").trim();
    let m;

    if (/^(reset|start over|clear everything)\b/.test(l)) return { special: "reset" };
    if (/\b(load|set up|use|start)\b.*\b(demo|sample)\b/.test(l) || /\bdemo family\b/.test(l))
      return { tool: "load_demo_family", args: {} };

    // groceries
    m = l.match(/\b(?:add|put|get|buy)\s+(.+?)\s+(?:to|on|onto)\s+(?:the|our|my)?\s*(?:grocery|groceries|shopping)(?:\s+list)?$/) ||
        l.match(/\b(?:add|put)\s+(.+?)\s+(?:to|on)\s+(?:the|our)\s+list$/) ||
        l.match(/^we (?:need|are out of|ran out of|have run out of)\s+(.+)$/);
    if (m) {
      const { qty, item } = splitQty(m[1]);
      const who = findMember(raw, family);
      return { tool: "grocery_add", args: { item, qty, ...(who ? { added_by: who } : {}) } };
    }
    if (/\b(grocery|groceries|shopping) list\b/.test(l) || /\bwhat do we need\b/.test(l) || /\bwhat'?s on the list\b/.test(l))
      return { tool: "grocery_list", args: {} };

    // pickups
    if (/\bwho (can|could|is able to|is free to)\s+(pick|get|collect|drive|do the pick)/.test(l)) {
      const t = parseTime(raw) || { h: 17, m: 30 };
      return { tool: "who_can_pickup", args: { start: stamp(today, t), end: stamp(today, addMinutes(t.h, t.m, 45)) } };
    }
    if (/\b(pick ?up|pick .{1,20} up|drop ?off|drop .{1,20} off|collect)\b/.test(l) && !/\bchore\b/.test(l)) {
      const t = parseTime(raw) || { h: 17, m: 30 };
      const who = findMember(raw, family);
      const verb = /drop/.test(l) ? "Drop off" : "Pick up";
      const from = raw.match(/\bfrom\s+([a-z ]+?)(?:\s+(?:at|by|around)\b|$)/i);
      const title = who ? `${verb} ${who}${from ? " from " + from[1].trim() : ""}` : "Pickup";
      return { tool: "assign_pickup", args: { title, start: stamp(today, t), end: stamp(today, addMinutes(t.h, t.m, 45)) } };
    }

    // chores
    m = l.match(/^(?:i\s+)?(?:finished|completed|did|done with|just finished|just did)\s+(?:the\s+)?(.+)$/) ||
        l.match(/^mark\s+(?:the\s+)?(.+?)\s+(?:as\s+)?(?:done|complete|completed|finished)$/) ||
        l.match(/^(?:the\s+)?(.+?)\s+(?:is|are)\s+(?:done|finished|complete|completed)$/);
    if (m) return { tool: "complete_chore", args: { title: m[1].replace(/^(?:chore\s+)/, "").trim() } };

    if (/\bchore\b/.test(l) && /^(add|new|create|give|assign|put|make)\b/.test(l)) {
      const args = {};
      const e = raw.match(/\beffort\s*(?:of\s*)?([1-5])\b/i);
      if (e) args.effort = parseInt(e[1], 10);
      else if (/\b(hard|big|heavy|deep|huge)\b/i.test(raw)) args.effort = 4;
      else if (/\b(easy|quick|small|tiny)\b/i.test(raw)) args.effort = 1;
      else args.effort = 2;
      let body = raw
        .replace(/\beffort\s*(?:of\s*)?[1-5]\b/i, "")
        .replace(/\b(hard|big|heavy|easy|quick|small|tiny|huge)\s+(?=chore\b)/gi, "")
        .replace(/^(?:please\s+)?(?:add|new|create|give|assign|put|make)\s+(?:a\s+|an\s+|the\s+)?(?:new\s+)?chore\s*(?:called|named|to|for|:|-)?\s*/i, "");
      const who = body.match(/\b(?:for|assign(?:ed)? to)\s+(\w+)\s*$/i) || body.match(/\bfor\s+(\w+)\b/i);
      if (who && family.some((n) => n.toLowerCase() === who[1].toLowerCase())) {
        args.assignee = family.find((n) => n.toLowerCase() === who[1].toLowerCase());
        body = body.replace(who[0], "");
      }
      if (/\bdue\s+today\b/i.test(body)) { args.due = today; body = body.replace(/\bdue\s+today\b/i, ""); }
      else if (/\bdue\s+tomorrow\b/i.test(body)) { args.due = plusDays(today, 1); body = body.replace(/\bdue\s+tomorrow\b/i, ""); }
      args.title = cap(body.replace(/\s+/g, " ").replace(/[,.;:]+$/, "")) || "New chore";
      return { tool: "add_chore", args };
    }

    m = l.match(/^(?:check off|tick off|cross off|bought|got)\s+(?:the\s+)?(.+?)(?:\s+(?:off|from)\b.*)?$/);
    if (m && !/\b(pickup|chore)\b/.test(l)) return { tool: "grocery_bought", args: { item: cap(m[1].replace(/^some\s+/, "")) } };

    // events
    if (/^(add|schedule|book|put|set up|create)\b/.test(l) && parseTime(raw)) {
      const who = findMember(raw, family);
      if (!who) return { error: "Who is that for? Say a name, for example: schedule dentist for Arjun at 4 pm." };
      const t = parseTime(raw);
      let working = raw;
      const dur = parseDuration(working);
      if (dur) working = working.replace(dur.match, "");
      let end = dur ? addMinutes(t.h, t.m, dur.minutes) : addMinutes(t.h, t.m, 60);
      const until = working.match(/\b(?:until|till|to)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b/i);
      if (until && !dur) {
        let h = parseInt(until[1], 10), mm = until[2] ? parseInt(until[2], 10) : 0;
        const ap = (until[3] || "").toLowerCase();
        if (ap === "pm" && h < 12) h += 12; else if (ap === "am" && h === 12) h = 0; else if (!ap && h >= 1 && h <= 7) h += 12;
        if (h * 60 + mm > t.h * 60 + t.m) end = { h, m: mm };
        working = working.replace(until[0], "");
      }
      working = working.replace(t.match, " ");
      let title = working
        .replace(/^(?:please\s+)?(?:add|schedule|book|put|set up|create)\s+(?:an?\s+|the\s+)?(?:new\s+)?(?:event|appointment|reminder)?\s*(?:called|named)?\s*/i, "")
        .replace(new RegExp(`\\b${who}'s\\s+`, "i"), "")
        .replace(/\s+(?:in|on|to)\s+(?:the\s+)?(?:calendar|schedule)\b/i, "");
      const cut = title.search(new RegExp(`\\s+(?:for|with)\\s+${who}\\b|^${who}\\b`, "i"));
      if (cut > 0) title = title.slice(0, cut);
      else title = title.replace(new RegExp(`^${who}\\s*(?:has|:|-)?\\s*`, "i"), "");
      title = title.replace(/^(?:an?|the)\s+/i, "").replace(/\s+/g, " ").replace(/[,.;:]+$/, "").trim();
      const day = /\btomorrow\b/.test(l) ? plusDays(today, 1) : today;
      title = title.replace(/\btomorrow\b/i, "").trim();
      return { tool: "add_event", args: { title: cap(title || "Event"), member: who, start: stamp(day, t), end: stamp(day, end) } };
    }

    // briefing and status
    if (/\b(brief|briefing|plan|schedule|agenda|what'?s (on|happening|up)|what do we have|what have we got|morning|today|tomorrow|day)\b/.test(l)) {
      return { tool: "daily_briefing", args: /\btomorrow\b/.test(l) ? { day: plusDays(today, 1) } : {} };
    }
    if (/\b(fair|fairness|workload|whose turn|who'?s turn|who has|who did|chores?|turn)\b/.test(l))
      return { tool: "chore_status", args: {} };

    return { help: true };
  }

  const api = { parseIntent, parseTime };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.HomeBaseIntents = api;
})(typeof window !== "undefined" ? window : globalThis);
