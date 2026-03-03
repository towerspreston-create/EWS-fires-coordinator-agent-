"""
Fires Coordinator Agent v9
EWS MAGTF Operations Afloat Training Tool

CHANGELOG v9:
- LRASM corrected to AIRCRAFT-LAUNCHED ONLY (removed from ship VLS loadouts)
- Coalition ship session initialization via sidebar
- Scaled loadouts matching EDL (2x HIMARS, 4x M777 FA section options)
- DESRON-specific missile counts for Pacific Guard SAG
- Section 10/11 reference integration (ISR/C2, coalition platforms)
- Improved ammo parsing (REMAINING vs EXPENDED disambiguation)
"""

import streamlit as st
import anthropic
import re
from pathlib import Path
import sys
import copy
import json
import math
import pandas as pd
from io import BytesIO

# Optional mapping dependencies
try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

try:
    import mgrs as mgrs_lib
    MGRS_AVAILABLE = True
except ImportError:
    MGRS_AVAILABLE = False

sys.path.insert(0, str(Path(__file__).parent))
from prompts.system_prompt import get_system_prompt_with_context

# =============================================================================
# CONFIGURATION
# =============================================================================
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
DEFAULT_MAP_CENTER = [15.0, 115.0]
DEFAULT_MAP_ZOOM = 5

# =============================================================================
# LOADOUT PRESETS
# Scaled to match Pacific Guard EDL and Blue Threat Guide
# NOTE: LRASM is NOT included in ship loadouts — aircraft-launched only
# =============================================================================
LOADOUT_PRESETS = {
    "Default (Planning)": {
        "HIMARS Battery (6x)": {
            "GMLRS": {"initial": 108, "expended": 0},
            "ATACMS": {"initial": 12, "expended": 0},
            "PrSM": {"initial": 24, "expended": 0},
        },
        "M777 Battery (6x)": {
            "155mm HE": {"initial": 600, "expended": 0},
            "Excalibur": {"initial": 36, "expended": 0},
            "ILLUM": {"initial": 60, "expended": 0},
            "Smoke": {"initial": 60, "expended": 0},
        },
        "DDG (NSFS)": {
            "5\" Rounds": {"initial": 600, "expended": 0},
            "TLAM": {"initial": 24, "expended": 0},
            "SM-6": {"initial": 12, "expended": 0},
        },
        "Mortar Plt (4x)": {
            "120mm HE": {"initial": 200, "expended": 0},
        },
    },
    "Pacific Guard — EDL Scaled": {
        # 2x HIMARS launchers per EDL
        "HIMARS (2x Launchers)": {
            "GMLRS": {"initial": 36, "expended": 0},
            "ATACMS": {"initial": 4, "expended": 0},
            "PrSM": {"initial": 8, "expended": 0},
        },
        # 4x M777 per FA section
        "M777 FA Section (4x)": {
            "155mm HE": {"initial": 400, "expended": 0},
            "Excalibur": {"initial": 24, "expended": 0},
            "ILLUM": {"initial": 40, "expended": 0},
            "Smoke": {"initial": 40, "expended": 0},
        },
        "Mortar Plt (4x)": {
            "120mm HE": {"initial": 200, "expended": 0},
        },
    },
    "Pacific Guard — DESRON SAG": {
        # CG-102 Lhasa (Ticonderoga-class) — flagship
        "CG-102 Lhasa": {
            "Tomahawk Block Va": {"initial": 8, "expended": 0},
            "SM-2": {"initial": 50, "expended": 0},
            "SM-6": {"initial": 16, "expended": 0},
            "ESSM": {"initial": 32, "expended": 0},
            "Harpoon": {"initial": 8, "expended": 0},
            "5\" Rounds": {"initial": 600, "expended": 0},
        },
        "DDG-173": {
            "Tomahawk Block Va": {"initial": 12, "expended": 0},
            "SM-2": {"initial": 24, "expended": 0},
            "SM-6": {"initial": 8, "expended": 0},
            "ESSM": {"initial": 16, "expended": 0},
            "5\" Rounds": {"initial": 600, "expended": 0},
        },
        "DDG-153": {
            "Tomahawk Block Va": {"initial": 12, "expended": 0},
            "SM-2": {"initial": 24, "expended": 0},
            "SM-6": {"initial": 8, "expended": 0},
            "ESSM": {"initial": 16, "expended": 0},
            "5\" Rounds": {"initial": 600, "expended": 0},
        },
        "FFG-1 (DESRON)": {
            "NSM": {"initial": 16, "expended": 0},
            "SM-2": {"initial": 16, "expended": 0},
            "ESSM": {"initial": 16, "expended": 0},
        },
        "FFG-2 (DESRON)": {
            "NSM": {"initial": 16, "expended": 0},
            "SM-2": {"initial": 16, "expended": 0},
            "ESSM": {"initial": 16, "expended": 0},
        },
        "FFG-3 (DESRON)": {
            "NSM": {"initial": 16, "expended": 0},
            "SM-2": {"initial": 16, "expended": 0},
            "ESSM": {"initial": 16, "expended": 0},
        },
        "FFG-4 (DESRON)": {
            "NSM": {"initial": 16, "expended": 0},
            "SM-2": {"initial": 16, "expended": 0},
            "ESSM": {"initial": 16, "expended": 0},
        },
        "NMESIS Plt": {
            "NSM": {"initial": 8, "expended": 0},
        },
    },
    "RCT w/ Reinforcing Fires": {
        "HIMARS Battery (6x)": {
            "GMLRS": {"initial": 108, "expended": 0},
            "ATACMS": {"initial": 12, "expended": 0},
        },
        "M777 Battery (6x)": {
            "155mm HE": {"initial": 600, "expended": 0},
            "Excalibur": {"initial": 36, "expended": 0},
        },
        "Mortar Plt (4x)": {
            "120mm HE": {"initial": 200, "expended": 0},
        },
        "DDG (NSFS)": {
            "5\" Rounds": {"initial": 600, "expended": 0},
            "TLAM": {"initial": 24, "expended": 0},
        },
        "OPF-M (7x JLTVs)": {
            "Hero-120": {"initial": 56, "expended": 0},
        },
    },
}

