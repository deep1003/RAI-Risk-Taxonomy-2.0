import fs from "node:fs/promises";
import { Workbook } from "@oai/artifact-tool";

const csvPath = new URL("../02_working/specifications/human_review_round2/user_directed_operations.csv", import.meta.url);
const csvText = await fs.readFile(csvPath, "utf8");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "Operations" });
const sheet = workbook.worksheets.getItem("Operations");
const used = sheet.getUsedRange();
const currentValues = used.values;
const header = currentValues[0];
const legacyHeader = [
  "Request_Date",
  "Operation",
  "Source_L4_IDs_Before",
  "Current_L4_IDs",
  "Representative_Source_L4_ID",
  "Target_L3_ID",
  "Mapping_Method",
  "L4_Title_ko",
  "L4_Title_en",
  "L4_Description_ko",
  "L4_Description_en",
  "Decision_Rationale",
  "Terminology_Sources",
  "Source_URLs",
];
const expectedHeader = [...legacyHeader, "Operation_ID", "Approval_Batch", "Source_Selectors"];
if (
  JSON.stringify(header) !== JSON.stringify(legacyHeader) &&
  JSON.stringify(header) !== JSON.stringify(expectedHeader)
) {
  throw new Error(`Unexpected operation CSV header: ${JSON.stringify(header)}`);
}

const approvedCurrentIds = new Set([
  "P_SYS_STATE_002|P_SYS_STATE_012",
  "G_SOC_CULT_015|G_SOC_CULT_016",
  "G_SOC_CULT_016",
  "G_INT_COPY_008|G_INT_COPY_009",
  "G_INT_PRIV_018|G_INT_PRIV_019",
  "G_INT_SELF_007|G_INT_SELF_011",
  "G_INT_VIOL_003|G_INT_VIOL_010",
]);
const existingRows = currentValues.slice(1)
  .filter((row) => !approvedCurrentIds.has(String(row[3] ?? "")))
  .map((row) => {
    const next = [...row];
    if (String(next[2] ?? "") === "G_INT_WEAP_001|G_INT_WEAP_005") {
      next[7] = "생물무기·화학무기";
      next[9] = "AI 시스템이 생물무기 또는 화학무기의 개발·제조·획득·이전·비축·확산·운용을 지원하여 대규모 인명 피해, 공중보건 위해 또는 환경 피해의 발생 가능성과 규모를 높이는 리스크.";
    }
    return next;
  });
