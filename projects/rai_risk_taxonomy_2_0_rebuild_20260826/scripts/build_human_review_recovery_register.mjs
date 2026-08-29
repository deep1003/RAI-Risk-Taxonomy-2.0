#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const project = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const sourceDir = path.join(project, "00_source_snapshot", "csv");
const baselineDir = path.join(project, "03_outputs", "release");
const appliedDir = path.join(project, "05_human_review_round2");
const outputDir = path.join(project, "06_human_review_recovery");

const domains = {
  General: "932056034",
  Agentic: "931437538",
  Physical: "930753013",
};

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') {
        cell += '"';
        i += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        cell += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(cell);
      cell = "";
    } else if (char === "\n") {
      row.push(cell.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  if (cell.length || row.length) {
    row.push(cell.replace(/\r$/, ""));
    rows.push(row);
  }
  const headers = rows.shift().map((value, index) => index === 0 ? value.replace(/^\uFEFF/, "") : value);
  return rows.filter((values) => values.some((value) => value !== "")).map((values) =>
    Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]))
  );
}

function encodeCsv(rows, headers) {
  const escape = (value) => {
    const text = String(value ?? "");
    return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  return `\uFEFF${[headers, ...rows.map((row) => headers.map((header) => row[header] ?? ""))]
    .map((values) => values.map(escape).join(","))
    .join("\n")}\n`;
}

async function readCsv(file) {
  return parseCsv(await fs.readFile(file, "utf8"));
}

async function fileInfo(file, role) {
  const bytes = await fs.readFile(file);
  const rows = parseCsv(bytes.toString("utf8"));
  return {
    Role: role,
    Path: path.relative(project, file),
    Rows: rows.length,
    Columns: rows.length ? Object.keys(rows[0]).length : 0,
    SHA256: crypto.createHash("sha256").update(bytes).digest("hex"),
  };
}

function tokens(text, strictDelete = false) {
  const value = String(text ?? "");
  const result = [];
  const add = (token) => { if (!result.includes(token)) result.push(token); };
  if ((strictDelete ? /삭제\s*제안|카드.{0,12}삭제|리스크.{0,12}삭제|^\s*삭제|\[삭제\]/ : /삭제/).test(value)) add("DELETE");
  if (/통합|중복/.test(value)) add("MERGE");
  if (/분리|분할/.test(value)) add("SPLIT");
  if (/이관|이동|재매핑|재분류|분류하고|매핑/.test(value)) add("REMAP");
  if (/수정|변경|명칭|정의|Title|Description|description|문안|띄어쓰기/.test(value)) add("REWRITE");
  if (/유지/.test(value)) add("KEEP");
  return result;
}

function implementationStatus(actions, ledger, outputs) {
  const decision = ledger.Decision ?? "";
  const changed = ledger.Changed_Fields ?? "";
  const hasOutput = outputs.length > 0;
  const checks = {
    DELETE: /DELETE/.test(decision) && !hasOutput,
    MERGE: /MERGE/.test(decision),
    SPLIT: /SPLIT/.test(decision),
    REMAP: /REASSIGN|REMAP|TRANSFER|MOVE/.test(decision),
    REWRITE: /TEXT|REWRITE|COPYEDIT|LANGUAGE/.test(`${decision}|${changed}`),
    KEEP: hasOutput,
  };
  if (!actions.length) return "NO_EXPLICIT_ROW_ACTION";
  const satisfied = actions.filter((action) => checks[action]).length;
  if (satisfied === actions.length) return "APPARENTLY_APPLIED_REQUIRES_TEXT_AUDIT";
  if (satisfied > 0) return "PARTIALLY_APPLIED";
  return "NOT_EVIDENCED_IN_LEDGER";
}

function columnName(index) {
  let n = index + 1;
  let name = "";
  while (n > 0) {
    n -= 1;
    name = String.fromCharCode(65 + (n % 26)) + name;
    n = Math.floor(n / 26);
  }
  return name;
}

async function main() {
  await fs.mkdir(outputDir, { recursive: true });
  const ledgerPath = path.join(appliedDir, "Human_Review_Round2_Decision_Ledger.csv");
  const ledgerRows = await readCsv(ledgerPath);
  const ledgerByKey = new Map(ledgerRows.map((row) => [`${row.Source_Domain}|${row.Source_Row_Number}`, row]));

  const outputsById = new Map();
  for (const domain of Object.keys(domains)) {
    const file = path.join(appliedDir, `L4_${domain}_Human_Review_Round2_Applied.csv`);
    for (const row of await readCsv(file)) outputsById.set(row.L4_ID, row);
  }

  const register = [];
  const manifest = [];
  manifest.push(await fileInfo(path.join(baselineDir, "L1_L2_L3_Master.csv"), "IMMUTABLE_L3_MASTER"));
  manifest.push(await fileInfo(ledgerPath, "BASELINE_DECISION_LEDGER"));

  for (const [domain, pageId] of Object.entries(domains)) {
    const baselinePath = path.join(baselineDir, `L4_${domain}.csv`);
    const reviewPath = path.join(sourceDir, `L4_${domain}_Human_Review_Round2_KTSPACE_${pageId}_20260828.csv`);
    const appliedPath = path.join(appliedDir, `L4_${domain}_Human_Review_Round2_Applied.csv`);
    manifest.push(await fileInfo(baselinePath, `${domain.toUpperCase()}_BASELINE_INPUT`));
    manifest.push(await fileInfo(reviewPath, `${domain.toUpperCase()}_ROUND2_REVIEW_SOURCE`));
    manifest.push(await fileInfo(appliedPath, `${domain.toUpperCase()}_BASELINE_APPLIED_OUTPUT`));

    const baseline = await readCsv(baselinePath);
    const review = await readCsv(reviewPath);
    if (baseline.length !== review.length) throw new Error(`row count mismatch ${domain}`);
    for (let index = 0; index < baseline.length; index += 1) {
      const before = baseline[index];
      const reviewed = review[index];
      const sourceRowNumber = String(index + 2);
      const ledger = ledgerByKey.get(`${domain}|${sourceRowNumber}`);
      if (!ledger) throw new Error(`missing ledger row ${domain}:${sourceRowNumber}`);
      const afterIds = ledger.L4_ID_After.split("|").map((part) => part.trim()).filter(Boolean);
      const outputs = afterIds.map((id) => outputsById.get(id)).filter(Boolean);
      const reviewComment = reviewed["휴먼검토의견"]?.trim() ?? "";
      const sourceInstruction = before.Source_Instruction_Prompt?.trim() ?? "";
      const reviewActions = tokens(reviewComment, true);
      const sourceActions = tokens(sourceInstruction);
      const directEdits = [];
      for (const field of ["L4_Title_ko", "L4_Title_en", "L4_Description_ko", "L4_Description_en"]) {
        if (Object.hasOwn(reviewed, field) && reviewed[field].trim() !== (before[field] ?? "").trim()) directEdits.push(field);
      }
      const outputL3 = [...new Set(outputs.map((row) => row.L3_ID))];
      const outputOthers = outputL3.some((id) => id.endsWith("Others"));
      const conflicts = [];
      if (reviewActions.includes("KEEP") && reviewActions.includes("DELETE")) conflicts.push("KEEP_VS_DELETE");
      if (reviewActions.includes("DELETE") && reviewActions.some((a) => ["MERGE", "SPLIT", "REMAP", "REWRITE"].includes(a))) conflicts.push("DELETE_VS_OTHER_ACTION");
      register.push({
        Register_ID: `HR2-${String(register.length + 1).padStart(4, "0")}`,
        Source_Domain: domain,
        Source_Row_Number: sourceRowNumber,
        source_row_id: before.source_row_id,
        Source_L4_IDs: before.Source_L4_IDs,
        Baseline_L4_ID: before.L4_ID,
        Baseline_L3_ID: before.L3_ID,
        Baseline_L4_Title_ko: before.L4_Title_ko,
        Baseline_L4_Title_en: before.L4_Title_en,
        Source_Instruction_Prompt: sourceInstruction,
        Human_Review_Comment_Verbatim: reviewComment,
        Directly_Edited_Fields_In_Review_Table: directEdits.join("|"),
        Parsed_Round2_Action_Tokens: reviewActions.join("|"),
        Parsed_Source_Instruction_Tokens: sourceActions.join("|"),
        Instruction_Conflict_Flags: conflicts.join("|"),
        Baseline_Decision: ledger.Decision,
        Baseline_Decision_Rationale: ledger.Decision_Rationale,
        Baseline_Changed_Fields: ledger.Changed_Fields,
        Output_L4_IDs: afterIds.join("|"),
        Output_L3_IDs: outputL3.join("|"),
        Output_L4_Titles_ko: [...new Set(outputs.map((row) => row.L4_Title_ko))].join("|"),
        Output_Count: outputs.length,
        Output_Is_Others: outputOthers ? "YES" : "NO",
        Preliminary_Implementation_Status: implementationStatus(reviewActions, ledger, outputs),
        Recovery_Review_Required: outputOthers || conflicts.length || /PENDING/.test(ledger.Decision) || implementationStatus(reviewActions, ledger, outputs) !== "APPARENTLY_APPLIED_REQUIRES_TEXT_AUDIT" && reviewActions.length ? "YES" : "NO",
        Proposed_Recovery_Action: "",
        Proposed_Target_L1_ID: "",
        Proposed_Target_L3_ID: "",
        Proposed_Merge_Representative_source_row_id: "",
        Proposed_Split_Output_Count: "",
        Recovery_Rationale: "",
        User_Approval_Status: "PENDING",
      });
    }
  }

  const headers = Object.keys(register[0]);
  const manifestHeaders = Object.keys(manifest[0]);
  const reviewRequired = register.filter((row) => row.Recovery_Review_Required === "YES");
  const conflicts = register.filter((row) => row.Instruction_Conflict_Flags !== "");
  const agent1Rows = await readCsv(path.join(outputDir, "Agent1_Methodology_Proposals.csv"));
  const agent2Rows = await readCsv(path.join(outputDir, "Agent2_Lineage_Proposals.csv"));
  const agent1 = new Map(agent1Rows.map((row) => [row.Register_ID, row]));
  const agent2 = new Map(agent2Rows.map((row) => [row.Register_ID, row]));
  const normaliseTargets = (value) => String(value ?? "").split("|").map((part) => part.trim()).filter(Boolean).sort().join("|");
  const comparison = reviewRequired.map((row) => {
    const first = agent1.get(row.Register_ID);
    const second = agent2.get(row.Register_ID);
    if (!first || !second) throw new Error(`missing agent proposal ${row.Register_ID}`);
    const actionAgreement = first.Action === second.Action;
    const targetAgreement = normaliseTargets(first.Target_L3_IDs) === normaliseTargets(second.Target_L3_IDs);
    const mergeAgreement = (first.Merge_Representative_source_row_id ?? "") === (second.Merge_Representative_source_row_id ?? "");
    const reasons = [];
    if (!actionAgreement) reasons.push("ACTION_DISAGREEMENT");
    if (!targetAgreement) reasons.push("TARGET_DISAGREEMENT");
    if (!mergeAgreement && (first.Action === "MERGE" || second.Action === "MERGE")) reasons.push("MERGE_REPRESENTATIVE_DISAGREEMENT");
    if (first.Confidence === "LOW") reasons.push("AGENT1_LOW_CONFIDENCE");
    if (second.User_Decision_Required === "YES") reasons.push("AGENT2_USER_DECISION");
    if (row.Instruction_Conflict_Flags) reasons.push(row.Instruction_Conflict_Flags);
    return {
      Register_ID: row.Register_ID,
      Source_Domain: row.Source_Domain,
      source_row_id: row.source_row_id,
      Baseline_L4_Title_ko: row.Baseline_L4_Title_ko,
      Human_Review_Comment_Verbatim: row.Human_Review_Comment_Verbatim,
      Source_Instruction_Prompt: row.Source_Instruction_Prompt,
      Agent1_Action: first.Action,
      Agent1_Target_L3_IDs: first.Target_L3_IDs,
      Agent1_Merge_Representative: first.Merge_Representative_source_row_id,
      Agent1_Split_Count: first.Split_Count,
      Agent1_Confidence: first.Confidence,
      Agent1_Basis: first.Basis,
      Agent1_Note: first.Reviewer_Note,
      Agent2_Action: second.Action,
      Agent2_Target_L3_IDs: second.Target_L3_IDs,
      Agent2_Merge_Representative: second.Merge_Representative_source_row_id,
      Agent2_Split_Count: second.Split_Count,
      Agent2_Confidence: second.Confidence,
      Agent2_Basis: second.Basis,
      Agent2_Note: second.Reviewer_Note,
      Action_Agreement: actionAgreement ? "YES" : "NO",
      Target_Agreement: targetAgreement ? "YES" : "NO",
      Merge_Representative_Agreement: mergeAgreement ? "YES" : "NO",
      User_Approval_Required: reasons.length ? "YES" : "NO",
      Approval_Reason: reasons.join("|"),
      User_Selected_Action: "",
      User_Selected_Target_L3_IDs: "",
      User_Selected_Merge_Representative: "",
      User_Decision_Note: "",
      User_Approval_Status: "PENDING",
    };
  });
  const approvalRows = comparison.filter((row) => row.User_Approval_Required === "YES");
  const summary = {
    baseline_commit: "6220567cacc93346d5c340eebfdbbcdef660482f",
    source_rows: register.length,
    by_domain: Object.fromEntries(Object.keys(domains).map((domain) => [domain, register.filter((row) => row.Source_Domain === domain).length])),
    rows_with_round2_comments: register.filter((row) => row.Human_Review_Comment_Verbatim).length,
    rows_with_direct_table_edits: register.filter((row) => row.Directly_Edited_Fields_In_Review_Table).length,
    outputs_in_others: register.filter((row) => row.Output_Is_Others === "YES").length,
    recovery_review_required: reviewRequired.length,
    explicit_instruction_conflicts: conflicts.length,
    agent_action_agreements: comparison.filter((row) => row.Action_Agreement === "YES").length,
    agent_target_agreements: comparison.filter((row) => row.Target_Agreement === "YES").length,
    user_approval_rows: approvalRows.length,
    l3_master_sha256: manifest.find((row) => row.Role === "IMMUTABLE_L3_MASTER").SHA256,
  };

  await fs.writeFile(path.join(outputDir, "Human_Review_Instruction_Register.csv"), encodeCsv(register, headers));
  await fs.writeFile(path.join(outputDir, "Recovery_Review_Required.csv"), encodeCsv(reviewRequired, headers));
  await fs.writeFile(path.join(outputDir, "Baseline_Integrity_Manifest.csv"), encodeCsv(manifest, manifestHeaders));
  await fs.writeFile(path.join(outputDir, "Agent_Proposal_Comparison.csv"), encodeCsv(comparison, Object.keys(comparison[0])));
  await fs.writeFile(path.join(outputDir, "User_Approval_Decisions.csv"), encodeCsv(approvalRows, Object.keys(approvalRows[0])));
  await fs.writeFile(path.join(outputDir, "Recovery_Scope_Summary.json"), `${JSON.stringify(summary, null, 2)}\n`);

  const workbook = Workbook.create();
  const summarySheet = workbook.worksheets.add("Summary");
  const registerSheet = workbook.worksheets.add("Instruction Register");
  const reviewSheet = workbook.worksheets.add("Review Required");
  const manifestSheet = workbook.worksheets.add("Integrity Manifest");
  const comparisonSheet = workbook.worksheets.add("Agent Comparison");
  const approvalSheet = workbook.worksheets.add("User Approval");
  summarySheet.showGridLines = false;
  summarySheet.getRange("A1:D1").merge();
  summarySheet.getRange("A1").values = [["RAI Risk Taxonomy 2.0 Human Review Recovery Register"]];
  summarySheet.getRange("A1:D1").format = { fill: "#1F4E78", font: { bold: true, color: "#FFFFFF", size: 15 }, rowHeight: 28 };
  const summaryRows = [
    ["Metric", "Value", "Gate", "Note"],
    ["Baseline commit", summary.baseline_commit, "LOCKED", "Existing valid work is preserved"],
    ["Source rows", summary.source_rows, "808 required", "All source rows must have a terminal disposition"],
    ["Round-2 comments", summary.rows_with_round2_comments, "AUDIT", "Verbatim comments retained"],
    ["Direct table edits", summary.rows_with_direct_table_edits, "AUDIT", "Reviewed table fields changed directly"],
    ["Rows linked to Others", summary.outputs_in_others, "MUST BECOME 0", "No EM rerun"],
    ["Recovery review required", summary.recovery_review_required, "USER REVIEW", "No data transformation yet"],
    ["Explicit conflicts", summary.explicit_instruction_conflicts, "USER DECISION", "Conflicting instructions are not auto-resolved"],
    ["Agent action agreements", summary.agent_action_agreements, `${comparison.length} reviewed`, "Independent action proposals"],
    ["Agent target agreements", summary.agent_target_agreements, `${comparison.length} reviewed`, "Independent L3 proposals"],
    ["User approval rows", summary.user_approval_rows, "APPROVAL GATE", "No delta application before approval"],
    ["L3 master SHA-256", summary.l3_master_sha256, "IMMUTABLE", "Must remain byte-identical"],
  ];
  summarySheet.getRange(`A3:D${summaryRows.length + 2}`).values = summaryRows;
  summarySheet.getRange("A3:D3").format = { fill: "#D9EAF7", font: { bold: true, color: "#17365D" }, borders: { preset: "outside", style: "thin", color: "#9EADBA" } };
  summarySheet.getRange(`A4:A${summaryRows.length + 2}`).format.font = { bold: true, color: "#17365D" };
  summarySheet.getRange(`A3:D${summaryRows.length + 2}`).format.wrapText = true;
  summarySheet.getRange("A:D").format.columnWidth = 28;
  summarySheet.getRange("B:B").format.columnWidth = 44;
  summarySheet.getRange("D:D").format.columnWidth = 48;

  function writeTable(sheet, rows, tableHeaders, tableName) {
    const matrix = [tableHeaders, ...rows.map((row) => tableHeaders.map((header) => row[header] ?? ""))];
    const endColumn = columnName(tableHeaders.length - 1);
    sheet.getRange(`A1:${endColumn}${matrix.length}`).values = matrix;
    sheet.getRange(`A1:${endColumn}1`).format = { fill: "#1F4E78", font: { bold: true, color: "#FFFFFF" }, wrapText: true, rowHeight: 32 };
    sheet.getRange(`A2:${endColumn}${matrix.length}`).format = { wrapText: true, verticalAlignment: "top" };
    sheet.freezePanes.freezeRows(1);
    sheet.freezePanes.freezeColumns(4);
    sheet.showGridLines = false;
    const table = sheet.tables.add(`A1:${endColumn}${matrix.length}`, true, tableName);
    table.style = "TableStyleMedium2";
    table.showFilterButton = true;
  }
  writeTable(registerSheet, register, headers, "InstructionRegisterTable");
  writeTable(reviewSheet, reviewRequired, headers, "ReviewRequiredTable");
  writeTable(manifestSheet, manifest, manifestHeaders, "IntegrityManifestTable");
  writeTable(comparisonSheet, comparison, Object.keys(comparison[0]), "AgentComparisonTable");
  writeTable(approvalSheet, approvalRows, Object.keys(approvalRows[0]), "UserApprovalTable");
  for (const sheet of [registerSheet, reviewSheet]) {
    sheet.getRange("A:AD").format.columnWidth = 18;
    sheet.getRange("I:N").format.columnWidth = 42;
    sheet.getRange("P:R").format.columnWidth = 36;
    sheet.getRange("U:AD").format.columnWidth = 24;
  }
  manifestSheet.getRange("A:A").format.columnWidth = 42;
  manifestSheet.getRange("B:B").format.columnWidth = 76;
  manifestSheet.getRange("C:D").format.columnWidth = 14;
  manifestSheet.getRange("E:E").format.columnWidth = 72;
  for (const sheet of [comparisonSheet, approvalSheet]) {
    sheet.getRange("A:AD").format.columnWidth = 18;
    sheet.getRange("D:F").format.columnWidth = 42;
    sheet.getRange("M:T").format.columnWidth = 26;
    sheet.getRange("Y:AD").format.columnWidth = 28;
  }

  const xlsx = await SpreadsheetFile.exportXlsx(workbook);
  await xlsx.save(path.join(outputDir, "Human_Review_Recovery_Register.xlsx"));

  const previewDir = path.join(outputDir, "_preview");
  await fs.mkdir(previewDir, { recursive: true });
  for (const [sheetName, range] of [
    ["Summary", "A1:D14"],
    ["Instruction Register", "A1:H18"],
    ["Review Required", "A1:H18"],
    ["Integrity Manifest", "A1:E12"],
    ["Agent Comparison", "A1:J18"],
    ["User Approval", "A1:J18"],
  ]) {
    const preview = await workbook.render({ sheetName, range, scale: 1 });
    await fs.writeFile(path.join(previewDir, `${sheetName.replaceAll(" ", "_")}.png`), new Uint8Array(await preview.arrayBuffer()));
  }

  const inspection = await workbook.inspect({ kind: "table", range: "Summary!A1:D14", include: "values,formulas", tableMaxRows: 15, tableMaxCols: 4 });
  const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 50 }, summary: "formula error scan" });
  console.log(inspection.ndjson);
  console.log(errors.ndjson);
  console.log(JSON.stringify(summary, null, 2));
}

await main();
