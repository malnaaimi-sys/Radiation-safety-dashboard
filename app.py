# app.py
import io
import json
import time
import hmac
import datetime as dt
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw


# ----------------------------
# Page configuration
# ----------------------------
st.set_page_config(
    page_title="KU Animal House Radiation Safety Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ----------------------------
# Optional authentication
# ----------------------------
SESSION_TIMEOUT_MINUTES = 20
TIMEOUT_SECONDS = SESSION_TIMEOUT_MINUTES * 60


def auth_available() -> bool:
    try:
        return bool(st.secrets.get("users", {}))
    except Exception:
        return False


def check_authentication() -> None:
    users = st.secrets.get("users", {})

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "last_active" not in st.session_state:
        st.session_state.last_active = time.time()

    if st.session_state.authenticated:
        now = time.time()
        if now - st.session_state.last_active > TIMEOUT_SECONDS:
            st.session_state.authenticated = False
            st.warning("🔒 Session expired. Please log in again.")
            time.sleep(1)
            st.rerun()
        st.session_state.last_active = now
        return

    st.title("🔐 KU Radiation Safety Dashboard")
    st.caption("Authorized users only")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        ok = st.form_submit_button("Sign in")

    if ok:
        if username in users and hmac.compare_digest(password, str(users[username])):
            st.session_state.authenticated = True
            st.session_state.last_active = time.time()
            st.success("✅ Login successful")
            time.sleep(0.6)
            st.rerun()
        st.error("❌ Invalid username or password")
    st.stop()


ENABLE_LOGIN = False
if ENABLE_LOGIN and auth_available():
    check_authentication()


# ----------------------------
# Sidebar
# ----------------------------
with st.sidebar:
    st.markdown("## KU Radiation Safety")
    st.caption("Committee demonstration mode")
    if auth_available():
        st.caption("Secrets file detected")
    else:
        st.caption("Running without login")

    if st.button("↺ Reset room tuning"):
        st.session_state.pop("room_configs", None)
        st.success("Room tuning reset to defaults")
        st.rerun()

    st.markdown("---")
    st.markdown(
        """
**Display goals**
- Committee-ready overview
- Interactive facility zoning
- Evidence-linked KPIs
- Editable room geometry
"""
    )


# ----------------------------
# Helpers
# ----------------------------
def avail_short(file_obj):
    return "Available" if file_obj is not None else "Not added"


def try_read_table(uploaded_file):
    if uploaded_file is None:
        return None

    name = uploaded_file.name.lower()

    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    try:
        if name.endswith(".csv"):
            try:
                df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
            except Exception:
                try:
                    uploaded_file.seek(0)
                except Exception:
                    pass
                df = pd.read_csv(uploaded_file)
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(uploaded_file)
        else:
            return None

        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return None


def find_col(df, keywords):
    if df is None or df.empty:
        return None
    lower = {str(c).lower().strip(): c for c in df.columns}
    for kw in keywords:
        kw = kw.lower().strip()
        for k, real in lower.items():
            if kw in k:
                return real
    return None


def last_date(df, col):
    if df is None or col is None or col not in df.columns:
        return None
    d = pd.to_datetime(df[col], errors="coerce")
    if d.notna().sum() == 0:
        return None
    return d.max()


def pill_card(title, icon, status, kpi_label, kpi_value, note):
    with st.container(border=True):
        st.markdown(f"### {icon} {title}")
        st.caption(note)
        st.metric(kpi_label, kpi_value)
        st.write(f"**Evidence:** {status}")


def box_norm_to_px(box_norm, size):
    w, h = size
    x1, y1, x2, y2 = box_norm
    return (int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h))


def points_norm_to_px(points_norm, size):
    w, h = size
    return [(int(x * w), int(y * h)) for x, y in points_norm]


def center_of(box_norm):
    x1, y1, x2, y2 = box_norm
    return ((x1 + x2) / 2, (y1 + y2) / 2)


# ----------------------------
# Layout configuration
# ----------------------------
APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"

