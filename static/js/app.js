let pipelines = [];
let currentResults = null;

document.addEventListener("DOMContentLoaded", () => {
    fetchPipelines();
});

async function fetchPipelines() {
    try {
        const resp = await fetch("/api/pipelines");
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        pipelines = await resp.json();
        renderPipelineCards(pipelines);
    } catch (err) {
        showError(`No se pudo cargar la lista de pipelines: ${err.message}`);
    }
}

function renderPipelineCards(list) {
    const grid = document.getElementById("pipelineGrid");
    if (!list || list.length === 0) {
        grid.innerHTML = "<p>No hay pipelines disponibles.</p>";
        return;
    }

    grid.innerHTML = list.map((p, idx) => `
        <div class="pipeline-card">
            <div class="card-header">
                <span class="card-number">${idx + 1}</span>
                ${engineBadge(p.engine)}
            </div>
            <h3 class="card-title">${escapeHtml(p.title)}</h3>
            <p class="card-description">${escapeHtml(p.description || "")}</p>
            <ul class="rules-list">
                ${(p.rules || []).map(r => `<li>${escapeHtml(r)}</li>`).join("")}
            </ul>
            <button class="btn-run" onclick="runPipeline('${p.id}', this)">
                Ejecutar Pipeline
            </button>
        </div>
    `).join("");
}

function engineBadge(engine) {
    if (engine === "both") return '<span class="card-badge badge-both">PyDatalog + Prolog</span>';
    if (engine === "prolog") return '<span class="card-badge badge-prolog">Prolog</span>';
    return '<span class="card-badge badge-pydatalog">PyDatalog</span>';
}

async function runPipeline(pipelineId, btnEl) {
    const overlay = document.getElementById("loadingOverlay");
    overlay.classList.remove("hidden");
    if (btnEl) btnEl.disabled = true;

    try {
        const resp = await fetch(`/api/run/${pipelineId}`, { method: "POST" });
        const data = await resp.json();

        if (!resp.ok) {
            throw new Error(data.error || `HTTP ${resp.status}`);
        }

        currentResults = data;
        renderResults(data, pipelineId);
    } catch (err) {
        showError(`Error ejecutando el pipeline: ${err.message}`);
    } finally {
        overlay.classList.add("hidden");
        if (btnEl) btnEl.disabled = false;
    }
}

function renderResults(data, pipelineId) {
    const section = document.getElementById("resultsSection");
    section.classList.remove("hidden");

    const meta = pipelines.find(p => p.id === pipelineId) || {};
    document.getElementById("resultsTitle").textContent =
        `Resultados: ${data.title || meta.title || pipelineId}`;
    document.getElementById("resultsTimestamp").textContent =
        data.timestamp ? new Date(data.timestamp).toLocaleString("es-UY") : new Date().toLocaleString("es-UY");

    const description = data.description || meta.description;
    if (description) {
        document.getElementById("pipelineInfoCard").classList.remove("hidden");
        document.getElementById("pipelineDescription").textContent = description;
    } else {
        document.getElementById("pipelineInfoCard").classList.add("hidden");
    }

    const stages = data.stages || [];
    if (stages.length === 0) {
        showError("El pipeline no retornó resultados.");
        return;
    }

    renderTabs(stages);
    section.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderTabs(stages) {
    const container = document.getElementById("tabsContainer");
    let html = '<div class="tab-buttons">';

    stages.forEach((s, i) => {
        html += `<button class="tab-btn ${i === 0 ? "active" : ""}" onclick="switchTab(${i})">${escapeHtml(s.name)}</button>`;
    });
    html += "</div>";

    stages.forEach((stage, i) => {
        html += `<div class="tab-content ${i === 0 ? "active" : ""}" id="tab-${i}">`;
        if (stage.facts && Object.keys(stage.facts).length > 0) {
            for (const [predicate, rows] of Object.entries(stage.facts)) {
                html += renderTable(predicate, rows);
            }
        } else {
            html += '<p style="color:#999;font-size:0.9rem;">Sin resultados para esta etapa.</p>';
        }
        html += "</div>";
    });

    container.innerHTML = html;
}

function renderTable(predicate, rows) {
    if (!rows || rows.length === 0) return "";

    const flatRows = rows.map(normalizeRow);
    const maxCols = Math.max(...flatRows.map(r => r.length), 1);
    const headers = Array.from({ length: maxCols }, (_, i) => `Arg${i + 1}`);

    const body = flatRows.map(cells => {
        const padded = [...cells];
        while (padded.length < maxCols) padded.push("");
        return `<tr>${padded.map(c => `<td>${formatValue(c)}</td>`).join("")}</tr>`;
    }).join("");

    return `
        <p class="predicate-title">${escapeHtml(predicate)}</p>
        <div class="data-table-wrapper">
            <table class="data-table">
                <thead><tr>${headers.map(h => `<th>${escapeHtml(h)}</th>`).join("")}</tr></thead>
                <tbody>${body}</tbody>
            </table>
        </div>
        <p class="row-count">${rows.length} fila${rows.length !== 1 ? "s" : ""}</p>
    `;
}

function normalizeRow(row) {
    if (Array.isArray(row)) {
        return row.flatMap(normalizeCell);
    }
    return [row];
}

function normalizeCell(value) {
    if (Array.isArray(value)) {
        return value.map(v => (Array.isArray(v) ? v.join(", ") : v));
    }
    return value;
}

function switchTab(index) {
    document.querySelectorAll(".tab-btn").forEach((btn, i) => {
        btn.classList.toggle("active", i === index);
    });
    document.querySelectorAll(".tab-content").forEach((content, i) => {
        content.classList.toggle("active", i === index);
    });
}

function clearResults() {
    currentResults = null;
    document.getElementById("resultsSection").classList.add("hidden");
}

function showError(msg) {
    const toast = document.getElementById("errorToast");
    toast.textContent = msg;
    toast.classList.remove("hidden");
    setTimeout(() => toast.classList.add("hidden"), 6000);
}

function escapeHtml(str) {
    if (str == null) return "";
    const div = document.createElement("div");
    div.textContent = String(str);
    return div.innerHTML;
}

function formatValue(val) {
    if (val === null || val === undefined || val === "") {
        return '<span style="color:#aaa">—</span>';
    }
    if (typeof val === "number") {
        return `<strong>${Number.isInteger(val) ? val : val.toFixed(2)}</strong>`;
    }
    return escapeHtml(String(val));
}