# =============================================================================
# ADVERSARY PRESETS
# =============================================================================
ADVERSARY_PRESETS = {
    "Olvana (Chinese-type)": {
        "naval": {
            "Type 055 (Renhai CG)": {"alpha": 6.0, "y": 8, "b": 3},
            "Type 052D (Luyang III DDG)": {"alpha": 4.0, "y": 6, "b": 2},
            "Type 054A (Jiangkai II FFG)": {"alpha": 3.0, "y": 4, "b": 2},
            "Type 056 (Jiangdao Corvette)": {"alpha": 2.0, "y": 2, "b": 1},
            "Type 022 (Houbei FAC)": {"alpha": 2.0, "y": 1, "b": 1},
        },
        "systems": {
            "ADA": ["HQ-9 (200km)", "HQ-16 (40km)", "HQ-7 (15km)", "PGZ-07 35mm SPAAG",
                    "LD-2000 CIWS", "HQ-17A (20km mobile)", "HQ-22 (170km)"],
            "IDF": ["PLZ-05 155mm SPH", "PCL-181 155mm Truck", "PHL-03 300mm MLRS",
                    "PHL-16 370mm MLRS"],
            "Armor": ["Type 99A MBT", "Type 96A MBT", "ZBD-04A IFV", "ZBL-08 APC",
                      "ZTD-05 Amphib Tank"],
            "Coastal": ["YJ-62 (400km ASCM)", "YJ-18 (500km ASCM)", "CM-802AKG shore battery"],
            "ISR/C2": ["MMRC-M (Radar)", "KJ-500 AEW", "WZ-8 Recon UAV", "CEC/CTN"],
        }
    },
    "Ariana (Iranian-type)": {
        "naval": {
            "Frigate": {"alpha": 2.0, "y": 2, "b": 2},
            "Corvette": {"alpha": 1.5, "y": 1, "b": 1},
            "Fast Attack Craft": {"alpha": 2.0, "y": 0, "b": 1},
        },
        "systems": {
            "ADA": ["SA-15 Tor (12km)", "SA-6 Gainful (24km)", "ZU-23-2 AAA", "Shahab SAM"],
            "IDF": ["2S19 Msta 152mm SPH", "D-30 122mm Howitzer", "Fajr-5 333mm MRL"],
            "Armor": ["T-90 MBT", "T-72 MBT", "BMP-2 IFV", "BTR-80 APC"],
            "Coastal": ["Noor ASCM (120km)", "Qader ASCM (200km)"],
            "ISR/C2": ["Radar sites", "C2 nodes"],
        }
    },
}

