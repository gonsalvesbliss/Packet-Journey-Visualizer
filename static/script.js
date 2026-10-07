// ===== SETTINGS: change these when Member 3's backend is ready =====
const API_URL = "/trace";       // POST {destination, mode} -> trace JSON
const HISTORY_URL = "/history"; // GET  -> list of past traces
const USE_MOCK = false;          // true = fake data. Set to false to use the real backend.
// ===================================================================

const $ = id => document.getElementById(id);
const root = document.documentElement;
let last = null, mode = "traceroute", slowestIdx = -1, destIdx = -1;
const mockHistory = [];

// Fake data in the agreed format. Hop 3 times out but the route continues.
function mockTrace(dest) {
  return {
    destination: dest, resolved_ip: "142.250.183.14",
    ping: { sent: 4, received: 4, packet_loss: 0, min_latency: 12, average_latency: 14.5, max_latency: 19 },
    hops: [
      { hop_number: 1, ip: "192.168.1.1", latency: 2, status: "ok" },
      { hop_number: 2, ip: "10.20.0.1", latency: 8, status: "ok" },
      { hop_number: 3, ip: "*", latency: null, status: "timeout" },
      { hop_number: 4, ip: "72.14.204.1", latency: 21, status: "ok" },
      { hop_number: 5, ip: "108.170.251.129", latency: 74, status: "ok" },
      { hop_number: 6, ip: "142.250.183.14", latency: 27, status: "ok" }
    ],
    statistics: { total_hops: 6, average_latency: 26.4, packet_loss: 16.7, min_latency: 2, max_latency: 74 }
  };
}

async function getTrace(dest, m) {
  if (USE_MOCK) { await new Promise(r => setTimeout(r, 600)); return mockTrace(dest); }
  const res = await fetch(API_URL, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ destination: dest, mode: m })   // backend may ignore "mode" for now
  });
  if (!res.ok) throw new Error("The server returned an error (" + res.status + ").");
  return res.json();
}

async function getHistory() {
  if (USE_MOCK) return mockHistory;
  try { const r = await fetch(HISTORY_URL); return r.ok ? await r.json() : []; } catch { return []; }
}

// ---------- helpers ----------
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const isTimeout = h => h.status === "timeout" || h.latency === null || h.latency === undefined;
const speed = v => (v < 30 ? "fast" : v < 100 ? "mid" : "slow");
const speedColor = v => ({ fast: "var(--good)", mid: "var(--warn)", slow: "var(--bad)" }[speed(v)]);
const ms = v => (v === null || v === undefined || isNaN(v) ? "-" : Math.round(v * 10) / 10 + " ms");
const pct = v => (v === null || v === undefined || isNaN(v) ? "-" : Math.round(v * 10) / 10 + "%");
// Index of the next hop that replied (the router the route continued through), or -1.
const nextReply = (hops, i) => hops.findIndex((h, j) => j > i && !isTimeout(h));

function networkStatus(st) {
  if (st.network_status || st.status) return st.network_status || st.status;
  if (st.average_latency < 50 && st.packet_loss === 0) return "GOOD";
  if (st.average_latency < 150 && st.packet_loss < 20) return "FAIR";
  return "POOR";
}
const statusColor = s => ({ GOOD: "var(--good)", FAIR: "var(--warn)", POOR: "var(--bad)" }[String(s).toUpperCase()]);

// Reads the ping result, tolerating a few possible field names from the backend.
function getPing(data) {
  const p = data.ping;
  if (!p) return null;
  const sent = p.sent, rec = p.received;
  return {
    sent, rec,
    loss: p.packet_loss ?? (sent ? ((sent - rec) / sent) * 100 : null),
    avg: p.average_latency ?? p.avg_latency ?? p.avg, min: p.min_latency ?? p.min, max: p.max_latency ?? p.max,
    reachable: rec !== undefined ? rec > 0 : (p.reachable ?? null)
  };
}

// ---------- stat cards (no IP addresses shown) ----------
function statCards(items) {
  $("stats").innerHTML = items.map(([v, l, c]) =>
    `<div class="stat"><span class="value"${c ? ` style="color:${c}"` : ""}>${esc(v)}</span><span class="label">${l}</span></div>`).join("");
}

