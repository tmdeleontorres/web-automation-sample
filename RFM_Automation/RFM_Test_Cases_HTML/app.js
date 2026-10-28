/* RFM Test Case Manager — editable UI over data.js */
(function () {
  "use strict";

  var STORAGE_KEY = "rfm_test_cases_v1";
  var COLUMNS = ["TC ID","Module","Test Type","Priority","Title","Preconditions",
                 "Test Steps","Expected Result","Status","Remarks"];
  var STATUSES = ["Not Executed","Pass","Fail","Blocked","In Review"];
  var KEYMAP = {
    id:["TC ID"], tc:["TC ID"], module:["Module"], mod:["Module"],
    type:["Test Type"], test:["Test Type"], priority:["Priority"], pri:["Priority"],
    status:["Status"], title:["Title"], pre:["Preconditions"], precondition:["Preconditions"],
    steps:["Test Steps"], step:["Test Steps"], expected:["Expected Result"], exp:["Expected Result"],
    remarks:["Remarks"], note:["Remarks"]
  };

  /* ---------- state ---------- */

  /** index.html?reset=1 -> set every Status back to "Not Executed".
      Clears the browser working copy only (case edits are kept); the automation
      files results.js / test_results.json are wiped separately on disk. */
  (function resetStatusesIfRequested() {
    if (!/[?&]reset=1\b/.test(location.search)) return;
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      var list = raw ? JSON.parse(raw) : null;
      if (Array.isArray(list)) {
        list.forEach(function (c) { c.Status = "Not Executed"; delete c._auto; });
        localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
      }
    } catch (e) { /* corrupted storage - fall through to defaults */ }
    history.replaceState(null, "", location.pathname + location.hash);
  })();

  var cases = load();
  var filters = { q:"", Module:"", "Test Type":"", Priority:"", Status:"" };
  var sort = { key:"TC ID", dir:1 };
  var editingIndex = -1; // -1 = new

  function load() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        var parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length) return mergeMissing(parsed);
      }
    } catch (e) { /* fall through to defaults */ }
    return clone(window.DEFAULT_TEST_CASES || []);
  }
  /** User-edited cases in localStorage always win, but scenarios added to the
      master CSV / data.js afterwards must still appear in the sheet. */
  function mergeMissing(stored) {
    var defs = window.DEFAULT_TEST_CASES || [];
    if (!defs.length) return stored;
    var have = {};
    stored.forEach(function (c) { have[String(c["TC ID"]).toLowerCase()] = true; });
    var missing = defs.filter(function (c) {
      return !have[String(c["TC ID"]).toLowerCase()];
    });
    if (missing.length) {
      stored = stored.concat(clone(missing));
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(stored)); }
      catch (e) { /* storage quota - keep them in memory only */ }
    }
    return stored;
  }
  function save() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(cases)); }
    catch (e) { toast("Could not save to local storage"); }
  }
  function clone(x) { return JSON.parse(JSON.stringify(x)); }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
      .replace(/"/g,"&quot;").replace(/'/g,"&#39;");
  }
  function slug(s) { return String(s).toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,""); }

  /* ---------- automation results (pytest writes results.js) ---------- */
  var lastResultToken = null;

  /**
   * Merge window.TEST_RESULTS (written by utils/results_report.py) into the
   * sheet. Called once at boot and again every few seconds while the suite runs,
   * so the Status column tracks the live test run.
   */
  function applyAutomationResults() {
    var R = window.TEST_RESULTS;
    if (!R || !R.cases) return false;
    var changed = false;
    Object.keys(R.cases).forEach(function (tc) {
      var rec = R.cases[tc];
      var target = null;
      for (var i = 0; i < cases.length; i++) {
        if (String(cases[i]["TC ID"]).toLowerCase() === String(tc).toLowerCase()) {
          target = cases[i]; break;
        }
      }
      if (!target) return;
      target._auto = rec;
      if (target.Status !== rec.status) { target.Status = rec.status; changed = true; }
    });
    var token = JSON.stringify(R.meta || {});
    if (token !== lastResultToken) { lastResultToken = token; changed = true; }
    if (changed) save();
    return changed;
  }

  function autoInfo(c) {
    if (!c || !c._auto) return "";
    var a = c._auto;
    return " · automation: " + a.status + (a.at ? " @ " + a.at : "") +
           (a.duration != null ? " (" + a.duration + "s)" : "");
  }

  /** Re-load results.js with a cache-buster so a running suite shows up live. */
  function pollResults() {
    if (document.hidden) return;
    var s = document.createElement("script");
    s.src = "results.js?_=" + Date.now();
    s.onload = function () {
      try { if (applyAutomationResults()) render(); }
      finally { if (s.parentNode) s.parentNode.removeChild(s); }
    };
    s.onerror = function () { if (s.parentNode) s.parentNode.removeChild(s); };
    document.body.appendChild(s);
  }

  /* ---------- filtering / sorting ---------- */
  function matches(c, ignoreModule) {
    if (!ignoreModule && filters.Module && c.Module !== filters.Module) return false;
    if (filters["Test Type"] && c["Test Type"] !== filters["Test Type"]) return false;
    if (filters.Priority && c.Priority !== filters.Priority) return false;
    if (filters.Status && c.Status !== filters.Status) return false;
    var tokens = filters.q.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (!tokens.length) return true;
    var hay = COLUMNS.map(function (k) { return c[k]; }).join(" ").toLowerCase();
    return tokens.every(function (t) {
      var m = /^([a-z]+):(.*)$/i.exec(t);
      if (m) {
        var cols = KEYMAP[m[1].toLowerCase()];
        var val = m[2].toLowerCase();
        if (cols && val) {
          return cols.some(function (k) {
            return String(c[k] == null ? "" : c[k]).toLowerCase().indexOf(val) !== -1;
          });
        }
      }
      return hay.indexOf(t) !== -1;
    });
  }

  function sortRows(list) {
    var k = sort.key;
    return list.slice().sort(function (a, b) {
      var x = String(a[k] == null ? "" : a[k]), y = String(b[k] == null ? "" : b[k]);
      if (k === "Priority") { var o = { High:0, Medium:1, Low:2 }; x = o[x]; y = o[y]; }
      if (x < y) return -1 * sort.dir;
      if (x > y) return 1 * sort.dir;
      return 0;
    });
  }

  function visible() {
    return sortRows(cases.filter(function (c) { return matches(c, false); }));
  }

  /* ---------- module tabs ---------- */
  function renderTabs() {
    var mods = unique("Module");
    var counts = {}, total = 0;
    cases.forEach(function (c) {
      if (!matches(c, true)) return;           // respect search / type / priority / status
      counts[c.Module] = (counts[c.Module] || 0) + 1;
      total++;
    });

    var html = ['<button class="tab' + (filters.Module ? "" : " active") + '" data-mod="">All modules <span class="cnt">' + total + "</span></button>"];
    mods.forEach(function (m) {
      var n = counts[m] || 0;
      html.push(
        '<button class="tab' + (filters.Module === m ? " active" : "") + (n ? "" : " zero") +
        '" data-mod="' + esc(m) + '" title="' + esc(m) + '">' + esc(m) +
        ' <span class="cnt">' + n + "</span></button>"
      );
    });
    var el = document.getElementById("tabs");
    el.innerHTML = html.join("");
    var active = el.querySelector(".tab.active");
    if (active && active.scrollIntoView) active.scrollIntoView({ block:"nearest", inline:"nearest" });
  }

  /* ---------- render ---------- */
  function render() {
    renderStats();
    renderFilters();
    renderTabs();

    var rows = visible();
    var html = rows.map(function (c) {
      var i = cases.indexOf(c);
      var typeCls = "t-" + slug(c["Test Type"]);
      var priCls = "p-" + slug(c.Priority);
      var stCls = "s-" + slug(c.Status);
      return "<tr>" +
        '<td class="c-id">' + esc(c["TC ID"]) + "</td>" +
        "<td>" + esc(c.Module) + "</td>" +
        '<td><span class="badge ' + typeCls + '">' + esc(c["Test Type"]) + "</span></td>" +
        '<td class="' + priCls + '">' + esc(c.Priority) + "</td>" +
        '<td class="c-title">' + esc(c.Title) + "</td>" +
        "<td>" + esc(c.Preconditions) + "</td>" +
        '<td class="c-steps">' + esc(c["Test Steps"]) + "</td>" +
        '<td class="c-exp">' + esc(c["Expected Result"]) + "</td>" +
        '<td class="col-status"><span class="badge s-badge ' + stCls +
          (c._auto ? " has-auto" : "") + '" data-cycle="' + i + '" title="' +
          esc("Click to cycle status" + autoInfo(c)) + '">' + esc(c.Status) +
          (c._auto ? '<i class="auto-dot" aria-hidden="true"></i>' : "") + "</span></td>" +
        "<td>" + esc(c.Remarks) + "</td>" +
        '<td class="c-actions">' +
          '<button class="btn btn-sm" data-edit="' + i + '">Edit</button> ' +
          '<button class="btn btn-sm" data-dup="' + i + '">Duplicate</button> ' +
          '<button class="btn btn-sm" data-del="' + i + '">Delete</button>' +
        "</td>" +
      "</tr>";
    }).join("");

    var tbody = document.getElementById("tbody");
    tbody.innerHTML = html;
    var emptyEl = document.getElementById("empty");
    emptyEl.hidden = rows.length !== 0;
    if (!emptyEl.hidden) {
      emptyEl.textContent = filters.Module
        ? 'No test cases in "' + filters.Module + '" match your filters.'
        : "No test cases match your filters.";
    }
    document.getElementById("resultCount").textContent =
      rows.length + " of " + cases.length + " test cases";

    var ths = document.querySelectorAll("thead th[data-sort]");
    Array.prototype.forEach.call(ths, function (th) {
      th.classList.remove("sorted-asc", "sorted-desc");
      if (th.dataset.sort === sort.key) th.classList.add(sort.dir === 1 ? "sorted-asc" : "sorted-desc");
    });

    var meta = (window.TEST_RESULTS || {}).meta || {};
    var autoTxt = meta.lastRun
      ? "  ·  automation " + meta.lastRun + ": " + (meta.pass || 0) + " pass / " +
        (meta.fail || 0) + " fail / " + (meta.blocked || 0) + " blocked"
      : "  ·  no automation run yet";
    document.getElementById("footInfo").textContent =
      cases.length + " test cases · " + unique("Module").length +
      " modules · last change saved locally" + autoTxt;
  }

  function unique(key) {
    var seen = {}, out = [];
    cases.forEach(function (c) { if (c[key] && !seen[c[key]]) { seen[c[key]] = 1; out.push(c[key]); } });
    return out.sort();
  }

  function renderStats() {
    var count = function (t) { return cases.filter(function (c) { return c["Test Type"] === t; }).length; };
    var pass = cases.filter(function (c) { return c.Status === "Pass"; }).length;
    var fail = cases.filter(function (c) { return c.Status === "Fail"; }).length;
    var cards = [
      ["tot", cases.length, "Total Cases"],
      ["hp", count("Happy Path"), "Happy Path"],
      ["neg", count("Negative"), "Negative"],
      ["edge", count("Edge Case") + count("Boundary"), "Edge / Boundary"],
      ["", pass + "/" + fail, "Passed / Failed"],
      ["", unique("Module").length, "Modules"]
    ];
    document.getElementById("stats").innerHTML = cards.map(function (c) {
      return '<div class="stat ' + c[0] + '"><b>' + c[1] + "</b><span>" + c[2] + "</span></div>";
    }).join("");
  }

  function renderFilters() {
    fill("fType", "Test Type", "All Test Types");
    fill("fPriority", "Priority", "All Priorities");
    fill("fStatus", "Status", "All Statuses");
    document.getElementById("moduleList").innerHTML =
      unique("Module").map(function (m) { return '<option value="' + esc(m) + '">'; }).join("");

    function fill(id, key, label) {
      var el = document.getElementById(id);
      var cur = filters[key];
      var opts = ['<option value="">' + label + "</option>"].concat(unique(key).map(function (v) {
        return '<option value="' + esc(v) + '"' + (v === cur ? " selected" : "") + ">" + esc(v) + "</option>";
      }));
      el.innerHTML = opts.join("");
      el.value = cur;
    }
  }

  /* ---------- modal ---------- */
  function openModal(index) {
    editingIndex = index;
    var f = document.getElementById("tcForm");
    f.reset();
    document.getElementById("formHint").textContent = "";
    document.getElementById("modalTitle").textContent = index === -1 ? "Add Test Case" : "Edit Test Case";

    var src = index === -1 ? nextId() : cases[index];
    COLUMNS.forEach(function (k) {
      if (f.elements[k]) f.elements[k].value = src[k] == null ? "" : src[k];
    });
    if (index === -1) f.elements.Status.value = "Not Executed";
    document.getElementById("backdrop").hidden = false;
    setTimeout(function () { document.getElementById("fId").focus(); }, 30);
  }
  function closeModal() { document.getElementById("backdrop").hidden = true; editingIndex = -1; }

  function nextId() {
    var max = 0;
    cases.forEach(function (c) {
      var m = /(\d+)\s*$/.exec(c["TC ID"] || "");
      if (m) max = Math.max(max, parseInt(m[1], 10));
    });
    return "TC-NEW-" + String(max + 1).padStart(3, "0");
  }

  function submitForm(e) {
    e.preventDefault();
    var f = document.getElementById("tcForm");
    var obj = {};
    COLUMNS.forEach(function (k) { obj[k] = f.elements[k] ? f.elements[k].value.trim() : ""; });

    if (!obj["TC ID"] || !obj.Title) { document.getElementById("formHint").textContent = "TC ID and Title are required."; return; }
    var dup = cases.findIndex(function (c, i) {
      return c["TC ID"].toLowerCase() === obj["TC ID"].toLowerCase() && i !== editingIndex;
    });
    if (dup !== -1) { document.getElementById("formHint").textContent = "TC ID already exists (" + cases[dup].Module + ")."; return; }

    if (editingIndex === -1) { cases.push(obj); toast("Test case " + obj["TC ID"] + " added"); }
    else { cases[editingIndex] = obj; toast(obj["TC ID"] + " updated"); }
    save(); closeModal(); render();
  }

  /* ---------- row actions ---------- */
  function onTableClick(e) {
    var t = e.target.closest("button, span[data-cycle]");
    if (!t) return;
    if (t.dataset.edit != null) return openModal(+t.dataset.edit);
    if (t.dataset.dup != null) {
      var copy = clone(cases[+t.dataset.dup]);
      copy["TC ID"] = copy["TC ID"] + "-COPY";
      cases.splice(+t.dataset.dup + 1, 0, copy);
      save(); render(); toast("Duplicated as " + copy["TC ID"]); return;
    }
    if (t.dataset.del != null) {
      var c = cases[+t.dataset.del];
      if (confirm("Delete " + c["TC ID"] + " — " + c.Title + "?")) {
        cases.splice(+t.dataset.del, 1); save(); render(); toast("Deleted " + c["TC ID"]);
      }
      return;
    }
    if (t.dataset.cycle != null) {
      var i = +t.dataset.cycle;
      var cur = cases[i].Status;
      var next = STATUSES[(STATUSES.indexOf(cur) + 1) % STATUSES.length];
      cases[i].Status = next; save(); render();
    }
  }

  /* ---------- CSV ---------- */
  function toCSV(rows) {
    var q = function (v) { return '"' + String(v == null ? "" : v).replace(/"/g, '""') + '"'; };
    return [COLUMNS.map(q).join(",")]
      .concat(rows.map(function (r) { return COLUMNS.map(function (k) { return q(r[k]); }).join(","); }))
      .join("\r\n");
  }
  function parseCSV(text) {
    var rows = [], row = [], field = "", inQ = false, i = 0;
    text = text.replace(/^\uFEFF/, "");
    while (i < text.length) {
      var ch = text[i];
      if (inQ) {
        if (ch === '"') {
          if (text[i + 1] === '"') { field += '"'; i += 2; continue; }
          inQ = false; i++; continue;
        }
        field += ch; i++; continue;
      }
      if (ch === '"') { inQ = true; i++; continue; }
      if (ch === ",") { row.push(field); field = ""; i++; continue; }
      if (ch === "\r") { i++; continue; }
      if (ch === "\n") { row.push(field); rows.push(row); row = []; field = ""; i++; continue; }
      field += ch; i++;
    }
    if (field.length || row.length) { row.push(field); rows.push(row); }
    return rows.filter(function (r) { return r.some(function (v) { return v.trim() !== ""; }); });
  }
  function download(name, text) {
    var blob = new Blob([text], { type: "text/csv;charset=utf-8;" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }

  function importCSV(file) {
    var reader = new FileReader();
    reader.onload = function () {
      var rows = parseCSV(String(reader.result));
      if (rows.length < 2) { toast("CSV has no data rows"); return; }
      var head = rows[0].map(function (h) { return h.trim(); });
      var missing = COLUMNS.filter(function (c) { return head.indexOf(c) === -1; });
      if (missing.length) { toast("Missing columns: " + missing.join(", ")); return; }
      var list = rows.slice(1).map(function (r) {
        var o = {};
        COLUMNS.forEach(function (c) { o[c] = (r[head.indexOf(c)] || "").trim(); });
        if (!o.Status) o.Status = "Not Executed";
        return o;
      });
      if (!confirm("Replace the current " + cases.length + " test cases with " + list.length + " imported rows?")) return;
      cases = list; save(); render(); toast("Imported " + list.length + " test cases");
    };
    reader.readAsText(file, "utf-8");
  }

  /* ---------- toast ---------- */
  var toastTimer;
  function toast(msg) {
    var el = document.getElementById("toast");
    el.textContent = msg; el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.hidden = true; }, 2600);
  }

  /* ---------- wiring ---------- */
  document.getElementById("search").addEventListener("input", function (e) {
    filters.q = e.target.value;
    // "module:Some Module" in the search box also switches the tab (exact module name)
    var m = /(?:^|\s)module:("[^"]+"|\S+)/i.exec(filters.q);
    if (m) {
      var want = m[1].replace(/"/g, "").toLowerCase();
      var hit = unique("Module").filter(function (x) { return x.toLowerCase() === want; })[0];
      if (hit) filters.Module = hit;
    }
    render();
  });
  [["fType","Test Type"],["fPriority","Priority"],["fStatus","Status"]].forEach(function (p) {
    document.getElementById(p[0]).addEventListener("change", function (e) { filters[p[1]] = e.target.value; render(); });
  });
  document.getElementById("tabs").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-mod]");
    if (!b) return;
    filters.Module = b.dataset.mod;
    render();
  });
  document.getElementById("btnClear").addEventListener("click", function () {
    filters = { q:"", Module:"", "Test Type":"", Priority:"", Status:"" };
    document.getElementById("search").value = ""; render();
  });
  Array.prototype.forEach.call(document.querySelectorAll("thead th[data-sort]"), function (th) {
    th.addEventListener("click", function () {
      var k = th.dataset.sort;
      if (sort.key === k) sort.dir *= -1; else { sort.key = k; sort.dir = 1; }
      render();
    });
  });
  document.getElementById("tbody").addEventListener("click", onTableClick);
  document.getElementById("btnAdd").addEventListener("click", function () { openModal(-1); });
  document.getElementById("tcForm").addEventListener("submit", submitForm);
  document.getElementById("btnClose").addEventListener("click", closeModal);
  document.getElementById("btnCancel").addEventListener("click", closeModal);
  document.getElementById("backdrop").addEventListener("click", function (e) { if (e.target.id === "backdrop") closeModal(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeModal(); });

  document.getElementById("btnExport").addEventListener("click", function () {
    download("RFM_Test_Cases.csv", toCSV(cases));
    toast("Exported " + cases.length + " test cases");
  });
  document.getElementById("btnImport").addEventListener("click", function () {
    document.getElementById("fileInput").click();
  });
  document.getElementById("fileInput").addEventListener("change", function (e) {
    if (e.target.files[0]) importCSV(e.target.files[0]);
    e.target.value = "";
  });
  document.getElementById("btnReset").addEventListener("click", function () {
    if (confirm("Discard all local edits and restore the original 134 test cases?")) {
      cases = clone(window.DEFAULT_TEST_CASES || []); save(); render(); toast("Reset to original test cases");
    }
  });

  applyAutomationResults();
  render();
  setInterval(pollResults, 5000);   // live status while the pytest run is going
})();