# =============================================================================
# REFERENCE DOCUMENT LOADING
# =============================================================================
@st.cache_data(show_spinner=False)
def load_reference_docs():
    """Load weapons reference and Hughes model from project files."""
    weapons_ref = ""
    hughes_model = ""

    weapons_path = Path("/mnt/project/weapons_reference_v2.md")
    if weapons_path.exists():
        weapons_ref = weapons_path.read_text(encoding="utf-8", errors="replace")

    hughes_path = Path("/mnt/project/hughes_salvo_model.md")
    if hughes_path.exists():
        hughes_model = hughes_path.read_text(encoding="utf-8", errors="replace")

    return weapons_ref, hughes_model


# =============================================================================
# AMMUNITION PARSING
# =============================================================================
def parse_ammo_updates(response_text: str) -> list[dict]:
    """
    Parse AMMO_UPDATE blocks from AI response.
    Handles both EXPENDED and REMAINING formats.
    Returns list of {asset, munition, expended} dicts.
    """
    updates = []
    pattern = r"AMMO_UPDATE:\s*\nASSET:\s*(.+)\nMUNITION:\s*(.+)\n(EXPENDED|REMAINING):\s*(\d+)"
    matches = re.finditer(pattern, response_text, re.IGNORECASE)

    for m in matches:
        asset = m.group(1).strip()
        munition = m.group(2).strip()
        update_type = m.group(3).strip().upper()
        value = int(m.group(4).strip())
        updates.append({
            "asset": asset,
            "munition": munition,
            "update_type": update_type,
            "value": value,
        })
    return updates


def apply_ammo_updates(ammo_status: dict, updates: list[dict]) -> dict:
    """Apply parsed ammo updates to the status tracker. Returns updated dict."""
    updated = copy.deepcopy(ammo_status)
    for upd in updates:
        asset = upd["asset"]
        munition = upd["munition"]
        update_type = upd["update_type"]
        value = upd["value"]

        # Fuzzy match asset
        matched_asset = None
        for a in updated:
            if a.lower() == asset.lower() or asset.lower() in a.lower() or a.lower() in asset.lower():
                matched_asset = a
                break

        if matched_asset is None:
            continue

        # Fuzzy match munition
        matched_munition = None
        for mn in updated[matched_asset]:
            if mn.lower() == munition.lower() or munition.lower() in mn.lower() or mn.lower() in munition.lower():
                matched_munition = mn
                break

        if matched_munition is None:
            continue

        initial = updated[matched_asset][matched_munition]["initial"]
        current_expended = updated[matched_asset][matched_munition]["expended"]

        if update_type == "EXPENDED":
            # value is additional rounds expended
            new_expended = min(initial, current_expended + value)
        elif update_type == "REMAINING":
            # value is what remains — back-calculate expended
            new_expended = max(0, initial - value)
        else:
            continue

        updated[matched_asset][matched_munition]["expended"] = new_expended

    return updated


def parse_ammo_from_chat(text: str, current_ammo: dict) -> dict:
    """
    Parse force composition or free-text ammo description from user input
    and adjust loadout accordingly. Returns modified ammo dict.
    """
    updated = copy.deepcopy(current_ammo)

    # Simple keyword patterns for auto-scaling
    patterns = [
        (r"(\d+)\s*x?\s*himars", "HIMARS"),
        (r"(\d+)\s*x?\s*m777", "M777"),
        (r"(\d+)\s*x?\s*ddg", "DDG"),
        (r"(\d+)\s*x?\s*cg\b", "CG"),
    ]

    for pattern, asset_type in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            count = int(match.group(1))
            if asset_type == "HIMARS":
                for asset_key in list(updated.keys()):
                    if "himars" in asset_key.lower():
                        for munition in updated[asset_key]:
                            if "gmlrs" in munition.lower():
                                updated[asset_key][munition]["initial"] = count * 18
                            elif "atacms" in munition.lower():
                                updated[asset_key][munition]["initial"] = count * 2
                            elif "prsm" in munition.lower():
                                updated[asset_key][munition]["initial"] = count * 4

    return updated


