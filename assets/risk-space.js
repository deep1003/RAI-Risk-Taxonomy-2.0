const DATA_URL = "./public/data/releases/v2.17.2/risk_space.json";
const NETWORK_URL = "./public/data/releases/v2.17.2/semantic_proximity_network.json";
const SVG_NS = "http://www.w3.org/2000/svg";

const state = {
  payload: null,
  network: null,
  points: [],
  filtered: [],
  filteredIds: new Set(),
  pointById: new Map(),
  nodeIndexById: new Map(),
  adjacency: [],
  selectedId: null,
  systemMode: "community",
  analysisView: "network",
  l3Centroids: new Map(),
  strengthCeiling: 1,
  affiliationCeiling: 1,
  pathStartId: null,
  pathNodeIds: new Set(),
  pathEdgeKeys: new Set(),
};

const els = {
  activeCards: document.querySelector("#activeCards"),
  visibleCount: document.querySelector("#visibleCount"),
  plot: document.querySelector("#riskPlot"),
  scaleDiagnostics: document.querySelector("#scaleDiagnostics"),
  degreePlot: document.querySelector("#degreePlot"),
  strengthPlot: document.querySelector("#strengthPlot"),
  search: document.querySelector("#searchInput"),
  domain: document.querySelector("#domainFilter"),
  l2: document.querySelector("#l2Filter"),
  l3: document.querySelector("#l3Filter"),
  hold: document.querySelector("#holdFilter"),
  reset: document.querySelector("#resetFilters"),
  modeButtons: document.querySelectorAll("[data-system-mode]"),
  viewButtons: document.querySelectorAll("[data-analysis-view]"),
  systemModeText: document.querySelector("#systemModeText"),
  viewCaption: document.querySelector("#viewCaption"),
  clusterLegend: document.querySelector("#clusterLegend"),
  emptyDetails: document.querySelector("#emptyDetails"),
  cardDetails: document.querySelector("#cardDetails"),
};

const MODE_TEXT = {
  community: "Color shows 50 EM communities; node size shows the number of meaningful L3 affiliations.",
  hold: "HOLD cards are pale gray; other nodes remain lightly colored by community.",
  attractor: "The selected card's released L3 family is highlighted.",
  path: "Select a start card and a target card to trace the shortest semantic-distance path.",
};

function formatInteger(value) {
  return Number(value).toLocaleString("en-US");
}

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "n/a";
  const number = Number(value);
  return number >= 1 ? number.toFixed(1) : number.toFixed(3);
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

function clusterColor(clusterId) {
  const hue = (clusterId * 137.508) % 360;
  const lightness = clusterId % 2 === 0 ? 43 : 54;
  return `hsl(${hue.toFixed(1)} 72% ${lightness}%)`;
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
  fillSelect(els.domain, uniqueSorted(state.points, (point) => point.path.l1_label_en), "All domains");
  fillSelect(els.l2, uniqueSorted(state.points, (point) => point.path.l2_label_en), "All L2 categories");
  fillSelect(
    els.l3,
    uniqueSorted(
      state.points,
      (point) => `${point.path.l3_label_en} (${point.path.l3_label_ko})`,
    ),
    "All L3 categories",
  );
}

function populateClusterLegend() {
  const largest = [...state.network.clusters]
    .sort((a, b) => b.size - a.size)
    .slice(0, 12);
  els.clusterLegend.innerHTML = largest
    .map(
      (cluster) => `
        <div>
          <span class="dot" style="background:${clusterColor(cluster.id)}"></span>
          ${escapeHtml(cluster.label_en)} · ${formatInteger(cluster.size)}
        </div>
      `,
    )
    .join("")
    + `<div>${state.network.clusters.length - largest.length} additional EM communities</div>`;
}

