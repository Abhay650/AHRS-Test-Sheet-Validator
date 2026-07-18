const state = {
  rows: [],
  testResultCols: [],
  results: [], // accumulated per-file detection results
};

const sheetEl = document.getElementById("sheet");
const statusLabel = document.getElementById("statusLabel");
const toastEl = document.getElementById("toast");

function toast(msg, warn = false) {
  const el = document.createElement("div");
  el.className = "toast-item" + (warn ? " warn" : "");
  el.textContent = msg;
  toastEl.appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

async function loadRows() {
  const res = await fetch("/api/rows");
  const data = await res.json();
  state.rows = data.rows;
  state.testResultCols = data.test_result_cols;
  drawTable();
}

async function recompute() {
  const res = await fetch("/api/compute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ results: state.results }),
  });
  const data = await res.json();
  drawTable(data.computed);
}

function drawTable(computed) {
  const cols = state.testResultCols;
  let html = "";

  // header
  html += `<thead>
    <tr>
      <th rowspan="2">SI.<br>No.</th>
      <th rowspan="2">Name of Parameter</th>
      <th colspan="2">Points as per RK (Part2)<br>Tech Req. / Test Pro.</th>
      <th colspan="2">Requirement of parameter<br>Nominal value / Maxm Deviation</th>
      <th colspan="${cols.length}">Test Result</th>
      <th class="rmse-header"></th>
    </tr>
    <tr class="subhead">
      <th>Tech.<br>Req.</th>
      <th>Test<br>Pro.</th>
      <th>Nominal<br>value</th>
      <th>Maxm<br>Deviation</th>
      ${cols.map((c) => `<th>${c}</th>`).join("")}
      <th class="rmse-header">2*RMSE</th>
    </tr>
  </thead>`;

  html += "<tbody>";
  let idx = 0;
  for (const row of state.rows) {
    if (row.sub) {
      html += `<tr class="row-heading">
        <td>${row.sl || ""}</td>
        <td>${row.sub}</td>
        <td>${row.tech || ""}</td>
        <td>${row.test || ""}</td>
        <td></td>
        <td></td>
        ${cols.map(() => `<td class="na-cell">N/A</td>`).join("")}
        <td class="rmse-col"></td>
      </tr>`;
    }

    const c = computed ? computed[idx] : null;
    const value = c ? c.value : "N/A";
    const color = c ? c.color : "black";

    html += `<tr>
      <td></td>
      <td>${row.angle}</td>
      <td></td>
      <td></td>
      <td>${row.nominal}</td>
      <td>${row.maxdev}</td>
      ${cols.map(() => `<td class="na-cell">N/A</td>`).join("")}
      <td class="rmse-col" style="color:${color}">${value}</td>
    </tr>`;
    idx++;
  }
  html += "</tbody>";

  sheetEl.innerHTML = html;
}

// ---- Upload ----
document.getElementById("uploadBtn").addEventListener("click", () => {
  document.getElementById("fileInput").click();
});

document.getElementById("fileInput").addEventListener("change", async (e) => {
  const files = e.target.files;
  if (!files || files.length === 0) return;

  const form = new FormData();
  for (const f of files) form.append("files", f);

  try {
    const res = await fetch("/api/process", { method: "POST", body: form });
    const data = await res.json();
    state.results.push(...data.results);
    statusLabel.textContent = `${state.results.length} file(s) loaded`;
    await recompute();
    if (data.problems && data.problems.length) {
      toast(`${data.problems.length} file(s) had issues — check filenames`, true);
    } else {
      toast(`${files.length} file(s) processed`);
    }
  } catch (err) {
    toast("Upload failed: " + err.message, true);
  } finally {
    e.target.value = "";
  }
});

// ---- Reset ----
document.getElementById("resetBtn").addEventListener("click", async () => {
  if (state.results.length === 0) return;
  if (!confirm("This will delete all uploaded entries and reset the sheet to blank (N/A).\n\nThis cannot be undone. Continue?")) return;
  state.results = [];
  statusLabel.textContent = "0 file(s) loaded";
  drawTable();
});

// ---- Save / Export ----
document.getElementById("saveBtn").addEventListener("click", async () => {
  try {
    const res = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ results: state.results }),
    });
    if (!res.ok) throw new Error("Export failed");
    const blob = await res.blob();
    const disp = res.headers.get("Content-Disposition") || "";
    const match = disp.match(/filename=(.+)/);
    const filename = match ? match[1] : "SBKV_Test_Sheet.txt";

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast("Sheet saved");
  } catch (err) {
    toast("Save failed: " + err.message, true);
  }
});

loadRows();
