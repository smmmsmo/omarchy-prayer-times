const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.join(__dirname, "..");
const model = require(path.join(root, "Model.js"));
let count = 0;
function check(name, fn) { fn(); count++; }

check("fixed date order and leading zero", () => {
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  assert.equal(model.displayDate("2026-11-24", months, String), "24 Nov 2026");
  assert.equal(model.displayDate("2027-01-05", months, String), "05 Jan 2027");
  assert.equal(model.displayDate("2026-02-30", months, String), "—");
  assert.equal(model.displayDate("2028-02-29", months, String), "29 Feb 2028");
});
check("localized digits", () => {
  const digits = n => String(n).replace(/\d/g, d => "০১২৩৪৫৬৭৮৯"[Number(d)]);
  assert.equal(model.displayDate("2026-11-05", Array(12).fill("নভে"), digits), "০৫ নভে ২০২৬");
});
check("time formatting and midnight", () => {
  assert.equal(model.formatTime({h: 0, m: 5}, false, String, "AM", "PM"), "12:05 AM");
  assert.equal(model.formatTime({h: 12, m: 0}, false, String, "AM", "PM"), "12:00 PM");
  assert.equal(model.formatTime({h: 5, m: 0}, true, String, "", ""), "05:00");
  assert.equal(model.formatTime(null, true, String, "", ""), "—");
});
check("countdown boundary", () => {
  assert.deepEqual(model.remaining(3661), {hours: 1, minutes: 2});
  assert.deepEqual(model.remaining(-60), {hours: 0, minutes: 0});
  assert.equal(model.nextEvent({ok: true, events: [{name: "Fajr", start: 200}]}, 200), null);
});
check("display settings do not trigger network refetch", () => {
  assert.deepEqual(model.requestSettings({hour24: true}), model.requestSettings({hour24: false}));
  assert.notDeepEqual(model.requestSettings({method: 0}), model.requestSettings({method: "auto"}));
});
check("all method options", () => {
  const options = model.methodOptions(String);
  assert.equal(options.length, 24);
  assert.equal(options.find(o => o.value === "0").label, "jafari");
  assert.equal(options.find(o => o.value === "7").label, "tehran");
});
check("malformed responses", () => {
  for (const text of ["", "null", "[]", "<img>", "{}", "x".repeat(131073)])
    assert.equal(model.parseResponse(text).ok, false);
  assert.deepEqual(model.parseResponse('{"schema":2,"ok":false,"error":"network"}'),
    {schema: 2, ok: false, error: "network"});
});
check("UI has plain-text-only sinks", () => {
  for (const file of fs.readdirSync(root).filter(n => n.endsWith(".qml"))) {
    const qml = fs.readFileSync(path.join(root, file), "utf8");
    if (file === "PlainLabel.qml") assert.match(qml, /textFormat: Text\.PlainText/);
    else assert.doesNotMatch(qml, /\bText\s*\{/);
  }
  const bar = fs.readFileSync(path.join(root, "BarWidget.qml"), "utf8");
  assert.match(bar, /tooltipText: ""/);
  assert.doesNotMatch(bar, /☪/);
});
check("catalog placeholders and fallback keys", () => {
  const directory = path.join(root, "i18n");
  const en = JSON.parse(fs.readFileSync(path.join(directory, "en.json"), "utf8"));
  for (const file of fs.readdirSync(directory)) {
    const catalog = JSON.parse(fs.readFileSync(path.join(directory, file), "utf8"));
    for (const [key, value] of Object.entries(catalog)) {
      assert.equal(typeof value, "string");
      assert.ok(en[key] !== undefined, `${file}: unknown key ${key}`);
      assert.deepEqual((value.match(/%\d/g) || []).sort(), (en[key].match(/%\d/g) || []).sort(),
        `${file}: mismatched placeholders in ${key}`);
    }
  }
  model.methodOptions(String).forEach(o => assert.ok(en[o.label], `missing method key: ${o.label}`));
});
if (process.argv[2]) check("backend/frontend contract and malicious inputs", () => {
  const report = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  assert.equal(model.validReport(report), true);
  for (const mutate of [
    r => r.rows[0].name = '<img src="https://example.invalid/tracker">',
    r => r.events = Array(100).fill(r.events[0]),
    r => r.clock[String(r.sehri)].h = 99,
    r => r.rows[0].end = r.rows[0].start - 1,
    r => r.date = "2026-02-30",
    r => r.schema = 1
  ]) {
    const copy = structuredClone(report); mutate(copy);
    assert.equal(model.validReport(copy), false);
  }
  const polar = structuredClone(report);
  polar.rows.forEach(r => {r.start = null; r.end = null});
  polar.events = [];
  ["sehri", "iftar", "sunrise", "sunset", "tomorrowSehri", "tomorrowIftar"].forEach(k => polar[k] = null);
  polar.clock = {};
  polar.warnings = ["solar"];
  assert.equal(model.validReport(polar), true);
});
console.log(`${count} JavaScript/display/security test groups passed.`);