def get_ammo_status_str(ammo_status: dict) -> str:
    """Format ammo status as a compact string for display."""
    lines = []
    for asset, munitions in ammo_status.items():
        for munition, counts in munitions.items():
            initial = counts.get("initial", 0)
            expended = counts.get("expended", 0)
            remaining = initial - expended
            pct = remaining / initial * 100 if initial > 0 else 0
            if pct > 50:
                indicator = "🟢"
            elif pct > 25:
                indicator = "🟡"
            else:
                indicator = "🔴"
            lines.append(f"{indicator} {asset} / {munition}: {remaining}/{initial}")
    return "\n".join(lines)


# =============================================================================
# DOCUMENT UPLOAD PARSING
# =============================================================================
def parse_uploaded_document(uploaded_file) -> tuple[str, str]:
    """
    Parse uploaded planning documents (Excel or PDF).
    Returns (doc_type, content_text).
    """
    filename = uploaded_file.name.lower()
    content = ""
    doc_type = "Unknown Document"

    if filename.endswith((".xlsx", ".xls")):
        try:
            df_dict = pd.read_excel(uploaded_file, sheet_name=None)
            parts = []
            for sheet_name, df in df_dict.items():
                parts.append(f"Sheet: {sheet_name}")
                parts.append(df.to_string(index=False, max_rows=50))
            content = "\n".join(parts)
        except Exception as e:
            content = f"[Error reading Excel: {e}]"

        if any(kw in filename for kw in ["agm", "tss", "hptl"]):
            doc_type = "AGM/TSS/HPTL Matrix"
        elif "tlws" in filename or "target" in filename:
            doc_type = "Target List Worksheet"
        elif "edl" in filename or "equipment" in filename:
            doc_type = "Equipment Density List"
        elif "opord" in filename:
            doc_type = "OPORD"
        elif "annex" in filename:
            doc_type = "Annex"
        else:
            doc_type = "Planning Document (Excel)"

    elif filename.endswith(".pdf"):
        try:
            import pdfminer.high_level as pdfminer
            from io import BytesIO
            content = pdfminer.extract_text(BytesIO(uploaded_file.read()))
            uploaded_file.seek(0)
        except Exception:
            content = "[PDF text extraction unavailable — summarize key details manually]"
        doc_type = "PDF Document"

    elif filename.endswith((".txt", ".md")):
        content = uploaded_file.read().decode("utf-8", errors="replace")
        doc_type = "Text Document"

    return doc_type, content[:6000]  # Cap at 6000 chars to manage context


# =============================================================================
# MAPPING
# =============================================================================
def mgrs_to_latlon(mgrs_str: str) -> tuple[float, float] | None:
    """Convert MGRS string to (lat, lon). Returns None if conversion fails."""
    if not MGRS_AVAILABLE:
        return None
    try:
        m = mgrs_lib.MGRS()
        lat, lon = m.toLatLon(mgrs_str.replace(" ", "").encode())
        return float(lat), float(lon)
    except Exception:
        return None


def build_tactical_map(units: list[dict], center: list = None, zoom: int = None) -> "folium.Map | None":
    """
    Build a Folium map with unit markers and threat rings.
    units: list of dicts with keys: name, type, lat, lon, color, range_km (optional)
    """
    if not FOLIUM_AVAILABLE:
        return None

    map_center = center or DEFAULT_MAP_CENTER
    map_zoom = zoom or DEFAULT_MAP_ZOOM

    m = folium.Map(
        location=map_center,
        zoom_start=map_zoom,
        tiles="OpenStreetMap",
    )

    color_map = {
        "blue": "blue",
        "red": "red",
        "green": "green",
        "orange": "orange",
        "purple": "purple",
        "gray": "gray",
    }

    for unit in units:
        lat = unit.get("lat")
        lon = unit.get("lon")
        if lat is None or lon is None:
            continue

        color = color_map.get(unit.get("color", "blue"), "blue")
        icon_type = "ship" if unit.get("type") in ("naval", "friendly_ship", "enemy_ship") else "flag"

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(
                f"<b>{unit['name']}</b><br>Type: {unit.get('type','')}<br>{unit.get('notes','')}",
                max_width=200,
            ),
            tooltip=unit["name"],
            icon=folium.Icon(color=color, icon="info-sign"),
        ).add_to(m)

        # Add threat/weapon ring if range provided
        range_km = unit.get("range_km")
        if range_km:
            ring_color = "red" if unit.get("color") == "red" else "blue"
            folium.Circle(
                location=[lat, lon],
                radius=range_km * 1000,
                color=ring_color,
                fill=False,
                weight=1.5,
                opacity=0.6,
                tooltip=f"{unit['name']} range: {range_km} km",
            ).add_to(m)

    return m


