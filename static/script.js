// ===== SETTINGS: change these when Member 3's backend is ready =====
const API_URL = "/trace";       // POST  {destination} -> trace JSON
const HISTORY_URL = "/history"; // GET   -> list of past traces
const USE_MOCK = true;          // true = fake data (no backend needed). Set to false later.
// ===================================================================

const $ = id => document.getElementById(id);
const root = document.documentElement;
let chart = null, last = null, slowestIdx = -1;
const mockHistory = [];

// Fake data in the agreed JSON format
function mockTrace(dest) {
  return {
    destination: dest, resolved_ip: "142.250.183.14",
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

async function getTrace(dest) {
  if (USE_MOCK) { await new Promise(r => setTimeout(r, 700)); return mockTrace(dest); }
  const res = await fetch(API_URL, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ destination: dest })
  });
  if (!res.ok) throw new Error("The server returned an error (" + res.status + ").");
  return res.json();
}

async function getHistory() {
  if (USE_MOCK) return mockHistory;
  try { const r = await fetch(HISTORY_URL); return r.ok ? await r.json() : []; } catch { return []; }
}

const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const isTimeout = h => h.status === "timeout" || h.latency === null || h.latency === undefined;
const speed = ms => (ms < 30 ? "fast" : ms < 100 ? "mid" : "slow");
const speedColor = ms => ({ fast: "#2f7d4a", mid: "#b7791f", slow: "#c8553d" }[speed(ms)]);

function networkStatus(st) {
  if (st.network_status || st.status) return st.network_status || st.status;
  if (st.average_latency < 50 && st.packet_loss === 0) return "GOOD";
  if (st.average_latency < 150 && st.packet_loss < 20) return "FAIR";
  return "POOR";
}

function renderStats(data) {
  const st = data.statistics;
  $("s-hops").textContent = st.total_hops;
  $("s-avg").textContent = Number(st.average_latency).toFixed(1) + " ms";
  $("s-min").textContent = st.min_latency + " ms";
  $("s-max").textContent = st.max_latency + " ms";
  $("s-loss").textContent = Number(st.packet_loss).toFixed(1) + "%";
  $("s-ip").textContent = data.resolved_ip;
  const status = networkStatus(st);
  const el = $("s-status");
  el.textContent = status;
  el.style.color = { GOOD: "var(--good)", FAIR: "var(--warn)", POOR: "var(--bad)" }[String(status).toUpperCase()] || "inherit";
}

function renderRoute(data) {
  $("route-title").textContent = "Your device to " + data.destination;
  const hops = data.hops;
  slowestIdx = -1;
  hops.forEach((h, i) => { if (!isTimeout(h) && (slowestIdx < 0 || h.latency > hops[slowestIdx].latency)) slowestIdx = i; });
  let html = `<li class="stop you endpoint" style="--i:0"><span class="marker"></span>
    <div><div class="name">You</div><div class="sub">Your device</div></div><span class="ms">start</span></li>`;
  hops.forEach((h, i) => {
    const last = i === hops.length - 1, t = isTimeout(h);
    const cls = "stop" + (last ? " endpoint" : "") + (t ? " timeout" : " " + speed(h.latency));
    const name = last ? esc(data.destination) : (i === 0 ? "Your router" : "Hop " + esc(h.hop_number));
    const badge = i === slowestIdx && hops.length > 2 ? '<span class="badge">slowest</span>' : "";
    html += `<li class="${cls}" style="--i:${i + 1}" data-i="${i}" tabindex="0" role="button">
      <span class="marker"></span><div><div class="name">${name}${badge}</div>
      <div class="sub">${t ? "No reply from this router" : esc(h.ip)}</div></div>
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
    $("detail").innerHTML = `<strong>Hop ${esc(h.hop_number)}</strong>: this router did not answer. Routers often ignore trace probes, so the trip can still succeed.`;
    return;
  }
  let extra = "";
  if (prev && !isTimeout(prev)) {
    const d = h.latency - prev.latency;
    extra = ` It added <strong>${d >= 0 ? "+" : ""}${d} ms</strong> compared with the previous hop.`;
  }
  if (i === slowestIdx) extra += " This is the slowest hop of the trip.";
  $("detail").innerHTML = `<strong>Hop ${esc(h.hop_number)}</strong> at <strong>${esc(h.ip)}</strong> replied in <strong>${esc(h.latency)} ms</strong>.${extra}`;
}

function renderChart(hops) {
  if (chart) chart.destroy();
  const css = getComputedStyle(root);
  Chart.defaults.color = css.getPropertyValue("--muted").trim();
  const line = css.getPropertyValue("--line").trim();
  chart = new Chart($("latency-chart"), {
    type: "line",
    data: {
      labels: hops.map(h => "Hop " + h.hop_number),
      datasets: [{
        label: "Latency (ms)", data: hops.map(h => (isTimeout(h) ? null : h.latency)),
        borderColor: line, backgroundColor: "rgba(90,169,214,.15)", fill: true, tension: 0.25, spanGaps: false,
        pointRadius: 6, pointBackgroundColor: hops.map(h => (isTimeout(h) ? line : speedColor(h.latency)))
      }]
    },
    options: {
      maintainAspectRatio: false, plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, title: { display: true, text: "ms" } } }
    }
  });
}

async function renderHistory() {
  const items = await getHistory();
  const names = [...new Set(items.map(x => (typeof x === "string" ? x : x.destination)).filter(Boolean))].slice(0, 8);
  $("history").innerHTML = names.length
    ? names.map(n => `<button class="chip" type="button" data-t="${esc(n)}">${esc(n)}</button>`).join("")
    : '<span class="note">Nothing yet. Run a trace.</span>';
}

async function runTrace(dest) {
  dest = dest.trim();
  if (!dest) return;
  $("target").value = dest;
  $("trace-btn").disabled = true;
  $("message").className = "";
  $("message").textContent = "Tracing " + dest + "... this can take up to a minute.";
  try {
    const data = await getTrace(dest);
    if (data.error) throw new Error(data.error);
    last = data;
    renderStats(data); renderRoute(data); renderChart(data.hops);
    $("results").hidden = false;
    $("message").textContent = "Resolved " + data.destination + " to " + data.resolved_ip + ".";
    if (USE_MOCK) mockHistory.unshift(dest);
    renderHistory();
  } catch (err) {
    $("results").hidden = true;
    $("message").className = "error";
    $("message").textContent = "Could not trace that address. " + err.message;
  } finally {
    $("trace-btn").disabled = false;
  }
}

// ---- events ----
$("trace-form").addEventListener("submit", e => { e.preventDefault(); runTrace($("target").value); });
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
$("replay").addEventListener("click", () => last && renderRoute(last));
$("export").addEventListener("click", () => {
  if (!last) return;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(last, null, 2)], { type: "application/json" }));
  a.download = "trace-" + last.destination + ".json";
  a.click();
});
root.dataset.theme = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
$("theme").addEventListener("click", () => {
  root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
  if (last) renderChart(last.hops);
});
renderHistory();