DEFAULT_LAYOUT_CANDIDATES = [
    ASSETS_DIR / "animal_layout.png",
    ASSETS_DIR / "animal_layout.PNG",
    ASSETS_DIR / "animal_layout.jpg",
    ASSETS_DIR / "animal_layout.jpeg",
    ASSETS_DIR / "Animal_House_Layout.png",
    ASSETS_DIR / "Animal_House_Layout.PNG",
    ASSETS_DIR / "Animal_House_Layout.jpg",
    ASSETS_DIR / "Animal_House_Layout.jpeg",
    ASSETS_DIR / "animal house Area 190-Model.png",
    ASSETS_DIR / "animal house Area 190-Model.PNG",
    ASSETS_DIR / "animal house Area 190-Model.jpg",
    ASSETS_DIR / "animal house Area 190-Model.jpeg",
    APP_DIR / "animal_layout.png",
    APP_DIR / "animal_layout.PNG",
    APP_DIR / "animal_layout.jpg",
    APP_DIR / "animal_layout.jpeg",
    APP_DIR / "Animal_House_Layout.png",
    APP_DIR / "Animal_House_Layout.PNG",
    APP_DIR / "Animal_House_Layout.jpg",
    APP_DIR / "Animal_House_Layout.jpeg",
    APP_DIR / "animal house Area 190-Model.png",
    APP_DIR / "animal house Area 190-Model.PNG",
    APP_DIR / "animal house Area 190-Model.jpg",
    APP_DIR / "animal house Area 190-Model.jpeg",
]

DEFAULT_ROOM_DEFINITIONS = {
    "Lab 189 (Scanner Room)": {
        "box_norm": (0.10, 0.10, 0.45, 0.37),
        "classification": "Controlled",
        "access": "Authorized trained staff only",
        "notes": "Scanner / imaging room in the upper-left block.",
    },
    "Lab 188 (Main Work Area)": {
        "box_norm": (0.10, 0.39, 0.46, 0.95),
        "classification": "Controlled",
        "access": "Authorized trained staff only",
        "notes": "Main preparation and working zone.",
    },
    "Central Corridor": {
        "box_norm": (0.47, 0.08, 0.59, 0.97),
        "classification": "Supervised",
        "access": "Staff movement corridor",
        "notes": "Link corridor connecting work and animal rooms.",
    },
    "Lab 194": {
        "box_norm": (0.60, 0.10, 0.94, 0.28),
        "classification": "Controlled",
        "access": "Authorized staff only",
        "notes": "Upper-right animal room.",
    },
    "Lab 193": {
        "box_norm": (0.60, 0.30, 0.94, 0.48),
        "classification": "Controlled",
        "access": "Authorized staff only",
        "notes": "Animal room adjacent to Lab 194.",
    },
    "Lab 192": {
        "box_norm": (0.60, 0.50, 0.94, 0.69),
        "classification": "Controlled",
        "access": "Authorized staff only",
        "notes": "Animal room adjacent to Lab 193.",
    },
    "Lab 191": {
        "box_norm": (0.60, 0.71, 0.94, 0.95),
        "classification": "Controlled",
        "access": "Authorized staff only",
        "notes": "Lower-right animal room.",
    },
}

ZONE_COLORS = {
    "Controlled": (220, 53, 69),
    "Supervised": (255, 193, 7),
    "Public": (40, 167, 69),
}

ROUTE_COLORS = {
    "Material transfer route": (235, 28, 36, 225),
    "Animal movement route": (245, 130, 32, 225),
    "Waste movement route": (70, 105, 255, 225),
}


def build_default_routes(room_configs):
    scanner = center_of(room_configs["Lab 189 (Scanner Room)"]["box_norm"])
    work = center_of(room_configs["Lab 188 (Main Work Area)"]["box_norm"])
    corridor = center_of(room_configs["Central Corridor"]["box_norm"])
    lab191 = center_of(room_configs["Lab 191"]["box_norm"])
    lab194 = center_of(room_configs["Lab 194"]["box_norm"])

    return {
        "None": {"description": "No route overlay."},
        "Material transfer route": {
            "color": ROUTE_COLORS["Material transfer route"],
            "points_norm": [work, (corridor[0], work[1]), corridor, (corridor[0], scanner[1]), scanner],
            "description": "Controlled movement of radioactive material between the main work area and scanner room.",
        },
        "Animal movement route": {
            "color": ROUTE_COLORS["Animal movement route"],
            "points_norm": [lab191, (corridor[0], lab191[1]), (corridor[0], work[1]), work],
            "description": "Illustrative animal movement between right-side rooms and the main work area.",
        },
        "Waste movement route": {
            "color": ROUTE_COLORS["Waste movement route"],
            "points_norm": [lab194, (corridor[0], lab194[1]), (corridor[0], 0.95), (work[0], 0.95)],
            "description": "Illustrative waste movement toward the lower exit / handling side.",
        },
        "All routes": {
            "combo": [
                "Material transfer route",
                "Animal movement route",
                "Waste movement route",
            ],
            "description": "Overlay all standard animal-house movement pathways.",
        },
    }


