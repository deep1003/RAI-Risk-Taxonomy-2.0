const DATA_URL = "./public/data/releases/v2.17.2/risk_space.json";

const COLORS = {
  "General-purpose AI": "#3767d8",
  "Agentic AI": "#10906f",
  "Physical AI": "#c0392b",
};

const state = {
  payload: null,
  points: [],
  filtered: [],
  selectedId: null,
  systemMode: "domain",
  l3Centroids: new Map(),
};

const els = {
  activeCards: document.querySelector("#activeCards"),
  activeCardStat: document.querySelector("#activeCardStat"),
  registeredIds: document.querySelector("#registeredIds"),
  mergedRecords: document.querySelector("#mergedRecords"),
  holdCards: document.querySelector("#holdCards"),
  visibleCount: document.querySelector("#visibleCount"),
  plot: document.querySelector("#riskPlot"),
  search: document.querySelector("#searchInput"),
  domain: document.querySelector("#domainFilter"),
  l2: document.querySelector("#l2Filter"),
  l3: document.querySelector("#l3Filter"),
  hold: document.querySelector("#holdFilter"),
  reset: document.querySelector("#resetFilters"),
  modeButtons: document.querySelectorAll("[data-system-mode]"),
  systemModeText: document.querySelector("#systemModeText"),
  emptyDetails: document.querySelector("#emptyDetails"),
  cardDetails: document.querySelector("#cardDetails"),
};

const MODE_TEXT = {
  domain: "Color shows L1 domains. Orange rings mark HOLD boundary signals.",
  hold: "Boundary mode emphasizes HOLD cards as uncertain or overlapping regions in the taxonomy space.",
  attractor: "Attractor mode highlights local L3 families. Selecting a card shows its nearest L3 centroid in this 2D projection.",
};

function formatInteger(value) {
  return Number(value).toLocaleString("en-US");
}

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "n/a";
  const n = Number(value);
  return n >= 1 ? n.toFixed(1) : n.toFixed(3);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function bilingual(en, ko) {
  if (!ko) return escapeHtml(en);
  return `${escapeHtml(en)} (${escapeHtml(ko)})`;
}

function classForDomain(domain) {
  if (domain === "Physical AI") return "physical";
  if (domain === "Agentic AI") return "agentic";
  return "general";
}

function populateStats(metadata) {
  els.activeCards.textContent = formatInteger(metadata.active_cards);
  els.activeCardStat.textContent = formatInteger(metadata.active_cards);
  els.registeredIds.textContent = formatInteger(metadata.registered_ids);
  els.mergedRecords.textContent = formatInteger(metadata.merged_records);
  els.holdCards.textContent = formatInteger(metadata.hold_cards);
}

function uniqueSorted(points, getter) {
  return [...new Set(points.map(getter).filter(Boolean))].sort((a, b) => a.localeCompare(b));
}

function fillSelect(select, values, defaultText) {
  const current = select.value;
  select.innerHTML = `<option value="">${defaultText}</option>`;
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
  if (values.includes(current)) select.value = current;
}

function populateFilters() {
  const points = state.points;
  fillSelect(els.domain, uniqueSorted(points, (p) => p.path.l1_label_en), "All domains");
  fillSelect(els.l2, uniqueSorted(points, (p) => p.path.l2_label_en), "All L2 categories");
  fillSelect(
    els.l3,
    uniqueSorted(points, (p) => `${p.path.l3_label_en} (${p.path.l3_label_ko})`),
    "All L3 categories",
  );
}

function buildL3Centroids() {
  const grouped = new Map();
  state.points.forEach((point) => {
    const key = point.path.l3_id;
    if (!grouped.has(key)) {
      grouped.set(key, {
        l3_id: key,
        label_en: point.path.l3_label_en,
        label_ko: point.path.l3_label_ko,
        x: 0,
        y: 0,
        count: 0,
      });
    }
    const item = grouped.get(key);
    item.x += point.x;
    item.y += point.y;
    item.count += 1;
  });
  state.l3Centroids = new Map();
  grouped.forEach((item) => {
    item.x /= item.count;
    item.y /= item.count;
    state.l3Centroids.set(item.l3_id, item);
  });
}

function pointText(point) {
  return [
    point.id,
    point.label_en,
    point.label_ko,
    point.definition_en,
    point.definition_ko,
    point.path.l1_label_en,
    point.path.l1_label_ko,
    point.path.l2_label_en,
    point.path.l2_label_ko,
    point.path.l3_label_en,
    point.path.l3_label_ko,
  ]
    .join(" ")
    .toLowerCase();
}

