import fs from "node:fs/promises";
import path from "node:path";
import { Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const release = path.join(root, "03_outputs", "release");
const expected = {
  "L1_Master.csv": 3,
  "L1_L2_L3_Master.csv": 49,
  "L4_General.csv": 613,
  "L4_Agentic.csv": 77,
  "L4_Physical.csv": 93,
};

for (const [name, rows] of Object.entries(expected)) {
  const csv = (await fs.readFile(path.join(release, name), "utf8")).replace(/^\uFEFF/, "");
  const workbook = await Workbook.fromCSV(csv, { sheetName: "Data" });
  const used = workbook.worksheets.getItem("Data").getUsedRange(true);
  if (used.rowCount !== rows + 1) {
    throw new Error(`${name}: expected ${rows} data rows, received ${used.rowCount - 1}`);
  }
  const inspection = await workbook.inspect({
    kind: "table", range: "Data!A1:I4", include: "values",
    tableMaxRows: 4, tableMaxCols: 9, maxChars: 1000,
  });
  console.log(JSON.stringify({ name, dataRows: rows, columns: used.columnCount, inspected: Boolean(inspection.ndjson) }));
}