# =============================================================================
# HUGHES SALVO CALCULATOR
# =============================================================================
def hughes_salvo_calc(
    alpha: float, A: int,
    beta: float, B: int,
    y: float, z: float,
    a: float, b: float,
) -> dict:
    """Run one salvo exchange and return results dict."""
    blue_missiles = alpha * A
    red_missiles = beta * B
    blue_missiles_through = max(0.0, blue_missiles - y * B)
    red_missiles_through = max(0.0, red_missiles - z * A)
    delta_B = blue_missiles_through / b
    delta_A = red_missiles_through / a
    return {
        "blue_missiles_fired": blue_missiles,
        "red_missiles_fired": red_missiles,
        "blue_missiles_through_defense": blue_missiles_through,
        "red_missiles_through_defense": red_missiles_through,
        "delta_B": delta_B,
        "delta_A": delta_A,
        "B_remaining": max(0, B - delta_B),
        "A_remaining": max(0, A - delta_A),
    }


# =============================================================================
# STREAMLIT UI
# =============================================================================
def render_ammo_sidebar(ammo_status: dict):
    """Render ammunition tracker in sidebar."""
    st.sidebar.markdown("### 📦 Ammunition Status")
    for asset, munitions in ammo_status.items():
        with st.sidebar.expander(asset, expanded=False):
            for munition, counts in munitions.items():
                initial = counts.get("initial", 0)
                expended = counts.get("expended", 0)
                remaining = initial - expended
                pct = remaining / initial if initial > 0 else 0
                color = "green" if pct > 0.5 else ("orange" if pct > 0.25 else "red")
                st.progress(pct, text=f"{munition}: {remaining}/{initial}")


def render_chat():
    """Render the chat interface."""
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        with st.chat_message(role):
            st.markdown(content)


def render_map_tab():
    """Render the interactive tactical map tab."""
    st.subheader("🗺️ Tactical Map")

    if not FOLIUM_AVAILABLE:
        st.warning("Mapping library (folium) not installed. Run: pip install folium streamlit-folium")
        return

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("**Add Unit/Platform**")
        unit_name = st.text_input("Unit Name", key="map_unit_name")
        unit_type = st.selectbox(
            "Type",
            ["friendly_ground", "friendly_ship", "enemy_ship", "enemy_ground", "target"],
            key="map_unit_type",
        )
        coord_type = st.radio("Coord Format", ["Lat/Lon", "MGRS"], horizontal=True)

        if coord_type == "Lat/Lon":
            lat = st.number_input("Latitude", value=15.0, key="map_lat")
            lon = st.number_input("Longitude", value=115.0, key="map_lon")
        else:
            mgrs_str = st.text_input("MGRS", key="map_mgrs", placeholder="e.g. 49QGF5050")
            lat, lon = (None, None)
            if mgrs_str:
                result = mgrs_to_latlon(mgrs_str)
                if result:
                    lat, lon = result
                    st.caption(f"Converted: {lat:.4f}, {lon:.4f}")
                else:
                    st.error("Could not convert MGRS. Check format.")

        range_km = st.number_input("Range Ring (km, 0=none)", min_value=0, value=0, key="map_range")
        unit_color = st.selectbox("Color", ["blue", "red", "green", "orange"], key="map_color")
        unit_notes = st.text_input("Notes", key="map_notes")

        if st.button("Add to Map"):
            if unit_name and lat is not None and lon is not None:
                if "map_units" not in st.session_state:
                    st.session_state.map_units = []
                st.session_state.map_units.append({
                    "name": unit_name,
                    "type": unit_type,
                    "lat": lat,
                    "lon": lon,
                    "range_km": range_km if range_km > 0 else None,
                    "color": unit_color,
                    "notes": unit_notes,
                })
                st.success(f"Added {unit_name}")
            else:
                st.error("Provide unit name and valid coordinates.")

        if st.button("Clear All Units"):
            st.session_state.map_units = []

    with col2:
        units = st.session_state.get("map_units", [])
        fmap = build_tactical_map(units)
        if fmap:
            st_folium(fmap, width=650, height=500)
        else:
            st.info("Map will appear here after adding units.")