function renderStats(data) {
  if (mode === "ping") {
    const p = getPing(data) || {};
    statCards([
      [p.reachable === null || p.reachable === undefined ? "-" : p.reachable ? "Yes" : "No", "Destination reachable",
        p.reachable ? "var(--good)" : p.reachable === false ? "var(--bad)" : ""],
      [p.sent !== undefined ? p.rec + " / " + p.sent : "-", "Replies received"],
      [pct(p.loss), "Packet loss"], [ms(p.avg), "Average response"], [ms(p.min), "Fastest"], [ms(p.max), "Slowest"]
    ]);
    return;
  }
  const st = data.statistics, hops = data.hops, silent = hops.filter(isTimeout).length, status = networkStatus(st);
  statCards([
    [st.total_hops ?? hops.length, "Hops"], [ms(st.average_latency), "Average latency"],
    [ms(st.min_latency), "Fastest hop"], [ms(st.max_latency), "Slowest hop"],
    [silent + " of " + hops.length, "Hops with no reply"], [status, "Network status", statusColor(status)]
  ]);
}

function renderPing(data) {
  const p = getPing(data), b = $("ping-banner");
  if (!p) {
    b.className = "banner";
    b.textContent = "The backend did not send ping results yet. Ask Member 3 to include a \"ping\" object in the /trace response.";
  } else if (p.reachable) {
    b.className = "banner ok";
    b.textContent = data.destination + " is reachable. Replies came back in about " + ms(p.avg) + ".";
  } else {
    b.className = "banner fail";
    b.textContent = "No reply from " + data.destination + ". It may be down or may block ping. Try Traceroute to see how far the packets get.";
  }
}

// ---------- journey list (left/bottom) ----------
function renderRoute(data) {
  $("route-title").textContent = "Your device to " + data.destination;
  const hops = data.hops;
  slowestIdx = -1;
  hops.forEach((h, i) => { if (!isTimeout(h) && (slowestIdx < 0 || h.latency > hops[slowestIdx].latency)) slowestIdx = i; });
  // The destination is the hop whose IP matches the DNS result, NOT simply the last item.
  // (IPs are used only for this check and are never displayed.)
  destIdx = hops.findIndex(h => !isTimeout(h) && h.ip === data.resolved_ip);
  $("route-note").textContent = destIdx >= 0 ? "" :
    "The destination was not confirmed in this trace. Some networks block traceroute replies, so this does not mean the destination is down.";

  let html = `<li class="stop you endpoint" style="--i:0"><span class="marker"></span>
    <div><div class="name">You</div><div class="sub">Your device</div></div><span class="ms">start</span></li>`;
  hops.forEach((h, i) => {
    const t = isTimeout(h), isDest = i === destIdx;
    const cls = "stop" + (isDest ? " endpoint" : "") + (t ? " timeout" : " " + speed(h.latency));
    const name = isDest ? esc(data.destination) : (!t && i === 0 ? "Your router" : "Hop " + esc(h.hop_number));
    const badge = i === slowestIdx && hops.length > 2 ? '<span class="badge">slowest</span>' : "";
    const nx = nextReply(hops, i);
    const sub = t ? "No reply" + (nx >= 0 ? ` <span class="via">&#8618; alternate route to Hop ${esc(hops[nx].hop_number)}</span>` : "")
                  : (isDest ? "Destination reached" : "Router replied");
    html += `<li class="${cls}" style="--i:${i + 1}" data-i="${i}" tabindex="0" role="button">
      <span class="marker"></span><div><div class="name">${name}${badge}</div><div class="sub">${sub}</div></div>
      <span class="ms">${t ? "timeout" : esc(h.latency) + " ms"}</span></li>`;
  });
  const route = $("route");
  route.innerHTML = html + '<span class="packet" id="packet"></span>';
  $("detail").textContent = "Select a station to see its details.";
  if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
    $("packet").animate([{ top: "6px" }, { top: (route.offsetHeight - 22) + "px" }],
      { duration: (hops.length + 1) * 420, easing: "linear", fill: "forwards" });
  }
}