const terminology = "L3_MASTER|HUMAN_REVIEW_ROUND2|USER_APPROVED_DUPLICATE_REVIEW_2026-08-29";
const sourceUrl = "https://deep1003.github.io/RAI-Risk-Taxonomy-2.0/glossary.html";
const approvedRows = [
  [
    "2026-08-29",
    "MERGE",
    "P_SYS_STATE_002|P_SYS_STATE_013",
    "P_SYS_STATE_002|P_SYS_STATE_012",
    "P_SYS_STATE_002",
    "P_SYS_STATE",
    "HD",
    "장기 계획에서 월드 모델의 상태 예측 오차 누적",
    "Compounding world-model state-prediction error in long-horizon planning",
    "피지컬 AI 시스템의 월드 모델이 미래 물리 상태를 예측하는 과정에서 발생한 오차가 장기 계획에 걸쳐 누적되어, 선택된 계획이 실제 접촉 조건과 운동 동역학에 부합하지 않고 안전하지 않은 물리적 행동으로 이어지는 리스크.",
    "The risk that errors arising when a physical AI system's world model predicts future physical states accumulate over long-horizon planning, causing the selected plan to diverge from actual contact conditions and motion dynamics and lead to unsafe physical action.",
    "User approved merge proposal 1; both cards describe compounding world-model prediction error over long-horizon planning and divergence from actual contact and motion dynamics.",
    terminology,
    sourceUrl,
  ],
  [
    "2026-08-29",
    "MERGE",
    "G_INT_ALLOC_004|G_SYS_CONTEXT_006",
    "G_SOC_CULT_016",
    "G_SYS_CONTEXT_006",
    "G_SOC_CULT",
    "HD",
    "저자원 언어와 문화적 의미의 침식",
    "Erosion of low-resource languages and cultural meaning",
    "AI 시스템이 저자원 언어와 해당 문화권의 표현, 가치에 내재된 뉘앙스 및 사회적 의미를 반복적으로 누락하거나 왜곡하여 언어 다양성과 언어적·문화적 지식을 침식하는 리스크.",
    "The risk that an AI system repeatedly omits or distorts expressions, value nuances, or social meanings in low-resource languages and their associated cultures, eroding linguistic diversity and linguistic and cultural knowledge.",
    "User approved consolidation of the low-resource-language cultural-risk components; the unrelated human-dignity source is retained separately after independent lineage review.",
    terminology,
    sourceUrl,
  ],
  [
    "2026-08-29",
    "MERGE",
    "G_INT_COPY_009|G_INT_COPY_006",
    "G_INT_COPY_008|G_INT_COPY_009",
    "G_INT_COPY_009",
    "G_INT_COPY",
    "HD",
    "저작물의 무단 복제·변형·배포",
    "Unauthorised reproduction, transformation, and distribution of copyrighted works",
    "AI 시스템이 저작물을 저작재산권자의 허락이나 그 밖의 적법한 근거 없이 복제·배포하거나 변형하여 2차적저작물을 작성함으로써 저작재산권과 권리자의 정당한 이익을 침해하는 리스크.",
    "The risk that an AI system reproduces or distributes a copyrighted work, or transforms it into a derivative work, without the economic rights holder's permission or another lawful basis, infringing economic rights and the legitimate interests of the rights holder.",
    "User approved merge proposal 3; unauthorized reproduction, transformation, and distribution are consolidated while retaining lawful-basis and rights-holder protections.",
    terminology,
    sourceUrl,
  ],
  [
    "2026-08-29",
    "MERGE",
    "G_INT_PRIV_019|G_INT_PRIV_005|G_INT_PRIV_025",
    "G_INT_PRIV_018|G_INT_PRIV_019",
    "G_INT_PRIV_005",
    "G_INT_PRIV",
    "HD",
    "재산 정보·개인정보·사적 사실의 부당한 노출",
    "Improper exposure of property information, personal information, and private facts",
    "AI 시스템이 대화·추론·출력 과정에서 재산 정보, 개인정보 또는 사적 사실을 정보주체의 동의, 정당한 권한 또는 그 밖의 적법한 근거 없이 노출하여 사생활의 비밀과 자유 및 개인정보자기결정권을 침해하는 리스크.",
    "The risk that an AI system exposes property information, personal information, or private facts during interaction, inference, or output without the data subject's consent, proper authority, or another lawful basis, infringing privacy, the secrecy and freedom of private life, and informational self-determination.",
    "User approved merge proposal 4; the merged card preserves property information, personal information, private facts, authorization, consent, legitimate purpose, privacy, and informational self-determination.",
    terminology,
    sourceUrl,
  ],
  [
    "2026-08-29",
    "MERGE",
    "G_INT_SELF_007|G_INT_SELF_010",
    "G_INT_SELF_007|G_INT_SELF_011",
    "G_INT_SELF_010",
    "G_INT_SELF",
    "HD",
    "자살 준비 행위의 조장 및 구체적 지원",
    "Promotion of and concrete assistance for preparatory conduct for suicide",
    "AI 시스템이 자살 수단 확보, 장소 선택 또는 주변의 개입 회피 등 자살 준비 행위를 조장·정상화하거나 이에 필요한 구체적인 정보를 생성·제공하여 개인의 생명과 신체적·정신적 안녕을 위협하는 리스크.",
    "The risk that an AI system encourages or normalises preparatory conduct for suicide, or generates or provides concrete information for acquiring means, selecting a location, or avoiding intervention, thereby threatening an individual's life and physical or psychological well-being.",
    "User approved merge proposal 5; the general preparatory-act card is absorbed into the specific assistance card, while the separately reviewed suicide-execution assistance card remains independent.",
    terminology,
    sourceUrl,
  ],
  [
    "2026-08-29",
    "MERGE",
    "G_INT_VIOL_003|G_INT_VIOL_010",
    "G_INT_VIOL_003|G_INT_VIOL_010",
    "G_INT_VIOL_003",
    "G_INT_VIOL",
    "HD",
    "폭력 선동·조장 및 실행 지원",
    "Incitement, promotion, and operational assistance for violence",
    "AI 시스템이 타인에 대한 폭력을 선동·조장·정당화하는 콘텐츠를 생성·제공하거나 그 실행을 구체적으로 지원하여 개인 또는 집단에 신체적·정신적 위해를 초래하는 리스크.",
    "The risk that an AI system generates or provides content that incites, promotes, or legitimises violence against others, or provides concrete operational assistance for its commission, causing physical or psychological harm to individuals or groups.",
    "User approved merge proposal 6; the merged definition retains violence incitement, promotion, legitimization, and operational assistance while excluding self-harm and generic illegality outside the Violence L3 scope.",
    terminology,
    sourceUrl,
  ],
];