def render_hughes_tab():
    """Render the Hughes Salvo Calculator tab."""
    st.subheader("⚓ Hughes Salvo Calculator")
    st.caption("ΔB = max(0, α×A − y×B) / b  |  ΔA = max(0, β×B − z×A) / a")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🔵 Blue Force**")
        A = st.number_input("Ships (A)", min_value=1, value=2, key="h_A")
        alpha = st.number_input("Offensive Power α (missiles/ship/salvo)", min_value=0.0, value=4.0, step=0.5, key="h_alpha")
        z = st.number_input("Defensive Power z (intercepts/ship)", min_value=0.0, value=6.0, step=0.5, key="h_z")
        a = st.number_input("Staying Power a (hits to kill)", min_value=1.0, value=2.0, step=0.5, key="h_a")

    with col2:
        st.markdown("**🔴 Red Force**")
        B = st.number_input("Ships (B)", min_value=1, value=3, key="h_B")
        beta = st.number_input("Offensive Power β (missiles/ship/salvo)", min_value=0.0, value=4.0, step=0.5, key="h_beta")
        y = st.number_input("Defensive Power y (intercepts/ship)", min_value=0.0, value=6.0, step=0.5, key="h_y")
        b = st.number_input("Staying Power b (hits to kill)", min_value=1.0, value=2.0, step=0.5, key="h_b")

    # NMESIS supplement
    st.markdown("**🛡️ Shore-Based NMESIS Supplement**")
    nmesis_missiles = st.number_input("NMESIS missiles added to Blue α", min_value=0, value=0, key="h_nmesis")

    if st.button("🔥 Calculate Salvo Exchange"):
        total_blue_alpha = alpha + (nmesis_missiles / A if A > 0 else 0)
        result = hughes_salvo_calc(total_blue_alpha, A, beta, B, y, z, a, b)

        st.markdown("---")
        st.markdown("**📊 Results**")

        rcol1, rcol2 = st.columns(2)
        with rcol1:
            st.metric("🔵 Blue missiles fired", f"{result['blue_missiles_fired']:.1f}")
            st.metric("Blue missiles through defense", f"{result['blue_missiles_through_defense']:.1f}")
            st.metric("🔴 Red ships lost (ΔB)", f"{result['delta_B']:.2f}")
            st.metric("Red ships remaining", f"{result['B_remaining']:.2f}")
        with rcol2:
            st.metric("🔴 Red missiles fired", f"{result['red_missiles_fired']:.1f}")
            st.metric("Red missiles through defense", f"{result['red_missiles_through_defense']:.1f}")
            st.metric("🔵 Blue ships lost (ΔA)", f"{result['delta_A']:.2f}")
            st.metric("Blue ships remaining", f"{result['A_remaining']:.2f}")

        if result["delta_B"] >= B:
            st.success("✅ Blue achieves BREAKTHROUGH — all Red ships killed/mission-killed")
        elif result["delta_B"] > 0:
            st.info(f"⚡ Partial effect — {result['delta_B']:.1f} Red ships killed/mission-killed")
        else:
            st.error("❌ Blue salvo absorbed by Red defenses — no penetrating hits")

        if result["delta_A"] >= A:
            st.error("🚨 Red achieves BREAKTHROUGH — all Blue ships killed/mission-killed")
        elif result["delta_A"] > 0:
            st.warning(f"⚠️ Blue takes {result['delta_A']:.1f} ships killed/mission-killed")
        else:
            st.success("✅ Blue defenses held — no Red missiles penetrated")