function applyFilters() {
  const query = els.search.value.trim().toLowerCase();
  const domain = els.domain.value;
  const l2 = els.l2.value;
  const l3 = els.l3.value;
  const hold = els.hold.value;

  state.filtered = state.points.filter((point) => {
    if (query && !pointText(point).includes(query)) return false;
    if (domain && point.path.l1_label_en !== domain) return false;
    if (l2 && point.path.l2_label_en !== l2) return false;
    if (l3 && `${point.path.l3_label_en} (${point.path.l3_label_ko})` !== l3) return false;
    if (hold === "hold" && !point.decision_required) return false;
    if (hold === "nonhold" && point.decision_required) return false;
    return true;
  });
  els.visibleCount.textContent = formatInteger(state.filtered.length);
  renderPlot();
}

function scaledCoordinates(point, bounds) {
  const { width, height, pad } = bounds;
  const x = pad + ((point.x + 1.2) / 2.4) * (width - pad * 2);
  const y = height - pad - ((point.y + 1.2) / 2.4) * (height - pad * 2);
  return { x, y };
}

function renderPlot() {
  const width = els.plot.clientWidth || 900;
  const height = els.plot.clientHeight || 620;
  const pad = 26;
  els.plot.setAttribute("viewBox", `0 0 ${width} ${height}`);
  els.plot.textContent = "";

  const axis = document.createElementNS("http://www.w3.org/2000/svg", "g");
  axis.setAttribute("opacity", "0.38");
  axis.innerHTML = `
    <line x1="${pad}" y1="${height / 2}" x2="${width - pad}" y2="${height / 2}" stroke="#cfd7e3" stroke-width="1" />
    <line x1="${width / 2}" y1="${pad}" x2="${width / 2}" y2="${height - pad}" stroke="#cfd7e3" stroke-width="1" />
  `;
  els.plot.appendChild(axis);

  const frag = document.createDocumentFragment();
  const bounds = { width, height, pad };
  state.filtered.forEach((point) => {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    const xy = scaledCoordinates(point, bounds);
    circle.setAttribute("cx", xy.x);
    circle.setAttribute("cy", xy.y);
    circle.setAttribute("r", radiusForPoint(point));
    circle.setAttribute("fill", fillForPoint(point));
    circle.setAttribute("opacity", opacityForPoint(point));
    circle.setAttribute(
      "class",
      `point ${point.decision_required ? "hold-ring" : ""} ${state.selectedId === point.id ? "selected" : ""}`,
    );
    circle.setAttribute("tabindex", "0");
    circle.setAttribute("role", "button");
    circle.setAttribute("aria-label", `${point.id} ${point.label_en}`);
    circle.addEventListener("click", () => selectPoint(point.id));
    circle.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") selectPoint(point.id);
    });
    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = `${point.id} · ${point.label_en}`;
    circle.appendChild(title);
    frag.appendChild(circle);
  });
  els.plot.appendChild(frag);
  if (state.systemMode === "attractor") renderVisibleCentroids(bounds);
}

function radiusForPoint(point) {
  if (state.systemMode === "hold") return point.decision_required ? "6.1" : "3.5";
  if (state.systemMode === "attractor") return state.selectedId === point.id ? "6.2" : "3.8";
  return point.decision_required ? "5.2" : "4.4";
}

function fillForPoint(point) {
  if (state.systemMode === "hold") return point.decision_required ? "#c45a14" : "#94a3b8";
  if (state.systemMode === "attractor") return point.path.l3_id === selectedPoint()?.path.l3_id ? "#111827" : "#94a3b8";
  return COLORS[point.path.l1_label_en] || "#64748b";
}

function opacityForPoint(point) {
  if (state.systemMode === "hold") return point.decision_required ? "0.92" : "0.25";
  if (state.systemMode === "attractor") return point.path.l3_id === selectedPoint()?.path.l3_id ? "0.82" : "0.22";
  return "0.78";
}

function selectedPoint() {
  return state.points.find((item) => item.id === state.selectedId);
}

function renderVisibleCentroids(bounds) {
  const visibleL3 = new Set(state.filtered.map((point) => point.path.l3_id));
  const selected = selectedPoint();
  const frag = document.createDocumentFragment();
  state.l3Centroids.forEach((centroid) => {
    if (!visibleL3.has(centroid.l3_id)) return;
    const xy = scaledCoordinates(centroid, bounds);
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.setAttribute("class", "centroid");
    group.setAttribute("opacity", selected?.path.l3_id === centroid.l3_id ? "1" : "0.38");
    group.innerHTML = `
      <circle cx="${xy.x}" cy="${xy.y}" r="${selected?.path.l3_id === centroid.l3_id ? 9 : 6}" fill="none" stroke="#111827" stroke-width="2" />
      <text x="${xy.x + 10}" y="${xy.y + 4}">${escapeHtml(centroid.label_en)}</text>
    `;
    frag.appendChild(group);
  });
  els.plot.appendChild(frag);
}

function selectPoint(id) {
  const point = state.points.find((item) => item.id === id);
  if (!point) return;
  state.selectedId = id;
  renderDetails(point);
  renderPlot();
}