function buildIndexes() {
  const networkNodeById = new Map(
    state.network.nodes.map((node, index) => {
      state.nodeIndexById.set(node.id, index);
      return [node.id, node];
    }),
  );
  state.points = state.payload.points
    .filter((point) => networkNodeById.has(point.id))
    .map((point) => ({ ...point, network: networkNodeById.get(point.id) }));
  state.pointById = new Map(state.points.map((point) => [point.id, point]));
  state.adjacency = Array.from({ length: state.network.nodes.length }, () => []);
  state.network.edges.forEach(([source, target, similarity, distance]) => {
    state.adjacency[source].push({ node: target, similarity, distance });
    state.adjacency[target].push({ node: source, similarity, distance });
  });
  const strengths = state.network.nodes.map((node) => node.strength).sort((a, b) => a - b);
  state.strengthCeiling = strengths[Math.floor(strengths.length * 0.95)] || 1;
  const affiliationCounts = state.network.nodes
    .map((node) => node.l3_affiliation_count)
    .sort((a, b) => a - b);
  state.affiliationCeiling = affiliationCounts[
    Math.floor(affiliationCounts.length * 0.95)
  ] || 1;
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
    item.x += point.network.x;
    item.y += point.network.y;
    item.count += 1;
  });
  grouped.forEach((item) => {
    item.x /= item.count;
    item.y /= item.count;
  });
  state.l3Centroids = grouped;
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
  state.filteredIds = new Set(state.filtered.map((point) => point.id));
  els.visibleCount.textContent = formatInteger(state.filtered.length);
  clearPath();
  renderActiveView();
}

function scaledCoordinates(node, bounds) {
  const { width, height, pad } = bounds;
  const x = pad + ((node.x + 1.05) / 2.1) * (width - pad * 2);
  const y = height - pad - ((node.y + 1.05) / 2.1) * (height - pad * 2);
  return { x, y };
}

function edgeKey(source, target) {
  return source < target ? `${source}:${target}` : `${target}:${source}`;
}

function renderPlot() {
  const width = els.plot.clientWidth || 900;
  const height = els.plot.clientHeight || 620;
  const pad = 34;
  const bounds = { width, height, pad };
  els.plot.setAttribute("viewBox", `0 0 ${width} ${height}`);
  els.plot.textContent = "";

  const edgeFragment = document.createDocumentFragment();
  state.network.edges.forEach(([sourceIndex, targetIndex, similarity]) => {
    const sourceNode = state.network.nodes[sourceIndex];
    const targetNode = state.network.nodes[targetIndex];
    if (!state.filteredIds.has(sourceNode.id) || !state.filteredIds.has(targetNode.id)) return;
    const source = scaledCoordinates(sourceNode, bounds);
    const target = scaledCoordinates(targetNode, bounds);
    const line = document.createElementNS(SVG_NS, "line");
    const isPath = state.pathEdgeKeys.has(edgeKey(sourceIndex, targetIndex));
    const isIncident = state.selectedId
      && (sourceNode.id === state.selectedId || targetNode.id === state.selectedId);
    line.setAttribute("x1", source.x);
    line.setAttribute("y1", source.y);
    line.setAttribute("x2", target.x);
    line.setAttribute("y2", target.y);
    line.setAttribute(
      "class",
      `network-edge${isPath ? " path-edge" : ""}${isIncident ? " selected-edge" : ""}`,
    );
    if (!isPath) {
      line.setAttribute("opacity", isIncident ? "0.62" : String(0.045 + similarity * 0.09));
      line.setAttribute("stroke-width", isIncident ? "1.5" : String(0.35 + similarity * 0.45));
    }
    edgeFragment.appendChild(line);
  });
  els.plot.appendChild(edgeFragment);

  const nodeFragment = document.createDocumentFragment();
  state.filtered.forEach((point) => {
    const circle = document.createElementNS(SVG_NS, "circle");
    const xy = scaledCoordinates(point.network, bounds);
    circle.setAttribute("cx", xy.x);
    circle.setAttribute("cy", xy.y);
    circle.setAttribute("r", radiusForPoint(point));
    circle.setAttribute("fill", fillForPoint(point));
    circle.setAttribute("opacity", opacityForPoint(point));
    circle.setAttribute(
      "class",
      `point ${state.selectedId === point.id ? "selected" : ""}`,
    );
    circle.setAttribute("tabindex", "0");
    circle.setAttribute("role", "button");
    circle.setAttribute(
      "aria-label",
      `${point.id} ${point.label_en}; ${point.network.l3_affiliation_count} L3 affiliations; degree ${point.network.degree}; strength ${point.network.strength.toFixed(2)}`,
    );
    circle.addEventListener("click", () => activatePoint(point.id));
    circle.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activatePoint(point.id);
      }
    });
    const title = document.createElementNS(SVG_NS, "title");
    title.textContent = `${point.id} · ${point.label_en} · ${point.network.l3_affiliation_count} L3 affiliations`;
    circle.appendChild(title);
    nodeFragment.appendChild(circle);
  });
  els.plot.appendChild(nodeFragment);

  if (state.systemMode === "community") renderCommunityLabels(bounds);
  if (state.systemMode === "attractor") renderVisibleL3Labels(bounds);
}

