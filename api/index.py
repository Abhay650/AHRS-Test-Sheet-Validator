"""
SBKV TEST SHEET - FastAPI backend
----------------------------------
Same detection/computation logic as the original Tkinter desktop app,
exposed as a small JSON API so a browser frontend can drive it.

Endpoints:
  POST /api/process   -> upload one or more .txt files, get back per-file
                          detection results (test_type, prep, angle, value, status)
  POST /api/export     -> given the current computed rows, get back a .txt
                          file (same layout as the desktop app's "Save Changes")
"""

import re
from datetime import datetime
from io import StringIO

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(title="SBKV Test Sheet API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TEST_RESULT_COLS = ["Before Vib", "After Vib", "Before cold", "After cold",
                     "Before Hot", "After Run-in", "After Hot/FATP"]


# =======================================================================
# PART A: reading / detecting values from an uploaded txt file
# =======================================================================
def detect_test_type(text_upper):
    if "ANGULAR" in text_upper or "HEADING" in text_upper:
        return "Angular"
    if "PITCH" in text_upper:
        return "Pitch"
    if "ROLL" in text_upper:
        return "Roll"
    return None


def detect_prep(text_upper):
    if "RAPID" in text_upper or "ACCELERATED" in text_upper:
        return "Rapid"
    if "NORMAL" in text_upper:
        return "Normal"
    return None


def detect_angle(text_upper):
    for mag in ["180", "85", "10"]:
        m = re.search(r"([+\-±]?)\s*" + mag + r"(?!\d)", text_upper)
        if m:
            return f"{m.group(1)}{mag}"
    return None


SIDE_BY_TEST = {"Angular": "Right", "Pitch": "Left", "Roll": "Left"}


def extract_rmse_values(text):
    numbers = re.findall(
        r"2\s*[\*×xX]\s*RMSE\s*=\s*(-?\d*\.\d+)",
        text,
        flags=re.IGNORECASE,
    )
    if len(numbers) < 2:
        return None, None
    return float(numbers[0]), float(numbers[1])


def process_text(filename, text):
    text_upper = text.upper()

    test_type = detect_test_type(text_upper)
    prep = detect_prep(text_upper)
    angle = detect_angle(text_upper)
    left_val, right_val = extract_rmse_values(text)

    result = {"file": filename, "test_type": test_type,
              "prep": prep, "angle": angle, "value": None, "status": "OK"}

    if not test_type or not prep or not angle:
        result["status"] = "Could not detect Test/Prep/Angle - check wording"
        return result
    if left_val is None:
        result["status"] = "Could not find 2xRMSE values in file"
        return result

    side = SIDE_BY_TEST[test_type]
    result["value"] = right_val if side == "Right" else left_val
    return result


def to_number(deg_text):
    m = re.search(r"([\d.]+)", deg_text)
    return float(m.group(1)) if m else None


