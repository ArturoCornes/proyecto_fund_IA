/* ═══════════════════════════════════════════════════════════════
   UY-CompraTracker — app.js
   Pipeline grid + Organismos bubble visualisation
═══════════════════════════════════════════════════════════════ */

let pipelines = [];
let currentResults = null;

// Organismos state
let _organismos = [];          // [ { nombre, cantidad_proveedores } ]
let _selectedOrg = null;       // nombre del organismo seleccionado
let _selectedProvider = null;  // nombre del proveedor seleccionado
let _allProviders = [];        // lista actual de proveedores para filtrar

document.addEventListener("DOMContentLoaded", () => {
    fetchPipelines();
});

/* ═══════════════════════════════════════════════════════════════
   PIPELINE GRID
═══════════════════════════════════════════════════════════════ */

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

/* ═══════════════════════════════════════════════════════════════
   ORGANISMOS — BUBBLE VISUALISATION
═══════════════════════════════════════════════════════════════ */

// Palette of bubble background colors (translucent)
const BUBBLE_COLORS = [
    "rgba(99,102,241,0.18)",   // indigo
    "rgba(168,85,247,0.18)",   // purple
    "rgba(236,72,153,0.18)",   // pink
    "rgba(20,184,166,0.18)",   // teal
    "rgba(59,130,246,0.18)",   // blue
    "rgba(245,158,11,0.18)",   // amber
    "rgba(16,185,129,0.18)",   // emerald
    "rgba(239,68,68,0.18)",    // red
    "rgba(251,146,60,0.18)",   // orange
    "rgba(34,211,238,0.18)",   // cyan
];
const BUBBLE_BORDER_COLORS = [
    "rgba(99,102,241,0.55)",
    "rgba(168,85,247,0.55)",
    "rgba(236,72,153,0.55)",
    "rgba(20,184,166,0.55)",
    "rgba(59,130,246,0.55)",
    "rgba(245,158,11,0.55)",
    "rgba(16,185,129,0.55)",
    "rgba(239,68,68,0.55)",
    "rgba(251,146,60,0.55)",
    "rgba(34,211,238,0.55)",
];
const FLOAT_ANIMS = ["float-a", "float-b", "float-c", "float-gentle"];

async function initOrganismos() {
    const btn = document.getElementById("btnLoadOrganismos");
    const overlay = document.getElementById("organismoLoadingOverlay");
    btn.disabled = true;
    overlay.classList.remove("hidden");
    document.getElementById("organismoLoadingText").textContent = "Ejecutando pipeline_08 — puede tardar unos momentos...";

    try {
        const resp = await fetch("/api/organismos");
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.error || `HTTP ${resp.status}`);
        }
        _organismos = await resp.json();
        renderBubbles(_organismos);
        btn.textContent = "✓ Organismos cargados";
        btn.style.background = "linear-gradient(135deg, #10b981, #059669)";
    } catch (err) {
        showError(`Error cargando organismos: ${err.message}`);
        btn.disabled = false;
    } finally {
        overlay.classList.add("hidden");
    }
}

