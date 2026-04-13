const state = {
  projectId: null,
  selectedStandards: new Map(),
  catalogResults: [],
  activeJob: null,
  discrepancies: [],
};

const byId = (id) => document.getElementById(id);

const renderCatalog = () => {
  byId("catalog-list").innerHTML = state.catalogResults.map((item) => `
    <li>
      <strong>${item.code} ${item.version}</strong>
      <div>${item.title}</div>
      <div class="catalog-meta">${item.issuer} · ${item.family} · ${item.citation}</div>
      <button data-standard='${JSON.stringify(item)}'>Add</button>
    </li>
  `).join("");
  byId("catalog-list").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      const item = JSON.parse(button.dataset.standard);
      state.selectedStandards.set(item.id, { ...item, source: "user", user_state: "selected" });
      renderSelected();
    });
  });
};

const renderSelected = () => {
  byId("selected-list").innerHTML = [...state.selectedStandards.values()].map((item) => `
    <li>
      <strong>${item.code} ${item.version}</strong>
      <div>${item.title}</div>
      <div class="catalog-meta">${item.source}</div>
      <button class="secondary" data-remove="${item.id}">Remove</button>
    </li>
  `).join("");
  byId("selected-list").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedStandards.delete(button.dataset.remove);
      renderSelected();
    });
  });
};

const renderFindings = () => {
  const query = byId("findings-search").value.trim().toLowerCase();
  const rows = state.discrepancies.filter((row) => {
    const blob = `${row.citation} ${row.description} ${row.document_kind} ${row.page_label}`.toLowerCase();
    return !query || blob.includes(query);
  });
  byId("findings-table").innerHTML = rows.map((row) => `
    <tr>
      <td>${row.row_number}</td>
      <td>${row.document_kind}</td>
      <td>${row.page_label}</td>
      <td>${row.citation}</td>
      <td>${row.description}</td>
      <td>${row.thumbnail_path ? `<img class="thumb" src="${row.thumbnail_path}" alt="thumbnail" />` : ""}</td>
    </tr>
  `).join("");
  byId("issues-live").innerHTML = rows.slice(-10).reverse().map((row) => `
    <div>#${row.row_number} · ${row.document_kind} · ${row.page_label} · ${row.description}</div>
  `).join("");
};

const loadProject = async () => {
  if (!state.projectId) return;
  const response = await fetch(`/api/projects/${state.projectId}`);
  const data = await response.json();
  state.selectedStandards.clear();
  data.selected_standards.forEach((item) => state.selectedStandards.set(item.id, item));
  renderSelected();
  byId("documents-list").innerHTML = data.documents.map((item) => `
    <li>${item.kind} · ${item.original_name} · ${item.page_count} pages</li>
  `).join("");
};

const pollJob = async () => {
  if (!state.activeJob) return;
  const response = await fetch(`/api/jobs/${state.activeJob}`);
  const data = await response.json();
  const job = data.job;
  state.discrepancies = data.discrepancies.map((row) => ({
    ...row,
    thumbnail_path: row.thumbnail_path ? `/${row.thumbnail_path.replace(/^\\/+/, "")}` : "",
  }));
  const percent = job.total_pages ? Math.round((job.processed_pages / job.total_pages) * 100) : 0;
  const eta = job.eta_seconds == null ? "estimating..." : `${job.eta_seconds}s remaining`;
  byId("job-progress").value = percent;
  byId("job-status").textContent = `${job.status} · ${job.processed_pages}/${job.total_pages} pages · ${job.findings_count} findings · ${eta}${job.error_message ? ` · ${job.error_message}` : ""}`;
  renderFindings();
  if (job.status === "running" || job.status === "pending") {
    setTimeout(pollJob, 1500);
  }
};

byId("project-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  payload.is_federal = form.get("is_federal") === "on";
  payload.is_military = form.get("is_military") === "on";
  payload.is_faa = form.get("is_faa") === "on";
  payload.requires_local_permit = form.get("requires_local_permit") === "on";
  if (!payload.contract_signed_on) payload.contract_signed_on = null;
  const response = await fetch("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  state.projectId = data.project.id;
  byId("project-status").textContent = `Project ready: ${data.project.id}`;
  await loadProject();
});

const uploadDocument = async (kind, inputId) => {
  if (!state.projectId) return;
  const file = byId(inputId).files[0];
  if (!file) return;
  const body = new FormData();
  body.append("kind", kind);
  body.append("file", file);
  await fetch(`/api/projects/${state.projectId}/documents`, { method: "POST", body });
  await loadProject();
};

byId("upload-drawings").addEventListener("click", () => uploadDocument("drawings", "drawings-file"));
byId("upload-specs").addEventListener("click", () => uploadDocument("specs", "specs-file"));

byId("catalog-search").addEventListener("input", async (event) => {
  const q = event.target.value;
  const response = await fetch(`/api/catalog/search?q=${encodeURIComponent(q)}`);
  const data = await response.json();
  state.catalogResults = data.items;
  renderCatalog();
});

byId("suggest-standards").addEventListener("click", async () => {
  if (!state.projectId) return;
  const response = await fetch(`/api/projects/${state.projectId}/suggest-standards`, { method: "POST" });
  const data = await response.json();
  data.suggestions.forEach((item) => {
    const catalogItem = state.catalogResults.find((candidate) => candidate.id === item.standard_id);
    if (catalogItem) {
      state.selectedStandards.set(catalogItem.id, { ...catalogItem, source: "suggested", user_state: "selected" });
    }
  });
  const searchResponse = await fetch("/api/catalog/search");
  const searchData = await searchResponse.json();
  searchData.items.forEach((item) => {
    if (data.suggestions.some((suggestion) => suggestion.standard_id === item.id)) {
      state.selectedStandards.set(item.id, { ...item, source: "suggested", user_state: "selected" });
    }
  });
  renderSelected();
});

byId("save-standards").addEventListener("click", async () => {
  if (!state.projectId) return;
  await fetch(`/api/projects/${state.projectId}/standards`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      items: [...state.selectedStandards.values()].map((item) => ({
        standard_id: item.id,
        source: item.source || "user",
        user_state: item.user_state || "selected",
      })),
    }),
  });
  await loadProject();
});

byId("show-diff").addEventListener("click", async () => {
  if (!state.projectId) return;
  const response = await fetch(`/api/projects/${state.projectId}/standards/diff`);
  const data = await response.json();
  byId("diff-list").innerHTML = data.items.map((item) => `
    <div><strong>${item.status}</strong> · ${item.code} ${item.version} · ${item.reason}</div>
  `).join("");
});

byId("start-review").addEventListener("click", async () => {
  if (!state.projectId) return;
  const response = await fetch(`/api/projects/${state.projectId}/review`, { method: "POST" });
  const data = await response.json();
  state.activeJob = data.job.id;
  pollJob();
});

byId("build-exports").addEventListener("click", async () => {
  if (!state.projectId) return;
  const response = await fetch(`/api/projects/${state.projectId}/exports`);
  const data = await response.json();
  byId("exports").innerHTML = Object.entries(data.exports).map(([label, path]) => {
    const filename = path.split("/").pop();
    return `<div><a href="/downloads/${state.projectId}/${filename}">${label}</a></div>`;
  }).join("");
});

byId("findings-search").addEventListener("input", renderFindings);

fetch("/api/catalog/search").then((response) => response.json()).then((data) => {
  state.catalogResults = data.items;
  renderCatalog();
});