# =======================================================================
# PART B: the sheet layout (SI 10 - 12), same words as the paper form
# =======================================================================
ROWS_BASE = [
    dict(sl="10", param="Error of determination and supply of\ncomponents of Angular speed",
         tech="1.2.9", test="3.8", sub="At Angular speed\n(Normal Preparation)",
         angle="± 10°/sec", nominal="0°/s", maxdev="±0.2°/s", cat="Angular", prep="Normal"),
    dict(sl="", param="", tech="", test="", sub="",
         angle="± 85°/sec", nominal="0°/s", maxdev="±0.85°/s", cat="Angular", prep="Normal"),
    dict(sl="", param="", tech="", test="", sub="",
         angle="± 180°/sec", nominal="0°/s", maxdev="±5.4°/s", cat="Angular", prep="Normal"),
    dict(sl="", param="", tech="", test="", sub="At Angular speed\n(Accelerated Preparation)",
         angle="± 10°/sec", nominal="0°/s", maxdev="±0.2°/s", cat="Angular", prep="Accelerated"),
    dict(sl="", param="", tech="", test="", sub="",
         angle="± 85°/sec", nominal="0°/s", maxdev="±0.85°/s", cat="Angular", prep="Accelerated"),
    dict(sl="", param="", tech="", test="", sub="",
         angle="± 180°/sec", nominal="0°/s", maxdev="±5.4°/s", cat="Angular", prep="Accelerated"),

    dict(sl="11", param="Error of determination and supply of\nRoll angle in the range ±180°",
         tech="1.2.10", test="3.8", sub="ROLL\n(Normal Preparation)",
         angle="± 10°/sec", nominal="0°", maxdev="±0.25°", cat="Roll", prep="Normal"),
    dict(sl="", param="", tech="", test="", sub="",
         angle="± 85°/sec", nominal="0°", maxdev="±0.5°", cat="Roll", prep="Normal"),
    dict(sl="", param="", tech="", test="", sub="",
         angle="± 180°/sec", nominal="0°", maxdev="±1.0°", cat="Roll", prep="Normal"),
    dict(sl="", param="", tech="", test="", sub="ROLL\n(Accelerated Preparation)",
         angle="± 10°/sec", nominal="0°", maxdev="±1.0°", cat="Roll", prep="Accelerated"),
    dict(sl="", param="", tech="", test="", sub="",
         angle="± 85°/sec", nominal="0°", maxdev="±1.5°", cat="Roll", prep="Accelerated"),
    dict(sl="", param="", tech="", test="", sub="",
         angle="± 180°/sec", nominal="0°", maxdev="±2.0°", cat="Roll", prep="Accelerated"),

    dict(sl="12", param="Error of determination and supply of Pitch\nAngle in the range ±90°",
         tech="1.2.11", test="3.8", sub="PITCH\n(Normal Preparation)",
         angle="± 10°/sec", nominal="0°", maxdev="±0.25°", cat="Pitch", prep="Normal"),
    dict(sl="", param="", tech="", test="", sub="",
         angle="± 85°/sec", nominal="0°", maxdev="±0.5°", cat="Pitch", prep="Normal"),
    dict(sl="", param="", tech="", test="", sub="PITCH\n(Accelerated Preparation)",
         angle="± 10°/sec", nominal="0°", maxdev="±1.0°", cat="Pitch", prep="Accelerated"),
    dict(sl="", param="", tech="", test="", sub="",
         angle="± 85°/sec", nominal="0°", maxdev="±1.5°", cat="Pitch", prep="Accelerated"),
]


def expand_signs(rows):
    out = []
    for row in rows:
        if row["cat"] in ("Angular", "Roll", "Pitch"):
            mag = re.search(r"(\d+)", row["angle"]).group(1)
            unit = re.sub(r"^[±\s\d]+", "", row["angle"])

            plus = dict(row)
            plus["angle"] = f"+ {mag}{unit}"
            plus["sign"] = "+"
            plus["mag"] = mag
            out.append(plus)

            minus = dict(row)
            minus["angle"] = f"- {mag}{unit}"
            minus["sign"] = "-"
            minus["mag"] = mag
            minus["sl"] = minus["param"] = minus["tech"] = minus["test"] = minus["sub"] = ""
            out.append(minus)
        else:
            r2 = dict(row)
            r2["sign"] = ""
            r2["mag"] = ""
            out.append(r2)
    return out


ROWS = expand_signs(ROWS_BASE)


def find_matching_value(row, results):
    if row["cat"] not in ("Angular", "Roll", "Pitch"):
        return None
    wanted_prep = "Rapid" if row["prep"] == "Accelerated" else row["prep"]

    for entry in results:
        if entry.get("test_type") != row["cat"]:
            continue
        if entry.get("prep") != wanted_prep:
            continue
        entry_angle = entry.get("angle") or ""
        m = re.match(r"([+\-±]?)(\d+)", entry_angle)
        if not m:
            continue
        esign, emag = m.group(1), m.group(2)
        if emag != row["mag"]:
            continue
        if esign in ("", "±") or esign == row["sign"]:
            return entry.get("value")
    return None


def format_value(v):
    s = f"{v:.3f}"
    if s.startswith("0."):
        s = s[1:]
    return s


def compute_result(row, results):
    value = find_matching_value(row, results)
    if value is None:
        return "N/A", "black"
    threshold = to_number(row["maxdev"])
    color = "#0a7d1f" if abs(value) <= threshold else "#c0392b"
    return format_value(value), color


def status_word(text, color):
    if text == "N/A":
        return "N/A"
    return "OK" if color == "#0a7d1f" else "NOT OK"


# =======================================================================
# API models
# =======================================================================
class ExportRequest(BaseModel):
    results: list = []


