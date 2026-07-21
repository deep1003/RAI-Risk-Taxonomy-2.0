const DATA_ROOT = "public/data/releases/v2.4.0";
const PAGE_SIZE = 36;

const state = {
  query: "",
  status: "all",
  l1: "all",
  l2: "all",
  l3: "all",
  page: 1,
  cards: [],
  nodes: [],
  manifest: null,
};

const ui = {};
const nodeById = new Map();
const childrenByParent = new Map();
const cardPath = new Map();

const ASSIGNMENT_META = {
  decision_required: { label: "HOLD" },
};

const DOMAIN_COLORS = {
  "RAI1-G": "#3867d6",
  "RAI1-A": "#148f77",
  "RAI1-P": "#c0392b",
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  bindUi();
  bindEvents();
  try {
    const [hierarchy, cards, manifest] = await Promise.all([
      fetchJson(`${DATA_ROOT}/hierarchy.json`),
      fetchJson(`${DATA_ROOT}/cards.json`),
      fetchJson(`${DATA_ROOT}/manifest.json`),
    ]);
    state.nodes = hierarchy.nodes;
    state.cards = cards.cards;
    state.manifest = manifest;
    indexHierarchy();
    populateFilters();
    renderStats();
    renderTree();
    render();
  } catch (error) {
    ui.cardsGrid.innerHTML = `<div class="empty-state"><strong>데이터를 불러오지 못했습니다.</strong><span>이 HTML을 웹 서버로 열어 주세요. (${escapeHtml(error.message)})</span></div>`;
    ui.cardsGrid.setAttribute("aria-busy", "false");
  }
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function bindUi() {
  ui.search = document.querySelector("#search-input");
  ui.status = document.querySelector("#status-filter");
  ui.l1 = document.querySelector("#l1-filter");
  ui.l2 = document.querySelector("#l2-filter");
  ui.l3 = document.querySelector("#l3-filter");
  ui.clear = document.querySelector("#clear-filters");
  ui.cardsGrid = document.querySelector("#cards-grid");
  ui.resultCount = document.querySelector("#result-count");
  ui.pagination = document.querySelector("#pagination");
  ui.tree = document.querySelector("#taxonomy-tree");
  ui.activeFilter = document.querySelector("#active-filter");
  ui.dialog = document.querySelector("#card-dialog");
  ui.dialogContent = document.querySelector("#dialog-content");
}

function bindEvents() {
  let timer;
  ui.search.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => updateState({ query: ui.search.value.trim(), page: 1 }), 120);
  });
  ui.status.addEventListener("change", () => updateState({ status: ui.status.value, page: 1 }));
  ui.l1.addEventListener("change", () => {
    state.l1 = ui.l1.value;
    state.l2 = "all";
    state.l3 = "all";
    refreshDependentFilters();
    updateState({ page: 1 });
  });
  ui.l2.addEventListener("change", () => {
    state.l2 = ui.l2.value;
    state.l3 = "all";
    refreshDependentFilters();
    updateState({ page: 1 });
  });
  ui.l3.addEventListener("change", () => updateState({ l3: ui.l3.value, page: 1 }));
  ui.clear.addEventListener("click", clearFilters);
  document.querySelectorAll(".domain-pill").forEach((button) => {
    button.addEventListener("click", () => {
      clearNavActive();
      button.classList.add("active");
      const domain = button.dataset.domain;
      const status = button.dataset.status;
      state.l1 = domain || "all";
      state.l2 = "all";
      state.l3 = "all";
      state.status = status || "all";
      state.page = 1;
      syncControls();
      refreshDependentFilters();
      render();
    });
  });
  document.querySelector(".dialog-close").addEventListener("click", () => ui.dialog.close());
  ui.dialog.addEventListener("click", (event) => {
    if (event.target === ui.dialog) ui.dialog.close();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && document.activeElement?.tagName !== "INPUT") {
      event.preventDefault();
      ui.search.focus();
    }
  });
}

function indexHierarchy() {
  state.nodes.forEach((node) => {
    nodeById.set(node.node_id, node);
    const parent = node.parent_id || "ROOT";
    if (!childrenByParent.has(parent)) childrenByParent.set(parent, []);
    childrenByParent.get(parent).push(node);
  });
  childrenByParent.forEach((nodes) => nodes.sort((a, b) => a.sequence - b.sequence));
  state.cards.forEach((card) => {
    if (!card.primary_l3_id) {
      cardPath.set(card.l4_id, { l1: null, l2: null, l3: null, nodes: [] });
      return;
    }
    const l3 = nodeById.get(card.primary_l3_id);
    const l2 = nodeById.get(l3?.parent_id);
    const l1 = nodeById.get(l2?.parent_id);
    cardPath.set(card.l4_id, { l1: l1?.node_id, l2: l2?.node_id, l3: l3?.node_id, nodes: [l1, l2, l3].filter(Boolean) });
  });
}