const auditBySourceIds = {
  "G_INT_REPR_010|G_INT_REPR_011": ["HR2-U001", "USER_APPROVED_20260829_BATCH_A", ""],
  "G_INT_REPR_013|G_INT_REPR_017": ["HR2-U002", "USER_APPROVED_20260829_BATCH_A", ""],
  "G_INT_ANTH_001|G_INT_ANTH_003": ["HR2-U003", "USER_APPROVED_20260829_BATCH_A", ""],
  "G_INT_WEAP_001|G_INT_WEAP_005": ["HR2-U004", "USER_APPROVED_20260829_BATCH_A", ""],
  "P_SYS_STATE_002|P_SYS_STATE_013": ["HR2-U005", "USER_APPROVED_20260829_BATCH_B", ""],
  "G_INT_ALLOC_004|G_SYS_CONTEXT_006": ["HR2-U006", "USER_APPROVED_20260829_BATCH_B", ""],
  "G_INT_COPY_009|G_INT_COPY_006": ["HR2-U007", "USER_APPROVED_20260829_BATCH_B", ""],
  "G_INT_PRIV_019|G_INT_PRIV_005|G_INT_PRIV_025": ["HR2-U008", "USER_APPROVED_20260829_BATCH_B", ""],
  "G_INT_SELF_007|G_INT_SELF_010": [
    "HR2-U009",
    "USER_APPROVED_20260829_BATCH_B",
    JSON.stringify({ G_INT_SELF_010: "자살 준비행위에 대한 구체적 지원" }),
  ],
  "G_INT_VIOL_003|G_INT_VIOL_010": ["HR2-U010", "USER_APPROVED_20260829_BATCH_B", ""],
};
function withAuditFields(row) {
  const base = row.slice(0, legacyHeader.length);
  const audit = auditBySourceIds[String(base[2] ?? "")];
  if (!audit) throw new Error(`Missing audit metadata for ${String(base[2] ?? "")}`);
  return [...base, ...audit];
}
const nextValues = [
  expectedHeader,
  ...existingRows.map(withAuditFields),
  ...approvedRows.map(withAuditFields),
];
used.clear({ applyTo: "contents" });
sheet.getRangeByIndexes(0, 0, nextValues.length, expectedHeader.length).values = nextValues;

const inspection = await workbook.inspect({
  kind: "table",
  range: `Operations!A1:Q${nextValues.length}`,
  include: "values",
  tableMaxRows: nextValues.length,
  tableMaxCols: 17,
  tableMaxCellChars: 120,
  maxChars: 12000,
});
console.log(inspection.ndjson);