@st.cache_data(show_spinner=False)
def load_default_layout_bytes():
    for layout_path in DEFAULT_LAYOUT_CANDIDATES:
        if layout_path.exists() and layout_path.is_file():
            try:
                return str(layout_path), layout_path.read_bytes()
            except Exception:
                continue
    return None, None


def get_default_layout():
    layout_path, raw = load_default_layout_bytes()
    if raw is None:
        return None, None
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        return img, layout_path
    except Exception:
        return None, layout_path


def ensure_room_configs():
    if "room_configs" not in st.session_state:
        st.session_state.room_configs = json.loads(json.dumps(DEFAULT_ROOM_DEFINITIONS))
    return st.session_state.room_configs


def get_room_definitions(base_img, room_configs):
    room_defs = {}
    for room_name, meta in room_configs.items():
        merged = dict(meta)
        merged["box"] = box_norm_to_px(meta["box_norm"], base_img.size)
        room_defs[room_name] = merged
    return room_defs


def draw_route(draw, route_name, size, routes, line_width_px):
    route = routes.get(route_name)
    if not route:
        return
    if "combo" in route:
        for child in route["combo"]:
            draw_route(draw, child, size, routes, line_width_px)
        return
    points = points_norm_to_px(route["points_norm"], size)
    draw.line(points, fill=route["color"], width=line_width_px, joint="curve")


def build_interactive_layout(
    base_img,
    room_defs,
    routes,
    selected_room=None,
    selected_route="None",
    show_zones=True,
    show_labels=True,
    zone_opacity=85,
    line_width_px=18,
):
    canvas = base_img.copy().convert("RGBA")
    overlay = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    if show_zones:
        for room, meta in room_defs.items():
            r, g, b = ZONE_COLORS.get(meta["classification"], (0, 123, 255))
            fill = (r, g, b, zone_opacity)
            draw.rounded_rectangle(meta["box"], radius=18, fill=fill)
            if show_labels:
                x1, y1, _, _ = meta["box"]
                draw.text((x1 + 10, y1 + 10), room, fill=(0, 0, 0, 255))

    if selected_room and selected_room in room_defs:
        x1, y1, x2, y2 = room_defs[selected_room]["box"]
        draw.rounded_rectangle((x1, y1, x2, y2), radius=18, outline=(0, 102, 204, 255), width=12)
        draw.rounded_rectangle((x1 + 8, y1 + 8, x2 - 8, y2 - 8), radius=14, outline=(255, 255, 255, 220), width=4)

    if selected_route != "None":
        draw_route(draw, selected_route, canvas.size, routes, line_width_px)

    return Image.alpha_composite(canvas, overlay)


def render_room_details(room_name, room_defs):
    if not room_name or room_name not in room_defs:
        st.info("Select an animal-house area to view classification, access control, and operational notes.")
        return
    meta = room_defs[room_name]
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Classification", meta["classification"])
    with c2:
        st.metric("Access", meta["access"])
    with c3:
        st.metric("Zone type", "Core room" if "Lab" in room_name else "Support / corridor")
    st.caption(meta["notes"])


# ----------------------------
# Fixed regulatory facts
# ----------------------------
DOC_NO = "HSC-NM-RSM-001"
VERSION = "2026 – Rev. 1"
REG_AUTH = "MOH – Radiation Protection Department (RPD)"
LICENSE_DUE_DATE = "05 June 2027"
RESPONSIBLE_PERSON = "Dr. Mohammad Saker"
RPD_LICENSE_NO = "1-2007"


