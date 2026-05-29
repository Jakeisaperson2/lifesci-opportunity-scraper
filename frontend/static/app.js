/* LifeSci Opportunity Discovery — Dashboard JS
 *
 * Two tabs: Opportunities and Faculty Directory.
 * Each tab has independent state, filters, and table rendering.
 */

// ---------------------------------------------------------------------------
// Tab management
// ---------------------------------------------------------------------------

let _facultyLoaded = false;

function showTab(name) {
  ["opportunities", "faculty"].forEach(t => {
    document.getElementById(`tab-${t}`).classList.toggle("hidden", t !== name);
    const btn = document.getElementById(`tabBtn${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (t === name) {
      btn.classList.add("bg-white");
      btn.style.color = "#00274C";
    } else {
      btn.classList.remove("bg-white");
      btn.style.color = "rgba(255,203,5,0.75)";
    }
  });

  // Lazy-load faculty on first visit to that tab
  if (name === "faculty" && !_facultyLoaded) {
    _facultyLoaded = true;
    loadFacultyStats();
    loadFaculty();
    loadDepartments();
  }
}

// ---------------------------------------------------------------------------
// Shared API helper
// ---------------------------------------------------------------------------

async function apiFetch(path, opts = {}) {
  const resp = await fetch(path, opts);
  if (!resp.ok) throw new Error(`API error ${resp.status}: ${await resp.text()}`);
  return resp.json();
}

// ===========================================================================
//  OPPORTUNITIES TAB
// ===========================================================================

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
    const all = await apiFetch("/api/opportunities?limit=1");
    document.getElementById("statTotal").textContent = all.total.toLocaleString();

    const week = await apiFetch("/api/opportunities?limit=1&days=7");
    document.getElementById("statWeek").textContent = week.total.toLocaleString();

    const runs = await apiFetch("/api/scrape/runs?limit=1");
    if (runs.length > 0) {
      const run = runs[0];
      const ts = run.completed_at || run.started_at;
      document.getElementById("statLastRun").textContent = ts ? new Date(ts).toLocaleString() : "In progress";
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
    tbody.innerHTML = `<tr><td colspan="8" class="px-4 py-12 text-center text-gray-400">No opportunities found. Try adjusting filters or run a scrape.</td></tr>`;
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
      <td class="px-4 py-3 text-xs text-green-700 font-medium whitespace-nowrap">${escHtml(o.funding_amount || "—")}</td>
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
      `<tr><td colspan="8" class="px-4 py-12 text-center text-gray-300">Loading...</td></tr>`;
  }
}

function renderTableError(msg) {
  document.getElementById("tableBody").innerHTML =
    `<tr><td colspan="8" class="px-4 py-12 text-center text-red-400">Error: ${escHtml(msg)}</td></tr>`;
}

// ---------------------------------------------------------------------------
// Alert bar (opportunities tab)
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
  for (let i = 0; i < 45; i++) {
    await sleep(4000);
    const runs = await apiFetch("/api/scrape/runs?limit=5");
    const allDone = runs.every(r => r.status !== "running");
    if (allDone) return;
  }
}

// ---------------------------------------------------------------------------
// Debounced filter handler (opportunities)
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
// Event listeners (opportunities tab)
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


// ===========================================================================
//  FACULTY TAB
// ===========================================================================

const facultyState = {
  page: 1,
  limit: 50,
  total: 0,
  pages: 1,
  search: "",
  department: "",
  labDataOnly: false,
};

function buildFacultyUrl() {
  const p = new URLSearchParams();
  if (facultyState.search)     p.set("search", facultyState.search);
  if (facultyState.department) p.set("department", facultyState.department);
  if (facultyState.labDataOnly) p.set("has_lab_data", "true");
  p.set("page", facultyState.page);
  p.set("limit", facultyState.limit);
  return `/api/faculty?${p.toString()}`;
}

async function loadFaculty() {
  setFacultyLoading(true);
  try {
    const data = await apiFetch(buildFacultyUrl());
    facultyState.total = data.total;
    facultyState.pages = data.pages;
    renderFacultyTable(data.items);
    renderFacultyPagination();
    document.getElementById("facultyStatShowing").textContent = data.items.length;
  } catch (e) {
    renderFacultyError(e.message);
  } finally {
    setFacultyLoading(false);
  }
}

async function loadFacultyStats() {
  try {
    const data = await apiFetch("/api/faculty?limit=1");
    document.getElementById("facultyStatTotal").textContent = data.total.toLocaleString();
  } catch (e) {
    console.warn("Faculty stats load failed:", e);
  }
}

async function loadDepartments() {
  try {
    const depts = await apiFetch("/api/faculty/departments");
    const sel = document.getElementById("facultyDeptFilter");
    depts.forEach(d => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      sel.appendChild(opt);
    });
  } catch (e) {
    console.warn("Departments load failed:", e);
  }
}

function renderFacultyTable(items) {
  const tbody = document.getElementById("facultyTableBody");
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="px-4 py-12 text-center text-gray-400">No faculty found. Try adjusting filters or click "Refresh Faculty".</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map(f => {
    const labSnippet = (f.lab_assets || "").substring(0, 150);
    const hasLabData = f.lab_assets || f.project_ideas;
    const rowClass = hasLabData ? "hover:bg-blue-50 bg-blue-50/30" : "hover:bg-blue-50";
    return `
    <tr class="${rowClass} transition-colors cursor-pointer" onclick="window.open('${escHtml(f.profile_url)}','_blank')">
      <td class="px-4 py-3">
        <a href="${escHtml(f.profile_url)}" target="_blank" rel="noopener"
           class="font-medium text-blue-800 hover:underline"
           onclick="event.stopPropagation()">
          ${escHtml(f.name)}
        </a>
        ${hasLabData ? '<span class="ml-1 inline-block w-1.5 h-1.5 rounded-full bg-green-500" title="Has BD profile"></span>' : ""}
      </td>
      <td class="px-4 py-3 text-xs text-gray-600">${escHtml(f.title || "—")}</td>
      <td class="px-4 py-3 text-xs text-gray-600 whitespace-nowrap">${escHtml(f.department || "—")}</td>
      <td class="px-4 py-3 text-xs text-gray-500 truncate-desc">${escHtml((f.research_interests || "").substring(0, 200) || "—")}</td>
      <td class="px-4 py-3 text-xs text-gray-500 truncate-desc" title="${escHtml(f.lab_assets || "")}">
        ${labSnippet ? escHtml(labSnippet) + (f.lab_assets.length > 150 ? "…" : "") : "<span class='text-gray-300'>—</span>"}
      </td>
      <td class="px-4 py-3 text-xs">
        ${f.email ? `<a href="mailto:${escHtml(f.email)}" class="text-blue-600 hover:underline" onclick="event.stopPropagation()">${escHtml(f.email)}</a>` : "—"}
      </td>
    </tr>`;
  }).join("");
}

function renderFacultyPagination() {
  document.getElementById("facultyPageInfo").textContent =
    `Page ${facultyState.page} of ${facultyState.pages} · ${facultyState.total.toLocaleString()} total`;
  document.getElementById("facultyPrevBtn").disabled = facultyState.page <= 1;
  document.getElementById("facultyNextBtn").disabled = facultyState.page >= facultyState.pages;
}

function setFacultyLoading(on) {
  if (on) {
    document.getElementById("facultyTableBody").innerHTML =
      `<tr><td colspan="6" class="px-4 py-12 text-center text-gray-300">Loading...</td></tr>`;
  }
}

function renderFacultyError(msg) {
  document.getElementById("facultyTableBody").innerHTML =
    `<tr><td colspan="6" class="px-4 py-12 text-center text-red-400">Error: ${escHtml(msg)}</td></tr>`;
}

function showFacultyAlert(msg, type = "info") {
  const bar = document.getElementById("facultyAlertBar");
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

async function triggerFacultyRefresh() {
  const btn = document.getElementById("facultyRefreshBtn");
  btn.disabled = true;
  btn.textContent = "Running...";
  showFacultyAlert("Refreshing faculty — pulling NIH Reporter data then enriching from U-M Tableau dashboard. This takes ~15 seconds.", "info");

  try {
    // POST /refresh now runs NIH scrape + Tableau enrichment sequentially
    await apiFetch("/api/faculty/refresh", { method: "POST" });
    await sleep(18000);  // wait for background tasks to complete
    showFacultyAlert("Refresh complete. Reloading faculty list...", "success");
    await Promise.all([loadFacultyStats(), loadFaculty(), loadDepartments()]);
  } catch (e) {
    showFacultyAlert(`Refresh failed: ${e.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Refresh Faculty";
  }
}

// ---------------------------------------------------------------------------
// Debounced filter handler (faculty)
// ---------------------------------------------------------------------------

let facultyDebounceTimer;
function onFacultyFilterChange() {
  clearTimeout(facultyDebounceTimer);
  facultyDebounceTimer = setTimeout(() => {
    facultyState.page = 1;
    facultyState.search      = document.getElementById("facultySearchInput").value.trim();
    facultyState.department  = document.getElementById("facultyDeptFilter").value;
    facultyState.labDataOnly = document.getElementById("facultyLabDataFilter").checked;
    loadFaculty();
  }, 350);
}

// ---------------------------------------------------------------------------
// Event listeners (faculty tab)
// ---------------------------------------------------------------------------

document.getElementById("facultyRefreshBtn").addEventListener("click", triggerFacultyRefresh);
document.getElementById("facultySearchInput").addEventListener("input", onFacultyFilterChange);
document.getElementById("facultyDeptFilter").addEventListener("change", onFacultyFilterChange);
document.getElementById("facultyLabDataFilter").addEventListener("change", onFacultyFilterChange);

document.getElementById("facultyClearBtn").addEventListener("click", () => {
  document.getElementById("facultySearchInput").value = "";
  document.getElementById("facultyDeptFilter").value = "";
  document.getElementById("facultyLabDataFilter").checked = false;
  onFacultyFilterChange();
});

document.getElementById("facultyPrevBtn").addEventListener("click", () => {
  if (facultyState.page > 1) { facultyState.page--; loadFaculty(); }
});
document.getElementById("facultyNextBtn").addEventListener("click", () => {
  if (facultyState.page < facultyState.pages) { facultyState.page++; loadFaculty(); }
});

// ===========================================================================
//  Shared utilities
// ===========================================================================

function escHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ===========================================================================
//  Bootstrap
// ===========================================================================

loadStats();
loadOpportunities();
