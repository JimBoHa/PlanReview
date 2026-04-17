const state = {
  projectId: null,
  automation: null,
  activeJob: null,
  discrepancies: [],
};

const byId = (id) => document.getElementById(id);

const renderAutomation = () => {
  const container = byId("automation-summary");
  if (!state.automation) {
    container.innerHTML = "<div>No automated baseline has been generated yet.</div>";
    return;
  }
  const standards = state.automation.standards.map((item) => `
    <div><strong>${item.citation}</strong> · ${item.source}</div>
  `).join("");
  const authorities = state.automation.authorities.map((item) => `<div>${item}</div>`).join("");
  const evidence = state.automation.evidence.map((item) => `<div>${item}</div>`).join("");
  container.innerHTML = `
    <div><strong>Authorities</strong>${authorities}</div>
    <div><strong>Standards</strong>${standards}</div>
    <div><strong>Evidence</strong>${evidence || "<div>No explicit document citations were detected.</div>"}</div>
  `;
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
  byId("job-status").textContent = `${job.status} · ${job.phase} · ${job.processed_pages}/${job.total_pages} pages · ${job.findings_count} findings · ${eta}${job.error_message ? ` · ${job.error_message}` : ""}`;
  renderFindings();
  if (job.status === "running" || job.status === "pending") {
    setTimeout(pollJob, 1500);
  }
};

byId("project-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  payload.is_federal = false;
  payload.is_military = false;
  payload.is_faa = false;
  payload.requires_local_permit = true;
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

byId("analyze-project").addEventListener("click", async () => {
  if (!state.projectId) return;
  const response = await fetch(`/api/projects/${state.projectId}/automation`, { method: "POST" });
  const data = await response.json();
  state.automation = data;
  renderAutomation();
});

byId("start-review").addEventListener("click", async () => {
  if (!state.projectId) return;
  if (!state.automation) {
    await fetch(`/api/projects/${state.projectId}/automation`, { method: "POST" })
      .then((response) => response.json())
      .then((data) => {
        state.automation = data;
        renderAutomation();
      });
  }
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
renderAutomation();
