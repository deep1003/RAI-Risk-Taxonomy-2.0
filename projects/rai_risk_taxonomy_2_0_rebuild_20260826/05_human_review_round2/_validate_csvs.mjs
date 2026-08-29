import fs from "node:fs/promises";
import path from "node:path";
import { Workbook } from "@oai/artifact-tool";

const folder = path.dirname(new URL(import.meta.url).pathname);
const files = [
  "L4_General_Human_Review_Round2_Applied.csv",
  "L4_Agentic_Human_Review_Round2_Applied.csv",
  "L4_Physical_Human_Review_Round2_Applied.csv",
  "Human_Review_Round2_Decision_Ledger.csv",
  "L3_Human_Review_Round2_Reference.csv",
  "user_directed_operations.csv",
  "L4_Korean_Copyedit_Approved_20260829.csv",
  "L4_English_Copyedit_Approved_20260829.csv",
  "L4_Top10_Similar_Pairs.csv",
  "L4_Top20_Similar_Pairs.csv",
  "L4_Top200_Similar_Pairs.csv",
  "L4_Top1000_SameL3_Similar_Pairs.csv",
];

for (const file of files) {
  const text = await fs.readFile(path.join(folder, file), "utf8");
  const workbook = await Workbook.fromCSV(text, { sheetName: "Data" });
  const inspection = await workbook.inspect({
    kind: "table",
    range: "Data!A1:F4",
    include: "values",
    tableMaxRows: 4,
    tableMaxCols: 6,
    maxChars: 1800,
  });
  console.log(JSON.stringify({ file, inspection: inspection.ndjson }));
}