function populateFilters() {
  const l1Nodes = state.nodes.filter((node) => node.level === 1);
  fillSelect(ui.l1, l1Nodes, "모든 L1");
  refreshDependentFilters();
}

function refreshDependentFilters() {
  const l2Nodes = state.nodes.filter((node) => node.level === 2 && (state.l1 === "all" || node.parent_id === state.l1));
  fillSelect(ui.l2, l2Nodes, "모든 L2", state.l2);
  if (![...ui.l2.options].some((option) => option.value === state.l2)) state.l2 = "all";
  const allowedL2 = new Set(l2Nodes.map((node) => node.node_id));
  const l3Nodes = state.nodes.filter((node) => node.level === 3 && (state.l2 !== "all" ? node.parent_id === state.l2 : allowedL2.has(node.parent_id)));
  fillSelect(ui.l3, l3Nodes, "모든 L3", state.l3);
  if (![...ui.l3.options].some((option) => option.value === state.l3)) state.l3 = "all";
  syncControls();
}

function fillSelect(select, nodes, allLabel, selected = "all") {
  select.innerHTML = `<option value="all">${allLabel}</option>${nodes.map((node) => `<option value="${node.node_id}">${escapeHtml(node.label_en)}</option>`).join("")}`;
  select.value = selected;
}

function renderStats() {
  const counts = state.manifest.counts;
  document.querySelector("#stat-total").textContent = counts.l4.toLocaleString();
  document.querySelector("#stat-locked").textContent = (counts.physical_total ?? counts.physical_locked).toLocaleString();
  document.querySelector("#stat-proposed").textContent = counts.classified.toLocaleString();
  document.querySelector("#stat-needs").textContent = counts.decision_required.toLocaleString();
}

function renderTree() {
  const counts = countCardsByNode();
  const domains = state.nodes.filter((node) => node.level === 1);
  const hierarchy = domains.map((domain) => {
    const l2Nodes = childrenByParent.get(domain.node_id) || [];
    return `<details class="tree-domain" open style="--domain-color:${DOMAIN_COLORS[domain.node_id]}">
      <summary><span class="tree-dot"></span>${escapeHtml(domain.label_en)}<span class="tree-count">${counts.get(domain.node_id) || 0}</span></summary>
      <div class="tree-children">
        ${l2Nodes.map((l2) => `<button class="tree-node" type="button" data-node="${l2.node_id}"><code>${l2.node_id.replace("RAI2-", "")}</code><span>${escapeHtml(l2.label_en)}</span><b>${counts.get(l2.node_id) || 0}</b></button>
          <div class="tree-children">${(childrenByParent.get(l2.node_id) || []).map((l3) => `<button class="tree-node" type="button" data-node="${l3.node_id}"><code>${l3.node_id.replace("RAI3-", "")}</code><span>${escapeHtml(l3.label_en)}</span><b>${counts.get(l3.node_id) || 0}</b></button>`).join("")}</div>`).join("")}
      </div>
    </details>`;
  }).join("");
  ui.tree.innerHTML = hierarchy;
  ui.tree.querySelectorAll("[data-node]").forEach((button) => button.addEventListener("click", () => selectTreeNode(button.dataset.node)));
}

function countCardsByNode() {
  const counts = new Map();
  state.cards.forEach((card) => {
    const path = cardPath.get(card.l4_id);
    [path.l1, path.l2, path.l3].filter(Boolean).forEach((id) => counts.set(id, (counts.get(id) || 0) + 1));
  });
  return counts;
}