function renderBubbles(organismos) {
    const arena = document.getElementById("bubbleArena");
    arena.innerHTML = ""; // clear placeholder

    if (!organismos || organismos.length === 0) {
        arena.innerHTML = '<p style="color:#9ca3af;text-align:center;">Sin datos de organismos.</p>';
        return;
    }

    // Compute bubble sizes: map cantidad_proveedores → radius
    const counts = organismos.map(o => o.cantidad_proveedores);
    const maxCount = Math.max(...counts, 1);
    const minCount = Math.min(...counts, 1);

    const arenaW = arena.clientWidth  || 800;
    const arenaH = arena.clientHeight || 420;

    // Radius range depends on total number of organismos
    const MIN_R = organismos.length > 30 ? 38 : 48;
    const MAX_R = organismos.length > 30 ? 80 : 95;

    // Place bubbles using a simple collision-avoiding layout
    const placed = []; // { cx, cy, r }

    function normalize(val) {
        if (maxCount === minCount) return 0.5;
        return (val - minCount) / (maxCount - minCount);
    }

    function overlaps(cx, cy, r) {
        for (const b of placed) {
            const dist = Math.hypot(cx - b.cx, cy - b.cy);
            if (dist < r + b.r + 8) return true;
        }
        return false;
    }

    function findPosition(r) {
        const margin = r + 4;
        for (let attempt = 0; attempt < 600; attempt++) {
            const cx = margin + Math.random() * (arenaW - 2 * margin);
            const cy = margin + Math.random() * (arenaH - 2 * margin);
            if (!overlaps(cx, cy, r)) return { cx, cy };
        }
        // fallback: spiral placement
        const angle = placed.length * 2.4;
        const dist = 60 + placed.length * 14;
        return {
            cx: Math.max(r, Math.min(arenaW - r, arenaW / 2 + Math.cos(angle) * dist)),
            cy: Math.max(r, Math.min(arenaH - r, arenaH / 2 + Math.sin(angle) * dist)),
        };
    }

    organismos.forEach((org, idx) => {
        const n = normalize(org.cantidad_proveedores);
        const r = Math.round(MIN_R + n * (MAX_R - MIN_R));
        const { cx, cy } = findPosition(r);
        placed.push({ cx, cy, r });

        const colorIdx = idx % BUBBLE_COLORS.length;
        const anim     = FLOAT_ANIMS[idx % FLOAT_ANIMS.length];
        const delay    = (idx * 0.37) % 5;
        const duration = 5 + (idx % 4);

        // Label: abbreviate if name is long
        const label = org.nombre.length > 28
            ? org.nombre.substring(0, 26) + "…"
            : org.nombre;

        const fontSize = r < 55 ? "0.6rem" : r < 70 ? "0.7rem" : "0.78rem";
        const countFontSize = r < 55 ? "0.55rem" : "0.68rem";

        const div = document.createElement("div");
        div.className = "bubble";
        div.id = `bubble-${idx}`;
        div.title = org.nombre;
        div.style.cssText = `
            width: ${r * 2}px;
            height: ${r * 2}px;
            left: ${cx - r}px;
            top: ${cy - r}px;
            background: radial-gradient(circle at 35% 35%, rgba(255,255,255,0.88) 0%, ${BUBBLE_COLORS[colorIdx]} 100%);
            border-color: ${BUBBLE_BORDER_COLORS[colorIdx]};
            animation: ${anim} ${duration}s ease-in-out ${delay}s infinite;
        `;

        div.innerHTML = `
            <span class="bubble-label" style="font-size:${fontSize}; max-width:${r * 1.5}px; -webkit-line-clamp:3;">${escapeHtml(label)}</span>
            <span class="bubble-count" style="font-size:${countFontSize};">${org.cantidad_proveedores} prov.</span>
        `;

        div.addEventListener("click", () => onBubbleClick(org, div));
        arena.appendChild(div);
    });
}

async function onBubbleClick(org, bubbleEl) {
    // Deselect previous
    document.querySelectorAll(".bubble.selected").forEach(b => b.classList.remove("selected"));
    bubbleEl.classList.add("selected");

    _selectedOrg = org.nombre;
    _selectedProvider = null;
    closeMoneyCard();

    const panel = document.getElementById("providersPanel");
    const list  = document.getElementById("providersList");
    const orgNameEl = document.getElementById("providersOrgName");
    const countEl   = document.getElementById("providersCount");

    orgNameEl.textContent = org.nombre;
    countEl.textContent   = `${org.cantidad_proveedores} proveedores registrados`;
    list.innerHTML = '<p style="color:#9ca3af;font-size:0.85rem;padding:0.5rem;">Cargando proveedores...</p>';
    document.getElementById("providerSearchInput").value = "";

    panel.classList.remove("hidden");
    panel.scrollIntoView({ behavior: "smooth", block: "nearest" });

    try {
        const resp = await fetch(`/api/organismos/${encodeURIComponent(org.nombre)}/proveedores`);
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.error || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        _allProviders = data.proveedores || [];
        renderProvidersList(_allProviders);
    } catch (err) {
        list.innerHTML = `<p style="color:#dc2626;font-size:0.85rem;">Error: ${escapeHtml(err.message)}</p>`;
    }
}