function radiusForPoint(point) {
  const ratio = Math.min(
    1,
    point.network.l3_affiliation_count / state.affiliationCeiling,
  );
  const base = 2.8 + Math.sqrt(ratio) * 6.4;
  return state.selectedId === point.id ? base + 1.5 : base;
}

function fillForPoint(point) {
  if (point.decision_required) return "#cbd5e1";
  if (state.systemMode === "attractor") {
    return point.path.l3_id === selectedPoint()?.path.l3_id ? "#111827" : "#d8dee8";
  }
  return clusterColor(point.network.cluster);
}

function opacityForPoint(point) {
  if (state.pathNodeIds.has(point.id)) return "1";
  if (state.systemMode === "hold") return point.decision_required ? "0.9" : "0.28";
  if (state.systemMode === "attractor") {
    return point.path.l3_id === selectedPoint()?.path.l3_id ? "0.9" : "0.2";
  }
  return point.decision_required ? "0.66" : "0.84";
}

function selectedPoint() {
  return state.pointById.get(state.selectedId);
}

function renderCommunityLabels(bounds) {
  const visibleClusters = new Set(state.filtered.map((point) => point.network.cluster));
  const labeledClusters = new Set(
    [...state.network.clusters]
      .filter((cluster) => visibleClusters.has(cluster.id))
      .sort((a, b) => b.size - a.size)
      .slice(0, 16)
      .map((cluster) => cluster.id),
  );
  const fragment = document.createDocumentFragment();
  state.network.clusters.forEach((cluster) => {
    if (!labeledClusters.has(cluster.id)) return;
    const xy = scaledCoordinates(cluster, bounds);
    const group = document.createElementNS(SVG_NS, "g");
    group.setAttribute("class", "community-label");
    group.innerHTML = `
      <circle cx="${xy.x}" cy="${xy.y}" r="6" stroke="${clusterColor(cluster.id)}" />
      <text x="${xy.x + 10}" y="${xy.y + 4}">${escapeHtml(cluster.label_en)}</text>
    `;
    fragment.appendChild(group);
  });
  els.plot.appendChild(fragment);
}

function renderVisibleL3Labels(bounds) {
  const visibleL3 = new Set(state.filtered.map((point) => point.path.l3_id));
  const selected = selectedPoint();
  const fragment = document.createDocumentFragment();
  state.l3Centroids.forEach((centroid) => {
    if (!visibleL3.has(centroid.l3_id)) return;
    const xy = scaledCoordinates(centroid, bounds);
    const group = document.createElementNS(SVG_NS, "g");
    group.setAttribute("class", "centroid");
    group.setAttribute("opacity", selected?.path.l3_id === centroid.l3_id ? "1" : "0.35");
    group.innerHTML = `
      <circle cx="${xy.x}" cy="${xy.y}" r="${selected?.path.l3_id === centroid.l3_id ? 9 : 6}" fill="none" stroke="#111827" stroke-width="2" />
      <text x="${xy.x + 10}" y="${xy.y + 4}">${escapeHtml(centroid.label_en)}</text>
    `;
    fragment.appendChild(group);
  });
  els.plot.appendChild(fragment);
}

