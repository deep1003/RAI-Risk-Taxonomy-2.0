import fs from "node:fs/promises";
import path from "node:path";
import { Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const output = path.join(root, "02_working", "review_csv");
const expected = { General: 610, Agentic: 85, Physical: 131 };

for (const [domain, count] of Object.entries(expected)) {
  const file = path.join(output, `L4_${domain}_PreMapping_Review.csv`);
  const csv = (await fs.readFile(file, "utf8")).replace(/^\uFEFF/, "");
  const workbook = await Workbook.fromCSV(csv, { sheetName: domain });
  const sheet = workbook.worksheets.getItem(domain);
  const used = sheet.getUsedRange(true);
  const rowCount = used.rowCount;
  const columnCount = used.columnCount;
  if (rowCount !== count + 1 || columnCount !== 25) {
    throw new Error(`${domain}: expected ${count + 1}x25, received ${rowCount}x${columnCount}`);
  }
  const header = sheet.getRange("A1:Y1").values[0];
  const required = ["target_domain", "source_row_id", "title_ko", "title_en", "description_ko", "description_en"];
  for (const field of required) {
    if (!header.includes(field)) throw new Error(`${domain}: missing ${field}`);
  }
  const inspection = await workbook.inspect({
    kind: "table",
    range: `${domain}!A1:I4`,
    include: "values",
    tableMaxRows: 4,
    tableMaxCols: 9,
    maxChars: 1200,
  });
  console.log(JSON.stringify({ domain, dataRows: count, columns: columnCount, inspected: Boolean(inspection.ndjson) }));
}
