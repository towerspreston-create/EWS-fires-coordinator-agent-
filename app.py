"""
Fires Coordinator Agent v8
EWS MAGTF Operations Afloat Training Tool

A Streamlit application that provides AI-assisted fires planning support
for USMC Expeditionary Warfare School students.

Features:
- Weapons-target matching with TSS integration
- Salvo calculations using Pk-based weaponeering
- Naval engagement analysis (Hughes Salvo Model)
- OPF-M (Hero-120) employment
- AGM/TSS/HPTL Matrix parsing and creation
- Target List Worksheet (TLWS) management
- Equipment Density List (EDL) parsing
- OPORD/Annex parsing with EFST extraction
- Ammunition tracking with dynamic loadouts
- Interactive map with threat rings
"""

import streamlit as st
import anthropic
import re
from pathlib import Path
import sys
import copy
import json
import pandas as pd
from io import BytesIO
import math

# Map imports
try:
    import folium
    from streamlit_folium import st_folium
    import mgrs
    MAPS_AVAILABLE = True
except ImportError:
    MAPS_AVAILABLE = False

# Add prompts directory to path
sys.path.insert(0, str(Path(__file__).parent))
from prompts.system_prompt import get_system_prompt_with_context

# =============================================================================
# CONFIGURATION
# =============================================================================

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096

# =============================================================================
# ADVERSARY DATA
# =============================================================================

ADVERSARY_PRESETS = {
    "Ariana (Iranian-type)": {
        "description": "Iranian-type adversary for Operation Dominion Advance",
        "systems": {
            "ADA": ["2S6M SHORAD", "Crotale P4R", "MTLBU (Radar)", "SA-15 Gauntlet"],
            "IDF": ["PRIMA MRLS", "2S19 Howitzer", "2S9", "D-30", "2S23", "BM-21 Grad"],
            "Armor": ["T-90", "T-80", "T-72B3", "BMP-2"],
            "INTEL": ["R-330K EW System", "BRDM-2", "Skylark IV UAV", "BRM-3K"],
            "Mech_Inf": ["BTR-80", "BMP", "BMP-2", "2330 TIGR", "BTR-82A"],
            "CSS": ["AEV IMR-2 CBT", "URAL 375D", "MTLB", "GAZ 66"],
        }
    },
    "Olvana (Chinese-type)": {
        "description": "Chinese-type adversary for Pacific operations",
        "systems": {
            "ADA": ["HQ-9 (200km)", "HQ-16 (40km)", "HQ-7 (15km)", "PGZ-07", "LD-2000 CIWS"],
            "IDF": ["PLZ-05 SPH", "PCL-181", "PHL-03 MLRS", "PHL-16"],
            "Armor": ["Type 99A", "Type 96A", "ZTD-05", "Type 15"],
            "INTEL": ["BZK-005 UAV", "WZ-7 Soaring Dragon", "YLC-8B Radar"],
            "Mech_Inf": ["ZBD-04A IFV", "ZBL-08", "ZBD-05"],
            "Naval": ["Type 055 (112 VLS)", "Type 052D (64 VLS)", "Type 054A (32 VLS)", "Type 056"],
            "Coastal_Defense": ["YJ-62 Battery", "YJ-18 Battery"],
            "CSS": ["Type 09 ARV", "GCZ-112 Engineer"],
        }
    },
    "Custom": {
        "description": "User-defined adversary",
        "systems": {}
    }
}

# =============================================================================
# LOADOUT PRESETS
# =============================================================================

LOADOUT_PRESETS = {
    "Standard MEU": {
        "description": "Standard Marine Expeditionary Unit loadout",
        "ammo": {
            "GMLRS": {"current": 108, "max": 108, "unit": "rockets"},
            "ATACMS": {"current": 12, "max": 12, "unit": "missiles"},
            "PrSM": {"current": 24, "max": 24, "unit": "missiles"},
            "OPF-M": {"current": 12, "max": 12, "unit": "missiles"},
            "155mm_HE": {"current": 600, "max": 600, "unit": "rounds"},
            "Excalibur": {"current": 36, "max": 36, "unit": "rounds"},
            "5in_Naval": {"current": 600, "max": 600, "unit": "rounds"},
            "VLS_Cells": {"current": 96, "max": 96, "unit": "cells"},
            "Harpoon_LRASM": {"current": 8, "max": 8, "unit": "missiles"},
            "Mortar_HE": {"current": 200, "max": 200, "unit": "rounds"},
            "Mortar_Illum": {"current": 48, "max": 48, "unit": "rounds"},
            "Mortar_Smoke": {"current": 24, "max": 24, "unit": "rounds"},
        }
    },
    "RCT (Dominion Advance)": {
        "description": "RCT-3 loadout based on EDL - 18x M777, 2x HIMARS",
        "ammo": {
            "GMLRS": {"current": 72, "max": 72, "unit": "rockets"},
            "ATACMS": {"current": 8, "max": 8, "unit": "missiles"},
            "OPF-M": {"current": 96, "max": 96, "unit": "missiles"},  # 12 launchers × 8 rounds
            "155mm_HE": {"current": 1800, "max": 1800, "unit": "rounds"},  # 18 guns × 100
            "Excalibur": {"current": 108, "max": 108, "unit": "rounds"},  # 18 guns × 6
            "81mm_Mortar": {"current": 480, "max": 480, "unit": "rounds"},  # 24 tubes × 20
            "60mm_Mortar": {"current": 270, "max": 270, "unit": "rounds"},  # 27 tubes × 10
        }
    },
    "EABO Light": {
        "description": "Expeditionary Advanced Base Operations - Light footprint",
        "ammo": {
            "GMLRS": {"current": 36, "max": 36, "unit": "rockets"},
            "ATACMS": {"current": 4, "max": 4, "unit": "missiles"},
            "PrSM": {"current": 8, "max": 8, "unit": "missiles"},
            "OPF-M": {"current": 24, "max": 24, "unit": "missiles"},
            "155mm_HE": {"current": 200, "max": 200, "unit": "rounds"},
            "Excalibur": {"current": 12, "max": 12, "unit": "rounds"},
            "5in_Naval": {"current": 300, "max": 300, "unit": "rounds"},
            "VLS_Cells": {"current": 48, "max": 48, "unit": "cells"},
            "Harpoon_LRASM": {"current": 4, "max": 4, "unit": "missiles"},
            "Mortar_HE": {"current": 100, "max": 100, "unit": "rounds"},
        }
    },
    "Naval Focus (Pacific Guard)": {
        "description": "Anti-surface warfare emphasis with NMESIS",
        "ammo": {
            "GMLRS": {"current": 54, "max": 54, "unit": "rockets"},
            "ATACMS": {"current": 6, "max": 6, "unit": "missiles"},
            "PrSM": {"current": 36, "max": 36, "unit": "missiles"},
            "OPF-M": {"current": 18, "max": 18, "unit": "missiles"},
            "NSM_NMESIS": {"current": 16, "max": 16, "unit": "missiles"},
            "155mm_HE": {"current": 300, "max": 300, "unit": "rounds"},
            "Excalibur": {"current": 18, "max": 18, "unit": "rounds"},
            "5in_Naval": {"current": 800, "max": 800, "unit": "rounds"},
            "VLS_Cells": {"current": 144, "max": 144, "unit": "cells"},
            "Harpoon_LRASM": {"current": 16, "max": 16, "unit": "missiles"},
        }
    },
    "Custom": {
        "description": "User-defined loadout",
        "ammo": {}
    }
}

DEFAULT_LOADOUT = "Standard MEU"

# Ammo type aliases for parsing
AMMO_ALIASES = {
    "gmlrs": "GMLRS",
    "atacms": "ATACMS",
    "prsm": "PrSM",
    "precision strike missile": "PrSM",
    "opf-m": "OPF-M",
    "opfm": "OPF-M",
    "hero-120": "OPF-M",
    "loitering": "OPF-M",
    "nsm": "NSM_NMESIS",
    "nmesis": "NSM_NMESIS",
    "155mm": "155mm_HE",
    "155mm he": "155mm_HE",
    "excalibur": "Excalibur",
    "m982": "Excalibur",
    "5 inch": "5in_Naval",
    "5in": "5in_Naval",
    "vls": "VLS_Cells",
    "tomahawk": "VLS_Cells",
    "tlam": "VLS_Cells",
    "harpoon": "Harpoon_LRASM",
    "lrasm": "Harpoon_LRASM",
    "mortar he": "Mortar_HE",
    "81mm": "81mm_Mortar",
    "60mm": "60mm_Mortar",
}

AMMO_DISPLAY_NAMES = {
    "GMLRS": "GMLRS",
    "ATACMS": "ATACMS", 
    "PrSM": "PrSM",
    "OPF-M": "OPF-M (Hero-120)",
    "NSM_NMESIS": "NSM/NMESIS",
    "155mm_HE": "155mm HE",
    "Excalibur": "Excalibur",
    "5in_Naval": "5in Naval",
    "VLS_Cells": "VLS Cells",
    "Harpoon_LRASM": "Harpoon/LRASM",
    "Mortar_HE": "Mortar HE",
    "Mortar_Illum": "Mortar Illum",
    "Mortar_Smoke": "Mortar Smoke",
    "81mm_Mortar": "81mm Mortar",
    "60mm_Mortar": "60mm Mortar",
}

AMMO_CATEGORIES = {
    "HIMARS Battery": ["GMLRS", "ATACMS", "PrSM"],
    "OPF-M Section": ["OPF-M"],
    "NMESIS Battery": ["NSM_NMESIS"],
    "Artillery Battery": ["155mm_HE", "Excalibur"],
    "DDG": ["5in_Naval", "VLS_Cells", "Harpoon_LRASM"],
    "Mortars": ["Mortar_HE", "Mortar_Illum", "Mortar_Smoke", "81mm_Mortar", "60mm_Mortar"],
}

# =============================================================================
# NAVAL PLATFORM LOADOUTS (for dynamic task org)
# =============================================================================

NAVAL_PLATFORM_LOADOUTS = {
    "DDG_FLT_IIA": {
        "name": "DDG-51 Flight IIA",
        "description": "Arleigh Burke Flight IIA with helo hangar",
        "ammo": {
            "VLS_Cells": 96,
            "5in_Naval": 600,
            "Harpoon_LRASM": 8,
        },
        "capabilities": ["MH-60R ASW", "AEGIS BMD"],
    },
    "DDG_FLT_III": {
        "name": "DDG-51 Flight III",
        "description": "Arleigh Burke Flight III with SPY-6 radar",
        "ammo": {
            "VLS_Cells": 96,
            "5in_Naval": 600,
            "Harpoon_LRASM": 8,
        },
        "capabilities": ["MH-60R ASW", "AEGIS BMD", "SPY-6 AMDR"],
    },
    "CG": {
        "name": "CG-47 Ticonderoga",
        "description": "Ticonderoga-class cruiser",
        "ammo": {
            "VLS_Cells": 122,
            "5in_Naval": 600,
            "Harpoon_LRASM": 8,
        },
        "capabilities": ["AEGIS", "2x 5in guns"],
    },
    "FFG": {
        "name": "FFG-62 Constellation",
        "description": "Constellation-class frigate",
        "ammo": {
            "VLS_Cells": 32,
            "5in_Naval": 400,
        },
        "capabilities": ["EASR radar", "MH-60R ASW"],
    },
    "LCS": {
        "name": "LCS",
        "description": "Littoral Combat Ship",
        "ammo": {
            "RAM": 21,
        },
        "capabilities": ["Mission modules", "Surface warfare"],
    },
}