function showDetail(i) {
  const h = last.hops[i], prev = last.hops[i - 1];
  document.querySelectorAll(".stop").forEach(s => s.classList.toggle("selected", s.dataset.i == i));
  if (isTimeout(h)) {
    const nx = nextReply(last.hops, i), n = last.hops[nx];
    $("detail").innerHTML = `<strong>Hop ${esc(h.hop_number)}</strong> did not reply. ` + (nx >= 0
      ? `This does not mean the route ended. The line stops here, then your data took an <strong>alternate route to Hop ${esc(n.hop_number)}</strong>, which replied in ${esc(n.latency)} ms. Traceroute cannot show the exact path used, only that traffic got through.`
      : "No later hop answered either, so the trace could not confirm what happens after this point.");
    return;
  }
  let extra = "";
  if (prev && !isTimeout(prev)) { const d = h.latency - prev.latency; extra = ` It added <strong>${d >= 0 ? "+" : ""}${d} ms</strong> compared with the previous hop.`; }
  if (i === slowestIdx) extra += " This is the slowest hop of the trip.";
  if (i === destIdx) extra += " This is the destination.";
  $("detail").innerHTML = `<strong>Hop ${esc(h.hop_number)}</strong> replied in <strong>${esc(h.latency)} ms</strong>.${extra}`;
}

// ---------- latency graph (SVG) with reroute animation ----------
let mapRun = 0;   // bumped on every render so an old animation stops when a new one starts

// Draws `p` (0..1) of a path. dash = null -> solid line, number -> dashed line.
function reveal(el, len, p, dash) {
  if (!dash) { el.style.strokeDasharray = len; el.style.strokeDashoffset = len * (1 - p); return; }
  const v = len * p; let a = [];
  for (let pos = 0; pos < v; pos += 2 * dash) a.push(Math.min(dash, v - pos), dash);
  if (!a.length) a = [0, len];
  a[a.length - 1] = len + 10;                    // big final gap so the pattern doesn't repeat
  el.style.strokeDasharray = a.join(" "); el.style.strokeDashoffset = 0;
}