function activatePoint(id) {
  if (state.systemMode !== "path") {
    selectPoint(id);
    return;
  }
  if (!state.pathStartId || state.pathNodeIds.size > 1) {
    state.pathStartId = id;
    state.pathNodeIds = new Set([id]);
    state.pathEdgeKeys = new Set();
    els.systemModeText.textContent = `Start: ${id}. Select a target card.`;
    selectPoint(id);
    return;
  }
  const path = shortestPath(state.pathStartId, id);
  if (!path.length) {
    els.systemModeText.textContent = "No path exists within the currently visible network.";
    return;
  }
  state.pathNodeIds = new Set(path.map((nodeIndex) => state.network.nodes[nodeIndex].id));
  state.pathEdgeKeys = new Set(
    path.slice(1).map((nodeIndex, index) => edgeKey(path[index], nodeIndex)),
  );
  els.systemModeText.textContent = `Shortest semantic-distance path: ${path.length - 1} links.`;
  selectPoint(id);
}

function shortestPath(sourceId, targetId) {
  const source = state.nodeIndexById.get(sourceId);
  const target = state.nodeIndexById.get(targetId);
  if (source === undefined || target === undefined) return [];
  const nodeCount = state.network.nodes.length;
  const distance = Array(nodeCount).fill(Infinity);
  const previous = Array(nodeCount).fill(-1);
  const visited = Array(nodeCount).fill(false);
  const queue = [[0, source]];
  distance[source] = 0;

  while (queue.length) {
    queue.sort((a, b) => b[0] - a[0]);
    const [currentDistance, node] = queue.pop();
    if (visited[node]) continue;
    visited[node] = true;
    if (node === target) break;
    for (const edge of state.adjacency[node]) {
      const neighborId = state.network.nodes[edge.node].id;
      if (!state.filteredIds.has(neighborId)) continue;
      const candidate = currentDistance + Math.max(edge.distance, 0.0001);
      if (candidate < distance[edge.node]) {
        distance[edge.node] = candidate;
        previous[edge.node] = node;
        queue.push([candidate, edge.node]);
      }
    }
  }
  if (!Number.isFinite(distance[target])) return [];
  const path = [];
  for (let node = target; node !== -1; node = previous[node]) path.push(node);
  return path.reverse();
}

function clearPath() {
  state.pathStartId = null;
  state.pathNodeIds = new Set();
  state.pathEdgeKeys = new Set();
  if (state.systemMode === "path") els.systemModeText.textContent = MODE_TEXT.path;
}

function selectPoint(id) {
  const point = state.pointById.get(id);
  if (!point) return;
  state.selectedId = id;
  renderDetails(point);
  if (state.analysisView === "network") renderPlot();
}