# ----------------------------
# Header
# ----------------------------
st.title("🛡️ KU Animal House Radiation Safety Dashboard")
st.markdown("## **A committee-ready visual dashboard for zoning, movement control, evidence, and occupational safety.**")

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Document", DOC_NO)
with m2:
    st.metric("Version", VERSION)
with m3:
    st.metric("RPD License No.", RPD_LICENSE_NO)
with m4:
    st.metric("License Due", LICENSE_DUE_DATE)

st.caption(
    f"Regulatory Authority: **{REG_AUTH}**  |  Responsible Person: **{RESPONSIBLE_PERSON}**  |  Updated: **{dt.datetime.now().strftime('%Y-%m-%d %H:%M')}**"
)

with st.container(border=True):
    st.markdown(
        "**Committee message:** This dashboard combines facility visualization, room classification, route control, and operational evidence into one live view for oversight, discussion, and future audit readiness."
    )

st.divider()


# ----------------------------
# Uploads
# ----------------------------
with st.expander("📁 Upload evidence files (optional)", expanded=False):
    a, b, c = st.columns(3)
    with a:
        receipt_log = st.file_uploader("📦 Receipt / Use Log (CSV/XLSX)", type=["csv", "xlsx"])
        sealed_source_log = st.file_uploader("🔐 Sealed Source Inventory (CSV/XLSX)", type=["csv", "xlsx"])
        qc_reports = st.file_uploader("🧪 QC Reports (PDF/CSV/XLSX)", type=["pdf", "csv", "xlsx"])
    with b:
        invivo_log = st.file_uploader("🐭 In vivo Admin Log (CSV/XLSX)", type=["csv", "xlsx"])
        invitro_log = st.file_uploader("🧫 In vitro Admin Log (CSV/XLSX)", type=["csv", "xlsx"])
        animals_log = st.file_uploader("🐾 Animals Management Log (CSV/XLSX)", type=["csv", "xlsx"])
    with c:
        floorplan_receipt = st.file_uploader("🧭 Facility layout override (PNG/JPG)", type=["png", "jpg", "jpeg"])
        zoning_plan = st.file_uploader("🗺️ Approved zoning plan (PNG/JPG)", type=["png", "jpg", "jpeg"])
        tld_log = st.file_uploader("📟 TLD Dose Table (CSV/XLSX)", type=["csv", "xlsx"])
        route_overlay = st.file_uploader("Optional route overlay (PNG)", type=["png"])

df_receipt = try_read_table(receipt_log)
df_sealed = try_read_table(sealed_source_log)
df_invivo = try_read_table(invivo_log)
df_invitro = try_read_table(invitro_log)
df_animals = try_read_table(animals_log)
df_tld = try_read_table(tld_log)


# ----------------------------
# Executive KPI pillars
# ----------------------------
st.subheader("Executive competency pillars")
date_col = find_col(df_receipt, ["date"])
form_col = find_col(df_receipt, ["form"])
purpose_col = find_col(df_receipt, ["purpose"])

last_receipt_dt = last_date(df_receipt, date_col)
last_receipt = last_receipt_dt.strftime("%Y-%m-%d") if last_receipt_dt is not None else "—"

sealed_count = "—"
if df_sealed is not None and not df_sealed.empty:
    sealed_count = str(len(df_sealed))
elif df_receipt is not None and form_col:
    sealed_count = str((df_receipt[form_col].astype(str).str.contains("sealed", case=False, na=False)).sum())

last_qc = "—"
if df_receipt is not None and date_col and purpose_col:
    qc_rows = df_receipt[purpose_col].astype(str).str.contains("qc", case=False, na=False)
    if qc_rows.any():
        qc_dt = pd.to_datetime(df_receipt.loc[qc_rows, date_col], errors="coerce").max()
        if pd.notna(qc_dt):
            last_qc = qc_dt.strftime("%Y-%m-%d")

invivo_count = "—"
if df_invivo is not None and not df_invivo.empty:
    invivo_count = str(len(df_invivo))
elif df_receipt is not None and purpose_col:
    invivo_count = str((df_receipt[purpose_col].astype(str).str.contains("in vivo", case=False, na=False)).sum())