function renderProvidersList(providers) {
    const list = document.getElementById("providersList");
    if (!providers || providers.length === 0) {
        list.innerHTML = '<p style="color:#9ca3af;font-size:0.85rem;padding:0.5rem;">Sin proveedores registrados.</p>';
        return;
    }

    list.innerHTML = providers.map((prov, idx) => {
        const montoStr = prov.monto != null
            ? `$ ${formatMoney(prov.monto)}`
            : "— sin dato";
        return `
            <div class="provider-item" id="prov-item-${idx}" onclick="onProviderClick('${escapeJs(prov.nombre)}', this)">
                <span class="provider-icon">🏢</span>
                <span class="provider-name" title="${escapeHtml(prov.nombre)}">${escapeHtml(prov.nombre)}</span>
                <span class="provider-monto">${escapeHtml(montoStr)}</span>
            </div>
        `;
    }).join("");
}

function filterProviders(query) {
    const q = query.trim().toLowerCase();
    _allProviders.forEach((prov, idx) => {
        const el = document.getElementById(`prov-item-${idx}`);
        if (!el) return;
        const matches = !q || prov.nombre.toLowerCase().includes(q);
        el.classList.toggle("hidden-filter", !matches);
    });
}

async function onProviderClick(providerName, itemEl) {
    // Deselect previous
    document.querySelectorAll(".provider-item.selected").forEach(el => el.classList.remove("selected"));
    itemEl.classList.add("selected");
    _selectedProvider = providerName;

    const moneyCard = document.getElementById("moneyCard");
    const amountEl  = document.getElementById("moneyCardAmount");
    const orgEl     = document.getElementById("moneyCardOrg");
    const provEl    = document.getElementById("moneyCardProvider");

    orgEl.textContent  = _selectedOrg;
    provEl.textContent = providerName;
    amountEl.textContent = "cargando…";
    moneyCard.classList.remove("hidden");
    // Re-trigger animation
    moneyCard.style.animation = "none";
    moneyCard.offsetHeight;   // reflow
    moneyCard.style.animation = "";

    try {
        const resp = await fetch(
            `/api/gasto/${encodeURIComponent(_selectedOrg)}/${encodeURIComponent(providerName)}`
        );
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.error || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        if (data.monto != null) {
            amountEl.textContent = `$ ${formatMoney(data.monto)}`;
        } else {
            amountEl.textContent = "Sin datos de monto";
        }
    } catch (err) {
        amountEl.textContent = "Error al obtener datos";
        showError(`Error: ${err.message}`);
    }

    moneyCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function closeProvidersPanel() {
    document.getElementById("providersPanel").classList.add("hidden");
    document.getElementById("moneyCard").classList.add("hidden");
    document.querySelectorAll(".bubble.selected").forEach(b => b.classList.remove("selected"));
    _selectedOrg = null;
    _selectedProvider = null;
}

function closeMoneyCard() {
    document.getElementById("moneyCard").classList.add("hidden");
    document.querySelectorAll(".provider-item.selected").forEach(el => el.classList.remove("selected"));
    _selectedProvider = null;
}

/* ═══════════════════════════════════════════════════════════════
   SHARED UTILITIES
═══════════════════════════════════════════════════════════════ */

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

/** Escape string for use inside a JS single-quoted attribute value */
function escapeJs(str) {
    if (str == null) return "";
    return String(str)
        .replace(/\\/g, "\\\\")
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"');
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

/**
 * Format a number as money with thousands separators.
 * e.g. 1234567.89 → "1.234.567,89"
 */
function formatMoney(val) {
    if (val == null) return "—";
    const num = typeof val === "number" ? val : parseFloat(val);
    if (isNaN(num)) return String(val);
    return num.toLocaleString("es-UY", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    });
}