function selectTreeNode(nodeId) {
  const node = nodeById.get(nodeId);
  if (!node) return;
  if (node.level === 2) {
    state.l1 = node.parent_id;
    state.l2 = node.node_id;
    state.l3 = "all";
  } else if (node.level === 3) {
    const parent = nodeById.get(node.parent_id);
    state.l1 = parent.parent_id;
    state.l2 = parent.node_id;
    state.l3 = node.node_id;
  }
  state.status = "all";
  state.page = 1;
  clearNavActive();
  refreshDependentFilters();
  render();
  document.querySelector("#risk-results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function updateState(patch) {
  Object.assign(state, patch);
  syncControls();
  render();
}

function syncControls() {
  ui.search.value = state.query;
  ui.status.value = state.status;
  ui.l1.value = state.l1;
  ui.l2.value = state.l2;
  ui.l3.value = state.l3;
}

function clearFilters() {
  Object.assign(state, { query: "", status: "all", l1: "all", l2: "all", l3: "all", page: 1 });
  clearNavActive();
  document.querySelector('[data-domain="all"]').classList.add("active");
  refreshDependentFilters();
  syncControls();
  render();
}

function clearNavActive() {
  document.querySelectorAll(".domain-pill").forEach((button) => button.classList.remove("active"));
}

function filteredCards() {
  const query = state.query.toLocaleLowerCase();
  return state.cards.filter((card) => {
    const path = cardPath.get(card.l4_id);
    const matchesQuery = !query || [card.l4_id, card.label_en, card.label_ko, card.definition_en, card.definition_ko]
      .filter(Boolean).join(" ").toLocaleLowerCase().includes(query);
    return matchesQuery
      && (state.status === "all" || (state.status === "decision_required" && card.decision_required))
      && (state.l1 === "all" || path.l1 === state.l1)
      && (state.l2 === "all" || path.l2 === state.l2)
      && (state.l3 === "all" || path.l3 === state.l3);
  });
}

function render() {
  const cards = filteredCards();
  const pageCount = Math.max(1, Math.ceil(cards.length / PAGE_SIZE));
  state.page = Math.min(state.page, pageCount);
  const start = (state.page - 1) * PAGE_SIZE;
  const pageCards = cards.slice(start, start + PAGE_SIZE);
  ui.resultCount.textContent = cards.length.toLocaleString();
  ui.cardsGrid.setAttribute("aria-busy", "false");
  ui.cardsGrid.innerHTML = pageCards.length ? pageCards.map(cardTemplate).join("") : `<div class="empty-state"><strong>조건에 맞는 리스크가 없습니다.</strong><span>검색어 또는 필터를 변경해 주세요.</span></div>`;
  ui.cardsGrid.querySelectorAll(".risk-card").forEach((card) => {
    card.addEventListener("click", () => openCard(card.dataset.id));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openCard(card.dataset.id); }
    });
  });
  renderPagination(pageCount);
  renderActiveFilter();
  syncTreeActive();
}

function cardTemplate(card) {
  const path = cardPath.get(card.l4_id);
  const pathLabel = path.nodes.length ? path.nodes.map((node) => node.label_en).join(" › ") : "L3 not assigned";
  return `<article class="risk-card" role="button" tabindex="0" data-id="${card.l4_id}" style="--card-accent:#3867d6" aria-label="${escapeHtml(card.l4_id)} ${escapeHtml(card.label_en)} 상세 보기">
    <div class="risk-card__top"><span class="risk-id">${card.l4_id}</span>${card.decision_required ? '<span class="status-badge status--decision">HOLD</span>' : ""}</div>
    <h3>${escapeHtml(card.label_en)}</h3>
    ${card.label_ko ? `<p class="risk-card__ko">${escapeHtml(card.label_ko)}</p>` : ""}
    <p class="risk-card__definition">${escapeHtml(card.definition_en || "정의 정보 없음")}</p>
    <div class="risk-card__bottom">
      <span class="breadcrumb">${escapeHtml(pathLabel)}</span>
      ${card.severity_1to5 != null ? `<span class="metric"><small>SEVERITY</small><strong>${formatMetric(card.severity_1to5)}</strong></span>` : ""}
    </div>
  </article>`;
}

function renderPagination(pageCount) {
  if (pageCount <= 1) { ui.pagination.innerHTML = ""; return; }
  const pages = paginationRange(state.page, pageCount);
  ui.pagination.innerHTML = `<button type="button" data-page="${state.page - 1}" ${state.page === 1 ? "disabled" : ""} aria-label="이전 페이지">‹</button>
    ${pages.map((page) => page === "…" ? `<span>…</span>` : `<button type="button" data-page="${page}" class="${page === state.page ? "active" : ""}" ${page === state.page ? 'aria-current="page"' : ""}>${page}</button>`).join("")}
    <button type="button" data-page="${state.page + 1}" ${state.page === pageCount ? "disabled" : ""} aria-label="다음 페이지">›</button>`;
  ui.pagination.querySelectorAll("button:not(:disabled)").forEach((button) => button.addEventListener("click", () => {
    state.page = Number(button.dataset.page);
    render();
    document.querySelector("#risk-results").scrollIntoView({ behavior: "smooth", block: "start" });
  }));
}