animals_count = "—"
if df_animals is not None and not df_animals.empty:
    animal_id = find_col(df_animals, ["animalid", "animal_id", "animal", "id"])
    animals_count = str(df_animals[animal_id].nunique()) if animal_id else str(len(df_animals))

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    pill_card("Source Security", "🔐", avail_short(sealed_source_log), "Sealed sources", sealed_count, "Accountability & controlled access")
with c2:
    pill_card("Safe Receiving", "📦", avail_short(receipt_log), "Last receipt date", last_receipt, "Traceable receipt-to-storage workflow")
with c3:
    pill_card("Quality Control", "🧪", avail_short(qc_reports), "Last QC date", last_qc, "Equipment readiness supported by QC")
with c4:
    pill_card("Safe Administration", "🐭", avail_short(invivo_log) if invivo_log else avail_short(receipt_log), "In vivo count", invivo_count, "Documented administration practices")
with c5:
    pill_card("Animal Management", "🐾", avail_short(animals_log), "Animals / records", animals_count, "Controlled housing & monitoring records")

st.divider()


# ----------------------------
# Dose performance
# ----------------------------
st.subheader("Occupational dose performance (MOH/RPD TLD)")
default_tld = pd.DataFrame([
    [778, "DR ESSA LOUTFI", 7134, 0.124, 0.139, ""],
    [1137, "MR AHMED MAHMOUD MPHAMED", 7145, 0.132, 0.139, ""],
    [1342, "MR MOHAMED ABDUL MONEM S.", 7153, 0.123, 0.122, ""],
    [1398, "DR B KUMARI VASANTHY", 7274, 0.122, 0.125, ""],
    [1411, "DR FATIMA AL-SAIDEE", 7346, 0.129, 0.133, ""],
    [1686, "MISS HEBA MOHAMED HAMED", 7348, 0.126, 0.124, ""],
    [1728, "MRS JEHAN AL SHAMMARI", 7393, 0.133, 0.131, ""],
    [3265, "MS ASEEL AHMED AL KANDARI", 7396, 0.123, 0.124, ""],
    [3285, "DR SAUD A H. AL-ENEZI", 7595, 0.123, 0.132, ""],
    [5078, "DR MOHAMMAD ZAFARYAB", 7755, 0.105, 0.106, ""],
    [5217, "DR F.X. ELIZABETH JAYANTHI", 7747, 0.106, 0.112, ""],
    [5218, "MRS FATIMA SEQUEIRA", 7739, 0.129, 0.135, ""],
    [5513, "DR SHOROUK FALEH DANNOON", 7738, 0.157, 0.169, ""],
    [6091, "MR WALEED SAMIR ALI", 7737, 0.137, 0.144, "NEW"],
    [8220, "DR MARIAM YOUSSEF HUSSAIN", 7724, 0.159, 0.159, ""],
    [8916, "MRS JEHAN ESSAM GHONEIM", 7722, 0.107, 0.114, ""],
    [9352, "MR MOHAMMED JASEEM PATTILLATH", 7721, 0.134, 0.130, "NEW"],
    [9698, "DR SELMA SAAD ALKAFEEF", 6639, 0.135, 0.131, "NEW"],
    [9699, "MRS ABIRAMI SELLAPANDIAN", 7241, 0.159, 0.163, "NEW"],
    [9700, "MR YOUSEF RAED YOUSEF", 6205, 0.120, 0.123, "NEW"],
], columns=["Code", "Name", "Card", "Hp10_mSv", "Hp07_mSv", "Remarks"])

tld = df_tld.copy() if (df_tld is not None and not df_tld.empty) else default_tld.copy()

hp10_col = find_col(tld, ["hp10", "hp(10)", "deep dose", "whole body"])
hp07_col = find_col(tld, ["hp07", "hp(07)", "skin dose"])
name_col = find_col(tld, ["name", "staff", "worker"])

if hp10_col is None:
    hp10_col = "Hp10_mSv"
    if hp10_col not in tld.columns:
        tld[hp10_col] = pd.NA

if hp07_col is None and "Hp07_mSv" in tld.columns:
    hp07_col = "Hp07_mSv"

if name_col is None:
    if "Name" not in tld.columns:
        tld["Name"] = ""
    name_col = "Name"

tld[hp10_col] = pd.to_numeric(tld[hp10_col], errors="coerce")

