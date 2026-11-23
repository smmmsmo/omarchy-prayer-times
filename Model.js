// Pure display and validation helpers, shared with the offline regression tests.
var prayerNames = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"];
var methodIds = [0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23];
var methodKeys = ["jafari", "karachi", "isna", "mwl", "makkah", "egypt", "tehran",
  "gulf", "kuwait", "qatar", "singapore", "france", "turkey", "russia", "moonsighting",
  "dubai", "malaysia", "tunisia", "algeria", "indonesia", "morocco", "portugal", "jordan"];
var errorCodes = ["network", "offline", "settings", "location", "coordinates", "response", "solar", "save"];

function neutralize(value) {
  return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function nextEvent(report, now) {
  if (!report || !report.ok || !Array.isArray(report.events)) return null;
  for (var i = 0; i < report.events.length; i++)
    if (report.events[i].start > now) return report.events[i];
  return null;
}

function remaining(seconds) {
  var minutes = Math.max(0, Math.ceil(seconds / 60));
  return {hours: Math.floor(minutes / 60), minutes: minutes % 60};
}

function dateParts(iso) {
  if (typeof iso !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return null;
  var parts = iso.split("-").map(Number);
  var date = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
  return date.toISOString().slice(0, 10) === iso ? parts : null;
}

// Formatting has a fixed DD MMM YYYY order, with localized month names/digits.
function displayDate(iso, months, number) {
  var parts = dateParts(iso);
  if (!parts || !months || months.length !== 12) return "—";
  var day = (parts[2] < 10 ? number(0) : "") + number(parts[2]);
  return day + " " + months[parts[1] - 1] + " " + number(parts[0]);
}

function formatTime(clock, hour24, number, am, pm) {
  if (!clock) return "—";
  var h = hour24 ? clock.h : (clock.h % 12 || 12);
  var hour = (hour24 && h < 10 ? number(0) : "") + number(h);
  var minute = (clock.m < 10 ? number(0) : "") + number(clock.m);
  return hour + ":" + minute + (hour24 ? "" : " " + (clock.h < 12 ? am : pm));
}

function methodOptions(translate) {
  return [{value: "auto", label: translate("methodAuto")}].concat(methodIds.map(function(id, index) {
    return {value: String(id), label: translate(methodKeys[index])};
  }));
}

// Exclude display preferences; changing clock format never needs a request.
function requestSettings(settings) {
  var defaults = {locationMode: "auto", city: "", country: "", state: "", latitude: "",
    longitude: "", locationName: "", method: "auto", school: 0, highLatitude: 3,
    shafaq: "general", ishaEnd: "midnight", offsets: {}, autoRefresh: false};
  var result = {};
  Object.keys(defaults).forEach(function(key) {
    result[key] = settings[key] === undefined ? defaults[key] : settings[key];
  });
  return result;
}

function validReport(r) {
  if (!r || r.schema !== 2 || r.ok !== true) return false;
  if (typeof r.location !== "string" || r.location.length > 304
      || typeof r.timezone !== "string" || r.timezone.length > 80 || !dateParts(r.date)) return false;
  if (!Number.isInteger(r.validFrom) || !Number.isInteger(r.validUntil)
      || r.validFrom < 946684800 || r.validUntil > 4102444800
      || r.validUntil - r.validFrom < 79200 || r.validUntil - r.validFrom > 93600) return false;
  if (!Array.isArray(r.rows) || r.rows.length !== 5
      || !Array.isArray(r.events) || r.events.length > 10
      || !r.clock || typeof r.clock !== "object" || Object.keys(r.clock).length > 32
      || methodIds.indexOf(r.method) < 0 || [0, 1].indexOf(r.school) < 0
      || ["midnight", "fajr"].indexOf(r.ishaEnd) < 0
      || !Array.isArray(r.warnings) || r.warnings.length > 2
      || r.warnings.some(function(w) { return ["solar", "window"].indexOf(w) < 0; })) return false;
  function validTime(epoch) {
    if (epoch === null) return true;
    var c = r.clock[String(epoch)];
    return Number.isInteger(epoch) && epoch >= r.validFrom - 172800
      && epoch < r.validUntil + 172800 && c
      && Number.isInteger(c.h) && c.h >= 0 && c.h < 24
      && Number.isInteger(c.m) && c.m >= 0 && c.m < 60
      && Number.isInteger(c.day) && c.day >= -1 && c.day <= 2;
  }
  for (var i = 0; i < r.rows.length; i++) {
    var row = r.rows[i];
    if (!row || row.name !== prayerNames[i] || !validTime(row.start) || !validTime(row.end)
        || (row.end !== null && (row.start === null || row.end <= row.start))) return false;
  }
  var previous = 0;
  for (var j = 0; j < r.events.length; j++) {
    var e = r.events[j];
    if (!e || prayerNames.indexOf(e.name) < 0 || e.start === null
        || !validTime(e.start) || e.start < previous) return false;
    previous = e.start;
  }
  return ["sunrise", "sunset", "sehri", "iftar", "tomorrowSehri", "tomorrowIftar"].every(function(key) {
    return validTime(r[key]);
  });
}

function parseResponse(text) {
  try {
    if (text.length > 131072) throw new Error("Response too large");
    var result = JSON.parse(text);
    if (validReport(result)) return result;
    if (result && result.schema === 2 && result.ok === false && errorCodes.indexOf(result.error) >= 0)
      return {schema: 2, ok: false, error: result.error};
  } catch (error) {}
  return {schema: 2, ok: false, error: "response"};
}

if (typeof module !== "undefined")
  module.exports = {neutralize: neutralize, nextEvent: nextEvent, remaining: remaining,
    dateParts: dateParts, displayDate: displayDate, formatTime: formatTime, methodOptions: methodOptions,
    methodIds: methodIds, prayerNames: prayerNames, requestSettings: requestSettings,
    validReport: validReport, parseResponse: parseResponse};
