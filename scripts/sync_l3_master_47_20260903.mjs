#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { Workbook } from "@oai/artifact-tool";

const ROOT = "/Users/deep1003/data3/RAI-Risk-Taxonomy";
const RELEASE = path.join(ROOT, "releases/RAI-Risk-Taxonomy-2.0-master/data");
const HANDOVER = path.join(ROOT, "handover/RAI-Risk-Taxonomy-2.0-master_20260829/01_data");
const REPORT_HANDOVER = path.join(ROOT, "handover/RAI-Risk-Taxonomy-2.0-technical-report_20260901/01_data");
const BACKUP = path.join(ROOT, "archives/pre_l3_master_47_sync_20260903");

const MASTER_FILE = "L1_L2_L3_Master.csv";
const L4_FILES = ["L4_General.csv", "L4_Agentic.csv", "L4_Physical.csv"];
const DATA_DIRS = [RELEASE, HANDOVER, REPORT_HANDOVER];

const updates = {
  G_SYS_POLICY: {
    L3_Description_ko:
      'AI 시스템이 시스템 프롬프트·내부 정책·안전장치·모델 구조·학습/평가 데이터·모델 가중치·기업 영업비밀 등 보호되는 비공개 기밀정보를 권한 없이 노출·추론·추출·공유하거나 이를 충분히 보호하지 못하여, 기밀성과 정당한 경제적 이익을 침해하는 리스크\n\n(개인정보·민감정보의 노출은 "Privacy Violation", 제3자의 저작권·상표·특허 등 지식재산권 침해 자체는 "Copyright Infringement", 적대적 입력·탈옥·무단 접근과 같은 실제 침해는 "Security and Adversarial Robustness Failure"에서 다룸).',
    L3_Description_en:
      'The risk that an AI system, without authorisation, discloses, infers, extracts, shares, or fails to adequately protect non-public confidential information, including system prompts, internal policies, safeguards, model architecture, training or evaluation data, model weights, and corporate trade secrets, thereby compromising confidentiality and legitimate economic interests.\n\n(Exposure of personal or sensitive information is covered under "Privacy Violation"; infringement of third-party copyright, trademarks, patents, or other intellectual-property rights is covered under "Copyright Infringement"; actual compromises such as adversarial inputs, jailbreaks, or unauthorised access are covered under "Security and Adversarial Robustness Failure".)',
    Source_Notes:
      "Revised under fourth-round human review and the user-approved 47-category L3 synchronisation on 2026-09-03.",
  },
  G_SYS_PERF: {
    L3_Title_ko: "운영영역 이탈 성능 저하",
    L3_Title_en: "Out-of-Domain Performance Degradation",
    L3_Description_ko:
      'AI 시스템이 검증된 운영영역(validated operating domain)을 벗어난 조건 — 데이터 분포 이동(drift), 저자원·희소 입력, 코너 케이스, 또는 시스템의 검증된 역량 범위를 넘어선 배치 등 — 에서 일반화에 실패하여 성능과 신뢰성이 저하되고, 부정확하거나 불안정한 결과를 산출하는 리스크\n\n(개별 입력의 의미적 오해는 "Input Comprehension Failure", 동일·유사 입력에 대한 출력 변동은 "Inconsistency", 불확실성 하의 부당한 확신은 "Overconfidence", 검증된 역량을 넘어 수행 가능한 것처럼 표상하는 문제는 "Over-Extension"에서 다룸. 또한 성능 저하가 보호대상 특성·사회집단과 체계적으로 연동되어 불리한 자원·기회·서비스 배분으로 이어지는 경우는 "Allocative Discrimination", 집단에 대한 비하·고정관념적 표현으로 나타나는 경우는 "Representational Harm and Stereotyping"에서 다루며, 본 범주는 특정 보호집단과 무관한 일반화·강건성 실패에 한정한다).',
    L3_Description_en:
      'The risk that an AI system fails to generalise under conditions outside its validated operating domain, including data-distribution shift or drift, low-resource or sparse inputs, corner cases, or deployment beyond its validated capabilities, thereby degrading performance and reliability and producing inaccurate or unstable outcomes.\n\n(Misinterpretation of an individual input is covered under "Input Comprehension Failure"; output variation for identical or substantively similar inputs under "Inconsistency"; unjustified certainty under uncertainty under "Overconfidence"; and claims or actions beyond validated capability under "Over-Extension". Where performance degradation is systematically associated with protected characteristics or social groups and leads to adverse allocation of resources, opportunities, services, or access, it is covered under "Allocative Discrimination"; where it manifests as degrading or stereotypical representations of groups, it is covered under "Representational Harm and Stereotyping". This category is limited to generalisation and robustness failures not systematically associated with a specific protected group.)',
    Source_Notes:
      "Reframed from Performance and Reliability Failure under the user-approved 47-category L3 synchronisation on 2026-09-03; stable ID retained for lineage.",
  },
  A_INT_COORD: {
    L3_Description_ko:
      "여러 에이전트가 균형(equilibrium) 선택의 불일치나 상대에 대한 사전 정보 부족으로 행동을 신뢰성 있게 맞추지 못하여 협력이 실패하고 집단적으로 나쁜 결과에 이르는 리스크.",
    L3_Description_en:
      "The risk that multiple agents fail to reliably align their actions because of mismatched equilibrium selection or insufficient prior information about one another, resulting in failed cooperation and collectively poor outcomes.",
    Source_Notes:
      "Definition aligned to the user-approved 47-category L3 master on 2026-09-03.",
  },
};