# Platform name aliases for parsing
PLATFORM_ALIASES = {
    "ddg": "DDG_FLT_IIA",
    "ddg-51": "DDG_FLT_IIA",
    "ddg flt ii": "DDG_FLT_IIA",
    "ddg flt iia": "DDG_FLT_IIA",
    "ddg flight iia": "DDG_FLT_IIA",
    "ddg flt iii": "DDG_FLT_III",
    "ddg flight iii": "DDG_FLT_III",
    "cg": "CG",
    "cg-47": "CG",
    "cruiser": "CG",
    "ticonderoga": "CG",
    "ffg": "FFG",
    "ffg-62": "FFG",
    "constellation": "FFG",
    "frigate": "FFG",
    "lcs": "LCS",
}

# Ground unit loadouts
GROUND_UNIT_LOADOUTS = {
    "HIMARS_BTY": {
        "name": "HIMARS Battery",
        "description": "6x M142 HIMARS launchers",
        "ammo": {
            "GMLRS": 108,
            "ATACMS": 12,
            "PrSM": 24,
        },
    },
    "ARTY_BTY_155": {
        "name": "Artillery Battery (M777)",
        "description": "6x M777A2 howitzers",
        "ammo": {
            "155mm_HE": 600,
            "Excalibur": 36,
        },
    },
    "NMESIS_PLT": {
        "name": "NMESIS Platoon",
        "description": "9x NMESIS launchers (18 NSM)",
        "ammo": {
            "NSM_NMESIS": 18,
        },
    },
    "OPF-M_SEC": {
        "name": "OPF-M Section",
        "description": "2x JLTV with Hero-120",
        "ammo": {
            "OPF-M": 12,
        },
    },
    "MORTAR_PLT": {
        "name": "81mm Mortar Platoon",
        "description": "4x 81mm mortars",
        "ammo": {
            "Mortar_HE": 200,
            "Mortar_Illum": 48,
            "Mortar_Smoke": 24,
        },
    },
}

# =============================================================================
# THREAT SYSTEMS DATA (for map visualization)
# =============================================================================

# Range in nautical miles for threat rings
THREAT_SYSTEMS = {
    # BLUE FORCE - Friendly systems
    "blue": {
        "HIMARS": {"range_nm": 40, "type": "fires", "color": "blue", "description": "GMLRS range"},
        "HIMARS_ER": {"range_nm": 81, "type": "fires", "color": "blue", "description": "GMLRS-ER range"},
        "PrSM": {"range_nm": 310, "type": "fires", "color": "blue", "description": "PrSM range"},
        "ATACMS": {"range_nm": 190, "type": "fires", "color": "blue", "description": "ATACMS range"},
        "M777": {"range_nm": 13, "type": "fires", "color": "blue", "description": "155mm HE range"},
        "Excalibur": {"range_nm": 22, "type": "fires", "color": "blue", "description": "Excalibur range"},
        "NSM_NMESIS": {"range_nm": 100, "type": "ascm", "color": "blue", "description": "NSM range"},
        "Harpoon": {"range_nm": 67, "type": "ascm", "color": "blue", "description": "Harpoon range"},
        "LRASM": {"range_nm": 200, "type": "ascm", "color": "blue", "description": "LRASM range"},
        "SM-6": {"range_nm": 130, "type": "sam", "color": "blue", "description": "SM-6 range"},
        "Tomahawk": {"range_nm": 900, "type": "strike", "color": "blue", "description": "TLAM range"},
    },
    # RED FORCE - Adversary systems (longest range threat per platform)
    "red": {
        # Naval - use longest range ASCM
        "Type_055": {"range_nm": 290, "type": "ascm", "color": "red", "description": "YJ-18 (290nm)"},
        "Type_052D": {"range_nm": 290, "type": "ascm", "color": "red", "description": "YJ-18 (290nm)"},
        "Type_052C": {"range_nm": 270, "type": "ascm", "color": "red", "description": "YJ-62 (270nm)"},
        "Type_054A": {"range_nm": 135, "type": "ascm", "color": "red", "description": "YJ-83 (135nm)"},
        "Type_056": {"range_nm": 40, "type": "ascm", "color": "red", "description": "YJ-83 (limited)"},
        "Type_022": {"range_nm": 135, "type": "ascm", "color": "red", "description": "YJ-83 (135nm)"},
        # Ground-based ADA - longest range SAM
        "HQ-9": {"range_nm": 108, "type": "sam", "color": "orange", "description": "HQ-9 (200km)"},
        "S-400": {"range_nm": 216, "type": "sam", "color": "orange", "description": "S-400 (400km)"},
        "HQ-16": {"range_nm": 27, "type": "sam", "color": "orange", "description": "HQ-16 (50km)"},
        "HQ-7": {"range_nm": 8, "type": "sam", "color": "orange", "description": "HQ-7 (15km)"},
        # Shore-based ASCM
        "YJ-62_Coastal": {"range_nm": 270, "type": "ascm", "color": "red", "description": "YJ-62 coastal (270nm)"},
        "YJ-12B": {"range_nm": 270, "type": "ascm", "color": "red", "description": "YJ-12B (270nm)"},
        # Ballistic missiles
        "DF-21D": {"range_nm": 810, "type": "asbm", "color": "darkred", "description": "DF-21D ASBM (810nm)"},
        "DF-26": {"range_nm": 2160, "type": "asbm", "color": "darkred", "description": "DF-26 (2160nm)"},
        # Ground fires
        "PHL-03": {"range_nm": 81, "type": "fires", "color": "yellow", "description": "PHL-03 MLRS (150km)"},
        "PHL-16": {"range_nm": 151, "type": "fires", "color": "yellow", "description": "PHL-16 (280km)"},
        "PLZ-05": {"range_nm": 27, "type": "fires", "color": "yellow", "description": "PLZ-05 155mm (50km)"},
    }
}

# Map default center (Indo-Pacific - South China Sea area)
MAP_DEFAULT_CENTER = [15.0, 120.0]
MAP_DEFAULT_ZOOM = 5

# =============================================================================
# DEFAULT TSS TEMPLATE
# =============================================================================

