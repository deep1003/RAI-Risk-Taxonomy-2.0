import fs from "node:fs/promises";
import { Workbook } from "@oai/artifact-tool";

const path = "/Users/deep1003/data3/RAI-Risk-Taxonomy/projects/rai_risk_taxonomy_2_0_rebuild_20260826/11_golden_reference_enrichment/L4_Golden_Reference_Ledger.csv";
const csvText = await fs.readFile(path, "utf8");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "GoldenReferences" });
const result = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 5000,
  tableMaxRows: 4,
  tableMaxCols: 24,
  tableMaxCellChars: 80,
});
console.log(result.ndjson);
