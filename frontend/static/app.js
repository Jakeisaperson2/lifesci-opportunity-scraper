/* LifeSci Opportunity Discovery — Dashboard JS
 *
 * All API calls go through apiFetch(). State is tracked in `state`.
 * Filters trigger a debounced reload via loadOpportunities().
 */

const state = {
  page: 1,
  limit: 50,
  total: 0,
  pages: 1,
  search: "",
  type: "",
  area: "",
  days: "",
};

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function apiFetch(path, opts = {}) {
  const resp = await fetch(path, opts);
  if (!resp.ok) throw new Error(`API error ${resp.status}: ${await resp.text()}`);
  return resp.json();
}

function buildOpportunitiesUrl() {
  const p = new URLSearchParams();
  if (state.search) p.set("search", state.search);
  if (state.type)   p.set("opportunity_type", state.type);
  if (state.area)   p.set("therapeutic_area", state.area);
  if (state.days)   p.set("days", state.days);
  p.set("page", state.page);
  p.set("limit", state.limit);
  return `/api/opportunities?${p.toString()}`;
}

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

async function loadOpportunities() {
  setTableLoading(true);
  try {
    const data = await apiFetch(buildOpportunitiesUrl());
    state.total = data.total;
    state.pages = data.pages;
    renderTable(data.items);
    renderPagination();
    document.getElementById("statShowing").textContent = data.items.length;
  } catch (e) {
    renderTableError(e.message);
  } finally {
    setTableLoading(false);
  }
}

async function loadStats() {
  try {
    // Total count
    const all = await apiFetch("/api/opportunities?limit=1");
    document.getElementById("statTotal").textContent = all.total.toLocaleString();

    // New this week
    const week = await apiFetch("/api/opportunities?limit=1&days=7");
    document.getElementById("statWeek").textContent = week.total.toLocaleString();

    // Last scrape run
    const runs = await apiFetch("/api/scrape/runs?limit=1");
    if (runs.length > 0) {
      const run = runs[0];
      const ts = run.completed_at || run.started_at;
      const label = ts ? new Date(ts).toLocaleString() : "In progress";
      document.getElementById("statLastRun").textContent = label;
    }
  } catch (e) {
    console.warn("Stats load failed:", e);
  }
}

// ---------------------------------------------------------------------------
// Table rendering
// ---------------------------------------------------------------------------

const TYPE_COLORS = {
  grant:             "bg-blue-100 text-blue-700",
  clinical_trial:    "bg-purple-100 text-purple-700",
  rfp:               "bg-orange-100 text-orange-700",
  collaboration:     "bg-teal-100 text-teal-700",
  sponsored_research:"bg-indigo-100 text-indigo-700",
  pilot_study:       "bg-yellow-100 text-yellow-700",
  data_partnership:  "bg-cyan-100 text-cyan-700",
  other:             "bg-gray-100 text-gray-500",
};

const AREA_COLORS = {
  oncology:           "bg-red-100 text-red-600",
  cardiology:         "bg-rose-100 text-rose-600",
  neurology:          "bg-violet-100 text-violet-700",
  rare_disease:       "bg-amber-100 text-amber-700",
  ai_digital_health:  "bg-sky-100 text-sky-700",
  immunology:         "bg-emerald-100 text-emerald-700",
  infectious_disease: "bg-lime-100 text-lime-700",
};