monitored = int(tld[hp10_col].notna().sum())
hp10_min = float(tld[hp10_col].min()) if monitored else 0.0
hp10_max = float(tld[hp10_col].max()) if monitored else 0.0
hp10_mean = float(tld[hp10_col].mean()) if monitored else 0.0
annual_proj = hp10_mean * 4

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Monitored staff", monitored)
with k2:
    st.metric("Quarterly Hp(10) range", f"{hp10_min:.3f}–{hp10_max:.3f} mSv" if monitored else "—")
with k3:
    st.metric("Average Hp(10)", f"{hp10_mean:.3f} mSv" if monitored else "—")
with k4:
    st.metric("Projected annual", f"{annual_proj:.2f} mSv/year" if monitored else "—")

st.caption("🟢 Doses are far below the occupational limit (20 mSv/year). This supports a strong ALARA message for committee review.")

with st.expander("🔎 View staff dose table", expanded=False):
    q = st.text_input("Search staff name", key="dose_search")
    view = tld.copy()
    if q.strip():
        view = view[view[name_col].astype(str).str.contains(q, case=False, na=False)]
    st.dataframe(view.sort_values(hp10_col, ascending=False), use_container_width=True, hide_index=True)

st.divider()


# ----------------------------
# Facility layout
# ----------------------------
st.subheader("Facility layout and interactive radiation flow")

base_layout = None
loaded_layout_name = None

if floorplan_receipt is not None:
    try:
        base_layout = Image.open(floorplan_receipt).convert("RGBA")
        loaded_layout_name = floorplan_receipt.name
    except Exception:
        base_layout = None
        loaded_layout_name = None

if base_layout is None:
    base_layout, loaded_layout_name = get_default_layout()

room_configs = ensure_room_configs()
routes = build_default_routes(room_configs)

with st.container(border=True):
    left, right = st.columns([1.45, 0.95])

    with right:
        st.markdown("### Layout controls")
        room_names = list(room_configs.keys())
        selected_room = st.selectbox("Highlight animal-house area", ["None"] + room_names)
        selected_route = st.selectbox("Overlay route", list(routes.keys()), index=3)
        show_zone_overlay = st.toggle("Show area classification overlay", value=True)
        show_room_labels = st.toggle("Show room labels on overlay", value=True)
        use_custom_overlay = st.toggle(
            "Use uploaded route overlay PNG",
            value=route_overlay is not None,
            disabled=route_overlay is None,
        )
        zone_opacity = st.slider("Zone overlay opacity", 20, 180, 85, 5)
        line_width_px = st.slider("Route line width", 6, 40, 18, 2)

        st.markdown("### Fine-tune selected area")
        editable_area = st.selectbox("Area to adjust", room_names, index=0)
        current = room_configs[editable_area]
        col_a, col_b = st.columns(2)

        with col_a:
            x1 = st.slider("x1", 0.00, 0.98, float(current["box_norm"][0]), 0.01, key=f"{editable_area}_x1")
            y1 = st.slider("y1", 0.00, 0.98, float(current["box_norm"][1]), 0.01, key=f"{editable_area}_y1")
            classification = st.selectbox(
                "Classification",
                ["Controlled", "Supervised", "Public"],
                index=["Controlled", "Supervised", "Public"].index(current["classification"]),
                key=f"{editable_area}_class",
            )
        with col_b:
            x2 = st.slider("x2", 0.02, 1.00, float(current["box_norm"][2]), 0.01, key=f"{editable_area}_x2")
            y2 = st.slider("y2", 0.02, 1.00, float(current["box_norm"][3]), 0.01, key=f"{editable_area}_y2")
            access = st.text_input("Access", value=current["access"], key=f"{editable_area}_access")

        notes = st.text_area("Operational notes", value=current["notes"], height=80, key=f"{editable_area}_notes")

        if x2 <= x1:
            x2 = min(1.0, x1 + 0.02)
        if y2 <= y1:
            y2 = min(1.0, y1 + 0.02)

        room_configs[editable_area] = {
            "box_norm": (x1, y1, x2, y2),
            "classification": classification,
            "access": access,
            "notes": notes,
        }
        st.session_state.room_configs = room_configs

        st.markdown("### Map legend")
        st.markdown(
            """
- 🔴 **Controlled**: scanner / main work / animal rooms  
- 🟡 **Supervised**: corridor / staff support movement  
- 🟢 **Public**: future public-facing or unrestricted zones  
- **Red route**: material transfer  
- **Orange route**: animal movement  
- **Blue route**: waste movement
"""
        )

        if loaded_layout_name:
            st.caption(f"Active base layout: **{Path(loaded_layout_name).name}**")
        else:
            st.caption("No local layout file detected yet")

    with left:
        if base_layout is not None:
            room_defs = get_room_definitions(base_layout, room_configs)
            routes = build_default_routes(room_configs)
            interactive_img = build_interactive_layout(
                base_img=base_layout,
                room_defs=room_defs,
                routes=routes,
                selected_room=None if selected_room == "None" else selected_room,
                selected_route=selected_route,
                show_zones=show_zone_overlay,
                show_labels=show_room_labels,
                zone_opacity=zone_opacity,
                line_width_px=line_width_px,
            )

            if use_custom_overlay and route_overlay is not None:
                try:
                    uploaded_overlay = Image.open(route_overlay).convert("RGBA").resize(interactive_img.size)
                    interactive_img = Image.alpha_composite(interactive_img, uploaded_overlay)
                except Exception:
                    st.warning("Uploaded route overlay could not be applied; showing built-in interactive view instead.")

            st.image(interactive_img, caption="Interactive animal-house facility layout", use_container_width=True)
            render_room_details(None if selected_room == "None" else selected_room, room_defs)
        else:
            st.warning("No facility layout available. Upload a PNG/JPG or keep an animal layout image inside the assets folder or next to the app file.")
            st.code("\n".join(str(p) for p in DEFAULT_LAYOUT_CANDIDATES), language="text")

