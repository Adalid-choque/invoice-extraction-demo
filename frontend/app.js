"use strict";

const FIELDS = ["nit", "fecha", "monto_total"];
const LABELS = { nit: "NIT", fecha: "Fecha", monto_total: "Monto total" };

// ── Metrics ──────────────────────────────────────────────────────────────────
async function loadMetrics() {
  try {
    const data = await fetch("/api/metrics").then(r => r.json());
    const tbody = document.getElementById("metrics-body");
    tbody.innerHTML = "";
    for (const field of FIELDS) {
      const g = data.metrics.gemini[field];
      const b = data.metrics.baseline[field];
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${LABELS[field]}</td>
        <td>${fmt(g.exact_match)}</td><td>${fmt(g.cer)}</td>
        <td>${fmt(b.exact_match)}</td><td>${fmt(b.cer)}</td>`;
      tbody.appendChild(tr);
    }
    // Macro row
    const tr = document.createElement("tr");
    tr.style.fontWeight = "600";
    tr.innerHTML = `
      <td>Macro promedio</td>
      <td>${fmt(data.metrics.gemini.macro_exact_match)}</td><td>—</td>
      <td>${fmt(data.metrics.baseline.macro_exact_match)}</td><td>—</td>`;
    tbody.appendChild(tr);
  } catch {
    document.getElementById("metrics-body").innerHTML =
      '<tr><td colspan="5" class="loading">No se pudieron cargar las métricas.</td></tr>';
  }
}

function fmt(v) { return typeof v === "number" ? v.toFixed(3) : v; }

// ── Examples ─────────────────────────────────────────────────────────────────
let selectedExample = null;

async function loadExamples() {
  const grid = document.getElementById("examples-grid");
  try {
    const examples = await fetch("/api/examples").then(r => r.json());
    grid.innerHTML = "";
    for (const ex of examples) {
      const card = document.createElement("div");
      card.className = "example-card";
      card.dataset.id = ex.id;
      card.innerHTML = `
        <img src="${ex.image_url}" alt="Factura ${ex.num_factura}" loading="lazy" />
        <div class="card-label">
          Nº ${ex.num_factura}
          <span class="card-tipo">${tipoLabel(ex.tipo_foto)}</span>
        </div>`;
      card.addEventListener("click", () => selectExample(card, ex));
      grid.appendChild(card);
    }

    // Analyze button for examples
    const btn = document.createElement("button");
    btn.id = "example-btn";
    btn.className = "btn-primary";
    btn.textContent = "Analizar";
    btn.disabled = true;
    btn.addEventListener("click", analyzeExample);
    document.getElementById("examples-section").appendChild(btn);
  } catch {
    grid.innerHTML = '<p class="loading">No se pudieron cargar los ejemplos.</p>';
  }
}

function tipoLabel(tipo) {
  return { bien_tomada: "Normal", con_sombra: "Con sombra", con_inclinacion: "Inclinada" }[tipo] ?? tipo;
}

function selectExample(card, ex) {
  document.querySelectorAll(".example-card").forEach(c => c.classList.remove("selected"));
  card.classList.add("selected");
  selectedExample = ex;
  document.getElementById("example-btn").disabled = false;
}

async function analyzeExample() {
  if (!selectedExample) return;
  const btn = document.getElementById("example-btn");
  btn.disabled = true;
  btn.textContent = "Analizando…";
  try {
    const res = await fetch(`/api/examples/${selectedExample.id}/analyze`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    showResult(selectedExample.image_url, data, null);
  } catch (e) {
    alert("Error al analizar: " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Analizar";
  }
}

// ── Upload ────────────────────────────────────────────────────────────────────
let uploadedFile = null;

document.getElementById("file-input").addEventListener("change", e => {
  const file = e.target.files[0];
  if (!file) return;
  uploadedFile = file;
  const label = document.getElementById("upload-label");
  label.classList.add("has-file");
  document.getElementById("upload-text").textContent = file.name;
  document.getElementById("upload-btn").disabled = false;
});

document.getElementById("upload-btn").addEventListener("click", async () => {
  if (!uploadedFile) return;
  const btn = document.getElementById("upload-btn");
  btn.disabled = true;
  btn.textContent = "Analizando…";
  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": uploadedFile.type },
      body: uploadedFile,
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    const url = URL.createObjectURL(uploadedFile);
    showResult(url, data, null);
  } catch (e) {
    alert("Error al analizar: " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Analizar imagen";
  }
});

// ── Result ────────────────────────────────────────────────────────────────────
function showResult(imageUrl, data, ref) {
  document.getElementById("result-image").src = imageUrl;
  const tbody = document.getElementById("result-body");
  tbody.innerHTML = "";

  for (const field of FIELDS) {
    const gVal = data.gemini?.[field] ?? "—";
    const bVal = data.baseline?.[field] ?? "—";
    const refVal = ref?.[field] ?? "—";
    const tr = document.createElement("tr");
    if (ref) tr.className = gVal === refVal ? "match" : "mismatch";
    tr.innerHTML = `
      <td>${LABELS[field]}</td>
      <td>${gVal || "—"}</td>
      <td>${bVal || "—"}</td>
      <td>${refVal}</td>`;
    tbody.appendChild(tr);
  }

  const warn = document.getElementById("result-warning");
  if (data.review_flag) {
    warn.textContent = "⚠ Revisión sugerida: " + (data.review_reason ?? "desacuerdo entre modelos.");
    warn.hidden = false;
  } else {
    warn.hidden = true;
  }

  const ms = data.elapsed_ms ?? data.gemini_ms;
  document.getElementById("result-time").textContent =
    ms ? `Tiempo de análisis: ${(ms / 1000).toFixed(1)} s` : "";

  document.getElementById("result-section").hidden = false;
  document.getElementById("result-section").scrollIntoView({ behavior: "smooth" });
}

// ── Init ──────────────────────────────────────────────────────────────────────
loadMetrics();
loadExamples();