function badge(value, colorMap, fallback = "bg-gray-100 text-gray-500") {
  if (!value) return "";
  const cls = colorMap[value] || fallback;
  const label = value.replace(/_/g, " ");
  return `<span class="badge ${cls}">${label}</span>`;
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function renderTable(items) {
  const tbody = document.getElementById("tableBody");
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="px-4 py-12 text-center text-gray-400">No opportunities found. Try adjusting filters or run a scrape.</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map(o => `
    <tr class="hover:bg-blue-50 transition-colors cursor-pointer" onclick="window.open('${escHtml(o.url)}','_blank')">
      <td class="px-4 py-3">
        <a href="${escHtml(o.url)}" target="_blank" rel="noopener"
           class="font-medium text-blue-800 hover:underline"
           onclick="event.stopPropagation()">
          ${escHtml(o.title)}
        </a>
        ${o.description ? `<p class="text-xs text-gray-400 mt-0.5 truncate-desc">${escHtml(o.description.substring(0, 200))}</p>` : ""}
      </td>
      <td class="px-4 py-3 text-xs text-gray-600 whitespace-nowrap">${escHtml(o.company_name || "—")}</td>
      <td class="px-4 py-3">${badge(o.opportunity_type, TYPE_COLORS)}</td>
      <td class="px-4 py-3">${badge(o.therapeutic_area, AREA_COLORS)}</td>
      <td class="px-4 py-3 text-xs whitespace-nowrap ${deadlineClass(o.deadline)}">${formatDate(o.deadline)}</td>
      <td class="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">${formatDate(o.date_discovered)}</td>
      <td class="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">${escHtml(o.source_name || "—")}</td>
    </tr>
  `).join("");
}

function deadlineClass(iso) {
  if (!iso) return "text-gray-400";
  const days = (new Date(iso) - Date.now()) / 86400000;
  if (days < 0) return "text-red-400 line-through";
  if (days < 14) return "text-orange-500 font-semibold";
  return "text-gray-600";
}

function renderPagination() {
  document.getElementById("pageInfo").textContent =
    `Page ${state.page} of ${state.pages} · ${state.total.toLocaleString()} total`;
  document.getElementById("prevBtn").disabled = state.page <= 1;
  document.getElementById("nextBtn").disabled = state.page >= state.pages;
}

function setTableLoading(on) {
  if (on) {
    document.getElementById("tableBody").innerHTML =
      `<tr><td colspan="7" class="px-4 py-12 text-center text-gray-300">Loading...</td></tr>`;
  }
}

function renderTableError(msg) {
  document.getElementById("tableBody").innerHTML =
    `<tr><td colspan="7" class="px-4 py-12 text-center text-red-400">Error: ${escHtml(msg)}</td></tr>`;
}

function escHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ---------------------------------------------------------------------------
// Alert bar
// ---------------------------------------------------------------------------

function showAlert(msg, type = "info") {
  const bar = document.getElementById("alertBar");
  const classes = {
    info:    "bg-blue-50 text-blue-700 border-blue-200",
    success: "bg-green-50 text-green-700 border-green-200",
    error:   "bg-red-50 text-red-600 border-red-200",
  };
  bar.className = `px-5 py-2.5 text-sm border-b ${classes[type] || classes.info}`;
  bar.textContent = msg;
  bar.classList.remove("hidden");
  if (type !== "info" || msg.includes("complete")) {
    setTimeout(() => bar.classList.add("hidden"), 6000);
  }
}

// ---------------------------------------------------------------------------
// Scrape trigger
// ---------------------------------------------------------------------------

async function triggerScrape() {
  const btn = document.getElementById("scrapeBtn");
  btn.disabled = true;
  btn.textContent = "Running...";
  showAlert("Scrape started — this may take a minute. The page will refresh when complete.", "info");

  try {
    await apiFetch("/api/scrape", { method: "POST" });
    // Poll until all runs complete
    await pollScrapeCompletion();
    showAlert("Scrape complete. Reloading results...", "success");
    await Promise.all([loadStats(), loadOpportunities()]);
  } catch (e) {
    showAlert(`Scrape failed: ${e.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Run Scrape";
  }
}

async function pollScrapeCompletion() {
  // Poll for up to 3 minutes, checking every 4 seconds
  for (let i = 0; i < 45; i++) {
    await sleep(4000);
    const runs = await apiFetch("/api/scrape/runs?limit=5");
    const allDone = runs.every(r => r.status !== "running");
    if (allDone) return;
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ---------------------------------------------------------------------------
// Debounced filter handler
// ---------------------------------------------------------------------------

let debounceTimer;
function onFilterChange() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    state.page = 1;
    state.search = document.getElementById("searchInput").value.trim();
    state.type   = document.getElementById("typeFilter").value;
    state.area   = document.getElementById("areaFilter").value;
    state.days   = document.getElementById("daysFilter").value;
    loadOpportunities();
  }, 350);
}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------

document.getElementById("scrapeBtn").addEventListener("click", triggerScrape);

document.getElementById("searchInput").addEventListener("input", onFilterChange);
document.getElementById("typeFilter").addEventListener("change", onFilterChange);
document.getElementById("areaFilter").addEventListener("change", onFilterChange);
document.getElementById("daysFilter").addEventListener("change", onFilterChange);

document.getElementById("clearBtn").addEventListener("click", () => {
  document.getElementById("searchInput").value = "";
  document.getElementById("typeFilter").value = "";
  document.getElementById("areaFilter").value = "";
  document.getElementById("daysFilter").value = "";
  onFilterChange();
});

document.getElementById("prevBtn").addEventListener("click", () => {
  if (state.page > 1) { state.page--; loadOpportunities(); }
});
document.getElementById("nextBtn").addEventListener("click", () => {
  if (state.page < state.pages) { state.page++; loadOpportunities(); }
});

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

loadStats();
loadOpportunities();