with st.expander("📋 Current room configuration", expanded=False):
    cfg_df = pd.DataFrame([
        {
            "Area": name,
            "Classification": meta["classification"],
            "Access": meta["access"],
            "x1": meta["box_norm"][0],
            "y1": meta["box_norm"][1],
            "x2": meta["box_norm"][2],
            "y2": meta["box_norm"][3],
            "Notes": meta["notes"],
        }
        for name, meta in room_configs.items()
    ])
    st.dataframe(cfg_df, use_container_width=True, hide_index=True)
    st.download_button(
        "Download room config JSON",
        data=json.dumps(room_configs, indent=2),
        file_name="ku_animal_layout_room_config.json",
        mime="application/json",
    )

with st.expander("🗺️ Additional maps and evidence", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        if zoning_plan is not None:
            try:
                st.image(Image.open(zoning_plan), caption="Uploaded approved zoning plan", use_container_width=True)
            except Exception:
                st.warning("Uploaded zoning plan could not be displayed.")
        else:
            st.info("Upload the approved zoning plan to compare with the dashboard overlay.")
    with col2:
        if route_overlay is not None:
            try:
                st.image(Image.open(route_overlay), caption="Uploaded route overlay", use_container_width=True)
            except Exception:
                st.warning("Uploaded route overlay could not be displayed.")
        else:
            st.info("Upload a transparent route overlay PNG if you want to compare the built-in routing with your approved overlay.")

with st.expander("📊 Simple charts", expanded=False):
    def bar_by_rn(df, title):
        rn = find_col(df, ["radionuclide", "isotope", "nuclide", "radioisotope"])
        if df is None or rn is None or df.empty:
            st.info("Upload a log with 'Radionuclide/Isotope' to show this chart.")
            return

        vc = df[rn].astype(str).str.strip()
        vc = vc[vc != ""].value_counts().head(8)

        if vc.empty:
            st.info("No radionuclide values found for this chart.")
            return

        fig = plt.figure()
        plt.bar(vc.index.tolist(), vc.values.tolist())
        plt.title(title)
        plt.xlabel("Radionuclide")
        plt.ylabel("Count")
        plt.xticks(rotation=30, ha="right")
        st.pyplot(fig)
        plt.close(fig)

    g1, g2, g3 = st.columns(3)
    with g1:
        bar_by_rn(df_receipt, "Receiving by radionuclide")
    with g2:
        bar_by_rn(df_sealed, "Sealed sources by radionuclide")
    with g3:
        bar_by_rn(df_invivo, "In vivo by radionuclide")