function renderDetails(point) {
  els.emptyDetails.classList.add("hidden");
  els.cardDetails.classList.remove("hidden");
  const domainClass = classForDomain(point.path.l1_label_en);
  const cluster = state.network.clusters[point.network.cluster];
  const affiliations = point.network.l3_affiliations
    .map((item) => `${escapeHtml(item.label_en)} (${(item.responsibility * 100).toFixed(1)}%)`)
    .join(" · ");
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
      <strong>Network position</strong>
      <p>${escapeHtml(cluster.label_en)}. ${point.network.l3_affiliation_count} meaningful L3 affiliations; ${point.network.degree} incident L4 links; weighted degree ${point.network.strength.toFixed(2)}.</p>
      <p>${affiliations}</p>
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

function ccdf(values) {
  const sorted = values.filter((value) => value > 0).sort((a, b) => a - b);
  const result = [];
  for (let index = 0; index < sorted.length; index += 1) {
    if (index > 0 && sorted[index] === sorted[index - 1]) continue;
    result.push({ x: sorted[index], y: (sorted.length - index) / sorted.length });
  }
  return result;
}

function logScale(value, minimum, maximum, start, end) {
  const low = Math.log10(minimum);
  const high = Math.log10(maximum);
  if (high === low) return (start + end) / 2;
  return start + ((Math.log10(value) - low) / (high - low)) * (end - start);
}

function logTicks(minimum, maximum, count = 5) {
  const low = Math.log10(minimum);
  const high = Math.log10(maximum);
  return Array.from({ length: count }, (_, index) => 10 ** (low + ((high - low) * index) / (count - 1)));
}

function tickLabel(value) {
  if (value >= 100) return Math.round(value).toString();
  if (value >= 10) return value.toFixed(0);
  if (value >= 1) return value.toFixed(1).replace(".0", "");
  if (value < 0.01) return value.toExponential(0);
  return value.toFixed(2);
}

function renderCcdf(svg, points, metric, title, xLabel) {
  const width = svg.clientWidth || 430;
  const height = svg.clientHeight || 460;
  const margin = { top: 42, right: 24, bottom: 56, left: 62 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const values = points.map((point) => point.network[metric]);
  const series = ccdf(values);
  if (!series.length) {
    svg.innerHTML = `<text x="24" y="42" class="diagnostic-label">No visible network values.</text>`;
    return;
  }
  const xMin = series[0].x;
  const xMax = series.at(-1).x;
  const yMin = Math.max(1 / values.length, 0.0001);
  const yMax = 1;
  const xAt = (value) => logScale(value, xMin, xMax, margin.left, margin.left + plotWidth);
  const yAt = (value) => logScale(value, yMin, yMax, margin.top + plotHeight, margin.top);
  const path = series
    .map((point, index) => `${index ? "L" : "M"}${xAt(point.x).toFixed(2)},${yAt(point.y).toFixed(2)}`)
    .join(" ");
  const xTicks = logTicks(xMin, xMax);
  const yTicks = logTicks(yMin, yMax);
  const leaders = [...points]
    .sort((a, b) => b.network[metric] - a.network[metric])
    .slice(0, 5);
  const ccdfAt = (value) => (
    values.filter((candidate) => candidate >= value).length / values.length
  );
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.innerHTML = `
    <text x="${margin.left}" y="24" class="diagnostic-title">${escapeHtml(title)}</text>
    ${xTicks.map((tick) => `
      <line x1="${xAt(tick)}" y1="${margin.top}" x2="${xAt(tick)}" y2="${margin.top + plotHeight}" class="diagnostic-grid" />
      <text x="${xAt(tick)}" y="${margin.top + plotHeight + 20}" text-anchor="middle" class="diagnostic-label">${tickLabel(tick)}</text>
    `).join("")}
    ${yTicks.map((tick) => `
      <line x1="${margin.left}" y1="${yAt(tick)}" x2="${margin.left + plotWidth}" y2="${yAt(tick)}" class="diagnostic-grid" />
      <text x="${margin.left - 9}" y="${yAt(tick) + 4}" text-anchor="end" class="diagnostic-label">${tickLabel(tick)}</text>
    `).join("")}
    <line x1="${margin.left}" y1="${margin.top + plotHeight}" x2="${margin.left + plotWidth}" y2="${margin.top + plotHeight}" class="diagnostic-axis" />
    <line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${margin.top + plotHeight}" class="diagnostic-axis" />
    <path d="${path}" class="diagnostic-series" />
    ${leaders.map((point, index) => {
      const value = point.network[metric];
      const x = xAt(value);
      const y = yAt(ccdfAt(value));
      const labelX = margin.left + plotWidth - 8;
      const labelY = margin.top + 18 + index * 17;
      return `
        <line x1="${x}" y1="${y}" x2="${labelX - 8}" y2="${labelY - 4}" class="diagnostic-leader" />
        <circle cx="${x}" cy="${y}" r="5.5" fill="${point.decision_required ? "#cbd5e1" : clusterColor(point.network.cluster)}" stroke="#111827" stroke-width="1.2" class="diagnostic-node" data-risk-id="${escapeHtml(point.id)}" />
        <text x="${labelX}" y="${labelY}" text-anchor="end" class="diagnostic-label diagnostic-node-label" data-risk-id="${escapeHtml(point.id)}">${index + 1}. ${escapeHtml(point.id)}</text>
      `;
    }).join("")}
    <text x="${margin.left + plotWidth / 2}" y="${height - 12}" text-anchor="middle" class="diagnostic-label">${escapeHtml(xLabel)} · log scale</text>
    <text x="16" y="${margin.top + plotHeight / 2}" text-anchor="middle" transform="rotate(-90 16 ${margin.top + plotHeight / 2})" class="diagnostic-label">P(X ≥ x) · log scale</text>
  `;
  svg.querySelectorAll("[data-risk-id]").forEach((element) => {
    element.addEventListener("click", () => {
      state.analysisView = "network";
      els.viewButtons.forEach((button) => {
        button.classList.toggle("active", button.dataset.analysisView === "network");
      });
      selectPoint(element.dataset.riskId);
      renderActiveView();
    });
  });
}

function renderScaleDiagnostics() {
  renderCcdf(
    els.degreePlot,
    state.filtered,
    "degree",
    "Empirical degree distribution",
    "Incident links",
  );
  renderCcdf(
    els.strengthPlot,
    state.filtered,
    "strength",
    "Empirical weighted-degree distribution",
    "Sum of semantic-similarity weights",
  );
}

function renderActiveView() {
  const showNetwork = state.analysisView === "network";
  els.plot.classList.toggle("hidden", !showNetwork);
  els.scaleDiagnostics.classList.toggle("hidden", showNetwork);
  if (showNetwork) {
    els.viewCaption.textContent = "Each L4 is linked to L3 families through EM responsibilities. L4 edge weight combines L3-profile similarity (0.65) and direct semantic similarity (0.35). Paths show semantic proximity, not observed causal propagation.";
    renderPlot();
  } else {
    els.viewCaption.textContent = "Log-log complementary cumulative distributions diagnose heavy-tailed connectivity and weighted strength. Click a labeled high-degree risk to inspect its network. Apparent linearity alone does not establish a power law.";
    requestAnimationFrame(renderScaleDiagnostics);
  }
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
  [els.search, els.domain, els.l2, els.l3, els.hold].forEach((element) => {
    element.addEventListener("input", applyFilters);
    element.addEventListener("change", applyFilters);
  });
  els.reset.addEventListener("click", resetFilters);
  els.modeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.systemMode = button.dataset.systemMode;
      clearPath();
      els.modeButtons.forEach((item) => item.classList.toggle("active", item === button));
      els.systemModeText.textContent = MODE_TEXT[state.systemMode];
      if (state.analysisView === "network") renderPlot();
    });
  });
  els.viewButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.analysisView = button.dataset.analysisView;
      els.viewButtons.forEach((item) => item.classList.toggle("active", item === button));
      renderActiveView();
    });
  });
  window.addEventListener("resize", renderActiveView);
}

async function init() {
  const [payloadResponse, networkResponse] = await Promise.all([
    fetch(DATA_URL),
    fetch(NETWORK_URL),
  ]);
  if (!payloadResponse.ok) throw new Error(`Failed to load ${DATA_URL}`);
  if (!networkResponse.ok) throw new Error(`Failed to load ${NETWORK_URL}`);
  state.payload = await payloadResponse.json();
  state.network = await networkResponse.json();
  buildIndexes();
  buildL3Centroids();
  els.activeCards.textContent = formatInteger(state.payload.metadata.active_cards);
  populateFilters();
  populateClusterLegend();
  installListeners();
  if (new URLSearchParams(window.location.search).get("view") === "scale") {
    state.analysisView = "scale";
    els.viewButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.analysisView === "scale");
    });
  }
  applyFilters();
  const firstGeneral = state.points.find(
    (point) => point.path.l1_label_en === "General-purpose AI",
  );
  selectPoint(firstGeneral?.id || state.points[0]?.id);
}

init().catch((error) => {
  console.error(error);
  els.plot.innerHTML = '<text x="24" y="42" fill="#c0392b">Failed to load semantic proximity network.</text>';
});