def render_coalition_sidebar():
    """Render coalition ship session initialization in sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🌐 Coalition Ships")

    if "coalition_ships" not in st.session_state:
        st.session_state.coalition_ships = []

    with st.sidebar.expander("Add Coalition Platform"):
        c_name = st.text_input("Ship Name", key="cs_name", placeholder="e.g. FDI Behlarra")
        c_nation = st.text_input("Nation", key="cs_nation", placeholder="e.g. Greece")
        c_type = st.selectbox("Type", ["DDG", "FFG", "CG", "LCS", "OPV", "Other"], key="cs_type")
        c_alpha = st.number_input("Offensive Power α", min_value=0.0, value=2.0, step=0.5, key="cs_alpha")
        c_y = st.number_input("Defensive Power y", min_value=0.0, value=4.0, step=0.5, key="cs_y")
        c_b = st.number_input("Staying Power b", min_value=1.0, value=2.0, step=0.5, key="cs_b")
        c_missiles = st.text_input("Key Missiles (comma-sep)", key="cs_missiles", placeholder="e.g. Aster 30 x16, Exocet x8")

        if st.button("Add Coalition Ship"):
            if c_name and c_nation:
                st.session_state.coalition_ships.append({
                    "name": c_name,
                    "nation": c_nation,
                    "type": c_type,
                    "alpha_power": c_alpha,
                    "defensive_power": c_y,
                    "staying_power": c_b,
                    "missiles": c_missiles,
                })
                st.success(f"Added {c_name} ({c_nation})")

    if st.session_state.coalition_ships:
        st.sidebar.markdown("**Current Coalition Ships:**")
        for ship in st.session_state.coalition_ships:
            st.sidebar.caption(f"• {ship['name']} ({ship['nation']}) α={ship['alpha_power']}")
        if st.sidebar.button("Clear Coalition Ships"):
            st.session_state.coalition_ships = []


# =============================================================================
# MAIN APP
# =============================================================================
def main():
    st.set_page_config(
        page_title="Fires Coordinator Agent v9",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Load reference documents
    weapons_ref, hughes_model = load_reference_docs()

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "ammo_status" not in st.session_state:
        st.session_state.ammo_status = copy.deepcopy(
            LOADOUT_PRESETS["Default (Planning)"]
        )

    if "current_loadout" not in st.session_state:
        st.session_state.current_loadout = "Default (Planning)"

    if "uploaded_docs" not in st.session_state:
        st.session_state.uploaded_docs = {}

    if "adversary" not in st.session_state:
        st.session_state.adversary = "Olvana (Chinese-type)"

    if "map_units" not in st.session_state:
        st.session_state.map_units = []

    if "coalition_ships" not in st.session_state:
        st.session_state.coalition_ships = []

    # ---- SIDEBAR ----
    with st.sidebar:
        st.title("🎯 Fires Coordinator")
        st.caption("v9 | EWS MAGTF Ops Afloat")

        # Adversary selector
        st.markdown("### 🔴 Adversary")
        adversary = st.selectbox(
            "Select Adversary",
            list(ADVERSARY_PRESETS.keys()),
            index=list(ADVERSARY_PRESETS.keys()).index(st.session_state.adversary),
            key="adversary_select",
        )
        st.session_state.adversary = adversary

        # Loadout selector
        st.markdown("### 📦 Loadout Preset")
        selected_loadout = st.selectbox(
            "Mission Loadout",
            list(LOADOUT_PRESETS.keys()),
            index=list(LOADOUT_PRESETS.keys()).index(st.session_state.current_loadout)
            if st.session_state.current_loadout in LOADOUT_PRESETS
            else 0,
            key="loadout_select",
        )

        if st.button("Apply Loadout"):
            st.session_state.ammo_status = copy.deepcopy(LOADOUT_PRESETS[selected_loadout])
            st.session_state.current_loadout = selected_loadout
            st.success(f"Loadout set: {selected_loadout}")

        # Ammo tracker
        render_ammo_sidebar(st.session_state.ammo_status)

        # Coalition ships
        render_coalition_sidebar()

        # Document upload
        st.markdown("---")
        st.markdown("### 📄 Document Upload")
        doc_type_hint = st.selectbox(
            "Document Type",
            ["Auto-Detect", "AGM/TSS/HPTL Matrix", "Target List Worksheet",
             "Equipment Density List", "OPORD", "Annex", "Other"],
            key="doc_type_select",
        )
        uploaded_file = st.file_uploader(
            "Upload Planning Doc",
            type=["xlsx", "xls", "pdf", "txt", "md"],
            key="doc_uploader",
        )
        if uploaded_file and st.button("Process Document"):
            with st.spinner("Processing..."):
                dtype, dcontent = parse_uploaded_document(uploaded_file)
                if doc_type_hint != "Auto-Detect":
                    dtype = doc_type_hint
                st.session_state.uploaded_docs[dtype] = dcontent
                st.success(f"Loaded: {dtype}")

        if st.session_state.uploaded_docs:
            st.markdown("**Loaded Documents:**")
            for dt in st.session_state.uploaded_docs:
                st.caption(f"✅ {dt}")
            if st.button("Clear Documents"):
                st.session_state.uploaded_docs = {}

        # Session reset
        st.markdown("---")
        if st.button("🔄 Reset Session"):
            for key in ["messages", "ammo_status", "uploaded_docs", "map_units", "coalition_ships"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # ---- MAIN CONTENT ----
    tab_chat, tab_map, tab_hughes = st.tabs(["💬 Fires Planning", "🗺️ Tactical Map", "⚓ Hughes Calculator"])

    with tab_chat:
        st.markdown(f"""
        ### 🎯 Fires Coordinator Agent — *Pacific Guard / MAGTF Fires Training*
        **Adversary:** {st.session_state.adversary} | **Loadout:** {st.session_state.current_loadout}

        I can assist with:
        - 🎯 **Weapons-target matching** recommendations
        - 📊 **Salvo calculations** using Pk-based weaponeering
        - ⚓ **Naval engagement analysis** using the Hughes Salvo Model
        - 📦 **Ammunition tracking** with status alerts
        - ⚠️ **LRASM** is aircraft-launched only (F/A-18E/F, F-35C) — not ship-launched

        **Example queries:**
        - *"Recommend a weapon to engage a HQ-9 battery at 80km"*
        - *"Calculate rounds required for 90% Pk against a hardened C2 bunker using GMLRS"*
        - *"Analyze: 2 DDGs + NMESIS vs Type 052D SAG with 3 ships"*
        - *"Update ammo: expended 18 GMLRS and 4 PrSM"*

        ---
        """)

        render_chat()

        if prompt := st.chat_input("Enter your fires planning query..."):
            st.session_state.messages.append({"role": "user", "content": prompt})

            # Check if user mentions force composition — auto-update ammo if parseable
            if any(kw in prompt.lower() for kw in ["himars", "m777", "ddg", "cg ", "ffg"]):
                st.session_state.ammo_status = parse_ammo_from_chat(
                    prompt, st.session_state.ammo_status
                )

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    system_prompt = get_system_prompt_with_context(
                        weapons_ref_text=weapons_ref,
                        hughes_model_text=hughes_model,
                        ammo_status=st.session_state.ammo_status,
                        uploaded_docs=st.session_state.uploaded_docs,
                        adversary_preset=st.session_state.adversary,
                        current_loadout=st.session_state.current_loadout,
                        coalition_ships=st.session_state.coalition_ships if st.session_state.coalition_ships else None,
                    )

                    client = anthropic.Anthropic()
                    response = client.messages.create(
                        model=MODEL,
                        max_tokens=MAX_TOKENS,
                        system=system_prompt,
                        messages=[
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages
                        ],
                    )

                    response_text = response.content[0].text
                    st.markdown(response_text)

                    # Parse and apply any ammo updates
                    updates = parse_ammo_updates(response_text)
                    if updates:
                        st.session_state.ammo_status = apply_ammo_updates(
                            st.session_state.ammo_status, updates
                        )

            st.session_state.messages.append(
                {"role": "assistant", "content": response_text}
            )

    with tab_map:
        render_map_tab()

    with tab_hughes:
        render_hughes_tab()


if __name__ == "__main__":
    main()