const preview = await workbook.render({
  sheetName: "Operations",
  range: `A1:Q${nextValues.length}`,
  scale: 0.8,
  format: "png",
});
await fs.writeFile("/tmp/rai_l4_user_operations_preview.png", new Uint8Array(await preview.arrayBuffer()));

function csvCell(value) {
  const text = String(value ?? "");
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}
const outputCsv = nextValues.map((row) => row.map(csvCell).join(",")).join("\n") + "\n";
await fs.writeFile(csvPath, outputCsv, "utf8");

const editorialPath = new URL("../02_working/specifications/human_review_round2/expert_review_editorial_operations.csv", import.meta.url);
const editorialText = await fs.readFile(editorialPath, "utf8");
const editorialWorkbook = await Workbook.fromCSV(editorialText, { sheetName: "Editorial" });
const editorialSheet = editorialWorkbook.worksheets.getItem("Editorial");
const editorialUsed = editorialSheet.getUsedRange();
const editorialValues = editorialUsed.values;
const editorialHeader = editorialValues[0];
const editorialIndex = Object.fromEntries(
  editorialHeader.map((value, index) => [String(value).replace(/^\uFEFF/, "").trim(), index]),
);
let correctedHumanDignityRows = 0;
const correctedEditorialRows = [editorialHeader];
for (const row of editorialValues.slice(1)) {
  const sourceId = String(row[editorialIndex.Source_L4_ID] ?? "").trim();
  const targetL3Id = String(row[editorialIndex.Target_L3_ID] ?? "").trim();
  if (sourceId === "G_SOC_CULT_010" && targetL3Id === "G_INT_REPR") {
    // The source card concerns human dignity and equal moral standing. It does
    // not support a separate protected-group stereotyping child.
    continue;
  }
  if (
    sourceId === "G_SOC_CULT_010" &&
    targetL3Id === "G_SOC_CULT"
  ) {
    row[editorialIndex.Operation] = "REWRITE";
    row[editorialIndex.Operation_Group_Key] = "REWRITE:G_SOC_CULT_010";
    row[editorialIndex.Output_Sequence] = "1";
    row[editorialIndex.L4_Title_ko] = "인간 존엄성과 동등한 도덕적 지위의 침식";
    row[editorialIndex.L4_Title_en] = "Erosion of human dignity and equal moral standing";
    row[editorialIndex.L4_Description_ko] = "AI 시스템이 사람을 프로필·점수·행동 표적으로 환원하거나 지능의 위계에서 열등한 존재로 취급하여 인간에 대한 존중, 존엄성 및 동등한 도덕적 지위를 침식하는 리스크.";
    row[editorialIndex.L4_Description_en] = "The risk that an AI system reduces people to profiles, scores, or behavioural targets, or treats humans as inferior within hierarchies of intelligence, eroding respect for persons, human dignity, and equal moral standing.";
    row[editorialIndex.Editorial_Note] = "Independent lineage review restored the human-dignity mechanism supported by the source; the unrelated low-resource-language wording was removed.";
    correctedHumanDignityRows += 1;
  }
  correctedEditorialRows.push(row);
}
if (correctedHumanDignityRows !== 1) {
  throw new Error(`Expected one G_SOC_CULT_010 cultural editorial row, found ${correctedHumanDignityRows}`);
}
editorialUsed.clear({ applyTo: "contents" });
editorialSheet.getRangeByIndexes(0, 0, correctedEditorialRows.length, editorialHeader.length).values = correctedEditorialRows;
const editorialInspection = await editorialWorkbook.inspect({
  kind: "match",
  searchTerm: "인간 존엄성과 동등한 도덕적 지위의 침식",
  options: { useRegex: false, maxResults: 10 },
  summary: "restored human dignity editorial operation",
});
console.log(editorialInspection.ndjson);
const editorialCsv = correctedEditorialRows.map((row) => row.map(csvCell).join(",")).join("\n") + "\n";
await fs.writeFile(editorialPath, editorialCsv, "utf8");