function paginationRange(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1);
  if (current <= 4) return [1, 2, 3, 4, 5, "…", total];
  if (current >= total - 3) return [1, "…", total - 4, total - 3, total - 2, total - 1, total];
  return [1, "…", current - 1, current, current + 1, "…", total];
}

function renderActiveFilter() {
  const labels = [];
  if (state.query) labels.push(`검색 “${state.query}”`);
  if (state.status !== "all") labels.push(ASSIGNMENT_META[state.status].label);
  [state.l1, state.l2, state.l3].filter((value) => value !== "all").forEach((id) => labels.push(`${id} ${nodeById.get(id)?.label_en || ""}`));
  ui.activeFilter.hidden = labels.length === 0;
  ui.activeFilter.textContent = labels.length ? `적용 필터 · ${labels.join(" · ")}` : "";
}

function syncTreeActive() {
  ui.tree.querySelectorAll(".tree-node").forEach((button) => button.classList.toggle("active", [state.l2, state.l3].includes(button.dataset.node)));
}

function openCard(l4Id) {
  const card = state.cards.find((item) => item.l4_id === l4Id);
  if (!card) return;
  const path = cardPath.get(card.l4_id);
  const references = card.references || [];
  const tags = card.three_h_one_r || [];
  ui.dialogContent.innerHTML = `<div class="dialog-body">
    <div><span class="risk-id">${card.l4_id}</span>${card.decision_required ? ' <span class="status-badge status--decision">HOLD</span>' : ""}</div>
    <h2>${escapeHtml(card.label_en)}</h2>
    ${card.label_ko ? `<p class="dialog-ko">${escapeHtml(card.label_ko)}</p>` : ""}
    <div class="dialog-path">${path.nodes.length ? path.nodes.map((node) => `${node.node_id} ${escapeHtml(node.label_en)}`).join(" › ") : "L3 not assigned"}</div>
    <section class="dialog-section"><h3>Risk definition</h3><p>${escapeHtml(card.definition_en || "정의 정보 없음")}</p></section>
    ${card.definition_ko ? `<section class="dialog-section"><h3>한국어 정의</h3><p>${escapeHtml(card.definition_ko)}</p></section>` : ""}
    <div class="dialog-metrics">
      <div><span>Severity</span><strong>${formatMetric(card.severity_1to5)}</strong></div>
      <div><span>Probability</span><strong>${formatMetric(card.probability_0to1)}</strong></div>
      <div><span>Impact</span><strong>${formatMetric(card.impact_score)}</strong></div>
    </div>
    ${tags.length ? `<section class="dialog-section"><h3>3H / Role</h3><div class="tag-row">${tags.map((tag) => `<span class="axis-tag">${escapeHtml(tag.axis_code)} ${escapeHtml(tag.axis_name)} [${escapeHtml(tag.priority_code)}]</span>`).join("")}</div></section>` : ""}
    <section class="dialog-section"><h3>References · ${references.length}</h3>${references.length ? `<ul class="reference-list">${references.map(referenceTemplate).join("")}</ul>` : `<p>등록된 근거 링크가 없습니다.</p>`}</section>
  </div>`;
  ui.dialog.showModal();
}

function referenceTemplate(reference) {
  const title = escapeHtml(reference.title || "Untitled reference");
  const source = escapeHtml(reference.source_system || "source");
  const type = escapeHtml(reference.type || "reference");
  const justification = reference.justification ? `<p class="reference-justification">${escapeHtml(reference.justification)}</p>` : "";
  if (!reference.url) return `<li>${justification}<span>${title}</span><small>${source} · ${type}</small></li>`;
  return `<li>${justification}<a href="${escapeAttribute(reference.url)}" target="_blank" rel="noopener noreferrer">${title} ↗</a><small>${source} · ${type}</small></li>`;
}

function formatMetric(value) {
  if (value == null || Number.isNaN(Number(value))) return "–";
  const numeric = Number(value);
  return numeric.toFixed(Math.abs(numeric) < 1 ? 3 : 1);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}

function escapeAttribute(value) {
  const url = String(value || "").trim();
  if (!/^https?:\/\//i.test(url)) return "#";
  return escapeHtml(url);
}