DEFAULT_TSS = {
    "FA": {"TLE": "100m", "Size": "Section", "Activity": "Stationary", "Time": "30 MIN", "Effects": "N"},
    "FW_CAS": {"TLE": "500m", "Size": "Section", "Activity": "Stat/Moving", "Time": "45 MIN", "Effects": "D"},
    "RW_CAS": {"TLE": "500m", "Size": "Section", "Activity": "Stat/Moving", "Time": "45 MIN", "Effects": "D"},
    "HIMARS": {"TLE": "50m", "Size": "Section", "Activity": "Stationary", "Time": "30 MIN", "Effects": "S"},
    "OPF-M": {"TLE": "500m", "Size": "Section", "Activity": "Stat/Moving", "Time": "45 MIN", "Effects": "N"},
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_reference_docs() -> dict:
    """Load all reference documents for the agent's knowledge base."""
    base_path = Path(__file__).parent / "data"
    docs = {}
    
    doc_files = {
        'doctrine': 'fires_doctrine_reference.md',
        'weapons': 'weapons_reference.md',
        'hughes': 'hughes_salvo_model.md'
    }
    
    for key, filename in doc_files.items():
        filepath = base_path / filename
        if filepath.exists():
            docs[key] = filepath.read_text(encoding='utf-8')
        else:
            docs[key] = f"{key.title()} reference not found."
    
    return docs


def get_ammo_status_string() -> str:
    """Generate ammunition status string for system prompt."""
    lines = ["Current ammunition status:"]
    for ammo_type, data in st.session_state.ammo.items():
        pct = (data["current"] / data["max"]) * 100 if data["max"] > 0 else 0
        status = get_status_label(pct)
        display_name = AMMO_DISPLAY_NAMES.get(ammo_type, ammo_type.replace("_", " "))
        lines.append(f"- {display_name}: {data['current']}/{data['max']} {data['unit']} ({pct:.0f}%) [{status}]")
    return "\n".join(lines)


# =============================================================================
# MAP HELPER FUNCTIONS
# =============================================================================

def mgrs_to_latlon(mgrs_string: str) -> tuple:
    """Convert MGRS coordinate to lat/lon. Returns (lat, lon) or None if invalid."""
    if not MAPS_AVAILABLE:
        return None
    try:
        m = mgrs.MGRS()
        # Clean up the MGRS string
        mgrs_clean = mgrs_string.upper().replace(" ", "")
        lat, lon = m.toLatLon(mgrs_clean)
        return (lat, lon)
    except Exception as e:
        st.warning(f"Invalid MGRS coordinate: {mgrs_string}")
        return None


def latlon_to_mgrs(lat: float, lon: float) -> str:
    """Convert lat/lon to MGRS string."""
    if not MAPS_AVAILABLE:
        return ""
    try:
        m = mgrs.MGRS()
        return m.toMGRS(lat, lon)
    except Exception:
        return ""


def parse_coordinates(coord_string: str) -> tuple:
    """
    Parse coordinates from various formats.
    Returns (lat, lon) tuple or None if invalid.
    
    Supports:
    - MGRS: "32S ME 5184 1489" or "32SME51841489"
    - Lat/Lon: "15.123, 120.456" or "15.123 120.456"
    """
    if not coord_string:
        return None
    
    coord_string = coord_string.strip()
    
    # Try lat/lon first (decimal degrees)
    latlon_pattern = r'^(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)$'
    match = re.match(latlon_pattern, coord_string)
    if match:
        try:
            lat = float(match.group(1))
            lon = float(match.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
        except ValueError:
            pass
    
    # Try MGRS
    if MAPS_AVAILABLE:
        result = mgrs_to_latlon(coord_string)
        if result:
            return result
    
    return None


def nm_to_meters(nm: float) -> float:
    """Convert nautical miles to meters."""
    return nm * 1852


def add_map_unit(unit_id: str, name: str, lat: float, lon: float, 
                 unit_type: str, force: str = "blue", system: str = None):
    """Add a unit to the map."""
    if "map_units" not in st.session_state:
        st.session_state.map_units = {}
    
    st.session_state.map_units[unit_id] = {
        "name": name,
        "lat": lat,
        "lon": lon,
        "type": unit_type,
        "force": force,  # "blue" or "red"
        "system": system,  # For threat ring lookup
        "mgrs": latlon_to_mgrs(lat, lon) if MAPS_AVAILABLE else ""
    }


def remove_map_unit(unit_id: str):
    """Remove a unit from the map."""
    if "map_units" in st.session_state and unit_id in st.session_state.map_units:
        del st.session_state.map_units[unit_id]


def clear_map_units(force: str = None):
    """Clear all map units, optionally filtered by force."""
    if "map_units" not in st.session_state:
        return
    
    if force is None:
        st.session_state.map_units = {}
    else:
        st.session_state.map_units = {
            uid: u for uid, u in st.session_state.map_units.items() 
            if u.get("force") != force
        }


def get_threat_range(system: str, force: str = "red") -> dict:
    """Get threat range info for a system."""
    systems = THREAT_SYSTEMS.get(force, {})
    return systems.get(system, None)


# =============================================================================
# DYNAMIC LOADOUT FUNCTIONS
# =============================================================================

def parse_loadout_updates(response: str) -> list:
    """
    Parse loadout updates from assistant response.
    Returns list of updates: [{"action": "set/add/clear", "ammo_type": str, "quantity": int}]
    """
    updates = []
    
    # Pattern for setting specific ammo counts
    # [LOADOUT_UPDATE] TYPE: GMLRS SET: 108 [/LOADOUT_UPDATE]
    pattern_set = r'\[LOADOUT_UPDATE\]\s*TYPE:\s*([^\n]+?)\s*SET:\s*(\d+)\s*\[/LOADOUT_UPDATE\]'
    for item, amount in re.findall(pattern_set, response, re.IGNORECASE):
        ammo_type = resolve_ammo_type(item.strip())
        if ammo_type:
            updates.append({"action": "set", "ammo_type": ammo_type, "quantity": int(amount)})
    
    # Pattern for adding to ammo counts
    # [LOADOUT_UPDATE] TYPE: VLS_Cells ADD: 96 [/LOADOUT_UPDATE]
    pattern_add = r'\[LOADOUT_UPDATE\]\s*TYPE:\s*([^\n]+?)\s*ADD:\s*(\d+)\s*\[/LOADOUT_UPDATE\]'
    for item, amount in re.findall(pattern_add, response, re.IGNORECASE):
        ammo_type = resolve_ammo_type(item.strip())
        if ammo_type:
            updates.append({"action": "add", "ammo_type": ammo_type, "quantity": int(amount)})
    
    # Pattern for platform-based loadout
    # [LOADOUT_UPDATE] PLATFORM: DDG_FLT_IIA COUNT: 2 [/LOADOUT_UPDATE]
    pattern_platform = r'\[LOADOUT_UPDATE\]\s*PLATFORM:\s*([^\n]+?)\s*COUNT:\s*(\d+)\s*\[/LOADOUT_UPDATE\]'
    for platform, count in re.findall(pattern_platform, response, re.IGNORECASE):
        platform_key = resolve_platform_type(platform.strip())
        if platform_key and platform_key in NAVAL_PLATFORM_LOADOUTS:
            loadout = NAVAL_PLATFORM_LOADOUTS[platform_key]
            for ammo_type, qty in loadout["ammo"].items():
                updates.append({"action": "add", "ammo_type": ammo_type, "quantity": qty * int(count)})
    
    # Pattern for ground unit loadout
    # [LOADOUT_UPDATE] UNIT: HIMARS_BTY COUNT: 1 [/LOADOUT_UPDATE]
    pattern_unit = r'\[LOADOUT_UPDATE\]\s*UNIT:\s*([^\n]+?)\s*COUNT:\s*(\d+)\s*\[/LOADOUT_UPDATE\]'
    for unit, count in re.findall(pattern_unit, response, re.IGNORECASE):
        unit_key = unit.strip().upper().replace(" ", "_").replace("-", "_")
        if unit_key in GROUND_UNIT_LOADOUTS:
            loadout = GROUND_UNIT_LOADOUTS[unit_key]
            for ammo_type, qty in loadout["ammo"].items():
                updates.append({"action": "add", "ammo_type": ammo_type, "quantity": qty * int(count)})
    
    # Pattern for clearing loadout
    # [LOADOUT_UPDATE] CLEAR: ALL [/LOADOUT_UPDATE]
    if re.search(r'\[LOADOUT_UPDATE\]\s*CLEAR:\s*ALL\s*\[/LOADOUT_UPDATE\]', response, re.IGNORECASE):
        updates.append({"action": "clear", "ammo_type": None, "quantity": 0})
    
    return updates


def resolve_platform_type(platform: str) -> str:
    """Resolve platform name to standard key."""
    platform_lower = platform.lower().strip()
    if platform_lower in PLATFORM_ALIASES:
        return PLATFORM_ALIASES[platform_lower]
    # Try direct match
    platform_upper = platform.upper().replace(" ", "_").replace("-", "_")
    if platform_upper in NAVAL_PLATFORM_LOADOUTS:
        return platform_upper
    return None


def apply_loadout_updates(updates: list):
    """Apply loadout updates to session state."""
    for update in updates:
        action = update["action"]
        ammo_type = update["ammo_type"]
        quantity = update["quantity"]
        
        if action == "clear":
            # Clear all ammo
            for key in st.session_state.ammo:
                st.session_state.ammo[key]["current"] = 0
                st.session_state.ammo[key]["max"] = 0
        elif action == "set":
            if ammo_type in st.session_state.ammo:
                st.session_state.ammo[ammo_type]["current"] = quantity
                st.session_state.ammo[ammo_type]["max"] = quantity
            else:
                # Add new ammo type
                st.session_state.ammo[ammo_type] = {
                    "current": quantity,
                    "max": quantity,
                    "unit": "rounds"
                }
        elif action == "add":
            if ammo_type in st.session_state.ammo:
                st.session_state.ammo[ammo_type]["current"] += quantity
                st.session_state.ammo[ammo_type]["max"] += quantity
            else:
                st.session_state.ammo[ammo_type] = {
                    "current": quantity,
                    "max": quantity,
                    "unit": "rounds"
                }
    
    # Update loadout name
    if updates:
        st.session_state.current_loadout = "Custom (from chat)"


def parse_map_updates(response: str) -> list:
    """
    Parse map unit updates from assistant response.
    Returns list of map updates.
    """
    updates = []
    
    # Pattern for adding map units
    # [MAP_UPDATE] ACTION: ADD NAME: "Enemy SAM" COORD: 32SME51841489 FORCE: red SYSTEM: HQ-9 [/MAP_UPDATE]
    pattern = r'\[MAP_UPDATE\]\s*ACTION:\s*ADD\s+NAME:\s*"([^"]+)"\s+COORD:\s*(\S+)\s+FORCE:\s*(\w+)\s+SYSTEM:\s*(\S+)\s*\[/MAP_UPDATE\]'
    for name, coord, force, system in re.findall(pattern, response, re.IGNORECASE):
        coords = parse_coordinates(coord)
        if coords:
            updates.append({
                "action": "add",
                "name": name,
                "lat": coords[0],
                "lon": coords[1],
                "force": force.lower(),
                "system": system
            })
    
    # Pattern for removing map units
    # [MAP_UPDATE] ACTION: REMOVE NAME: "Enemy SAM" [/MAP_UPDATE]
    pattern_remove = r'\[MAP_UPDATE\]\s*ACTION:\s*REMOVE\s+NAME:\s*"([^"]+)"\s*\[/MAP_UPDATE\]'
    for name in re.findall(pattern_remove, response, re.IGNORECASE):
        updates.append({"action": "remove", "name": name})
    
    # Pattern for clearing map
    # [MAP_UPDATE] ACTION: CLEAR FORCE: red [/MAP_UPDATE]
    pattern_clear = r'\[MAP_UPDATE\]\s*ACTION:\s*CLEAR\s+FORCE:\s*(\w+)\s*\[/MAP_UPDATE\]'
    for force in re.findall(pattern_clear, response, re.IGNORECASE):
        updates.append({"action": "clear", "force": force.lower()})
    
    return updates


def apply_map_updates(updates: list):
    """Apply map updates to session state."""
    for update in updates:
        action = update["action"]
        
        if action == "add":
            unit_id = f"{update['name']}_{update['lat']:.4f}_{update['lon']:.4f}"
            add_map_unit(
                unit_id=unit_id,
                name=update["name"],
                lat=update["lat"],
                lon=update["lon"],
                unit_type=update.get("system", "unknown"),
                force=update.get("force", "blue"),
                system=update.get("system")
            )
        elif action == "remove":
            # Find and remove by name
            if "map_units" in st.session_state:
                to_remove = [uid for uid, u in st.session_state.map_units.items() 
                           if u["name"] == update["name"]]
                for uid in to_remove:
                    remove_map_unit(uid)
        elif action == "clear":
            clear_map_units(update.get("force"))


def create_map() -> 'folium.Map':
    """Create a folium map with all plotted units and threat rings."""
    if not MAPS_AVAILABLE:
        return None
    
    # Initialize map centered on Indo-Pacific
    m = folium.Map(
        location=MAP_DEFAULT_CENTER,
        zoom_start=MAP_DEFAULT_ZOOM,
        tiles="OpenStreetMap"
    )
    
    # Get map units
    map_units = st.session_state.get("map_units", {})
    
    # Color mapping
    force_colors = {
        "blue": "blue",
        "red": "red",
    }
    
    # Add units and threat rings
    for unit_id, unit in map_units.items():
        lat, lon = unit["lat"], unit["lon"]
        force = unit.get("force", "blue")
        system = unit.get("system")
        name = unit.get("name", "Unknown")
        
        # Marker color based on force
        marker_color = force_colors.get(force, "gray")
        
        # Create marker
        popup_text = f"<b>{name}</b><br>System: {system}<br>MGRS: {unit.get('mgrs', 'N/A')}"
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_text, max_width=200),
            icon=folium.Icon(color=marker_color, icon="info-sign")
        ).add_to(m)
        
        # Add threat ring if system has range data
        if system:
            threat_data = get_threat_range(system, force)
            if threat_data:
                range_meters = nm_to_meters(threat_data["range_nm"])
                ring_color = threat_data.get("color", marker_color)
                
                folium.Circle(
                    location=[lat, lon],
                    radius=range_meters,
                    color=ring_color,
                    fill=True,
                    fillOpacity=0.1,
                    popup=f"{name}: {threat_data['description']}"
                ).add_to(m)
    
    return m


def get_hptl_tss_context() -> str:
    """Generate HPTL/TSS/AGM context string for system prompt."""
    if "hptl_data" not in st.session_state or not st.session_state.hptl_data:
        return ""
    
    data = st.session_state.hptl_data
    lines = ["## CURRENT HPTL/TSS/AGM\n"]
    
    # HPTL
    if data.get("hptl"):
        lines.append("### HIGH-PAYOFF TARGET LIST (HPTL)")
        for entry in data["hptl"]:
            lines.append(f"- Priority {entry['priority']}: {entry['category']} - {', '.join(entry.get('systems', []))}")
        lines.append("")
    
    # TSS
    if data.get("tss"):
        lines.append("### TARGET SELECTION STANDARDS (TSS)")
        lines.append("When recommending fires, apply these standards:")
        for system, categories in data["tss"].items():
            lines.append(f"\n**{system}:**")
            for cat, standards in categories.items():
                lines.append(f"  - vs {cat}: TLE {standards.get('TLE', 'N/A')}, Size {standards.get('Size', 'N/A')}, "
                           f"Activity {standards.get('Activity', 'N/A')}, Time {standards.get('Time', 'N/A')}, "
                           f"Effects: {standards.get('Effects', 'N/A')}")
        lines.append("")
    
    return "\n".join(lines)


def get_tlws_context() -> str:
    """Generate Target List Worksheet context string."""
    if "tlws_data" not in st.session_state or not st.session_state.tlws_data:
        return ""
    
    targets = st.session_state.tlws_data
    if not targets:
        return ""
    
    lines = ["## TARGET LIST WORKSHEET\n"]
    lines.append("| Line | Target # | Description | Location | Remarks |")
    lines.append("|------|----------|-------------|----------|---------|")
    for t in targets[:20]:  # Limit to 20 for context
        lines.append(f"| {t.get('line', '')} | {t.get('target_num', '')} | {t.get('description', '')} | {t.get('location', '')} | {t.get('remarks', '')} |")
    
    if len(targets) > 20:
        lines.append(f"\n*...and {len(targets) - 20} more targets*")
    
    return "\n".join(lines)