function renderMap(hops) {
  const tok = ++mapRun;
  const n = hops.length, GAP = 100, L = 64, T = 56, PH = 230, B = 64;
  const X = k => L + k * GAP, W = X(n) + 56, H = T + PH + B, base = T + PH;
  const lats = hops.filter(h => !isTimeout(h)).map(h => h.latency);
  const top = Math.max(20, Math.ceil(Math.max(...lats, 10) * 1.15 / 10) * 10);
  const Y = v => base - (v / top) * PH;
  const pt = p => p.x + " " + p.y;

  const rep = [{ k: 0, x: X(0), y: Y(0) }];                       // origin = "You"
  hops.forEach((h, i) => { if (!isTimeout(h)) rep.push({ k: i + 1, x: X(i + 1), y: Y(h.latency), i }); });

  // where each timeout node sits (just below the line)
  const tpos = {};
  hops.forEach((h, i) => {
    if (!isTimeout(h)) return;
    const k = i + 1, x = X(k);
    const prev = [...rep].reverse().find(p => p.k < k), next = rep.find(p => p.k > k);
    const lineY = next ? prev.y + ((next.y - prev.y) * (x - prev.x)) / (next.x - prev.x) : prev.y;
    tpos[k] = { x, y: Math.min(lineY + 38, base - 14), i };
  });

  // ---- build the list of segments the packet will travel, in order ----
  const segs = [];
  for (let j = 1; j < rep.length; j++) {
    const a = rep[j - 1], b = rep[j];
    if (b.k === a.k + 1) { segs.push({ type: "main", d: `M${pt(a)} L${pt(b)}` }); continue; }
    const ks = []; for (let k = a.k + 1; k < b.k; k++) ks.push(k);
    segs.push({ type: "dead", ks, d: "M" + pt(a) + ks.map(k => ` L${tpos[k].x} ${tpos[k].y}`).join("") });
    const cy = Math.max(Math.min(a.y, b.y) - 70, 10);
    segs.push({ type: "alt", d: `M${pt(a)} Q${(a.x + b.x) / 2} ${cy} ${pt(b)}`,
                mid: { x: (a.x + b.x) / 2, y: 0.25 * a.y + 0.5 * cy + 0.25 * b.y } });
  }
  const lastRep = rep[rep.length - 1];
  if (lastRep.k < n) {                                             // timeouts at the very end, no way forward
    const ks = []; for (let k = lastRep.k + 1; k <= n; k++) ks.push(k);
    segs.push({ type: "dead", final: true, ks, d: "M" + pt(lastRep) + ks.map(k => ` L${tpos[k].x} ${tpos[k].y}`).join("") });
  }

  // ---- draw ----
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Latency graph: the packet hits a timeout, then takes an alternate route">`;
  for (let g = 0; g <= 4; g++) {
    const v = (top / 4) * g, y = Y(v);
    s += `<line x1="${L}" y1="${y}" x2="${W - 20}" y2="${y}" class="${g ? "m-grid" : "m-axis"}"/>
          <text x="${L - 10}" y="${y + 4}" class="m-tick" text-anchor="end">${Math.round(v)}</text>`;
  }
  s += `<line x1="${L}" y1="${T - 10}" x2="${L}" y2="${base}" class="m-axis"/>
        <text x="14" y="${T + PH / 2}" class="m-tick" text-anchor="middle" transform="rotate(-90 14 ${T + PH / 2})">Latency (ms)</text>
        <text id="m-status" x="${L + 8}" y="22" class="m-status"></text>`;

  segs.forEach((g, i) => {
    const cls = g.type === "main" ? "m-line" : g.type === "dead" ? "m-branch" : "m-altpath";
    s += `<path id="seg${i}" d="${g.d}" class="${cls}" fill="none"/>`;
    if (g.type === "alt") s += `<text id="altl${i}" x="${g.mid.x}" y="${g.mid.y - 8}" class="m-alt-label" style="opacity:0">alternate route</text>`;
  });

  Object.keys(tpos).forEach(k => {                                 // timeout nodes (dim until the packet gets there)
    const t = tpos[k];
    s += `<g id="tn${k}" style="opacity:.3">
            <circle cx="${t.x}" cy="${t.y}" r="13" class="m-node m-t" style="stroke:var(--bad)"/>
            <text x="${t.x}" y="${t.y + 7}" class="m-x">&times;</text>
            <text x="${t.x}" y="${t.y + 30}" class="m-name" style="fill:var(--bad)">Timeout</text>
          </g>`;
  });

  rep.forEach(p => {
    const start = p.k === 0, dest = p.i === destIdx && !start, c = start ? "var(--line)" : speedColor(hops[p.i].latency);
    s += `<circle cx="${p.x}" cy="${p.y}" r="${start || dest ? 10 : 8}" class="m-node" style="stroke:${c}"/>`;
    if (!start) s += `<text x="${p.x}" y="${p.y - 16}" class="m-lat" style="fill:${c}">${esc(hops[p.i].latency)} ms</text>`;
  });
  s += `<text x="${X(0)}" y="${base + 20}" class="m-name">You</text>`;
  hops.forEach((h, i) => { s += `<text x="${X(i + 1)}" y="${base + 20}" class="m-name"${isTimeout(h) ? ' style="fill:var(--bad)"' : ""}>${i === destIdx ? "Destination" : "Hop " + esc(h.hop_number)}</text>`; });
  s += `<circle id="pk" r="7" cx="${rep[0].x}" cy="${rep[0].y}" class="m-packet"/>`;
  $("map").innerHTML = s + "</svg>";

  // ---- animate ----
  const svg = $("map").querySelector("svg"), pk = svg.querySelector("#pk"), st = svg.querySelector("#m-status");
  const say = t => { st.textContent = t; };
  const mv = p => { pk.setAttribute("cx", p.x); pk.setAttribute("cy", p.y); };
  const dashOf = g => g.type === "main" ? null : g.type === "dead" ? 5 : 8;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const tween = (dur, fn) => new Promise(res => {
    const t0 = performance.now();
    (function f() {
      if (tok !== mapRun) return res(false);
      const p = Math.min(1, (performance.now() - t0) / dur);
      fn(p); p < 1 ? requestAnimationFrame(f) : res(true);
    })();
  });
  const finalMsg = () => destIdx >= 0 ? "Packet reached the destination." : "Trace finished.";

  if (matchMedia("(prefers-reduced-motion: reduce)").matches) {   // static version, everything visible
    segs.forEach((g, i) => { const el = svg.querySelector("#seg" + i); reveal(el, el.getTotalLength(), 1, dashOf(g)); if (g.type === "alt") svg.querySelector("#altl" + i).style.opacity = 1; });
    Object.keys(tpos).forEach(k => svg.querySelector("#tn" + k).style.opacity = 1);
    pk.remove(); say("Timeouts are shown as red branches; the amber arc is the alternate route."); return;
  }

  segs.forEach((g, i) => { const el = svg.querySelector("#seg" + i); reveal(el, el.getTotalLength(), 0, dashOf(g)); });

  (async () => {
    say("Sending packet...");
    for (let i = 0; i < segs.length; i++) {
      const g = segs[i], el = svg.querySelector("#seg" + i), len = el.getTotalLength(), dash = dashOf(g);
      if (g.type === "dead") say("Hop " + hops[g.ks[0] - 1].hop_number + " is not replying...");
      if (g.type === "alt") say("Rerouting: taking an alternate path...");
      if (!await tween(Math.max(450, len * 5), p => { reveal(el, len, p, dash); mv(el.getPointAtLength(p * len)); })) return;

      if (g.type === "dead") {
        g.ks.forEach(k => svg.querySelector("#tn" + k).style.opacity = 1);
        pk.classList.add("lost");
        say("Timed out. No reply from Hop " + hops[g.ks[g.ks.length - 1] - 1].hop_number + ".");
        await sleep(1200); if (tok !== mapRun) return;
        if (g.final) { say("No later hop replied, so the rest of the path is unknown."); return; }
        say("Packet lost on this path. Backing up...");
        if (!await tween(450, p => mv(el.getPointAtLength((1 - p) * len)))) return;
        pk.classList.remove("lost");
        await sleep(300); if (tok !== mapRun) return;
      }
      if (g.type === "alt") svg.querySelector("#altl" + i).style.opacity = 1;
    }
    say(finalMsg());
  })();
}

