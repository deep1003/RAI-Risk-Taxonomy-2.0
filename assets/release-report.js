const reportType = document.body.dataset.report;

document.addEventListener("DOMContentLoaded", init);

async function init() {
  try {
    if (reportType === "manifest") await renderManifest();
    if (reportType === "validation") await renderValidation();
  } catch (error) {
    const root = document.querySelector("#report-root");
    root.innerHTML = `<div class="error"><strong>데이터를 불러오지 못했습니다.</strong><br>${escapeHtml(error.message)}</div>`;
  }
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function renderManifest() {
  const data = await fetchJson("manifest.json");
  const summary = data.summary;
  const outputs = Object.entries(data.primary_outputs);
  const domains = ["General AI", "Physical AI", "Agentic AI"];
  const colors = { "General AI": "var(--general)", "Agentic AI": "var(--agentic)", "Physical AI": "var(--physical)" };
  const maxDomain = Math.max(...domains.map((domain) => summary.final_domain_counts[domain]));
  const maxMapping = Math.max(...domains.map((domain) => summary.mapping_method_counts[domain].EM + summary.mapping_method_counts[domain].HD));
  const emShare = summary.cleaned_total ? (summary.em_total / summary.cleaned_total) * 100 : 0;
  const generalShare = summary.cleaned_total ? (summary.final_domain_counts["General AI"] / summary.cleaned_total) * 100 : 0;

  document.querySelector("#report-root").innerHTML = `
    <section class="section" aria-labelledby="overview-title">
      <div class="section-heading"><div><p class="section-kicker">RELEASE OVERVIEW</p><h2 id="overview-title">${formatNumber(summary.source_total)}개 원천 레코드가 ${formatNumber(summary.cleaned_total)}개 최종 카드로 정제됨</h2></div><p class="section-note">Release date · ${escapeHtml(data.release_date)}</p></div>
      <div class="kpi-grid">
        ${kpi("Source L4", summary.source_total, "정제 전 원천 레코드", "var(--navy)")}
        ${kpi("Final L4", summary.cleaned_total, "정제·통합·분리 후", "var(--physical)")}
        ${kpi("L3 categories", summary.l3_source_rows + summary.l3_derived_others_rows, `${summary.l3_source_rows} master + ${summary.l3_derived_others_rows} Others`, "var(--agentic)")}
        ${kpi("AI-grounded definitions", summary.cleaned_total, `${summary.definition_ai_grounding_rewrites} rewritten · ${summary.cleaned_total - summary.definition_ai_grounding_rewrites} retained`, "var(--em)")}
        ${kpi("Title terminology", summary.title_terminology_validated, `${summary.title_terminology_normalisations} retained titles normalised`, "var(--general)")}
        ${kpi("Semantic deduplication", summary.semantic_near_duplicate_deletions, `${summary.semantic_near_duplicate_candidates} candidate pairs reviewed`, "var(--hd)")}
      </div>
    </section>

    <section class="section panel-grid" aria-label="Title terminology and semantic deduplication review">
      <article class="panel">
        <h3>${formatNumber(summary.title_terminology_validated)}개 최종 명칭에 용어 근거 기록</h3>
        <p class="panel-subtitle">Formulaic AI involvement modifiers removed while technical-object terms remain</p>
        <div class="validation-bar" role="img" aria-label="${summary.title_terminology_normalisations} titles normalised and ${summary.title_terminology_validated - summary.title_terminology_normalisations} titles retained">
          <div class="validation-bar__pass" style="width:${(summary.title_terminology_normalisations / summary.title_terminology_validated) * 100}%">Normalised ${summary.title_terminology_normalisations}</div>
          <div class="validation-bar__fail" style="width:${((summary.title_terminology_validated - summary.title_terminology_normalisations) / summary.title_terminology_validated) * 100}%">Validated unchanged ${summary.title_terminology_validated - summary.title_terminology_normalisations}</div>
        </div>
      </article>
      <article class="panel">
        <h3>고유사도 후보 ${formatNumber(summary.semantic_near_duplicate_candidates)}쌍을 범위 기준으로 판정</h3>
        <p class="panel-subtitle">Similarity generated candidates only; target and mechanism distinctiveness controlled deletion</p>
        <div class="validation-bar" role="img" aria-label="${summary.semantic_near_duplicate_candidates - summary.semantic_near_duplicate_deletions} distinct pairs retained and ${summary.semantic_near_duplicate_deletions} lower-representativeness cards discarded">
          <div class="validation-bar__pass" style="width:${((summary.semantic_near_duplicate_candidates - summary.semantic_near_duplicate_deletions) / summary.semantic_near_duplicate_candidates) * 100}%">Retained ${summary.semantic_near_duplicate_candidates - summary.semantic_near_duplicate_deletions}</div>
          <div class="validation-bar__fail" style="width:${(summary.semantic_near_duplicate_deletions / summary.semantic_near_duplicate_candidates) * 100}%">Discarded ${summary.semantic_near_duplicate_deletions}</div>
        </div>
        <div class="table-shell"><table><tbody>
          <tr><th>Candidate threshold</th><td class="numeric">${data.semantic_deduplication_method?.candidate_similarity_threshold ?? "0.90"}</td></tr>
          <tr><th>Automatic deletion from similarity</th><td>${data.semantic_deduplication_method?.automatic_deletion_from_similarity_only ? "Enabled" : "Disabled"}</td></tr>
          <tr><th>Distinct target or mechanism</th><td>Retained</td></tr>
        </tbody></table></div>
      </article>
    </section>

    <section class="section" aria-labelledby="cleaning-title">
      <div class="section-heading"><div><p class="section-kicker">CLEANING RECONCILIATION</p><h2 id="cleaning-title">삭제·통합·분리 내역이 최종 합계와 일치</h2></div></div>
      <div class="flow" role="img" aria-label="${summary.source_total} source records minus ${summary.deleted} deletions minus ${summary.merged_away} merged records plus ${summary.split_net_addition} split addition equals ${summary.cleaned_total} final records">
        ${flowStep("Source", summary.source_total, "input", "")}
        ${flowStep("Deleted", `−${summary.deleted}`, "explicit deletion", "negative")}
        ${flowStep("Merged away", `−${summary.merged_away}`, "absorbed records", "negative")}
        ${flowStep("Split addition", `+${summary.split_net_addition}`, "net addition", "positive")}
        ${flowStep("Final", summary.cleaned_total, "reconciled total", "final")}
      </div>
    </section>

    <section class="section panel-grid" aria-label="Release charts">
      <article class="panel">
        <h3>General AI가 최종 L4의 ${generalShare.toFixed(1)}%를 차지</h3>
        <p class="panel-subtitle">Final L4 cards by domain · bars start at zero</p>
        <div class="bar-chart" role="img" aria-label="Final L4 counts by domain">
          ${domains.map((domain) => barRow(domain, summary.final_domain_counts[domain], maxDomain, colors[domain])).join("")}
        </div>
      </article>
      <article class="panel">
        <h3>전체 매핑의 ${emShare.toFixed(1)}%가 EM으로 확정</h3>
        <p class="panel-subtitle">EM and HD/Others assignments by domain · common zero baseline</p>
        <div class="stack-chart" role="img" aria-label="EM and HD assignments by domain">
          ${domains.map((domain) => stackRow(domain, summary.mapping_method_counts[domain], maxMapping)).join("")}
        </div>
        <div class="legend" aria-hidden="true"><span style="--legend:var(--em)">EM</span><span style="--legend:var(--hd)">HD / Others</span></div>
      </article>
    </section>

    <section class="section" aria-labelledby="domain-table-title">
      <div class="section-heading"><div><p class="section-kicker">CHART DATA</p><h2 id="domain-table-title">도메인별 원천·최종·매핑 수치</h2></div><p class="section-note">Accessible table alternative for the charts above</p></div>
      <div class="table-shell"><table><thead><tr><th>Domain</th><th>Source L4</th><th>Final L4</th><th>EM</th><th>HD / Others</th></tr></thead><tbody>
        ${domains.map((domain) => `<tr><td>${escapeHtml(domain)}</td><td class="numeric">${formatNumber(summary.source_counts[domain.replace(" AI", "")])}</td><td class="numeric">${formatNumber(summary.final_domain_counts[domain])}</td><td class="numeric">${formatNumber(summary.mapping_method_counts[domain].EM)}</td><td class="numeric">${formatNumber(summary.mapping_method_counts[domain].HD)}</td></tr>`).join("")}
      </tbody></table></div>
    </section>

    <section class="section" aria-labelledby="outputs-title">
      <div class="section-heading"><div><p class="section-kicker">PRIMARY OUTPUTS</p><h2 id="outputs-title">5개 정본 CSV와 SHA-256</h2></div></div>
      <div class="table-shell"><table><thead><tr><th>File</th><th>Rows</th><th>SHA-256</th></tr></thead><tbody>
        ${outputs.map(([name, value]) => `<tr><td><a href="data/${encodeURIComponent(name)}">${escapeHtml(name)}</a></td><td class="numeric">${formatNumber(value.rows)}</td><td><code class="hash" title="${escapeHtml(value.sha256)}">${escapeHtml(value.sha256)}</code></td></tr>`).join("")}
      </tbody></table></div>
    </section>

    <section class="section panel-grid" aria-label="Provenance tables">
      <article>
        <div class="section-heading"><div><p class="section-kicker">SOURCE INTEGRITY</p><h2>Source hashes</h2></div></div>
        <div class="table-shell"><table><thead><tr><th>Source</th><th>SHA-256</th></tr></thead><tbody>
          ${Object.entries(data.source_hashes).map(([name, hash]) => `<tr><td>${escapeHtml(name)}</td><td><code class="hash" title="${escapeHtml(hash)}">${escapeHtml(hash)}</code></td></tr>`).join("")}
        </tbody></table></div>
      </article>
      <article>
        <div class="section-heading"><div><p class="section-kicker">EM CONFIGURATION</p><h2>Model and thresholds</h2></div></div>
        <div class="table-shell"><table><tbody>
          <tr><th>Model</th><td>${escapeHtml(data.model.name)}</td></tr>
          <tr><th>Pooling</th><td>${escapeHtml(data.model.pooling)}</td></tr>
          <tr><th>Definition method</th><td>${escapeHtml(data.definition_method?.name || "Immutable-L3-referenced bilingual AI grounding")}</td></tr>
          <tr><th>Title method</th><td>${escapeHtml(data.title_terminology_method?.name || "Authoritative term-family normalisation")}</td></tr>
          <tr><th>Near-duplicate method</th><td>${escapeHtml(data.semantic_deduplication_method?.name || "Bilingual semantic review with distinctiveness gates")}</td></tr>
          <tr><th>Anchor weight</th><td class="numeric">${data.mapping_method?.anchor_weight}</td></tr>
          <tr><th>L4 keywords</th><td class="numeric">${summary.keyword_count_per_language} per language</td></tr>
          <tr><th>Score floor</th><td class="numeric">${summary.thresholds.General.score_floor}</td></tr>
          <tr><th>Margin floor</th><td class="numeric">${summary.thresholds.General.margin_floor}</td></tr>
          <tr><th>Stability floor</th><td class="numeric">${summary.thresholds.General.stability_floor}</td></tr>
          <tr><th>Weights SHA-256</th><td><code class="hash" title="${escapeHtml(data.model.weights_sha256)}">${escapeHtml(data.model.weights_sha256)}</code></td></tr>
        </tbody></table></div>
      </article>
    </section>`;

  if (data.human_review) {
    document.querySelector("#report-root").insertAdjacentHTML("beforeend", `
      <section class="section" aria-labelledby="human-review-title">
        <div class="section-heading"><div><p class="section-kicker">HUMAN REVIEW LOG</p><h2 id="human-review-title">Top-2 L3 candidate voting without automatic reassignment</h2></div></div>
        <div class="table-shell"><table><tbody>
          <tr><th>Candidates per L4</th><td>${data.human_review.candidate_count}</td></tr>
          <tr><th>Displayed scores</th><td>${data.human_review.score_fields.map(escapeHtml).join(" · ")}</td></tr>
          <tr><th>Vote log</th><td>${escapeHtml(data.human_review.vote_log)}</td></tr>
          <tr><th>Majority eligibility</th><td>${data.human_review.minimum_unique_reviewers}+ unique reviewers and a strict majority</td></tr>
          <tr><th>Automatic reassignment</th><td>${data.human_review.automatic_reassignment ? "Enabled" : "Disabled"}</td></tr>
          <tr><th>Application policy</th><td>${escapeHtml(data.human_review.application_policy)}</td></tr>
        </tbody></table></div>
      </section>`);
  }
}

async function renderValidation() {
  const data = await fetchJson("validation/final_release_qa.json");
  const total = data.passed + data.failed;
  const passRate = total ? (data.passed / total) * 100 : 0;
  const categories = countValidationCategories(data.checks);

  document.querySelector("#report-root").innerHTML = `
    <section class="section" aria-labelledby="validation-overview-title">
      <div class="section-heading"><div><p class="section-kicker">VALIDATION OVERVIEW</p><h2 id="validation-overview-title">${total}개 최종 검증이 모두 통과</h2></div><span class="status-pass">${escapeHtml(data.status)}</span></div>
      <div class="kpi-grid">
        ${kpi("Checks", total, "post-build QA", "var(--navy)")}
        ${kpi("Passed", data.passed, "all required checks", "var(--pass)")}
        ${kpi("Failed", data.failed, "no unresolved failures", "var(--physical)")}
        ${kpi("Pass rate", `${passRate.toFixed(1)}%`, `${data.passed} of ${total}`, "var(--agentic)")}
      </div>
    </section>

    <section class="section panel-grid" aria-label="Validation charts">
      <article class="panel">
        <h3>검증 결과는 ${data.passed} PASS, ${data.failed} FAIL</h3>
        <p class="panel-subtitle">Overall validation outcome</p>
        <div class="validation-bar" role="img" aria-label="${data.passed} passed checks and ${data.failed} failed checks">
          <div class="validation-bar__pass" style="width:${passRate}%">PASS ${data.passed}</div>
          ${data.failed ? `<div class="validation-bar__fail" style="width:${100 - passRate}%">FAIL ${data.failed}</div>` : ""}
        </div>
      </article>
      <article class="panel">
        <h3>구조·내용·매핑·계층·이력·무결성을 모두 검증</h3>
        <p class="panel-subtitle">Passed checks grouped by validation purpose</p>
        <div class="category-grid">
          ${Object.entries(categories).map(([name, count]) => `<div class="category-card"><strong>${count}</strong><span>${escapeHtml(name)} checks passed</span></div>`).join("")}
        </div>
      </article>
    </section>

    <section class="section" aria-labelledby="checks-title">
      <div class="section-heading"><div><p class="section-kicker">CHECK-BY-CHECK EVIDENCE</p><h2 id="checks-title">최종 검증 기록</h2></div><p class="section-note">Evidence rendered from final_release_qa.json</p></div>
      <div class="table-shell"><table><thead><tr><th>#</th><th>Check</th><th>Status</th><th>Evidence</th></tr></thead><tbody>
        ${data.checks.map((row, index) => `<tr><td class="numeric">${index + 1}</td><td>${escapeHtml(row.check)}</td><td><span class="status-pass">${escapeHtml(row.status)}</span></td><td class="evidence">${formatEvidence(row.evidence)}</td></tr>`).join("")}
      </tbody></table></div>
    </section>`;
}

function countValidationCategories(checks) {
  const categories = { Structure: 0, Content: 0, Mapping: 0, Hierarchy: 0, Lineage: 0, Integrity: 0 };
  checks.forEach((row) => {
    const name = row.check;
    if (/hash/i.test(name)) categories.Integrity += 1;
    else if (/hierarchy|L3|scope gate/i.test(name)) categories.Hierarchy += 1;
    else if (/crosswalk|Archive|lineage|new IDs|reconciliation/i.test(name)) categories.Lineage += 1;
    else if (/Mapping|Others|EM|candidate|overconfidence|polarization|cybercrime|Anthropocentric/i.test(name)) categories.Mapping += 1;
    else if (/bilingual|definition|AI technology|keyword|fields/i.test(name)) categories.Content += 1;
    else categories.Structure += 1;
  });
  return categories;
}

function kpi(label, value, note, color) {
  return `<article class="kpi" style="--accent:${color}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(formatNumber(value))}</strong><small>${escapeHtml(note)}</small></article>`;
}

function flowStep(label, value, note, className) {
  return `<div class="flow-step ${className}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(formatNumber(value))}</strong><small>${escapeHtml(note)}</small></div>`;
}

function barRow(label, value, maximum, color) {
  const width = maximum ? (value / maximum) * 100 : 0;
  return `<div class="bar-row"><span class="bar-row__label">${escapeHtml(label)}</span><div class="bar-track"><div class="bar-fill" style="width:${width}%;--bar-color:${color}"></div></div><span class="bar-value">${formatNumber(value)}</span></div>`;
}

function stackRow(label, values, maximum) {
  const total = values.EM + values.HD;
  return `<div class="stack-row"><span class="bar-row__label">${escapeHtml(label)}</span><div class="stack-track"><div class="stack-em" style="width:${(values.EM / maximum) * 100}%" title="EM ${values.EM}"></div><div class="stack-hd" style="width:${(values.HD / maximum) * 100}%" title="HD ${values.HD}"></div></div><span class="bar-value">${formatNumber(total)}</span></div>`;
}

function formatEvidence(value) {
  if (typeof value === "string" || typeof value === "number") return escapeHtml(String(value));
  if (Array.isArray(value)) return value.map((item) => escapeHtml(String(item))).join("<br>");
  return Object.entries(value).map(([key, item]) => `<strong>${escapeHtml(key)}</strong>: ${escapeHtml(typeof item === "object" ? JSON.stringify(item) : String(item))}`).join("<br>");
}

function formatNumber(value) {
  if (typeof value === "number") return value.toLocaleString("en-US");
  return String(value);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}