def get_edl_context() -> str:
    """Generate Equipment Density List context string."""
    if "edl_data" not in st.session_state or not st.session_state.edl_data:
        return ""
    
    edl = st.session_state.edl_data
    lines = ["## EQUIPMENT DENSITY LIST (Fires-Relevant)\n"]
    
    # Extract fires-relevant equipment
    fires_items = ["M777", "M142", "HIMARS", "OPF-M", "Mortar", "AN/TPS", "MADIS", "AH-1", "F-35", "MQ-9"]
    
    for unit, items in edl.items():
        relevant = [(item, qty) for item, qty in items if any(fi.lower() in item.lower() for fi in fires_items)]
        if relevant:
            lines.append(f"**{unit}:**")
            for item, qty in relevant:
                lines.append(f"  - {item}: {qty}")
    
    return "\n".join(lines) if len(lines) > 1 else ""


def get_adversary_context() -> str:
    """Generate adversary systems context string."""
    if "adversary" not in st.session_state or not st.session_state.adversary:
        return ""
    
    adv = st.session_state.adversary
    if adv == "Custom" or adv not in ADVERSARY_PRESETS:
        return ""
    
    data = ADVERSARY_PRESETS[adv]
    lines = [f"## ADVERSARY REFERENCE ({adv})\n"]
    
    for category, systems in data["systems"].items():
        lines.append(f"**{category.replace('_', ' ')}:** {', '.join(systems)}")
    
    return "\n".join(lines)


def get_status_label(percentage: float) -> str:
    if percentage > 50:
        return "GREEN"
    elif percentage > 25:
        return "AMBER"
    else:
        return "RED"


def get_status_color(percentage: float) -> str:
    if percentage > 50:
        return "#22c55e"
    elif percentage > 25:
        return "#f59e0b"
    else:
        return "#ef4444"


def parse_ammo_updates(response: str) -> list[tuple[str, int, str]]:
    """Parse ammunition updates from assistant response."""
    updates = []
    pattern_expended = r'\[AMMO_UPDATE\]\s*ITEM:\s*([^\n]+)\s*EXPENDED:\s*(\d+)\s*\[/AMMO_UPDATE\]'
    pattern_remaining = r'\[AMMO_UPDATE\]\s*ITEM:\s*([^\n]+)\s*REMAINING:\s*(\d+)\s*\[/AMMO_UPDATE\]'
    
    for item, amount in re.findall(pattern_expended, response, re.IGNORECASE):
        ammo_type = resolve_ammo_type(item.strip())
        if ammo_type:
            updates.append((ammo_type, int(amount), 'expended'))
    
    for item, amount in re.findall(pattern_remaining, response, re.IGNORECASE):
        ammo_type = resolve_ammo_type(item.strip())
        if ammo_type:
            updates.append((ammo_type, int(amount), 'remaining'))
    
    return updates


def resolve_ammo_type(item: str) -> str | None:
    item_lower = item.lower()
    if item_lower in AMMO_ALIASES:
        return AMMO_ALIASES[item_lower]
    if item in st.session_state.ammo:
        return item
    for alias, ammo_type in AMMO_ALIASES.items():
        if alias in item_lower or item_lower in alias:
            return ammo_type
    return None


def apply_ammo_updates(updates: list[tuple[str, int, str]]) -> list[str]:
    messages = []
    for ammo_type, amount, update_type in updates:
        if ammo_type in st.session_state.ammo:
            old_val = st.session_state.ammo[ammo_type]["current"]
            if update_type == 'expended':
                new_val = max(0, old_val - amount)
            else:
                new_val = max(0, min(amount, st.session_state.ammo[ammo_type]["max"]))
            st.session_state.ammo[ammo_type]["current"] = new_val
            messages.append(f"Updated {ammo_type}: {old_val} → {new_val}")
    return messages


def load_loadout(loadout_name: str):
    if loadout_name in LOADOUT_PRESETS and loadout_name != "Custom":
        st.session_state.ammo = copy.deepcopy(LOADOUT_PRESETS[loadout_name]["ammo"])
        st.session_state.current_loadout = loadout_name


def reset_ammunition():
    loadout = st.session_state.get("current_loadout", DEFAULT_LOADOUT)
    if loadout in LOADOUT_PRESETS and loadout != "Custom":
        st.session_state.ammo = copy.deepcopy(LOADOUT_PRESETS[loadout]["ammo"])
    else:
        st.session_state.ammo = copy.deepcopy(LOADOUT_PRESETS[DEFAULT_LOADOUT]["ammo"])


# =============================================================================
# EXCEL PARSING FUNCTIONS
# =============================================================================

def parse_agm_tss_hptl_excel(file) -> dict:
    """Parse AGM/TSS/HPTL Excel file in EWS format."""
    try:
        xlsx = pd.ExcelFile(file)
        result = {"hptl": [], "tss": {}, "agm": [], "opord": "", "dtg": ""}
        
        for sheet_name in xlsx.sheet_names:
            df = pd.read_excel(xlsx, sheet_name=sheet_name, header=None)
            
            # Find OPORD and DTG
            for i, row in df.iterrows():
                for j, cell in enumerate(row):
                    if pd.notna(cell):
                        cell_str = str(cell)
                        if "OPORD" in cell_str.upper():
                            result["opord"] = cell_str
                        if "DTG" in cell_str.upper():
                            result["dtg"] = cell_str
            
            # Parse HPTL (rows with PRIORITY and DESCRIPTION)
            priority_row = None
            desc_row = None
            systems_rows = []
            
            for i, row in df.iterrows():
                first_cell = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
                if "PRIORITY" in first_cell.upper():
                    priority_row = i
                elif "DESCRIPTION" in first_cell.upper():
                    desc_row = i
                elif priority_row and desc_row and i > desc_row and i < desc_row + 4:
                    systems_rows.append(i)
                elif "ATTACK SYSTEMS" in first_cell.upper():
                    break
            
            if priority_row is not None and desc_row is not None:
                # Extract priorities and descriptions
                for col in range(2, min(17, len(df.columns)), 3):
                    priority = df.iloc[priority_row, col] if pd.notna(df.iloc[priority_row, col]) else None
                    category = df.iloc[desc_row, col] if pd.notna(df.iloc[desc_row, col]) else None
                    
                    if priority and category:
                        systems = []
                        for sys_row in systems_rows:
                            if col + 1 < len(df.columns):
                                sys = df.iloc[sys_row, col + 1]
                                if pd.notna(sys) and str(sys).strip():
                                    systems.append(str(sys).strip().replace("\\n", ""))
                        
                        result["hptl"].append({
                            "priority": int(priority) if isinstance(priority, (int, float)) else priority,
                            "category": str(category).strip(),
                            "systems": systems
                        })
            
            # Parse TSS (Attack Systems section)
            attack_systems = ["FA", "FW CAS", "RW CAS", "HIMARS", "OPF-M"]
            current_system = None
            
            for i, row in df.iterrows():
                first_cell = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
                second_cell = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
                
                # Check if this row starts an attack system section
                combined = f"{first_cell} {second_cell}".strip()
                for sys in attack_systems:
                    if sys in combined.upper() or sys.replace(" ", "") in combined.upper().replace(" ", ""):
                        current_system = sys.replace(" ", "_")
                        if current_system not in result["tss"]:
                            result["tss"][current_system] = {}
                        
                        # Parse TSS data for each HPTL category
                        for h_idx, hptl_entry in enumerate(result["hptl"]):
                            col_base = 2 + (h_idx * 3)
                            if col_base + 2 < len(df.columns):
                                tss_entry = {
                                    "TLE": str(df.iloc[i, col_base]) if pd.notna(df.iloc[i, col_base]) else "",
                                    "Effects": str(df.iloc[i, col_base + 1]) if pd.notna(df.iloc[i, col_base + 1]) else "",
                                }
                                # Get size, activity, time from subsequent rows
                                if i + 1 < len(df):
                                    tss_entry["Size"] = str(df.iloc[i + 1, col_base]) if pd.notna(df.iloc[i + 1, col_base]) else ""
                                if i + 2 < len(df):
                                    tss_entry["Activity"] = str(df.iloc[i + 2, col_base]) if pd.notna(df.iloc[i + 2, col_base]) else ""
                                if i + 3 < len(df):
                                    tss_entry["Time"] = str(df.iloc[i + 3, col_base]) if pd.notna(df.iloc[i + 3, col_base]) else ""
                                
                                result["tss"][current_system][hptl_entry["category"]] = tss_entry
                        break
        
        return result
    except Exception as e:
        return {"error": str(e)}


def parse_tlws_excel(file) -> list:
    """Parse Target List Worksheet Excel file."""
    try:
        xlsx = pd.ExcelFile(file)
        targets = []
        
        for sheet_name in xlsx.sheet_names:
            df = pd.read_excel(xlsx, sheet_name=sheet_name, header=None)
            
            # Find the header row (contains "Target" and "DESCRIPTION")
            header_row = None
            for i, row in df.iterrows():
                row_str = " ".join([str(c) for c in row if pd.notna(c)]).upper()
                if "TARGET" in row_str and "DESCRIPTION" in row_str:
                    header_row = i
                    break
            
            if header_row is None:
                continue
            
            # Parse data rows
            for i in range(header_row + 2, len(df)):  # Skip header and column letters row
                row = df.iloc[i]
                
                # Check if row has data
                if pd.isna(row.iloc[0]) and pd.isna(row.iloc[1]):
                    continue
                
                target = {
                    "line": row.iloc[0] if pd.notna(row.iloc[0]) else "",
                    "target_num": row.iloc[1] if pd.notna(row.iloc[1]) else "",
                    "description": row.iloc[2] if pd.notna(row.iloc[2]) else "",
                    "location": row.iloc[3] if pd.notna(row.iloc[3]) else "",
                    "altitude": row.iloc[4] if len(row) > 4 and pd.notna(row.iloc[4]) else "",
                    "attitude": row.iloc[5] if len(row) > 5 and pd.notna(row.iloc[5]) else "",
                    "size_length": row.iloc[6] if len(row) > 6 and pd.notna(row.iloc[6]) else "",
                    "size_width": row.iloc[7] if len(row) > 7 and pd.notna(row.iloc[7]) else "",
                    "source_accuracy": row.iloc[8] if len(row) > 8 and pd.notna(row.iloc[8]) else "",
                    "remarks": row.iloc[9] if len(row) > 9 and pd.notna(row.iloc[9]) else "",
                }
                
                # Only add if there's meaningful data
                if target["target_num"] or target["description"]:
                    targets.append(target)
        
        return targets
    except Exception as e:
        return [{"error": str(e)}]


def parse_edl_excel(file) -> dict:
    """Parse Equipment Density List Excel file."""
    try:
        xlsx = pd.ExcelFile(file)
        edl = {}
        
        for sheet_name in xlsx.sheet_names:
            df = pd.read_excel(xlsx, sheet_name=sheet_name, header=None)
            
            # Find unit columns (header row with "Unit" / "End Item" / "Quantity")
            header_row = None
            for i, row in df.iterrows():
                row_str = " ".join([str(c) for c in row if pd.notna(c)]).upper()
                if "UNIT" in row_str and "END ITEM" in row_str:
                    header_row = i
                    break
            
            if header_row is None:
                continue
            
            # Parse each unit column group (columns are in groups of 3: Unit, End Item, Quantity)
            num_groups = len(df.columns) // 4  # Each group is 3 cols + 1 spacer
            
            for g in range(num_groups):
                col_base = g * 4
                if col_base + 2 >= len(df.columns):
                    break
                
                current_unit = None
                for i in range(header_row + 1, len(df)):
                    row = df.iloc[i]
                    
                    unit_cell = row.iloc[col_base] if pd.notna(row.iloc[col_base]) else None
                    item_cell = row.iloc[col_base + 1] if pd.notna(row.iloc[col_base + 1]) else None
                    qty_cell = row.iloc[col_base + 2] if pd.notna(row.iloc[col_base + 2]) else None
                    
                    if unit_cell:
                        current_unit = str(unit_cell).strip()
                        if current_unit not in edl:
                            edl[current_unit] = []
                    
                    if current_unit and item_cell:
                        edl[current_unit].append((str(item_cell).strip(), str(qty_cell) if qty_cell else ""))
        
        return edl
    except Exception as e:
        return {"error": str(e)}