// ---------- history ----------
async function renderHistory() {
  const items = await getHistory();
  const names = [...new Set(items.map(x => (typeof x === "string" ? x : x.destination)).filter(Boolean))].slice(0, 8);
  $("history").innerHTML = names.length
    ? names.map(n => `<button class="chip" type="button" data-t="${esc(n)}">${esc(n)}</button>`).join("")
    : '<span class="note">Nothing yet. Run a test.</span>';
}

// ---------- run a test ----------
async function runTrace(dest) {
  dest = dest.trim().replace(/^https?:\/\//i, "").split("/")[0];
  if (!dest) return;
  mode = document.querySelector('input[name="mode"]:checked').value;
  const label = mode === "ping" ? "Ping" : "Traceroute";
  $("target").value = dest;
  $("trace-btn").disabled = true;
  $("message").className = "";
  $("message").textContent = "Running " + label + " on " + dest + (mode === "ping" ? "..." : "... this can take up to a minute.");
  try {
    const data = await getTrace(dest, mode);
    if (data.error) throw new Error(data.error);
    last = data;
    renderStats(data);
    $("ping-view").hidden = mode !== "ping";
    $("trace-view").hidden = mode !== "traceroute";
    if (mode === "ping") renderPing(data); else { renderRoute(data); renderMap(data.hops); }
    $("results").hidden = false;
    $("message").textContent = label + " finished for " + data.destination + ".";
    if (USE_MOCK) mockHistory.unshift(dest);
    renderHistory();
  } catch (err) {
    $("results").hidden = true;
    $("message").className = "error";
    $("message").textContent = "Could not run " + label + ". " + err.message;
  } finally {
    $("trace-btn").disabled = false;
  }
}

// ---------- events ----------
$("trace-form").addEventListener("submit", e => { e.preventDefault(); runTrace($("target").value); });
document.querySelectorAll('input[name="mode"]').forEach(r => r.addEventListener("change", () => {
  $("trace-btn").textContent = "Run " + (r.value === "ping" ? "Ping" : "Traceroute");
}));
$("quick").innerHTML = ["google.com", "github.com", "wikipedia.org", "8.8.8.8"]
  .map(n => `<button class="chip" type="button" data-t="${n}">${n}</button>`).join("");
document.body.addEventListener("click", e => {
  const chip = e.target.closest(".chip"); if (chip) return runTrace(chip.dataset.t);
  const stop = e.target.closest(".stop[data-i]"); if (stop) showDetail(+stop.dataset.i);
});
document.body.addEventListener("keydown", e => {
  const stop = e.target.closest && e.target.closest(".stop[data-i]");
  if (stop && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); showDetail(+stop.dataset.i); }
});
$("replay").addEventListener("click", () => { if (last && mode === "traceroute") { renderRoute(last); renderMap(last.hops); } });
$("export").addEventListener("click", () => {
  if (!last) return;
  // IP addresses are stripped from the export for security.
  const { resolved_ip, ...safe } = last;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify({ ...safe, hops: last.hops.map(({ ip, ...rest }) => rest) }, null, 2)], { type: "application/json" }));
  a.download = "trace-" + last.destination + ".json";
  a.click();
});
root.dataset.theme = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
$("theme").addEventListener("click", () => {
  root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";   // the SVG map recolours itself via CSS variables
});
renderHistory();