function renderDetails(point) {
  els.emptyDetails.classList.add("hidden");
  els.cardDetails.classList.remove("hidden");
  const domainClass = classForDomain(point.path.l1_label_en);
  const refs = point.references
    .map((ref) => {
      const title = escapeHtml(ref.title || "Reference");
      const url = escapeHtml(ref.url || "#");
      const type = escapeHtml(ref.type || "reference");
      return `<a href="${url}" target="_blank" rel="noopener noreferrer">${title} ↗</a><small>${type}</small>`;
    })
    .join("");
  const reviewPath = point.semantic_review_path
    ? `<div class="path"><strong>Semantic review path</strong><br>${bilingual(point.semantic_review_path.l2_label_en, point.semantic_review_path.l2_label_ko)} › ${bilingual(point.semantic_review_path.l3_label_en, point.semantic_review_path.l3_label_ko)}</div>`
    : "";
  const systemsRead = systemInterpretation(point);
  els.cardDetails.innerHTML = `
    <div class="badge-row">
      <span class="badge">${escapeHtml(point.id)}</span>
      <span class="badge ${domainClass}">${bilingual(point.path.l1_label_en, point.path.l1_label_ko)}</span>
      ${point.decision_required ? '<span class="badge hold">HOLD</span>' : ""}
    </div>
    <h3>${bilingual(point.label_en, point.label_ko)}</h3>
    <div class="path">
      <strong>Taxonomy path</strong><br>
      ${bilingual(point.path.l1_label_en, point.path.l1_label_ko)} ›
      ${bilingual(point.path.l2_label_en, point.path.l2_label_ko)} ›
      ${bilingual(point.path.l3_label_en, point.path.l3_label_ko)}
    </div>
    ${reviewPath}
    <div class="systems-card">
      <strong>Complex systems reading</strong>
      <p>${systemsRead}</p>
    </div>
    <div class="definition">
      <strong>Risk definition</strong>
      <p>${escapeHtml(point.definition_en)}</p>
      ${point.definition_ko ? `<p>${escapeHtml(point.definition_ko)}</p>` : ""}
    </div>
    <div class="metrics">
      <div class="metric"><span>Severity</span><strong>${formatNumber(point.severity)}</strong></div>
      <div class="metric"><span>Probability</span><strong>${formatNumber(point.probability)}</strong></div>
      <div class="metric"><span>Impact</span><strong>${formatNumber(point.impact)}</strong></div>
    </div>
    <div class="references">
      <strong>References · ${point.references_count}</strong>
      ${refs || "<p>No reference metadata available.</p>"}
    </div>
  `;
}

function systemInterpretation(point) {
  const centroid = state.l3Centroids.get(point.path.l3_id);
  const distance = centroid ? Math.hypot(point.x - centroid.x, point.y - centroid.y) : null;
  const distanceLabel = distance === null ? "unknown" : distance.toFixed(3);
  if (point.decision_required) {
    return `This card sits in a boundary region. It is assigned operationally, but its HOLD marker indicates taxonomy uncertainty, overlapping L3 attractors, or evidence that requires human review. Distance to its current L3 centroid in this projection is ${distanceLabel}.`;
  }
  if (point.path.l1_label_en === "Physical AI") {
    return `This card belongs to the Physical AI subsystem. These cards tend to form more stable attractors because their mechanisms involve sensing, embodiment, physical action, or cyber-physical coupling. Distance to the current L3 centroid is ${distanceLabel}.`;
  }
  return `This card is interpreted as a local risk state near the ${point.path.l3_label_en} L3 attractor. Nearby cards may share mechanisms, evidence patterns, or transition pathways, but proximity should not be read as identical risk. Distance to the current L3 centroid is ${distanceLabel}.`;
}

function resetFilters() {
  els.search.value = "";
  els.domain.value = "";
  els.l2.value = "";
  els.l3.value = "";
  els.hold.value = "";
  applyFilters();
}

function installListeners() {
  [els.search, els.domain, els.l2, els.l3, els.hold].forEach((el) => {
    el.addEventListener("input", applyFilters);
    el.addEventListener("change", applyFilters);
  });
  els.reset.addEventListener("click", resetFilters);
  els.modeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.systemMode = button.dataset.systemMode;
      els.modeButtons.forEach((item) => item.classList.toggle("active", item === button));
      els.systemModeText.textContent = MODE_TEXT[state.systemMode];
      renderPlot();
    });
  });
  window.addEventListener("resize", () => renderPlot());
}

async function init() {
  const res = await fetch(DATA_URL);
  if (!res.ok) throw new Error(`Failed to load ${DATA_URL}`);
  state.payload = await res.json();
  state.points = state.payload.points;
  buildL3Centroids();
  populateStats(state.payload.metadata);
  populateFilters();
  installListeners();
  applyFilters();
  const firstGeneral = state.points.find((point) => point.path.l1_label_en === "General-purpose AI");
  selectPoint(firstGeneral?.id || state.points[0]?.id);
}

init().catch((error) => {
  console.error(error);
  els.plot.innerHTML = `<text x="24" y="42" fill="#c0392b">Failed to load risk space data.</text>`;
});