def create_tlws_excel(targets: list) -> BytesIO:
    """Create Target List Worksheet Excel file."""
    output = BytesIO()
    
    # Create DataFrame
    data = []
    for t in targets:
        data.append({
            "Line #": t.get("line", ""),
            "Target #": t.get("target_num", ""),
            "Description": t.get("description", ""),
            "Location": t.get("location", ""),
            "Altitude": t.get("altitude", ""),
            "Attitude": t.get("attitude", ""),
            "Size (Length)": t.get("size_length", ""),
            "Size (Width)": t.get("size_width", ""),
            "Source/Accuracy": t.get("source_accuracy", ""),
            "Remarks": t.get("remarks", ""),
        })
    
    df = pd.DataFrame(data)
    df.to_excel(output, index=False, sheet_name="TLWS")
    output.seek(0)
    return output


def create_agm_excel(hptl_data: dict) -> BytesIO:
    """Create AGM/TSS/HPTL Excel file in EWS format."""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Create a simplified version of the AGM matrix
        rows = []
        
        # Header
        rows.append(["AGM/TSS/HPTL", "", "", "", "", "", "", "", "", "DTG:", "", "", "", "", ""])
        rows.append([""])
        rows.append(["HIGH-PAYOFF TARGETS"])
        
        # HPTL priorities
        priority_row = ["PRIORITY", ""]
        desc_row = ["DESCRIPTION", ""]
        
        for entry in hptl_data.get("hptl", []):
            priority_row.extend([entry["priority"], "", ""])
            desc_row.extend([entry["category"], "", ""])
        
        rows.append(priority_row)
        rows.append(desc_row)
        
        # Systems rows
        for i in range(3):
            sys_row = ["", ""]
            for entry in hptl_data.get("hptl", []):
                systems = entry.get("systems", [])
                sys_row.extend(["", systems[i] if i < len(systems) else "", ""])
            rows.append(sys_row)
        
        df = pd.DataFrame(rows)
        df.to_excel(writer, index=False, header=False, sheet_name="AGM_TSS_HPTL")
    
    output.seek(0)
    return output


# =============================================================================
# OPORD/ANNEX PARSING
# =============================================================================

OPORD_PARSE_PROMPT = """You are parsing a military Operations Order (OPORD), Annex C (Fires), Appendix 17 (Fire Support), or similar fire support planning document.

Extract ALL fire support relevant information and return it as a JSON object. Be thorough.

{
    "document_info": {
        "title": "Document title/name",
        "dtg": "Date-time group if present",
        "classification": "UNCLASSIFIED/etc",
        "unit": "Issuing unit"
    },
    "commanders_intent_fires": "Full text of commander's intent for fires if present",
    "concept_of_fires": "Summary of concept of fires by phase",
    "efsts": [
        {
            "number": "EFST 1",
            "phase": "Phase IA",
            "task": "Disrupt Tornado-S platoon...",
            "purpose": "Allow RCT 6 freedom of movement...",
            "target_number": "AG1015",
            "target_location": "32S ME 5184 1489",
            "trigger": "Upon PID of 2 or more Tornado-S sections",
            "observer": "UAS/FW/Recon",
            "delivery_asset": "FW/HIMARS",
            "attack_guidance": "4x GBU-12 / 4x M31",
            "effects": "3 of 3 Tornado-S neutralized",
            "restrictions": "No cratering munitions on MSRs"
        }
    ],
    "fscms": {
        "fscl": [{"name": "FSCL 1", "grid_points": ["grid1", "grid2"], "effective": "D-Day"}],
        "bcl": [{"name": "BCL 1 / PL Green", "grid_points": ["grid1", "grid2"], "effective": "D-Day to D+5"}],
        "nfas": [{"name": "NFA 1", "grid": "grid reference", "description": "details"}],
        "rfas": [{"name": "RFA 1", "grid": "grid reference", "restrictions": "restrictions"}],
        "acas": [{"name": "ACA CHESTY", "min_alt": "8000 MSL", "max_alt": "30000 MSL", "location": "Between BCL 1 to FSCL 1", "effective": "D-Day to D+4"}],
        "other": [{"type": "type", "name": "name", "details": "details"}]
    },
    "air_support": {
        "general": "Description of air support concept",
        "allocation_by_phase": [
            {"phase": "Ph IB", "unit": "MAG 14", "assets": "4 x section F-35B (8 sorties)"}
        ],
        "scl": [
            {"platform": "F-35B", "loadout": "2x AIM-120, 2x GBU-12"},
            {"platform": "AH-1Z", "loadout": "19x HE 2.75in, 4x AGM-114"}
        ]
    },
    "artillery_support": {
        "general": "Description of artillery support",
        "organization": [
            {"unit": "Btry E, 2/10", "type": "M777A2", "quantity": 6, "role": "DS to RCT 6"}
        ],
        "radar_assets": [{"type": "AN/TPS-80", "quantity": 2}]
    },
    "ammunition_allocations": {
        "himars": [
            {"nomenclature": "M31 Unitary", "type": "GMLRS", "quantity": 50},
            {"nomenclature": "M57 ATACMS", "type": "ATACMS", "quantity": 4}
        ],
        "artillery_155mm": [
            {"nomenclature": "HE M795", "type": "155mm_HE", "quantity": 272},
            {"nomenclature": "Excalibur M982A1", "type": "Excalibur", "quantity": 20},
            {"nomenclature": "Illum M485", "type": "155mm_Illum", "quantity": 20}
        ],
        "mortars_81mm": [
            {"nomenclature": "HE M374A2", "type": "81mm_HE", "quantity": 480}
        ]
    },
    "coordinating_instructions": [
        "FASCAM/DPICM release authority at USAFRICOM",
        "Target nominations due by 0800 daily"
    ],
    "target_blocks": [
        {"unit": "SPMAGTF-A CE", "block": "AG 1000-1999"}
    ],
    "key_restrictions": [
        "No cratering munitions on MSRs"
    ],
    "summary": "2-3 sentence summary of fire support plan"
}

CRITICAL: Extract ALL EFSTs with full details including target numbers, locations, triggers, delivery assets.
CRITICAL: Extract ALL ammunition allocations with exact quantities.
CRITICAL: Extract ALL FSCMs including FSCL, BCL, ACAs with grid coordinates.

Return ONLY valid JSON. Use null or empty arrays [] for sections not found.
"""


def parse_opord_annex(file) -> dict:
    """Parse OPORD/Annex document (PDF, DOCX, TXT) using Claude."""
    try:
        # Extract text based on file type
        filename = file.name.lower()
        
        if filename.endswith('.pdf'):
            try:
                import pypdf
                pdf_reader = pypdf.PdfReader(file)
                file_content = "\n".join(page.extract_text() for page in pdf_reader.pages)
            except ImportError:
                return {"error": "PDF support requires pypdf library"}
        
        elif filename.endswith('.docx'):
            try:
                import docx
                doc = docx.Document(file)
                file_content = "\n".join(para.text for para in doc.paragraphs)
            except ImportError:
                return {"error": "DOCX support requires python-docx library"}
        
        elif filename.endswith('.doc'):
            return {"error": ".doc format not supported. Please convert to .docx or .pdf"}
        
        else:  # .txt, .md, or other text
            file_content = file.read().decode('utf-8')
        
        if not file_content or len(file_content.strip()) < 100:
            return {"error": "Document appears to be empty or too short"}
        
        # Use Claude to parse the document
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=OPORD_PARSE_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Parse this fire support document:\n\n{file_content[:15000]}"  # Limit to ~15k chars
            }]
        )
        
        # Track tokens
        if hasattr(response, 'usage'):
            st.session_state.total_tokens += response.usage.input_tokens + response.usage.output_tokens
        
        # Extract and parse JSON
        response_text = response.content[0].text.strip()
        
        # Handle markdown code blocks
        if response_text.startswith("```"):
            response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        parsed_data = json.loads(response_text)
        return parsed_data
    
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse AI response as JSON: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to parse document: {str(e)}"}


