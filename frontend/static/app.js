/* FFMI Brain — CRM + BD Intelligence Platform */

// ---------------------------------------------------------------------------
// Tab management
// ---------------------------------------------------------------------------

const ALL_TABS = ["opportunities", "pipeline", "organizations", "contacts", "activities", "tasks", "faculty"];
let _lazyLoaded = {};

function showTab(name) {
  ALL_TABS.forEach(t => {
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

  if (!_lazyLoaded[name]) {
    _lazyLoaded[name] = true;
    if (name === "pipeline")       { loadPipeline(); loadPipelineTable(); }
    if (name === "organizations")  { loadOrganizations(); }
    if (name === "contacts")       { loadContacts(); }
    if (name === "activities")     { loadActivities(); }
    if (name === "tasks")          { loadTasks(); }
    if (name === "faculty")        { loadFacultyStats(); loadFaculty(); loadDepartments(); }
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

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function escHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function deadlineClass(iso) {
  if (!iso) return "text-gray-400";
  const days = (new Date(iso) - Date.now()) / 86400000;
  if (days < 0)  return "text-red-400 line-through";
  if (days < 14) return "text-orange-500 font-semibold";
  return "text-gray-600";
}

// ---------------------------------------------------------------------------
// Badge helpers
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

const CRM_STATUS_COLORS = {
  new:                  "bg-gray-100 text-gray-600",
  reviewing:            "bg-blue-100 text-blue-700",
  interested:           "bg-sky-100 text-sky-700",
  outreach_started:     "bg-indigo-100 text-indigo-700",
  proposal_in_progress: "bg-violet-100 text-violet-700",
  submitted:            "bg-yellow-100 text-yellow-700",
  negotiating:          "bg-orange-100 text-orange-700",
  awarded:              "bg-green-100 text-green-700",
  lost:                 "bg-red-100 text-red-600",
  archived:             "bg-gray-100 text-gray-400",
};

const PRIORITY_COLORS = {
  urgent: "bg-red-100 text-red-700",
  high:   "bg-orange-100 text-orange-700",
  medium: "bg-yellow-100 text-yellow-700",
  low:    "bg-gray-100 text-gray-500",
};

const ACTIVITY_TYPE_COLORS = {
  email:                "bg-blue-100 text-blue-700",
  meeting:              "bg-green-100 text-green-700",
  phone_call:           "bg-teal-100 text-teal-700",
  proposal_submission:  "bg-violet-100 text-violet-700",
  follow_up:            "bg-yellow-100 text-yellow-700",
  internal_review:      "bg-gray-100 text-gray-600",
  negotiation:          "bg-orange-100 text-orange-700",
};

const ORG_STATUS_COLORS = {
  prospect: "bg-blue-100 text-blue-700",
  active:   "bg-green-100 text-green-700",
  partner:  "bg-indigo-100 text-indigo-700",
  inactive: "bg-gray-100 text-gray-400",
};

function badge(value, colorMap, fallback = "bg-gray-100 text-gray-500") {
  if (!value) return "";
  const cls = colorMap[value] || fallback;
  const label = value.replace(/_/g, " ");
  return `<span class="badge ${cls}">${escHtml(label)}</span>`;
}


// ===========================================================================
//  OPPORTUNITIES TAB
// ===========================================================================

const oppState = { page: 1, limit: 50, total: 0, pages: 1, search: "", type: "", area: "", crm_status: "", days: "" };

function buildOpportunitiesUrl() {
  const p = new URLSearchParams();
  if (oppState.search)     p.set("search", oppState.search);
  if (oppState.type)       p.set("opportunity_type", oppState.type);
  if (oppState.area)       p.set("therapeutic_area", oppState.area);
  if (oppState.crm_status) p.set("crm_status", oppState.crm_status);
  if (oppState.days)       p.set("days", oppState.days);
  p.set("page", oppState.page);
  p.set("limit", oppState.limit);
  return `/api/opportunities?${p.toString()}`;
}

async function loadOpportunities() {
  setTableLoading("tableBody", 7);
  try {
    const data = await apiFetch(buildOpportunitiesUrl());
    oppState.total = data.total;
    oppState.pages = data.pages;
    renderOppTable(data.items);
    document.getElementById("pageInfo").textContent = `Page ${oppState.page} of ${oppState.pages} · ${oppState.total.toLocaleString()} total`;
    document.getElementById("prevBtn").disabled = oppState.page <= 1;
    document.getElementById("nextBtn").disabled = oppState.page >= oppState.pages;
    document.getElementById("statShowing").textContent = data.items.length;
  } catch (e) {
    document.getElementById("tableBody").innerHTML = `<tr><td colspan="7" class="px-4 py-12 text-center text-red-400">Error: ${escHtml(e.message)}</td></tr>`;
  }
}

async function loadStats() {
  try {
    const all  = await apiFetch("/api/opportunities?limit=1");
    document.getElementById("statTotal").textContent = all.total.toLocaleString();
    const week = await apiFetch("/api/opportunities?limit=1&days=7");
    document.getElementById("statWeek").textContent  = week.total.toLocaleString();
    const runs = await apiFetch("/api/scrape/runs?limit=1");
    if (runs.length > 0) {
      const ts = runs[0].completed_at || runs[0].started_at;
      document.getElementById("statLastRun").textContent = ts ? new Date(ts).toLocaleString() : "In progress";
    }
  } catch (e) { console.warn("Stats load failed:", e); }
}

function renderOppTable(items) {
  const tbody = document.getElementById("tableBody");
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="px-4 py-12 text-center text-gray-400">No opportunities found. Try adjusting filters or run a scrape.</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map(o => `
    <tr class="hover:bg-blue-50 transition-colors">
      <td class="px-4 py-3">
        <a href="${escHtml(o.url)}" target="_blank" rel="noopener" class="font-medium text-blue-800 hover:underline">${escHtml(o.title)}</a>
        ${o.description ? `<p class="text-xs text-gray-400 mt-0.5 truncate-desc">${escHtml(o.description.substring(0, 200))}</p>` : ""}
      </td>
      <td class="px-4 py-3 text-xs text-gray-600 whitespace-nowrap">${escHtml(o.organization_name || o.company_name || "—")}</td>
      <td class="px-4 py-3">${badge(o.opportunity_type, TYPE_COLORS)}</td>
      <td class="px-4 py-3 text-xs text-green-700 font-medium whitespace-nowrap">${escHtml(o.funding_amount || "—")}</td>
      <td class="px-4 py-3 text-xs whitespace-nowrap ${deadlineClass(o.deadline)}">${formatDate(o.deadline)}</td>
      <td class="px-4 py-3">
        <select onchange="updateOppCrmStatus(${o.id}, this.value)"
          class="text-xs border-0 rounded px-1.5 py-0.5 cursor-pointer focus:outline-none ${CRM_STATUS_COLORS[o.crm_status] || 'bg-gray-100 text-gray-600'}">
          ${CRM_STATUS_OPTIONS.map(s => `<option value="${s.value}" ${o.crm_status === s.value ? 'selected' : ''}>${s.label}</option>`).join("")}
        </select>
      </td>
      <td class="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">${formatDate(o.date_discovered)}</td>
    </tr>
  `).join("");
}

const CRM_STATUS_OPTIONS = [
  { value: "new",                  label: "New" },
  { value: "reviewing",            label: "Reviewing" },
  { value: "interested",           label: "Interested" },
  { value: "outreach_started",     label: "Outreach Started" },
  { value: "proposal_in_progress", label: "Proposal In Progress" },
  { value: "submitted",            label: "Submitted" },
  { value: "negotiating",          label: "Negotiating" },
  { value: "awarded",              label: "Awarded" },
  { value: "lost",                 label: "Lost" },
  { value: "archived",             label: "Archived" },
];

async function updateOppCrmStatus(id, status) {
  try {
    await apiFetch(`/api/opportunities/${id}/crm_status?status=${encodeURIComponent(status)}`, { method: "PATCH" });
    if (_lazyLoaded["pipeline"]) { loadPipeline(); }
  } catch (e) {
    showAlert(`Failed to update status: ${e.message}`, "error");
  }
}

function showAlert(msg, type = "info") {
  const bar = document.getElementById("alertBar");
  const classes = { info: "bg-blue-50 text-blue-700 border-blue-200", success: "bg-green-50 text-green-700 border-green-200", error: "bg-red-50 text-red-600 border-red-200" };
  bar.className = `px-5 py-2.5 text-sm border-b ${classes[type] || classes.info}`;
  bar.textContent = msg;
  bar.classList.remove("hidden");
  if (type !== "info" || msg.includes("complete")) setTimeout(() => bar.classList.add("hidden"), 6000);
}

async function triggerScrape() {
  const btn = document.getElementById("scrapeBtn");
  btn.disabled = true;
  btn.textContent = "Running...";
  showAlert("Scrape started — this may take a minute.", "info");
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
    if (runs.every(r => r.status !== "running")) return;
  }
}

let oppDebounce;
function onOppFilterChange() {
  clearTimeout(oppDebounce);
  oppDebounce = setTimeout(() => {
    oppState.page = 1;
    oppState.search     = document.getElementById("searchInput").value.trim();
    oppState.type       = document.getElementById("typeFilter").value;
    oppState.area       = document.getElementById("areaFilter").value;
    oppState.crm_status = document.getElementById("crmStatusFilter").value;
    oppState.days       = document.getElementById("daysFilter").value;
    loadOpportunities();
  }, 350);
}

document.getElementById("scrapeBtn").addEventListener("click", triggerScrape);
document.getElementById("searchInput").addEventListener("input", onOppFilterChange);
document.getElementById("typeFilter").addEventListener("change", onOppFilterChange);
document.getElementById("areaFilter").addEventListener("change", onOppFilterChange);
document.getElementById("crmStatusFilter").addEventListener("change", onOppFilterChange);
document.getElementById("daysFilter").addEventListener("change", onOppFilterChange);
document.getElementById("clearBtn").addEventListener("click", () => {
  ["searchInput","typeFilter","areaFilter","crmStatusFilter","daysFilter"].forEach(id => {
    const el = document.getElementById(id);
    el.tagName === "INPUT" ? (el.value = "") : (el.value = "");
  });
  onOppFilterChange();
});
document.getElementById("prevBtn").addEventListener("click", () => { if (oppState.page > 1) { oppState.page--; loadOpportunities(); } });
document.getElementById("nextBtn").addEventListener("click", () => { if (oppState.page < oppState.pages) { oppState.page++; loadOpportunities(); } });


// ===========================================================================
//  PIPELINE TAB
// ===========================================================================

let pipelineFilterStatus = null;
const pipelineState = { page: 1, limit: 50, total: 0, pages: 1 };

async function loadPipeline() {
  try {
    const data = await apiFetch("/api/crm/pipeline");
    renderPipelineStages(data.stages);
  } catch (e) {
    document.getElementById("pipelineStages").innerHTML = `<p class="text-red-400 text-sm">Error loading pipeline: ${escHtml(e.message)}</p>`;
  }
}

async function loadPipelineTable() {
  setTableLoading("pipelineTableBody", 6);
  const p = new URLSearchParams({ page: pipelineState.page, limit: pipelineState.limit });
  if (pipelineFilterStatus) p.set("crm_status", pipelineFilterStatus);
  try {
    const data = await apiFetch(`/api/opportunities?${p.toString()}`);
    pipelineState.total = data.total;
    pipelineState.pages = data.pages;
    renderPipelineTable(data.items);
    document.getElementById("pipelinePageInfo").textContent = `Page ${pipelineState.page} of ${pipelineState.pages} · ${pipelineState.total.toLocaleString()} total`;
    document.getElementById("pipelinePrevBtn").disabled = pipelineState.page <= 1;
    document.getElementById("pipelineNextBtn").disabled = pipelineState.page >= pipelineState.pages;
  } catch (e) {
    document.getElementById("pipelineTableBody").innerHTML = `<tr><td colspan="6" class="px-4 py-12 text-center text-red-400">Error: ${escHtml(e.message)}</td></tr>`;
  }
}

function renderPipelineStages(stages) {
  const container = document.getElementById("pipelineStages");
  container.innerHTML = stages.map(s => {
    const isActive = pipelineFilterStatus === s.key;
    const border = isActive ? "border-2" : "border border-transparent";
    const countColor = s.key === "awarded" ? "text-green-600" : s.key === "lost" ? "text-red-500" : "#00274C";
    return `
      <div onclick="filterPipelineByStage('${escHtml(s.key)}')"
        class="bg-white rounded-xl shadow p-3 cursor-pointer hover:shadow-md transition-shadow ${border} ${isActive ? 'border-blue-500' : ''}">
        <p class="text-xs text-gray-400 font-medium truncate">${escHtml(s.label)}</p>
        <p class="text-2xl font-bold mt-1" style="color: ${countColor};">${s.count}</p>
      </div>
    `;
  }).join("");
}

function filterPipelineByStage(key) {
  if (pipelineFilterStatus === key) {
    pipelineFilterStatus = null;
    document.getElementById("pipelineTableTitle").textContent = "All Active Opportunities";
    document.getElementById("pipelineClearFilter").classList.add("hidden");
  } else {
    pipelineFilterStatus = key;
    const label = key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    document.getElementById("pipelineTableTitle").textContent = `Stage: ${label}`;
    document.getElementById("pipelineClearFilter").classList.remove("hidden");
  }
  pipelineState.page = 1;
  loadPipeline();
  loadPipelineTable();
}

function renderPipelineTable(items) {
  const tbody = document.getElementById("pipelineTableBody");
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="px-4 py-12 text-center text-gray-400">No opportunities in this stage.</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map(o => `
    <tr class="hover:bg-blue-50 transition-colors">
      <td class="px-4 py-3">
        <a href="${escHtml(o.url)}" target="_blank" rel="noopener" class="font-medium text-blue-800 hover:underline">${escHtml(o.title)}</a>
      </td>
      <td class="px-4 py-3 text-xs text-gray-600 whitespace-nowrap">${escHtml(o.organization_name || o.company_name || "—")}</td>
      <td class="px-4 py-3">${badge(o.opportunity_type, TYPE_COLORS)}</td>
      <td class="px-4 py-3 text-xs text-green-700 font-medium whitespace-nowrap">${escHtml(o.funding_amount || "—")}</td>
      <td class="px-4 py-3 text-xs whitespace-nowrap ${deadlineClass(o.deadline)}">${formatDate(o.deadline)}</td>
      <td class="px-4 py-3">
        <select onchange="updateOppCrmStatus(${o.id}, this.value); this.className='text-xs border-0 rounded px-1.5 py-0.5 '+getCrmStatusClass(this.value)"
          class="text-xs border-0 rounded px-1.5 py-0.5 cursor-pointer focus:outline-none ${CRM_STATUS_COLORS[o.crm_status] || 'bg-gray-100 text-gray-600'}">
          ${CRM_STATUS_OPTIONS.map(s => `<option value="${s.value}" ${o.crm_status === s.value ? 'selected' : ''}>${s.label}</option>`).join("")}
        </select>
      </td>
    </tr>
  `).join("");
}

function getCrmStatusClass(val) { return CRM_STATUS_COLORS[val] || "bg-gray-100 text-gray-600"; }

document.getElementById("pipelineClearFilter").addEventListener("click", () => filterPipelineByStage(pipelineFilterStatus));
document.getElementById("pipelinePrevBtn").addEventListener("click", () => { if (pipelineState.page > 1) { pipelineState.page--; loadPipelineTable(); } });
document.getElementById("pipelineNextBtn").addEventListener("click", () => { if (pipelineState.page < pipelineState.pages) { pipelineState.page++; loadPipelineTable(); } });


// ===========================================================================
//  ORGANIZATIONS TAB
// ===========================================================================

const orgState = { page: 1, limit: 50, total: 0, pages: 1, search: "", status: "" };

async function loadOrganizations() {
  setTableLoading("orgTableBody", 8);
  const p = new URLSearchParams({ page: orgState.page, limit: orgState.limit });
  if (orgState.search) p.set("search", orgState.search);
  if (orgState.status) p.set("relationship_status", orgState.status);
  try {
    const data = await apiFetch(`/api/crm/organizations?${p.toString()}`);
    orgState.total = data.total;
    orgState.pages = data.pages;
    document.getElementById("orgStatTotal").textContent = `${data.total.toLocaleString()} organizations`;
    renderOrgsTable(data.items);
    document.getElementById("orgPageInfo").textContent = `Page ${orgState.page} of ${orgState.pages} · ${orgState.total.toLocaleString()} total`;
    document.getElementById("orgPrevBtn").disabled = orgState.page <= 1;
    document.getElementById("orgNextBtn").disabled = orgState.page >= orgState.pages;
  } catch (e) {
    document.getElementById("orgTableBody").innerHTML = `<tr><td colspan="8" class="px-4 py-12 text-center text-red-400">Error: ${escHtml(e.message)}</td></tr>`;
  }
}

function renderOrgsTable(items) {
  const tbody = document.getElementById("orgTableBody");
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="px-4 py-12 text-center text-gray-400">No organizations found.</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map(o => `
    <tr class="hover:bg-blue-50 transition-colors">
      <td class="px-4 py-3 font-medium text-gray-800">${escHtml(o.name)}</td>
      <td class="px-4 py-3 text-xs text-gray-600">${escHtml(o.org_type ? o.org_type.replace(/_/g," ") : "—")}</td>
      <td class="px-4 py-3">${badge(o.relationship_status, ORG_STATUS_COLORS)}</td>
      <td class="px-4 py-3 text-xs text-blue-600">
        ${o.website ? `<a href="${escHtml(o.website)}" target="_blank" rel="noopener" class="hover:underline truncate block max-w-32">${escHtml(o.website.replace(/^https?:\/\//, ''))}</a>` : "—"}
      </td>
      <td class="px-4 py-3 text-xs text-gray-600 text-center">${o.contact_count}</td>
      <td class="px-4 py-3 text-xs text-gray-600 text-center">${o.opportunity_count}</td>
      <td class="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">${formatDate(o.next_followup_date)}</td>
      <td class="px-4 py-3 text-xs flex gap-2">
        <button onclick='openOrgModal(${JSON.stringify(o)})' class="text-blue-600 hover:underline">Edit</button>
        <button onclick="deleteOrg(${o.id})" class="text-red-400 hover:underline">Del</button>
      </td>
    </tr>
  `).join("");
}

function openOrgModal(org = null) {
  const isEdit = !!org;
  document.getElementById("modalTitle").textContent = isEdit ? "Edit Organization" : "New Organization";
  document.getElementById("modalBody").innerHTML = `
    <div class="space-y-3">
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Name *</label>
        <input id="fOrgName" value="${escHtml(org ? org.name : '')}" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" /></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Type</label>
        <select id="fOrgType" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none">
          <option value="">— Select —</option>
          ${["pharma","biotech","academic","government","nonprofit","other"].map(t => `<option value="${t}" ${org && org.org_type === t ? 'selected':''}>${t.charAt(0).toUpperCase()+t.slice(1)}</option>`).join("")}
        </select></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Website</label>
        <input id="fOrgWebsite" value="${escHtml(org ? org.website || '' : '')}" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" /></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Relationship Status</label>
        <select id="fOrgStatus" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none">
          ${["prospect","active","partner","inactive"].map(s => `<option value="${s}" ${org && org.relationship_status === s ? 'selected':''}>${s.charAt(0).toUpperCase()+s.slice(1)}</option>`).join("")}
        </select></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Next Follow-up Date</label>
        <input id="fOrgFollowup" type="date" value="${org && org.next_followup_date ? org.next_followup_date.substring(0,10) : ''}" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" /></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Notes</label>
        <textarea id="fOrgNotes" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">${escHtml(org ? org.notes || '' : '')}</textarea></div>
    </div>`;
  _modalSave = async () => {
    const name = document.getElementById("fOrgName").value.trim();
    if (!name) { alert("Name is required."); return; }
    const payload = {
      name,
      org_type: document.getElementById("fOrgType").value || null,
      website: document.getElementById("fOrgWebsite").value.trim() || null,
      relationship_status: document.getElementById("fOrgStatus").value,
      next_followup_date: document.getElementById("fOrgFollowup").value || null,
      notes: document.getElementById("fOrgNotes").value.trim() || null,
    };
    const url    = isEdit ? `/api/crm/organizations/${org.id}` : "/api/crm/organizations";
    const method = isEdit ? "PUT" : "POST";
    await apiFetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    closeModal();
    _lazyLoaded["organizations"] = false;
    loadOrganizations();
  };
  showModal();
}

async function deleteOrg(id) {
  if (!confirm("Delete this organization?")) return;
  await apiFetch(`/api/crm/organizations/${id}`, { method: "DELETE" });
  _lazyLoaded["organizations"] = false;
  loadOrganizations();
}

let orgDebounce;
function onOrgFilterChange() {
  clearTimeout(orgDebounce);
  orgDebounce = setTimeout(() => {
    orgState.page = 1;
    orgState.search = document.getElementById("orgSearch").value.trim();
    orgState.status = document.getElementById("orgStatusFilter").value;
    loadOrganizations();
  }, 350);
}

document.getElementById("orgSearch").addEventListener("input", onOrgFilterChange);
document.getElementById("orgStatusFilter").addEventListener("change", onOrgFilterChange);
document.getElementById("orgClearBtn").addEventListener("click", () => {
  document.getElementById("orgSearch").value = "";
  document.getElementById("orgStatusFilter").value = "";
  onOrgFilterChange();
});
document.getElementById("orgPrevBtn").addEventListener("click", () => { if (orgState.page > 1) { orgState.page--; loadOrganizations(); } });
document.getElementById("orgNextBtn").addEventListener("click", () => { if (orgState.page < orgState.pages) { orgState.page++; loadOrganizations(); } });


// ===========================================================================
//  CONTACTS TAB
// ===========================================================================

const contactState = { page: 1, limit: 50, total: 0, pages: 1, search: "" };

async function loadContacts() {
  setTableLoading("contactTableBody", 7);
  const p = new URLSearchParams({ page: contactState.page, limit: contactState.limit });
  if (contactState.search) p.set("search", contactState.search);
  try {
    const data = await apiFetch(`/api/crm/contacts?${p.toString()}`);
    contactState.total = data.total;
    contactState.pages = data.pages;
    document.getElementById("contactStatTotal").textContent = `${data.total.toLocaleString()} contacts`;
    renderContactsTable(data.items);
    document.getElementById("contactPageInfo").textContent = `Page ${contactState.page} of ${contactState.pages} · ${contactState.total.toLocaleString()} total`;
    document.getElementById("contactPrevBtn").disabled = contactState.page <= 1;
    document.getElementById("contactNextBtn").disabled = contactState.page >= contactState.pages;
  } catch (e) {
    document.getElementById("contactTableBody").innerHTML = `<tr><td colspan="7" class="px-4 py-12 text-center text-red-400">Error: ${escHtml(e.message)}</td></tr>`;
  }
}

function renderContactsTable(items) {
  const tbody = document.getElementById("contactTableBody");
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="px-4 py-12 text-center text-gray-400">No contacts found.</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map(c => `
    <tr class="hover:bg-blue-50 transition-colors">
      <td class="px-4 py-3 font-medium text-gray-800">${escHtml(c.name)}</td>
      <td class="px-4 py-3 text-xs text-gray-600">${escHtml(c.title || "—")}</td>
      <td class="px-4 py-3 text-xs text-gray-600">${escHtml(c.organization_name || "—")}</td>
      <td class="px-4 py-3 text-xs">
        ${c.email ? `<a href="mailto:${escHtml(c.email)}" class="text-blue-600 hover:underline">${escHtml(c.email)}</a>` : "—"}
      </td>
      <td class="px-4 py-3 text-xs text-gray-600">${escHtml(c.phone || "—")}</td>
      <td class="px-4 py-3 text-xs">
        ${c.linkedin ? `<a href="${escHtml(c.linkedin)}" target="_blank" rel="noopener" class="text-blue-600 hover:underline">LinkedIn</a>` : "—"}
      </td>
      <td class="px-4 py-3 text-xs flex gap-2">
        <button onclick='openContactModal(${JSON.stringify(c)})' class="text-blue-600 hover:underline">Edit</button>
        <button onclick="deleteContact(${c.id})" class="text-red-400 hover:underline">Del</button>
      </td>
    </tr>
  `).join("");
}

async function loadOrgOptions() {
  try {
    const data = await apiFetch("/api/crm/organizations?limit=200");
    return data.items || [];
  } catch { return []; }
}

async function openContactModal(contact = null) {
  const isEdit = !!contact;
  const orgs = await loadOrgOptions();
  document.getElementById("modalTitle").textContent = isEdit ? "Edit Contact" : "New Contact";
  document.getElementById("modalBody").innerHTML = `
    <div class="space-y-3">
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Name *</label>
        <input id="fConName" value="${escHtml(contact ? contact.name : '')}" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" /></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Title</label>
        <input id="fConTitle" value="${escHtml(contact ? contact.title || '' : '')}" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" /></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Organization</label>
        <select id="fConOrg" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none">
          <option value="">— None —</option>
          ${orgs.map(o => `<option value="${o.id}" ${contact && contact.organization_id === o.id ? 'selected':''}>${escHtml(o.name)}</option>`).join("")}
        </select></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Email</label>
        <input id="fConEmail" type="email" value="${escHtml(contact ? contact.email || '' : '')}" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" /></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Phone</label>
        <input id="fConPhone" value="${escHtml(contact ? contact.phone || '' : '')}" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" /></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">LinkedIn URL</label>
        <input id="fConLinkedin" value="${escHtml(contact ? contact.linkedin || '' : '')}" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" /></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Notes</label>
        <textarea id="fConNotes" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">${escHtml(contact ? contact.notes || '' : '')}</textarea></div>
    </div>`;
  _modalSave = async () => {
    const name = document.getElementById("fConName").value.trim();
    if (!name) { alert("Name is required."); return; }
    const orgVal = document.getElementById("fConOrg").value;
    const payload = {
      name,
      title: document.getElementById("fConTitle").value.trim() || null,
      organization_id: orgVal ? parseInt(orgVal) : null,
      email: document.getElementById("fConEmail").value.trim() || null,
      phone: document.getElementById("fConPhone").value.trim() || null,
      linkedin: document.getElementById("fConLinkedin").value.trim() || null,
      notes: document.getElementById("fConNotes").value.trim() || null,
    };
    const url    = isEdit ? `/api/crm/contacts/${contact.id}` : "/api/crm/contacts";
    const method = isEdit ? "PUT" : "POST";
    await apiFetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    closeModal();
    _lazyLoaded["contacts"] = false;
    loadContacts();
  };
  showModal();
}

async function deleteContact(id) {
  if (!confirm("Delete this contact?")) return;
  await apiFetch(`/api/crm/contacts/${id}`, { method: "DELETE" });
  _lazyLoaded["contacts"] = false;
  loadContacts();
}

let contactDebounce;
function onContactFilterChange() {
  clearTimeout(contactDebounce);
  contactDebounce = setTimeout(() => {
    contactState.page = 1;
    contactState.search = document.getElementById("contactSearch").value.trim();
    loadContacts();
  }, 350);
}

document.getElementById("contactSearch").addEventListener("input", onContactFilterChange);
document.getElementById("contactClearBtn").addEventListener("click", () => {
  document.getElementById("contactSearch").value = "";
  onContactFilterChange();
});
document.getElementById("contactPrevBtn").addEventListener("click", () => { if (contactState.page > 1) { contactState.page--; loadContacts(); } });
document.getElementById("contactNextBtn").addEventListener("click", () => { if (contactState.page < contactState.pages) { contactState.page++; loadContacts(); } });


// ===========================================================================
//  ACTIVITIES TAB
// ===========================================================================

const activityState = { page: 1, limit: 50, total: 0, pages: 1, activity_type: "" };

async function loadActivities() {
  setTableLoading("activityTableBody", 7);
  const p = new URLSearchParams({ page: activityState.page, limit: activityState.limit });
  if (activityState.activity_type) p.set("activity_type", activityState.activity_type);
  try {
    const data = await apiFetch(`/api/crm/activities?${p.toString()}`);
    activityState.total = data.total;
    activityState.pages = data.pages;
    document.getElementById("activityStatTotal").textContent = `${data.total.toLocaleString()} activities`;
    renderActivitiesTable(data.items);
    document.getElementById("activityPageInfo").textContent = `Page ${activityState.page} of ${activityState.pages} · ${activityState.total.toLocaleString()} total`;
    document.getElementById("activityPrevBtn").disabled = activityState.page <= 1;
    document.getElementById("activityNextBtn").disabled = activityState.page >= activityState.pages;
  } catch (e) {
    document.getElementById("activityTableBody").innerHTML = `<tr><td colspan="7" class="px-4 py-12 text-center text-red-400">Error: ${escHtml(e.message)}</td></tr>`;
  }
}

function renderActivitiesTable(items) {
  const tbody = document.getElementById("activityTableBody");
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="px-4 py-12 text-center text-gray-400">No activities logged yet.</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map(a => `
    <tr class="hover:bg-blue-50 transition-colors">
      <td class="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">${formatDate(a.date)}</td>
      <td class="px-4 py-3">${badge(a.activity_type, ACTIVITY_TYPE_COLORS)}</td>
      <td class="px-4 py-3 text-xs text-gray-700 truncate-desc">${escHtml(a.description || "—")}</td>
      <td class="px-4 py-3 text-xs text-gray-600">${escHtml(a.opportunity_title ? a.opportunity_title.substring(0, 60) + (a.opportunity_title.length > 60 ? '…' : '') : "—")}</td>
      <td class="px-4 py-3 text-xs text-gray-600">${escHtml(a.organization_name || "—")}</td>
      <td class="px-4 py-3 text-xs text-gray-600">${escHtml(a.contact_name || "—")}</td>
      <td class="px-4 py-3 text-xs flex gap-2">
        <button onclick="deleteActivity(${a.id})" class="text-red-400 hover:underline">Del</button>
      </td>
    </tr>
  `).join("");
}

async function openActivityModal() {
  const orgs    = await loadOrgOptions();
  const contacts = await apiFetch("/api/crm/contacts?limit=200").then(d => d.items).catch(() => []);
  const opps    = await apiFetch("/api/opportunities?limit=200").then(d => d.items).catch(() => []);

  document.getElementById("modalTitle").textContent = "Log Activity";
  document.getElementById("modalBody").innerHTML = `
    <div class="space-y-3">
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Activity Type *</label>
        <select id="fActType" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none">
          <option value="">— Select —</option>
          ${["email","meeting","phone_call","proposal_submission","follow_up","internal_review","negotiation"]
            .map(t => `<option value="${t}">${t.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</option>`).join("")}
        </select></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Date</label>
        <input id="fActDate" type="date" value="${new Date().toISOString().substring(0,10)}" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" /></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Description</label>
        <textarea id="fActDesc" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"></textarea></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Related Opportunity</label>
        <select id="fActOpp" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none">
          <option value="">— None —</option>
          ${opps.map(o => `<option value="${o.id}">${escHtml(o.title.substring(0,80))}</option>`).join("")}
        </select></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Related Organization</label>
        <select id="fActOrg" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none">
          <option value="">— None —</option>
          ${orgs.map(o => `<option value="${o.id}">${escHtml(o.name)}</option>`).join("")}
        </select></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Related Contact</label>
        <select id="fActContact" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none">
          <option value="">— None —</option>
          ${contacts.map(c => `<option value="${c.id}">${escHtml(c.name)}${c.organization_name ? ' (' + escHtml(c.organization_name) + ')' : ''}</option>`).join("")}
        </select></div>
    </div>`;
  _modalSave = async () => {
    const aType = document.getElementById("fActType").value;
    if (!aType) { alert("Activity type is required."); return; }
    const payload = {
      activity_type: aType,
      date: document.getElementById("fActDate").value || null,
      description: document.getElementById("fActDesc").value.trim() || null,
      opportunity_id: document.getElementById("fActOpp").value ? parseInt(document.getElementById("fActOpp").value) : null,
      organization_id: document.getElementById("fActOrg").value ? parseInt(document.getElementById("fActOrg").value) : null,
      contact_id: document.getElementById("fActContact").value ? parseInt(document.getElementById("fActContact").value) : null,
    };
    await apiFetch("/api/crm/activities", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    closeModal();
    _lazyLoaded["activities"] = false;
    loadActivities();
  };
  showModal();
}

async function deleteActivity(id) {
  if (!confirm("Delete this activity?")) return;
  await apiFetch(`/api/crm/activities/${id}`, { method: "DELETE" });
  _lazyLoaded["activities"] = false;
  loadActivities();
}

document.getElementById("activityTypeFilter").addEventListener("change", () => {
  activityState.page = 1;
  activityState.activity_type = document.getElementById("activityTypeFilter").value;
  loadActivities();
});
document.getElementById("activityClearBtn").addEventListener("click", () => {
  document.getElementById("activityTypeFilter").value = "";
  activityState.activity_type = "";
  activityState.page = 1;
  loadActivities();
});
document.getElementById("activityPrevBtn").addEventListener("click", () => { if (activityState.page > 1) { activityState.page--; loadActivities(); } });
document.getElementById("activityNextBtn").addEventListener("click", () => { if (activityState.page < activityState.pages) { activityState.page++; loadActivities(); } });


// ===========================================================================
//  TASKS TAB
// ===========================================================================

const taskState = { page: 1, limit: 100, total: 0, pages: 1, status: "open", priority: "" };

async function loadTasks() {
  setTableLoading("taskTableBody", 7);
  const p = new URLSearchParams({ page: taskState.page, limit: taskState.limit });
  if (taskState.status)   p.set("status", taskState.status);
  if (taskState.priority) p.set("priority", taskState.priority);
  try {
    const data = await apiFetch(`/api/crm/tasks?${p.toString()}`);
    taskState.total = data.total;
    taskState.pages = data.pages;
    document.getElementById("taskStatTotal").textContent = `${data.total.toLocaleString()} tasks`;
    renderTasksTable(data.items);
    document.getElementById("taskPageInfo").textContent = `Page ${taskState.page} of ${taskState.pages} · ${taskState.total.toLocaleString()} total`;
    document.getElementById("taskPrevBtn").disabled = taskState.page <= 1;
    document.getElementById("taskNextBtn").disabled = taskState.page >= taskState.pages;
  } catch (e) {
    document.getElementById("taskTableBody").innerHTML = `<tr><td colspan="7" class="px-4 py-12 text-center text-red-400">Error: ${escHtml(e.message)}</td></tr>`;
  }
}

function renderTasksTable(items) {
  const tbody = document.getElementById("taskTableBody");
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="px-4 py-12 text-center text-gray-400">No tasks found.</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map(t => {
    const isDone   = t.status === "complete";
    const isOverdue = t.due_date && !isDone && (new Date(t.due_date) < Date.now());
    return `
    <tr class="hover:bg-blue-50 transition-colors ${isDone ? 'opacity-60' : ''}">
      <td class="px-4 py-3 text-center">
        <input type="checkbox" ${isDone ? 'checked' : ''} class="accent-blue-600 cursor-pointer"
          onchange="toggleTaskStatus(${t.id}, this.checked)" />
      </td>
      <td class="px-4 py-3 text-sm ${isDone ? 'line-through text-gray-400' : 'text-gray-800'}">${escHtml(t.task_name)}</td>
      <td class="px-4 py-3 text-xs whitespace-nowrap ${isOverdue ? 'text-red-500 font-semibold' : 'text-gray-500'}">${formatDate(t.due_date)}</td>
      <td class="px-4 py-3">${badge(t.priority, PRIORITY_COLORS)}</td>
      <td class="px-4 py-3 text-xs text-gray-600">${escHtml(t.assigned_to || "—")}</td>
      <td class="px-4 py-3 text-xs text-gray-600">${escHtml(t.opportunity_title ? t.opportunity_title.substring(0,60) + (t.opportunity_title.length > 60 ? '…' : '') : "—")}</td>
      <td class="px-4 py-3 text-xs flex gap-2">
        <button onclick='openTaskModal(${JSON.stringify(t)})' class="text-blue-600 hover:underline">Edit</button>
        <button onclick="deleteTask(${t.id})" class="text-red-400 hover:underline">Del</button>
      </td>
    </tr>`;
  }).join("");
}

async function toggleTaskStatus(id, checked) {
  const status = checked ? "complete" : "open";
  await apiFetch(`/api/crm/tasks/${id}/status?status=${status}`, { method: "PATCH" });
  setTimeout(() => loadTasks(), 300);
}

async function openTaskModal(task = null) {
  const isEdit = !!task;
  const opps = await apiFetch("/api/opportunities?limit=200").then(d => d.items).catch(() => []);
  document.getElementById("modalTitle").textContent = isEdit ? "Edit Task" : "New Task";
  document.getElementById("modalBody").innerHTML = `
    <div class="space-y-3">
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Task Name *</label>
        <input id="fTaskName" value="${escHtml(task ? task.task_name : '')}" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" /></div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="block text-xs font-medium text-gray-600 mb-1">Due Date</label>
          <input id="fTaskDue" type="date" value="${task && task.due_date ? task.due_date.substring(0,10) : ''}" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" /></div>
        <div><label class="block text-xs font-medium text-gray-600 mb-1">Priority</label>
          <select id="fTaskPriority" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none">
            ${["urgent","high","medium","low"].map(p => `<option value="${p}" ${task && task.priority === p ? 'selected':''}>${p.charAt(0).toUpperCase()+p.slice(1)}</option>`).join("")}
          </select></div>
      </div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Assigned To</label>
        <input id="fTaskAssigned" value="${escHtml(task ? task.assigned_to || '' : '')}" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" /></div>
      <div><label class="block text-xs font-medium text-gray-600 mb-1">Related Opportunity</label>
        <select id="fTaskOpp" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none">
          <option value="">— None —</option>
          ${opps.map(o => `<option value="${o.id}" ${task && task.opportunity_id === o.id ? 'selected':''}>${escHtml(o.title.substring(0,80))}</option>`).join("")}
        </select></div>
      ${isEdit ? `<div><label class="block text-xs font-medium text-gray-600 mb-1">Status</label>
        <select id="fTaskStatus" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none">
          ${["open","in_progress","complete"].map(s => `<option value="${s}" ${task && task.status === s ? 'selected':''}>${s.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</option>`).join("")}
        </select></div>` : ''}
    </div>`;
  _modalSave = async () => {
    const name = document.getElementById("fTaskName").value.trim();
    if (!name) { alert("Task name is required."); return; }
    const payload = {
      task_name: name,
      due_date: document.getElementById("fTaskDue").value || null,
      priority: document.getElementById("fTaskPriority").value,
      assigned_to: document.getElementById("fTaskAssigned").value.trim() || null,
      opportunity_id: document.getElementById("fTaskOpp").value ? parseInt(document.getElementById("fTaskOpp").value) : null,
      status: isEdit ? document.getElementById("fTaskStatus").value : "open",
    };
    const url    = isEdit ? `/api/crm/tasks/${task.id}` : "/api/crm/tasks";
    const method = isEdit ? "PUT" : "POST";
    await apiFetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    closeModal();
    _lazyLoaded["tasks"] = false;
    loadTasks();
  };
  showModal();
}

async function deleteTask(id) {
  if (!confirm("Delete this task?")) return;
  await apiFetch(`/api/crm/tasks/${id}`, { method: "DELETE" });
  _lazyLoaded["tasks"] = false;
  loadTasks();
}

document.getElementById("taskStatusFilter").addEventListener("change", () => {
  taskState.page = 1;
  taskState.status = document.getElementById("taskStatusFilter").value;
  loadTasks();
});
document.getElementById("taskPriorityFilter").addEventListener("change", () => {
  taskState.page = 1;
  taskState.priority = document.getElementById("taskPriorityFilter").value;
  loadTasks();
});
document.getElementById("taskClearBtn").addEventListener("click", () => {
  document.getElementById("taskStatusFilter").value = "open";
  document.getElementById("taskPriorityFilter").value = "";
  taskState.status = "open"; taskState.priority = ""; taskState.page = 1;
  loadTasks();
});
document.getElementById("taskPrevBtn").addEventListener("click", () => { if (taskState.page > 1) { taskState.page--; loadTasks(); } });
document.getElementById("taskNextBtn").addEventListener("click", () => { if (taskState.page < taskState.pages) { taskState.page++; loadTasks(); } });


// ===========================================================================
//  FACULTY TAB
// ===========================================================================

const facultyState = { page: 1, limit: 50, total: 0, pages: 1, search: "", department: "", labDataOnly: false };

async function loadFaculty() {
  setTableLoading("facultyTableBody", 6);
  const p = new URLSearchParams({ page: facultyState.page, limit: facultyState.limit });
  if (facultyState.search)     p.set("search", facultyState.search);
  if (facultyState.department) p.set("department", facultyState.department);
  if (facultyState.labDataOnly) p.set("has_lab_data", "true");
  try {
    const data = await apiFetch(`/api/faculty?${p.toString()}`);
    facultyState.total = data.total;
    facultyState.pages = data.pages;
    renderFacultyTable(data.items);
    document.getElementById("facultyStatShowing").textContent = data.items.length;
    document.getElementById("facultyPageInfo").textContent = `Page ${facultyState.page} of ${facultyState.pages} · ${facultyState.total.toLocaleString()} total`;
    document.getElementById("facultyPrevBtn").disabled = facultyState.page <= 1;
    document.getElementById("facultyNextBtn").disabled = facultyState.page >= facultyState.pages;
  } catch (e) {
    document.getElementById("facultyTableBody").innerHTML = `<tr><td colspan="6" class="px-4 py-12 text-center text-red-400">Error: ${escHtml(e.message)}</td></tr>`;
  }
}

async function loadFacultyStats() {
  try {
    const data = await apiFetch("/api/faculty?limit=1");
    document.getElementById("facultyStatTotal").textContent = data.total.toLocaleString();
  } catch (e) { console.warn("Faculty stats failed:", e); }
}

async function loadDepartments() {
  try {
    const depts = await apiFetch("/api/faculty/departments");
    const sel = document.getElementById("facultyDeptFilter");
    depts.forEach(d => {
      const opt = document.createElement("option");
      opt.value = d; opt.textContent = d;
      sel.appendChild(opt);
    });
  } catch (e) { console.warn("Departments load failed:", e); }
}

function renderFacultyTable(items) {
  const tbody = document.getElementById("facultyTableBody");
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="px-4 py-12 text-center text-gray-400">No faculty found.</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map(f => {
    const labSnippet = (f.lab_assets || "").substring(0, 150);
    const hasLabData = f.lab_assets || f.project_ideas;
    const rowClass = hasLabData ? "hover:bg-blue-50 bg-blue-50/30" : "hover:bg-blue-50";
    return `
    <tr class="${rowClass} transition-colors cursor-pointer" onclick="window.open('${escHtml(f.profile_url)}','_blank')">
      <td class="px-4 py-3">
        <a href="${escHtml(f.profile_url)}" target="_blank" rel="noopener" class="font-medium text-blue-800 hover:underline" onclick="event.stopPropagation()">${escHtml(f.name)}</a>
        ${hasLabData ? '<span class="ml-1 inline-block w-1.5 h-1.5 rounded-full bg-green-500" title="Has BD profile"></span>' : ""}
      </td>
      <td class="px-4 py-3 text-xs text-gray-600">${escHtml(f.title || "—")}</td>
      <td class="px-4 py-3 text-xs text-gray-600 whitespace-nowrap">${escHtml(f.department || "—")}</td>
      <td class="px-4 py-3 text-xs text-gray-500 truncate-desc">${escHtml((f.research_interests || "").substring(0, 200) || "—")}</td>
      <td class="px-4 py-3 text-xs text-gray-500 truncate-desc" title="${escHtml(f.lab_assets || "")}">
        ${labSnippet ? escHtml(labSnippet) + (f.lab_assets && f.lab_assets.length > 150 ? "…" : "") : "<span class='text-gray-300'>—</span>"}
      </td>
      <td class="px-4 py-3 text-xs">
        ${f.email ? `<a href="mailto:${escHtml(f.email)}" class="text-blue-600 hover:underline" onclick="event.stopPropagation()">${escHtml(f.email)}</a>` : "—"}
      </td>
    </tr>`;
  }).join("");
}

function showFacultyAlert(msg, type = "info") {
  const bar = document.getElementById("facultyAlertBar");
  const classes = { info: "bg-blue-50 text-blue-700 border-blue-200", success: "bg-green-50 text-green-700 border-green-200", error: "bg-red-50 text-red-600 border-red-200" };
  bar.className = `px-5 py-2.5 text-sm border-b ${classes[type] || classes.info}`;
  bar.textContent = msg;
  bar.classList.remove("hidden");
  if (type !== "info" || msg.includes("complete")) setTimeout(() => bar.classList.add("hidden"), 6000);
}

async function triggerFacultyRefresh() {
  const btn = document.getElementById("facultyRefreshBtn");
  btn.disabled = true; btn.textContent = "Running...";
  showFacultyAlert("Refreshing faculty — pulling NIH Reporter data then enriching from U-M Tableau dashboard. ~15 seconds.", "info");
  try {
    await apiFetch("/api/faculty/refresh", { method: "POST" });
    await sleep(18000);
    showFacultyAlert("Refresh complete. Reloading faculty list...", "success");
    await Promise.all([loadFacultyStats(), loadFaculty(), loadDepartments()]);
  } catch (e) {
    showFacultyAlert(`Refresh failed: ${e.message}`, "error");
  } finally {
    btn.disabled = false; btn.textContent = "Refresh Faculty";
  }
}

let facultyDebounce;
document.getElementById("facultyRefreshBtn").addEventListener("click", triggerFacultyRefresh);
document.getElementById("facultySearchInput").addEventListener("input", () => {
  clearTimeout(facultyDebounce);
  facultyDebounce = setTimeout(() => {
    facultyState.page = 1;
    facultyState.search = document.getElementById("facultySearchInput").value.trim();
    facultyState.department = document.getElementById("facultyDeptFilter").value;
    facultyState.labDataOnly = document.getElementById("facultyLabDataFilter").checked;
    loadFaculty();
  }, 350);
});
document.getElementById("facultyDeptFilter").addEventListener("change", () => { facultyState.department = document.getElementById("facultyDeptFilter").value; loadFaculty(); });
document.getElementById("facultyLabDataFilter").addEventListener("change", () => { facultyState.labDataOnly = document.getElementById("facultyLabDataFilter").checked; loadFaculty(); });
document.getElementById("facultyClearBtn").addEventListener("click", () => {
  document.getElementById("facultySearchInput").value = "";
  document.getElementById("facultyDeptFilter").value = "";
  document.getElementById("facultyLabDataFilter").checked = false;
  facultyState.search = ""; facultyState.department = ""; facultyState.labDataOnly = false; facultyState.page = 1;
  loadFaculty();
});
document.getElementById("facultyPrevBtn").addEventListener("click", () => { if (facultyState.page > 1) { facultyState.page--; loadFaculty(); } });
document.getElementById("facultyNextBtn").addEventListener("click", () => { if (facultyState.page < facultyState.pages) { facultyState.page++; loadFaculty(); } });


// ===========================================================================
//  MODAL SYSTEM
// ===========================================================================

let _modalSave = null;

function showModal() {
  const overlay = document.getElementById("modalOverlay");
  overlay.style.display = "flex";
}

function closeModal() {
  document.getElementById("modalOverlay").style.display = "none";
  _modalSave = null;
}

document.getElementById("modalSaveBtn").addEventListener("click", async () => {
  if (!_modalSave) return;
  const btn = document.getElementById("modalSaveBtn");
  btn.disabled = true;
  btn.textContent = "Saving...";
  try {
    await _modalSave();
  } catch (e) {
    alert(`Save failed: ${e.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "Save";
  }
});

document.getElementById("modalOverlay").addEventListener("click", e => {
  if (e.target === document.getElementById("modalOverlay")) closeModal();
});


// ===========================================================================
//  Shared table helpers
// ===========================================================================

function setTableLoading(tbodyId, cols) {
  document.getElementById(tbodyId).innerHTML =
    `<tr><td colspan="${cols}" class="px-4 py-12 text-center text-gray-300">Loading...</td></tr>`;
}


// ===========================================================================
//  Bootstrap
// ===========================================================================

loadStats();
loadOpportunities();
