/**
 * Pair-judgment survey store — Google Apps Script web app.
 *
 * Deployment (once, ~5 minutes):
 *   1. sheets.new  →  name the spreadsheet "pair_judgment_responses"
 *   2. Extensions → Apps Script → paste this file over Code.gs
 *   3. Deploy → New deployment → type "Web app"
 *        Execute as: Me
 *        Who has access: Anyone
 *   4. Copy the /exec URL and put it in
 *      data/experiments/review/survey_endpoint.txt (single line), commit, push.
 *
 * POST  {rater, saved_at, survey_sha, verdicts, notes}  → appends one row
 * GET   ?key=<READ_KEY>                                 → returns all rows as JSON
 */
var READ_KEY = 'rai-pairs-2026';   // change if you want a private read key

function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var d = JSON.parse(e.postData.contents);
    if (!d.rater || !d.verdicts || d.verdicts.length !== 135) {
      return json_({ok: false, error: 'invalid payload'});
    }
    var sh = sheet_();
    sh.appendRow([
      new Date().toISOString(),
      String(d.rater).slice(0, 80),
      String(d.saved_at || ''),
      String(d.survey_sha || ''),
      String(d.verdicts),
      JSON.stringify(d.notes || {}).slice(0, 45000)
    ]);
    return json_({ok: true, rows: sh.getLastRow() - 1});
  } catch (err) {
    return json_({ok: false, error: String(err)});
  } finally {
    lock.releaseLock();
  }
}

function doGet(e) {
  if (!e.parameter || e.parameter.key !== READ_KEY) {
    return json_({ok: false, error: 'missing or wrong key'});
  }
  var sh = sheet_();
  var rows = sh.getDataRange().getValues();
  var out = [];
  for (var i = 1; i < rows.length; i++) {
    out.push({
      received_at: rows[i][0], rater: rows[i][1], saved_at: rows[i][2],
      survey_sha: rows[i][3], verdicts: rows[i][4],
      notes: safeParse_(rows[i][5])
    });
  }
  return json_({ok: true, responses: out});
}

function sheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('responses');
  if (!sh) {
    sh = ss.insertSheet('responses');
    sh.appendRow(['received_at', 'rater', 'saved_at', 'survey_sha',
                  'verdicts', 'notes_json']);
  }
  return sh;
}
function safeParse_(s) { try { return JSON.parse(s); } catch (e) { return {}; } }
function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o))
    .setMimeType(ContentService.MimeType.JSON);
}