def get_opord_context() -> str:
    """Generate OPORD/Annex context string for system prompt."""
    if "opord_data" not in st.session_state or not st.session_state.opord_data:
        return ""
    
    data = st.session_state.opord_data
    lines = ["## OPERATIONS ORDER / FIRE SUPPORT ANNEX\n"]
    
    # Document info
    doc_info = data.get("document_info", {})
    if doc_info:
        if doc_info.get("title"):
            lines.append(f"**Document:** {doc_info['title']}")
        if doc_info.get("dtg"):
            lines.append(f"**DTG:** {doc_info['dtg']}")
        if doc_info.get("unit"):
            lines.append(f"**Unit:** {doc_info['unit']}")
        lines.append("")
    
    # Commander's Intent
    if data.get("commanders_intent_fires"):
        lines.append("### COMMANDER'S INTENT FOR FIRES")
        lines.append(data["commanders_intent_fires"])
        lines.append("")
    
    # Concept of Fires
    if data.get("concept_of_fires"):
        lines.append("### CONCEPT OF FIRES")
        lines.append(data["concept_of_fires"])
        lines.append("")
    
    # EFSTs - Essential Fire Support Tasks
    if data.get("efsts"):
        lines.append("### ESSENTIAL FIRE SUPPORT TASKS (EFSTs)")
        for efst in data["efsts"]:
            lines.append(f"\n**{efst.get('number', 'EFST')} - {efst.get('phase', '')}**")
            lines.append(f"- **Task:** {efst.get('task', '')}")
            lines.append(f"- **Purpose:** {efst.get('purpose', '')}")
            lines.append(f"- **Target:** {efst.get('target_number', '')} @ {efst.get('target_location', '')}")
            lines.append(f"- **Trigger:** {efst.get('trigger', '')}")
            lines.append(f"- **Observer:** {efst.get('observer', '')}")
            lines.append(f"- **Delivery:** {efst.get('delivery_asset', '')}")
            lines.append(f"- **Attack Guidance:** {efst.get('attack_guidance', '')}")
            lines.append(f"- **Effects:** {efst.get('effects', '')}")
        lines.append("")
    
    # FSCMs
    fscms = data.get("fscms", {})
    if any(fscms.get(k) for k in ["fscl", "bcl", "nfas", "rfas", "acas", "other"]):
        lines.append("### FIRE SUPPORT COORDINATION MEASURES")
        
        if fscms.get("fscl"):
            lines.append("\n**Fire Support Coordination Lines (FSCLs):**")
            for fscl in fscms["fscl"]:
                grids = ", ".join(fscl.get("grid_points", [])) if fscl.get("grid_points") else fscl.get("grid", "")
                lines.append(f"- {fscl.get('name', 'FSCL')}: {grids} (Effective: {fscl.get('effective', 'TBD')})")
        
        if fscms.get("bcl"):
            lines.append("\n**Boundary Coordination Lines (BCLs):**")
            for bcl in fscms["bcl"]:
                grids = ", ".join(bcl.get("grid_points", [])) if bcl.get("grid_points") else bcl.get("grid", "")
                lines.append(f"- {bcl.get('name', 'BCL')}: {grids} (Effective: {bcl.get('effective', 'TBD')})")
        
        if fscms.get("acas"):
            lines.append("\n**Airspace Coordination Areas (ACAs):**")
            for aca in fscms["acas"]:
                lines.append(f"- {aca.get('name', 'ACA')}: {aca.get('min_alt', '')} - {aca.get('max_alt', '')}, {aca.get('location', '')} (Effective: {aca.get('effective', 'TBD')})")
        
        if fscms.get("nfas"):
            lines.append("\n**No-Fire Areas (NFAs):**")
            for nfa in fscms["nfas"]:
                lines.append(f"- {nfa.get('name', 'NFA')}: {nfa.get('grid', '')} - {nfa.get('description', '')}")
        
        if fscms.get("rfas"):
            lines.append("\n**Restrictive Fire Areas (RFAs):**")
            for rfa in fscms["rfas"]:
                lines.append(f"- {rfa.get('name', 'RFA')}: {rfa.get('grid', '')} - {rfa.get('restrictions', '')}")
        lines.append("")
    
    # Air Support
    air = data.get("air_support", {})
    if air:
        lines.append("### AIR SUPPORT")
        if air.get("general"):
            lines.append(air["general"])
        if air.get("allocation_by_phase"):
            lines.append("\n**Allocation by Phase:**")
            for alloc in air["allocation_by_phase"]:
                lines.append(f"- {alloc.get('phase', '')}: {alloc.get('unit', '')} - {alloc.get('assets', '')}")
        if air.get("scl"):
            lines.append("\n**Standard Conventional Loadouts:**")
            for scl in air["scl"]:
                lines.append(f"- {scl.get('platform', '')}: {scl.get('loadout', '')}")
        lines.append("")
    
    # Artillery Support
    arty = data.get("artillery_support", {})
    if arty:
        lines.append("### ARTILLERY SUPPORT")
        if arty.get("general"):
            lines.append(arty["general"])
        if arty.get("organization"):
            lines.append("\n**Organization for Combat:**")
            for org in arty["organization"]:
                lines.append(f"- {org.get('unit', '')}: {org.get('quantity', '')}x {org.get('type', '')} ({org.get('role', '')})")
        if arty.get("radar_assets"):
            lines.append("\n**Radar Assets:**")
            for radar in arty["radar_assets"]:
                lines.append(f"- {radar.get('quantity', '')}x {radar.get('type', '')}")
        lines.append("")
    
    # Coordinating instructions
    if data.get("coordinating_instructions"):
        lines.append("### COORDINATING INSTRUCTIONS")
        for instr in data["coordinating_instructions"]:
            lines.append(f"- {instr}")
        lines.append("")
    
    # Key Restrictions
    if data.get("key_restrictions"):
        lines.append("### KEY RESTRICTIONS")
        for r in data["key_restrictions"]:
            lines.append(f"- {r}")
        lines.append("")
    
    # Target Blocks
    if data.get("target_blocks"):
        lines.append("### TARGET BLOCKS")
        for tb in data["target_blocks"]:
            lines.append(f"- {tb.get('unit', '')}: {tb.get('block', '')}")
        lines.append("")
    
    # Summary
    if data.get("summary"):
        lines.append(f"\n**Summary:** {data['summary']}")
    
    return "\n".join(lines)


def apply_opord_ammo_to_loadout(data: dict):
    """Apply ammunition allocations from OPORD to session state ammo."""
    ammo_alloc = data.get("ammunition_allocations", {})
    if not ammo_alloc:
        return
    
    # Map from OPORD types to our internal types
    type_mapping = {
        "GMLRS": "GMLRS",
        "ATACMS": "ATACMS",
        "155mm_HE": "155mm_HE",
        "Excalibur": "Excalibur",
        "155mm_Illum": "155mm_Illum",
        "155mm_Smoke": "155mm_Smoke",
        "155mm_DPICM": "155mm_DPICM",
        "155mm_RAP": "155mm_RAP",
        "81mm_HE": "81mm_HE",
        "81mm_WP": "81mm_WP",
        "81mm_Illum": "81mm_Illum",
    }
    
    new_ammo = {}
    
    # Process HIMARS
    for item in ammo_alloc.get("himars", []):
        ammo_type = type_mapping.get(item.get("type"), item.get("type"))
        qty = item.get("quantity", 0)
        if ammo_type and qty:
            new_ammo[ammo_type] = {"current": qty, "max": qty, "unit": "rounds"}
    
    # Process Artillery
    for item in ammo_alloc.get("artillery_155mm", []):
        ammo_type = type_mapping.get(item.get("type"), item.get("type"))
        qty = item.get("quantity", 0)
        if ammo_type and qty:
            new_ammo[ammo_type] = {"current": qty, "max": qty, "unit": "rounds"}
    
    # Process Mortars
    for item in ammo_alloc.get("mortars_81mm", []):
        ammo_type = type_mapping.get(item.get("type"), item.get("type"))
        qty = item.get("quantity", 0)
        if ammo_type and qty:
            new_ammo[ammo_type] = {"current": qty, "max": qty, "unit": "rounds"}
    
    # Update session state if we found ammo
    if new_ammo:
        st.session_state.ammo = new_ammo
        st.session_state.current_loadout = "Custom (from OPORD)"
    ammo = data.get("ammunition_guidance", {})
    if ammo and any(ammo.get(k) for k in ["csr", "rsr", "restrictions"]):
        lines.append("### AMMUNITION GUIDANCE")
        if ammo.get("csr"):
            lines.append(f"- **CSR:** {ammo['csr']}")
        if ammo.get("rsr"):
            lines.append(f"- **RSR:** {ammo['rsr']}")
        if ammo.get("restrictions"):
            for r in ammo["restrictions"]:
                lines.append(f"- {r}")
        lines.append("")
    
    # Available assets
    if data.get("available_assets"):
        lines.append("### AVAILABLE FIRE SUPPORT ASSETS")
        for asset in data["available_assets"]:
            lines.append(f"- {asset.get('unit', '')}: {asset.get('quantity', '')} {asset.get('type', '')} @ {asset.get('location', asset.get('availability', ''))}")
        lines.append("")
    
    # Summary
    if data.get("summary"):
        lines.append(f"\n**Summary:** {data['summary']}")
    
    return "\n".join(lines)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_loadout" not in st.session_state:
        st.session_state.current_loadout = DEFAULT_LOADOUT
    if "ammo" not in st.session_state:
        reset_ammunition()
    if "total_tokens" not in st.session_state:
        st.session_state.total_tokens = 0
    if "hptl_data" not in st.session_state:
        st.session_state.hptl_data = None
    if "tlws_data" not in st.session_state:
        st.session_state.tlws_data = []
    if "edl_data" not in st.session_state:
        st.session_state.edl_data = None
    if "opord_data" not in st.session_state:
        st.session_state.opord_data = None
    if "adversary" not in st.session_state:
        st.session_state.adversary = "Olvana (Chinese-type)"
    if "map_units" not in st.session_state:
        st.session_state.map_units = {}
    if "show_map" not in st.session_state:
        st.session_state.show_map = False


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_sidebar():
    """Render the sidebar with all controls."""
    with st.sidebar:
        # =========================
        # DOCUMENT UPLOAD SECTION
        # =========================
        st.markdown("## 📄 Document Upload")
        
        upload_type = st.selectbox(
            "Document Type",
            ["AGM/TSS/HPTL Matrix", "Target List Worksheet", "Equipment Density List", "OPORD/Annex (Fires)"],
            key="upload_type"
        )
        
        # Set allowed file types based on document type
        if upload_type == "OPORD/Annex (Fires)":
            allowed_types = ["pdf", "docx", "doc", "txt", "md"]
        else:
            allowed_types = ["xlsx", "xls"]
        
        uploaded_file = st.file_uploader(
            f"Upload {upload_type}",
            type=allowed_types,
            key="doc_uploader"
        )
        
        if uploaded_file:
            with st.spinner(f"Parsing {upload_type}..."):
                if upload_type == "AGM/TSS/HPTL Matrix":
                    result = parse_agm_tss_hptl_excel(uploaded_file)
                    if "error" not in result:
                        st.session_state.hptl_data = result
                        st.success(f"✅ Loaded {len(result.get('hptl', []))} HPTL priorities")
                    else:
                        st.error(f"Error: {result['error']}")
                
                elif upload_type == "Target List Worksheet":
                    result = parse_tlws_excel(uploaded_file)
                    if result and "error" not in result[0] if result else True:
                        st.session_state.tlws_data = result
                        st.success(f"✅ Loaded {len(result)} targets")
                    else:
                        st.error(f"Error parsing TLWS")
                
                elif upload_type == "Equipment Density List":
                    result = parse_edl_excel(uploaded_file)
                    if "error" not in result:
                        st.session_state.edl_data = result
                        st.success(f"✅ Loaded {len(result)} units")
                    else:
                        st.error(f"Error: {result['error']}")
                
                elif upload_type == "OPORD/Annex (Fires)":
                    result = parse_opord_annex(uploaded_file)
                    if "error" not in result:
                        st.session_state.opord_data = result
                        efst_count = len(result.get("efsts", []))
                        st.success(f"✅ Parsed fire support annex ({efst_count} EFSTs)")
                        
                        # Check if there are ammunition allocations
                        ammo_alloc = result.get("ammunition_allocations", {})
                        if any(ammo_alloc.get(k) for k in ["himars", "artillery_155mm", "mortars_81mm"]):
                            st.info("📦 Ammunition allocations found in OPORD")
                    else:
                        st.error(f"Error: {result['error']}")
        
        # Show loaded documents status
        with st.expander("📋 Loaded Documents", expanded=False):
            if st.session_state.hptl_data:
                st.markdown(f"**AGM/TSS/HPTL:** {len(st.session_state.hptl_data.get('hptl', []))} priorities")
                if st.button("Clear HPTL", key="clear_hptl"):
                    st.session_state.hptl_data = None
                    st.rerun()
            
            if st.session_state.tlws_data:
                st.markdown(f"**TLWS:** {len(st.session_state.tlws_data)} targets")
                if st.button("Clear TLWS", key="clear_tlws"):
                    st.session_state.tlws_data = []
                    st.rerun()
            
            if st.session_state.edl_data:
                st.markdown(f"**EDL:** {len(st.session_state.edl_data)} units")
                if st.button("Clear EDL", key="clear_edl"):
                    st.session_state.edl_data = None
                    st.rerun()
            
            if st.session_state.get("opord_data"):
                opord = st.session_state.opord_data
                efst_count = len(opord.get("efsts", []))
                st.markdown(f"**OPORD/Annex:** {efst_count} EFSTs")
                
                # Button to apply ammo from OPORD
                ammo_alloc = opord.get("ammunition_allocations", {})
                if any(ammo_alloc.get(k) for k in ["himars", "artillery_155mm", "mortars_81mm"]):
                    if st.button("📦 Apply OPORD Ammo", key="apply_opord_ammo"):
                        apply_opord_ammo_to_loadout(opord)
                        st.rerun()
                
                if st.button("Clear OPORD", key="clear_opord"):
                    st.session_state.opord_data = None
                    st.rerun()
        
        st.markdown("---")
        
        # =========================
        # ADVERSARY SELECTION
        # =========================
        st.markdown("## 🎯 Adversary")
        adversary = st.selectbox(
            "Select Threat",
            list(ADVERSARY_PRESETS.keys()),
            index=list(ADVERSARY_PRESETS.keys()).index(st.session_state.adversary),
            key="adversary_select"
        )
        st.session_state.adversary = adversary
        if adversary != "Custom":
            st.caption(ADVERSARY_PRESETS[adversary]["description"])
        
        st.markdown("---")
        
        # =========================
        # MISSION LOADOUT
        # =========================
        st.markdown("## ⚙️ Mission Loadout")
        
        loadout_options = list(LOADOUT_PRESETS.keys())
        current_idx = loadout_options.index(st.session_state.current_loadout) if st.session_state.current_loadout in loadout_options else 0
        
        selected_loadout = st.selectbox(
            "Select Loadout",
            options=loadout_options,
            index=current_idx,
            key="loadout_selector"
        )
        
        if selected_loadout != "Custom":
            st.caption(LOADOUT_PRESETS[selected_loadout]["description"])
        
        if selected_loadout != st.session_state.current_loadout and selected_loadout != "Custom":
            if st.button("📦 Apply Loadout", use_container_width=True):
                load_loadout(selected_loadout)
                st.rerun()
        
        st.markdown("---")
        
        # =========================
        # AMMUNITION STATUS
        # =========================
        st.markdown("## 📊 Ammunition Status")
        
        for category, ammo_types in AMMO_CATEGORIES.items():
            present_types = [at for at in ammo_types if at in st.session_state.ammo]
            if not present_types:
                continue
            
            st.markdown(f"**{category}**")
            for ammo_type in present_types:
                data = st.session_state.ammo[ammo_type]
                pct = (data["current"] / data["max"]) * 100 if data["max"] > 0 else 0
                color = get_status_color(pct)
                display_name = AMMO_DISPLAY_NAMES.get(ammo_type, ammo_type.replace("_", " "))
                
                st.markdown(
                    f'<div style="margin-bottom: 4px;">'
                    f'<span style="font-size: 0.85em;">{display_name}</span>'
                    f'<span style="float: right; font-size: 0.85em; color: {color};">'
                    f'{data["current"]}/{data["max"]}</span></div>',
                    unsafe_allow_html=True
                )
                st.progress(pct / 100)
            st.markdown("")
        
        st.markdown("---")
        
        # Control buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Reset", use_container_width=True):
                reset_ammunition()
                st.rerun()
        with col2:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.messages = []
                st.session_state.total_tokens = 0
                st.rerun()
        
        # Token usage
        if st.session_state.total_tokens > 0:
            st.markdown("---")
            st.markdown(f"**Tokens:** {st.session_state.total_tokens:,}")
            est_cost = (st.session_state.total_tokens / 1000) * 0.003
            st.markdown(f"**Est. Cost:** ${est_cost:.4f}")
        
        # Manual adjustment
        with st.expander("🔧 Manual Adjustment"):
            ammo_select = st.selectbox(
                "Ammunition",
                options=list(st.session_state.ammo.keys()),
                format_func=lambda x: AMMO_DISPLAY_NAMES.get(x, x.replace("_", " "))
            )
            if ammo_select:
                current = st.session_state.ammo[ammo_select]["current"]
                max_val = st.session_state.ammo[ammo_select]["max"]
                new_val = st.number_input("Value", min_value=0, max_value=max_val, value=current, key="manual_ammo")
                if st.button("Update", key="update_ammo"):
                    st.session_state.ammo[ammo_select]["current"] = new_val
                    st.rerun()
        
        # Disclaimer
        st.markdown("---")
        st.markdown(
            '<div style="font-size: 0.75em; color: #888; text-align: center;">'
            '⚠️ UNCLASSIFIED TRAINING TOOL<br>'
            'Do not input CUI/classified<br><br>'
            'EWS AY26 | CG-13'
            '</div>',
            unsafe_allow_html=True
        )


