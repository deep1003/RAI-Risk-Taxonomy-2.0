import fs from "node:fs/promises";
import path from "node:path";

const inputPath = "/tmp/rai_round4_confluence_tables.json";
const outputDir = path.resolve(
  "/Users/deep1003/data3/RAI-Risk-Taxonomy/projects/rai_risk_taxonomy_2_0_rebuild_20260826/00_source_snapshot/csv",
);

const sources = {
  general: {
    pageId: "937139849",
    fileName: "L4_General_Human_Review_Round4_KTSPACE_937139849_20260901.csv",
  },
  agentic: {
    pageId: "937205808",
    fileName: "L4_Agentic_Human_Review_Round4_KTSPACE_937205808_20260901.csv",
  },
  physical: {
    pageId: "938216713",
    fileName: "L4_Physical_Human_Review_Round4_KTSPACE_938216713_20260901.csv",
  },
};

function csvCell(value) {
  const text = value == null ? "" : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function toCsv(rows) {
  return rows.map((row) => row.map(csvCell).join(",")).join("\r\n") + "\r\n";
}

const payload = JSON.parse(await fs.readFile(inputPath, "utf8"));
await fs.mkdir(outputDir, { recursive: true });

for (const [domain, source] of Object.entries(sources)) {
  const rows = payload[domain];
  if (!Array.isArray(rows) || rows.length < 2) {
    throw new Error(`Missing table rows for ${domain}`);
  }
  const width = rows[0].length;
  if (width !== 26 || rows.some((row) => row.length !== width)) {
    throw new Error(`Unexpected schema for ${domain}: expected 26 columns`);
  }
  rows[0][25] = "휴먼검수 4차 의견";
  await fs.writeFile(path.join(outputDir, source.fileName), `\uFEFF${toCsv(rows)}`, "utf8");
}