function csvEscape(value) {
  const text = value == null ? "" : String(value);
  return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function matrixToCsv(matrix) {
  return `\ufeff${matrix.map((row) => row.map(csvEscape).join(",")).join("\n")}\n`;
}

async function readMatrix(file) {
  const text = await fs.readFile(file, "utf8");
  const workbook = await Workbook.fromCSV(text.replace(/^\ufeff/, ""), { sheetName: "Data" });
  const sheet = workbook.worksheets.getItem("Data");
  return sheet.getUsedRange(true).values;
}

function rowObject(headers, row) {
  return Object.fromEntries(headers.map((header, index) => [header, row[index] ?? ""]));
}

function updateRow(headers, row, values) {
  const output = [...row];
  for (const [field, value] of Object.entries(values)) {
    const index = headers.indexOf(field);
    if (index < 0) throw new Error(`Missing column ${field}`);
    output[index] = value;
  }
  return output;
}

async function writeMatrix(file, matrix) {
  const workbook = Workbook.create();
  const sheet = workbook.worksheets.add("Data");
  sheet.getRangeByIndexes(0, 0, matrix.length, matrix[0].length).values = matrix;
  const inspected = await workbook.inspect({
    kind: "region",
    sheetId: "Data",
    range: `A1:V${matrix.length}`,
    maxChars: 1200,
    tableMaxRows: 3,
    tableMaxCols: 22,
  });
  if (!inspected.ndjson.includes('"Data"')) throw new Error(`Artifact inspection failed for ${file}`);
  await fs.writeFile(file, matrixToCsv(matrix));
}

async function backupInputs() {
  try {
    await fs.access(BACKUP);
    return;
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  for (const directory of DATA_DIRS) {
    const relative = path.relative(ROOT, directory);
    const target = path.join(BACKUP, relative);
    await fs.mkdir(target, { recursive: true });
    for (const file of [MASTER_FILE, ...L4_FILES]) {
      await fs.copyFile(path.join(directory, file), path.join(target, file));
    }
  }
  const webDir = path.join(ROOT, "public/data/releases/RAI-Risk-Taxonomy-2.0-master");
  const webBackup = path.join(BACKUP, "public/data/releases/RAI-Risk-Taxonomy-2.0-master");
  await fs.mkdir(webBackup, { recursive: true });
  for (const file of ["hierarchy.json", "cards.json", "manifest.json"]) {
    await fs.copyFile(path.join(webDir, file), path.join(webBackup, file));
  }
}

async function buildMasterMatrix(source) {
  const matrix = await readMatrix(source);
  const headers = matrix[0].map(String);
  const idIndex = headers.indexOf("L3_ID");
  if (idIndex < 0) throw new Error("L3_ID column missing");
  const rows = [];
  for (const row of matrix.slice(1)) {
    const id = String(row[idIndex] ?? "");
    if (["G_Others", "A_Others", "P_Others"].includes(id)) continue;
    rows.push(updates[id] ? updateRow(headers, row, updates[id]) : row);
  }
  const evaluationIndex = rows.findIndex((row) => String(row[idIndex]) === "G_SYS_EVAL");
  const performanceIndex = rows.findIndex((row) => String(row[idIndex]) === "G_SYS_PERF");
  if (evaluationIndex >= 0 && performanceIndex > evaluationIndex) {
    const [performanceRow] = rows.splice(performanceIndex, 1);
    rows.splice(evaluationIndex, 0, performanceRow);
  }
  if (rows.length !== 47) throw new Error(`Expected 47 L3 rows, got ${rows.length}`);
  const ids = rows.map((row) => String(row[idIndex]));
  if (new Set(ids).size !== 47) throw new Error("Duplicate L3 IDs after filtering");
  return [headers, ...rows];
}

async function syncL4(file, masterMatrix) {
  const matrix = await readMatrix(file);
  const headers = matrix[0].map(String);
  const masterHeaders = masterMatrix[0].map(String);
  const l3IdIndex = headers.indexOf("L3_ID");
  const masterIdIndex = masterHeaders.indexOf("L3_ID");
  const master = new Map(masterMatrix.slice(1).map((row) => [String(row[masterIdIndex]), rowObject(masterHeaders, row)]));
  const hierarchyFields = [
    "L0_ID", "L0_Title_ko", "L0_Title_en", "L1_ID", "L1_Title_ko", "L1_Title_en",
    "L1_Description_ko", "L1_Description_en", "L2_ID", "L2_Title_ko", "L2_Title_en",
    "L2_Description_ko", "L2_Description_en", "L3_ID", "L3_Title_ko", "L3_Title_en",
    "L3_Description_ko", "L3_Description_en",
  ];
  const rows = matrix.slice(1).map((row) => {
    const l3Id = String(row[l3IdIndex] ?? "");
    const reference = master.get(l3Id);
    if (!reference) throw new Error(`${file}: unknown or removed L3 ${l3Id}`);
    return updateRow(headers, row, Object.fromEntries(hierarchyFields.map((field) => [field, reference[field] ?? ""])));
  });
  await writeMatrix(file, [headers, ...rows]);
  return rows.length;
}

async function sha256(file) {
  return crypto.createHash("sha256").update(await fs.readFile(file)).digest("hex");
}

async function main() {
  await backupInputs();
  const masterMatrix = await buildMasterMatrix(path.join(RELEASE, MASTER_FILE));
  const counts = {};
  for (const directory of DATA_DIRS) {
    const masterFile = path.join(directory, MASTER_FILE);
    await writeMatrix(masterFile, masterMatrix);
    counts[path.relative(ROOT, masterFile)] = 47;
    for (const name of L4_FILES) {
      const file = path.join(directory, name);
      counts[path.relative(ROOT, file)] = await syncL4(file, masterMatrix);
    }
  }
  const hashes = {};
  for (const directory of DATA_DIRS) {
    for (const name of [MASTER_FILE, ...L4_FILES]) {
      const file = path.join(directory, name);
      hashes[path.relative(ROOT, file)] = await sha256(file);
    }
  }
  console.log(JSON.stringify({ counts, hashes, backup: path.relative(ROOT, BACKUP) }, null, 2));
}

await main();