@app.get("/api/rows")
def get_rows():
    """Static sheet layout the frontend needs to draw the blank table."""
    return {"rows": ROWS, "test_result_cols": TEST_RESULT_COLS}


@app.post("/api/process")
async def process(files: list[UploadFile] = File(...)):
    results = []
    problems = []
    for f in files:
        raw = await f.read()
        text = raw.decode("utf-8", errors="ignore")
        res = process_text(f.filename, text)
        results.append(res)
        if res["status"] != "OK":
            problems.append(f"{res['file']}: {res['status']}")
    return JSONResponse({"results": results, "problems": problems})


@app.post("/api/compute")
def compute(payload: ExportRequest):
    """Given the accumulated list of per-file results, compute the
    live sheet values (value/color/status per row) without exporting."""
    computed = []
    for row in ROWS:
        text, color = compute_result(row, payload.results)
        computed.append({"value": text, "color": color, "status": status_word(text, color)})
    return {"computed": computed}


@app.post("/api/export")
def export(payload: ExportRequest):
    results = payload.results

    col_w = {
        "sl": 4, "param": 42, "tech": 12, "test": 8,
        "angle": 14, "nominal": 8, "maxdev": 10,
        "testres": 10, "rmse": 8, "status": 8,
    }

    lines = []
    lines.append("SBKV TEST SHEET")
    lines.append("Part no  KMIV.402113.002-01              Sl.No.                              J.O.No.")
    lines.append("Document No. KMIV.402113.002-01RK   Document Issue No. NIL          Project: SBKV")
    lines.append(f"Saved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Files loaded: {len(results)}")
    lines.append("")

    header1 = (
        "SI.No.".ljust(col_w["sl"]) + " | " +
        "Name of Parameter".ljust(col_w["param"]) + " | " +
        "Tech.Req.".ljust(col_w["tech"]) + " | " +
        "Test Pro.".ljust(col_w["test"]) + " | " +
        "Angle".ljust(col_w["angle"]) + " | " +
        "Nominal".ljust(col_w["nominal"]) + " | " +
        "MaxDev".ljust(col_w["maxdev"]) + " | " +
        " | ".join(c[:9].ljust(col_w["testres"]) for c in TEST_RESULT_COLS) + " | " +
        "2*RMSE".ljust(col_w["rmse"]) + " | " +
        "Status".ljust(col_w["status"])
    )
    lines.append(header1)
    lines.append("-" * len(header1))

    for row in ROWS:
        if row["sub"]:
            sl = row["sl"] or ""
            param = (row["sub"].replace("\n", " ") or "")
            tech = row["tech"] or ""
            test = row["test"] or ""
            testres_cells = " | ".join("N/A".ljust(col_w["testres"]) for _ in TEST_RESULT_COLS)
            line = (
                sl.ljust(col_w["sl"]) + " | " +
                param.ljust(col_w["param"]) + " | " +
                tech.ljust(col_w["tech"]) + " | " +
                test.ljust(col_w["test"]) + " | " +
                "".ljust(col_w["angle"]) + " | " +
                "".ljust(col_w["nominal"]) + " | " +
                "".ljust(col_w["maxdev"]) + " | " +
                testres_cells + " | " +
                "".ljust(col_w["rmse"]) + " | " +
                "".ljust(col_w["status"])
            )
            lines.append(line)

        value_text, color = compute_result(row, results)
        status = status_word(value_text, color)
        testres_cells = " | ".join("N/A".ljust(col_w["testres"]) for _ in TEST_RESULT_COLS)
        line = (
            "".ljust(col_w["sl"]) + " | " +
            "".ljust(col_w["param"]) + " | " +
            "".ljust(col_w["tech"]) + " | " +
            "".ljust(col_w["test"]) + " | " +
            row["angle"].ljust(col_w["angle"]) + " | " +
            row["nominal"].ljust(col_w["nominal"]) + " | " +
            row["maxdev"].ljust(col_w["maxdev"]) + " | " +
            testres_cells + " | " +
            value_text.ljust(col_w["rmse"]) + " | " +
            status.ljust(col_w["status"])
        )
        lines.append(line)

    lines.append("")
    lines.append("Signature")
    lines.append("Prepared By: Sweta        Shop")
    lines.append("Approved By: G Chandra   QC")

    buf = StringIO("\n".join(lines))
    filename = f"SBKV_Test_Sheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