def render_data_tabs():
    """Render tabs for HPTL/TSS, TLWS, and EDL data."""
    if not any([st.session_state.hptl_data, st.session_state.tlws_data, st.session_state.edl_data]):
        return
    
    tabs = []
    tab_names = []
    
    if st.session_state.hptl_data:
        tab_names.append("📊 HPTL/TSS")
    if st.session_state.tlws_data:
        tab_names.append("🎯 Target List")
    if st.session_state.edl_data:
        tab_names.append("📦 EDL")
    if st.session_state.get("opord_data"):
        tab_names.append("📋 OPORD/Annex")
    
    if not tab_names:
        return
    
    tabs = st.tabs(tab_names)
    tab_idx = 0
    
    # HPTL/TSS Tab
    if st.session_state.hptl_data:
        with tabs[tab_idx]:
            data = st.session_state.hptl_data
            
            st.markdown("### High-Payoff Target List")
            if data.get("hptl"):
                hptl_df = pd.DataFrame([
                    {
                        "Priority": h["priority"],
                        "Category": h["category"],
                        "Systems": ", ".join(h.get("systems", []))
                    }
                    for h in data["hptl"]
                ])
                st.dataframe(hptl_df, use_container_width=True, hide_index=True)
            
            if data.get("tss"):
                st.markdown("### Target Selection Standards")
                for system, categories in data["tss"].items():
                    with st.expander(f"**{system.replace('_', ' ')}**"):
                        for cat, standards in categories.items():
                            st.markdown(f"**vs {cat}:** TLE: {standards.get('TLE', '-')}, "
                                       f"Size: {standards.get('Size', '-')}, "
                                       f"Activity: {standards.get('Activity', '-')}, "
                                       f"Time: {standards.get('Time', '-')}, "
                                       f"Effects: {standards.get('Effects', '-')}")
            
            # Export button
            if st.button("📥 Export AGM/TSS/HPTL", key="export_agm"):
                excel_file = create_agm_excel(data)
                st.download_button(
                    "Download Excel",
                    excel_file,
                    "AGM_TSS_HPTL.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        tab_idx += 1
    
    # TLWS Tab
    if st.session_state.tlws_data:
        with tabs[tab_idx]:
            st.markdown("### Target List Worksheet")
            
            targets = st.session_state.tlws_data
            if targets:
                tlws_df = pd.DataFrame([
                    {
                        "Line": t.get("line", ""),
                        "Target #": t.get("target_num", ""),
                        "Description": t.get("description", ""),
                        "Location": t.get("location", ""),
                        "Remarks": t.get("remarks", "")
                    }
                    for t in targets
                ])
                st.dataframe(tlws_df, use_container_width=True, hide_index=True)
            
            # Add new target
            with st.expander("➕ Add Target"):
                col1, col2 = st.columns(2)
                with col1:
                    new_tgt_num = st.text_input("Target #", key="new_tgt_num")
                    new_tgt_desc = st.text_input("Description", key="new_tgt_desc")
                with col2:
                    new_tgt_loc = st.text_input("Location (MGRS)", key="new_tgt_loc")
                    new_tgt_rmk = st.text_input("Remarks", key="new_tgt_rmk")
                
                if st.button("Add Target", key="add_target"):
                    new_target = {
                        "line": len(targets) + 1,
                        "target_num": new_tgt_num,
                        "description": new_tgt_desc,
                        "location": new_tgt_loc,
                        "remarks": new_tgt_rmk
                    }
                    st.session_state.tlws_data.append(new_target)
                    st.rerun()
            
            # Export button
            if st.button("📥 Export TLWS", key="export_tlws"):
                excel_file = create_tlws_excel(targets)
                st.download_button(
                    "Download Excel",
                    excel_file,
                    "TLWS.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        tab_idx += 1
    
    # EDL Tab
    if st.session_state.edl_data:
        with tabs[tab_idx]:
            st.markdown("### Equipment Density List (Fires-Relevant)")
            
            edl = st.session_state.edl_data
            fires_keywords = ["M777", "M142", "HIMARS", "OPF-M", "Mortar", "81mm", "60mm", 
                           "AN/TPS", "MADIS", "AH-1", "F-35", "MQ-9", "Javelin", "TOW"]
            
            for unit, items in edl.items():
                relevant = [(item, qty) for item, qty in items 
                           if any(kw.lower() in item.lower() for kw in fires_keywords)]
                if relevant:
                    with st.expander(f"**{unit}**"):
                        for item, qty in relevant:
                            st.markdown(f"- {item}: **{qty}**")
        tab_idx += 1
    
    # OPORD/Annex Tab
    if st.session_state.get("opord_data"):
        with tabs[tab_idx]:
            data = st.session_state.opord_data
            
            st.markdown("### OPORD / Fire Support Annex")
            
            # Document info
            doc_info = data.get("document_info", {})
            if doc_info:
                cols = st.columns(3)
                with cols[0]:
                    if doc_info.get("title"):
                        st.markdown(f"**Document:** {doc_info['title']}")
                with cols[1]:
                    if doc_info.get("dtg"):
                        st.markdown(f"**DTG:** {doc_info['dtg']}")
                with cols[2]:
                    if doc_info.get("unit"):
                        st.markdown(f"**Unit:** {doc_info['unit']}")
            
            # EFSTs - Essential Fire Support Tasks
            if data.get("efsts"):
                with st.expander("**Essential Fire Support Tasks (EFSTs)**", expanded=True):
                    for efst in data["efsts"]:
                        st.markdown(f"**{efst.get('number', 'EFST')} - {efst.get('phase', '')}**")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"- **Task:** {efst.get('task', '')}")
                            st.markdown(f"- **Purpose:** {efst.get('purpose', '')}")
                            st.markdown(f"- **Target:** {efst.get('target_number', '')} @ {efst.get('target_location', '')}")
                        with col2:
                            st.markdown(f"- **Trigger:** {efst.get('trigger', '')}")
                            st.markdown(f"- **Delivery:** {efst.get('delivery_asset', '')}")
                            st.markdown(f"- **Attack Guidance:** {efst.get('attack_guidance', '')}")
                            st.markdown(f"- **Effects:** {efst.get('effects', '')}")
                        st.markdown("---")
            
            # FSCMs
            fscms = data.get("fscms", {})
            if any(fscms.get(k) for k in ["fscl", "bcl", "acas", "nfas", "rfas", "other"]):
                with st.expander("**Fire Support Coordination Measures**"):
                    if fscms.get("fscl"):
                        st.markdown("**FSCLs:**")
                        for f in fscms["fscl"]:
                            grids = ", ".join(f.get("grid_points", []))[:50] + "..." if f.get("grid_points") else ""
                            st.markdown(f"- {f.get('name', 'FSCL')}: {grids} (Effective: {f.get('effective', 'TBD')})")
                    if fscms.get("bcl"):
                        st.markdown("**BCLs:**")
                        for b in fscms["bcl"]:
                            grids = ", ".join(b.get("grid_points", []))[:50] + "..." if b.get("grid_points") else ""
                            st.markdown(f"- {b.get('name', 'BCL')}: {grids} (Effective: {b.get('effective', 'TBD')})")
                    if fscms.get("acas"):
                        st.markdown("**ACAs:**")
                        for a in fscms["acas"]:
                            st.markdown(f"- {a.get('name', 'ACA')}: {a.get('min_alt', '')} - {a.get('max_alt', '')}, {a.get('location', '')} (Effective: {a.get('effective', 'TBD')})")
                    if fscms.get("nfas"):
                        st.markdown("**NFAs:**")
                        for nfa in fscms["nfas"]:
                            st.markdown(f"- {nfa.get('name', 'NFA')}: {nfa.get('grid', '')} - {nfa.get('description', '')}")
                    if fscms.get("rfas"):
                        st.markdown("**RFAs:**")
                        for rfa in fscms["rfas"]:
                            st.markdown(f"- {rfa.get('name', 'RFA')}: {rfa.get('grid', '')} - {rfa.get('restrictions', '')}")
            
            # Air Support
            air = data.get("air_support", {})
            if air:
                with st.expander("**Air Support**"):
                    if air.get("allocation_by_phase"):
                        st.markdown("**Allocation by Phase:**")
                        for alloc in air["allocation_by_phase"]:
                            st.markdown(f"- {alloc.get('phase', '')}: {alloc.get('unit', '')} - {alloc.get('assets', '')}")
                    if air.get("scl"):
                        st.markdown("**Standard Conventional Loadouts:**")
                        for scl in air["scl"]:
                            st.markdown(f"- {scl.get('platform', '')}: {scl.get('loadout', '')}")
            
            # Artillery Support
            arty = data.get("artillery_support", {})
            if arty:
                with st.expander("**Artillery Support**"):
                    if arty.get("organization"):
                        for org in arty["organization"]:
                            st.markdown(f"- {org.get('unit', '')}: {org.get('quantity', '')}x {org.get('type', '')} ({org.get('role', '')})")
                    if arty.get("radar_assets"):
                        st.markdown("**Radar Assets:**")
                        for radar in arty["radar_assets"]:
                            st.markdown(f"- {radar.get('quantity', '')}x {radar.get('type', '')}")
            
            # Ammunition Allocations
            ammo = data.get("ammunition_allocations", {})
            if any(ammo.get(k) for k in ["himars", "artillery_155mm", "mortars_81mm"]):
                with st.expander("**Ammunition Allocations**"):
                    if ammo.get("himars"):
                        st.markdown("**HIMARS:**")
                        for a in ammo["himars"]:
                            st.markdown(f"- {a.get('nomenclature', '')}: **{a.get('quantity', '')}** rds")
                    if ammo.get("artillery_155mm"):
                        st.markdown("**155mm Artillery:**")
                        for a in ammo["artillery_155mm"]:
                            st.markdown(f"- {a.get('nomenclature', '')}: **{a.get('quantity', '')}** rds")
                    if ammo.get("mortars_81mm"):
                        st.markdown("**81mm Mortars:**")
                        for a in ammo["mortars_81mm"]:
                            st.markdown(f"- {a.get('nomenclature', '')}: **{a.get('quantity', '')}** rds")
            
            # Coordinating instructions
            if data.get("coordinating_instructions"):
                with st.expander("**Coordinating Instructions**"):
                    for instr in data["coordinating_instructions"]:
                        st.markdown(f"- {instr}")
            
            # Key Restrictions
            if data.get("key_restrictions"):
                with st.expander("**Key Restrictions**"):
                    for r in data["key_restrictions"]:
                        st.markdown(f"- {r}")
            
            # Summary
            if data.get("summary"):
                st.info(f"**Summary:** {data['summary']}")


def render_chat():
    """Render the main chat interface."""
    # Show data tabs if data is loaded
    render_data_tabs()
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Enter your fires planning query..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = get_assistant_response(prompt)
                st.markdown(response)
        
        # Parse all update types
        ammo_updates = parse_ammo_updates(response)
        loadout_updates = parse_loadout_updates(response)
        map_updates = parse_map_updates(response)
        
        # Apply updates
        if ammo_updates:
            apply_ammo_updates(ammo_updates)
        if loadout_updates:
            apply_loadout_updates(loadout_updates)
        if map_updates:
            apply_map_updates(map_updates)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Rerun if any updates were made
        if ammo_updates or loadout_updates or map_updates:
            st.rerun()


def render_map_section():
    """Render the interactive map section."""
    if not MAPS_AVAILABLE:
        st.warning("Map functionality requires folium and mgrs libraries. Install with: pip install folium streamlit-folium mgrs")
        return
    
    st.markdown("### 🗺️ Operational Map")
    
    # Map controls
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        # Quick add unit form
        with st.expander("➕ Add Unit", expanded=False):
            unit_name = st.text_input("Unit Name", key="map_unit_name", placeholder="e.g., Enemy SAM Site 1")
            coord_input = st.text_input("Coordinates (MGRS or Lat,Lon)", key="map_coord", placeholder="32SME51841489 or 15.5, 120.3")
            force_select = st.selectbox("Force", ["red", "blue"], key="map_force")
            
            # System selection based on force
            if force_select == "red":
                systems = list(THREAT_SYSTEMS["red"].keys())
            else:
                systems = list(THREAT_SYSTEMS["blue"].keys())
            system_select = st.selectbox("System Type", systems, key="map_system")
            
            if st.button("Add to Map", key="add_map_unit"):
                if unit_name and coord_input:
                    coords = parse_coordinates(coord_input)
                    if coords:
                        unit_id = f"{unit_name}_{coords[0]:.4f}_{coords[1]:.4f}"
                        add_map_unit(unit_id, unit_name, coords[0], coords[1], 
                                   system_select, force_select, system_select)
                        st.success(f"Added {unit_name}")
                        st.rerun()
                    else:
                        st.error("Invalid coordinates")
                else:
                    st.warning("Enter unit name and coordinates")
    
    with col2:
        # Show current units
        with st.expander("📍 Plotted Units", expanded=False):
            map_units = st.session_state.get("map_units", {})
            if map_units:
                for uid, unit in map_units.items():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        force_icon = "🔵" if unit["force"] == "blue" else "🔴"
                        st.markdown(f"{force_icon} **{unit['name']}** ({unit['system']})")
                    with col_b:
                        if st.button("❌", key=f"del_{uid}"):
                            remove_map_unit(uid)
                            st.rerun()
            else:
                st.caption("No units plotted")
    
    with col3:
        if st.button("🗑️ Clear All", key="clear_map"):
            clear_map_units()
            st.rerun()
        
        if st.button("🔴 Clear Red", key="clear_red"):
            clear_map_units("red")
            st.rerun()
        
        if st.button("🔵 Clear Blue", key="clear_blue"):
            clear_map_units("blue")
            st.rerun()
    
    # Render the map
    map_obj = create_map()
    if map_obj:
        st_folium(map_obj, width=700, height=500)
    
    # Legend
    with st.expander("📖 Map Legend"):
        st.markdown("""
        **Threat Rings by Color:**
        - 🔴 **Red** - Anti-ship missiles (ASCM)
        - 🟠 **Orange** - Air defense (SAM)
        - 🟡 **Yellow** - Ground fires (Artillery/MLRS)
        - 🔵 **Blue** - Friendly weapon systems
        - 🟤 **Dark Red** - Ballistic missiles (ASBM)
        
        **Coordinates:**
        - Enter MGRS: `32SME51841489` or `32S ME 5184 1489`
        - Enter Lat/Lon: `15.5, 120.3`
        """)


def get_assistant_response(user_message: str) -> str:
    """Get response from Claude API."""
    try:
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        
        # Load all reference documents
        docs = load_reference_docs()
        
        # Build comprehensive context
        hptl_context = get_hptl_tss_context()
        tlws_context = get_tlws_context()
        edl_context = get_edl_context()
        adversary_context = get_adversary_context()
        opord_context = get_opord_context()
        
        system_prompt = get_system_prompt_with_context(
            ammo_status=get_ammo_status_string(),
            doctrine_ref=docs.get('doctrine', ''),
            weapons_ref=docs.get('weapons', ''),
            hughes_ref=docs.get('hughes', ''),
            appendix17_data="\n\n".join(filter(None, [hptl_context, tlws_context, edl_context, adversary_context, opord_context]))
        )
        
        messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        messages.append({"role": "user", "content": user_message})
        
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=messages
        )
        
        if hasattr(response, 'usage'):
            st.session_state.total_tokens += response.usage.input_tokens + response.usage.output_tokens
        
        return response.content[0].text
    
    except anthropic.APIError as e:
        return f"⚠️ **API Error:** {str(e)}"
    except KeyError:
        return "⚠️ **Configuration Error:** API key not found."
    except Exception as e:
        return f"⚠️ **Error:** {str(e)}"


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    st.set_page_config(
        page_title="Fires Coordinator Agent",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
        <style>
        .main-header { text-align: center; padding: 1rem 0; border-bottom: 2px solid #1a365d; margin-bottom: 1rem; }
        .main-header h1 { color: #1a365d; margin-bottom: 0.25rem; }
        .main-header p { color: #4a5568; font-size: 1.1em; margin: 0; }
        .stProgress > div > div { height: 8px; border-radius: 4px; }
        </style>
    """, unsafe_allow_html=True)
    
    init_session_state()
    
    st.markdown("""
        <div class="main-header">
            <h1>🎯 Fires Coordinator Agent</h1>
            <p>EWS MAGTF Operations Afloat Training Tool</p>
        </div>
    """, unsafe_allow_html=True)
    
    render_sidebar()
    
    # Main content tabs
    main_tab1, main_tab2 = st.tabs(["💬 Chat", "🗺️ Map"])
    
    with main_tab1:
        if not st.session_state.messages:
            adv = st.session_state.adversary
            st.markdown(f"""
            **Welcome to the Fires Coordinator Agent v8.**
            
            **Current Setup:**
            - Loadout: {st.session_state.current_loadout}
            - Adversary: {adv}
            - HPTL/TSS: {"Loaded" if st.session_state.hptl_data else "Not loaded"}
            - Target List: {len(st.session_state.tlws_data)} targets
            - EDL: {"Loaded" if st.session_state.edl_data else "Not loaded"}
            - Map Units: {len(st.session_state.get('map_units', {}))} plotted
            
            **Capabilities:**
            - 🎯 Weapons-target matching with TSS integration
            - 📊 Salvo calculations (Pk-based weaponeering)
            - ⚓ Naval engagement analysis (Hughes Salvo Model)
            - 🚁 OPF-M Hero-120 employment (20km std / 60km extended)
            - 📄 Document parsing (OPORD, AGM/TSS/HPTL, TLWS, EDL)
            - 📦 **Dynamic loadouts** - describe your task org and ammo updates automatically
            - 🗺️ **Interactive map** - plot units with threat rings
            
            **NEW in v8 - Dynamic Loadouts:**
            - *"We have a SAG with 2x DDG FLT IIA and 1x CG"* → sidebar updates
            - *"Add a HIMARS battery"* → adds to existing loadout
            - *"Our Excalibur allocation is 50 rounds"* → updates specific ammo
            
            **NEW in v8 - Map Visualization:**
            - *"Plot an HQ-9 site at 32S ME 5184 1489"* → adds to map with threat ring
            - Use the Map tab to manually add/remove units
            - View threat rings showing weapon ranges
            
            **To get started:**
            1. Upload your OPORD/Annex, AGM/TSS/HPTL, TLWS, or EDL from the sidebar
            2. Describe your task organization (SAG composition, ground units)
            3. Ask fires planning questions!
            
            **Example queries:**
            - *"Our SAG has 2 DDGs and an FFG - what's our loadout?"*
            - *"Recommend fires against a Type 055 at 150nm"*
            - *"Analyze engagement: 3 DDGs vs 2 Type 052D"*
            - *"Plot enemy S-400 at 15.5, 121.3"*
            ---
            """)
        
        render_chat()
    
    with main_tab2:
        render_map_section()


if __name__ == "__main__":
    main()
