const state = {
  data: null,
  tab: "activities",
  query: "",
  selectedDb: null,
};

const el = {
  stats: document.getElementById("stats"),
  databases: document.getElementById("databases"),
  thead: document.getElementById("thead"),
  tbody: document.getElementById("tbody"),
  search: document.getElementById("search"),
  footer: document.getElementById("footer-note"),
  browseTitle: document.getElementById("browse-title"),
  browseSub: document.getElementById("browse-sub"),
};

function chip(label, value) {
  return `<span class="chip">${label}: <strong>${value}</strong></span>`;
}

function renderStats() {
  const d = state.data;
  el.stats.innerHTML = [
    chip("Project", d.project),
    chip("Databases", d.databases.length),
    chip("LCIA methods", d.method_count),
  ].join("");
}

function renderDatabases() {
  el.databases.innerHTML = state.data.databases
    .map((db) => {
      const active = db.name === state.selectedDb ? "active" : "";
      return `<li><button type="button" class="db-item ${active}" data-db="${db.name}">
        <span class="name">${db.name}</span>
        <span class="meta">${db.records.toLocaleString()} records</span>
      </button></li>`;
    })
    .join("");
}

function filteredActivities() {
  const q = state.query.trim().toLowerCase();
  return state.data.activities_sample.filter((a) => {
    if (!q) return true;
    const hay = [a.name, ...(a.categories || []), a.unit, a.type]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return hay.includes(q);
  });
}

function filteredMethods() {
  const q = state.query.trim().toLowerCase();
  return state.data.methods_sample.filter((m) => {
    if (!q) return true;
    return m.label.toLowerCase().includes(q);
  });
}

function renderTable() {
  if (state.tab === "methods") {
    el.browseTitle.textContent = "LCIA methods";
    el.browseSub.textContent = `Sample of ${state.data.methods_sample.length} methods (project has ${state.data.method_count}).`;
    el.thead.innerHTML = `<tr><th>Method</th><th>Path</th></tr>`;
    const rows = filteredMethods();
    el.tbody.innerHTML = rows.length
      ? rows
          .map(
            (m) => `<tr><td>${escapeHtml(m.key[m.key.length - 1] || m.label)}</td>
            <td class="cat">${escapeHtml(m.label)}</td></tr>`
          )
          .join("")
      : `<tr><td colspan="2" class="empty">No methods match “${escapeHtml(state.query)}”.</td></tr>`;
    el.footer.textContent = `Showing ${rows.length} of ${state.data.methods_sample.length} sampled methods.`;
    return;
  }

  el.browseTitle.textContent = "Biosphere flows";
  el.browseSub.textContent = "Search sample activities from biosphere3.";
  el.thead.innerHTML = `<tr><th>Name</th><th>Categories</th><th>Unit</th><th>Type</th></tr>`;
  const rows = filteredActivities();
  el.tbody.innerHTML = rows.length
    ? rows
        .map(
          (a) => `<tr>
          <td>${escapeHtml(a.name || "")}</td>
          <td class="cat">${escapeHtml((a.categories || []).join(" / "))}</td>
          <td>${escapeHtml(a.unit || "")}</td>
          <td>${escapeHtml(a.type || "")}</td>
        </tr>`
        )
        .join("")
    : `<tr><td colspan="4" class="empty">No activities match “${escapeHtml(state.query)}”.</td></tr>`;
  el.footer.textContent = `Showing ${rows.length} of ${state.data.activities_sample.length} sampled flows · ${state.data.note}`;
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function bind() {
  el.search.addEventListener("input", (e) => {
    state.query = e.target.value;
    renderTable();
  });

  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.tab = btn.dataset.tab;
      renderTable();
    });
  });

  el.databases.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-db]");
    if (!btn) return;
    state.selectedDb = btn.dataset.db;
    renderDatabases();
  });
}

async function boot() {
  const res = await fetch("./data/snapshot.json");
  if (!res.ok) throw new Error("Could not load Brightway snapshot");
  state.data = await res.json();
  state.selectedDb = state.data.databases[0]?.name || null;
  renderStats();
  renderDatabases();
  renderTable();
  bind();
}

boot().catch((err) => {
  el.stats.textContent = err.message;
  console.error(err);
});
