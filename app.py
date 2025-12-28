"""
Fires Coordinator Agent v4
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
- Ammunition tracking
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

def load_reference_docs() -> tuple[str, str]:
    """Load reference documentation from files."""
    base_path = Path(__file__).parent / "data"
    weapons_ref = ""
    hughes_ref = ""
    
    weapons_path = base_path / "weapons_reference.md"
    hughes_path = base_path / "hughes_salvo_model.md"
    
    if weapons_path.exists():
        weapons_ref = weapons_path.read_text()
    if hughes_path.exists():
        hughes_ref = hughes_path.read_text()
    
    return weapons_ref, hughes_ref


def get_ammo_status_string() -> str:
    """Generate ammunition status string for system prompt."""
    lines = ["Current ammunition status:"]
    for ammo_type, data in st.session_state.ammo.items():
        pct = (data["current"] / data["max"]) * 100 if data["max"] > 0 else 0
        status = get_status_label(pct)
        display_name = AMMO_DISPLAY_NAMES.get(ammo_type, ammo_type.replace("_", " "))
        lines.append(f"- {display_name}: {data['current']}/{data['max']} {data['unit']} ({pct:.0f}%) [{status}]")
    return "\n".join(lines)


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
    if "adversary" not in st.session_state:
        st.session_state.adversary = "Olvana (Chinese-type)"


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
            ["AGM/TSS/HPTL Matrix", "Target List Worksheet", "Equipment Density List"],
            key="upload_type"
        )
        
        uploaded_file = st.file_uploader(
            f"Upload {upload_type}",
            type=["xlsx", "xls"],
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
        
        updates = parse_ammo_updates(response)
        if updates:
            apply_ammo_updates(updates)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        if updates:
            st.rerun()


def get_assistant_response(user_message: str) -> str:
    """Get response from Claude API."""
    try:
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        
        weapons_ref, hughes_ref = load_reference_docs()
        
        # Build comprehensive context
        hptl_context = get_hptl_tss_context()
        tlws_context = get_tlws_context()
        edl_context = get_edl_context()
        adversary_context = get_adversary_context()
        
        system_prompt = get_system_prompt_with_context(
            ammo_status=get_ammo_status_string(),
            weapons_ref=weapons_ref,
            hughes_ref=hughes_ref,
            appendix17_data="\n\n".join(filter(None, [hptl_context, tlws_context, edl_context, adversary_context]))
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
    
    if not st.session_state.messages:
        adv = st.session_state.adversary
        st.markdown(f"""
        **Welcome to the Fires Coordinator Agent v4.**
        
        **Current Setup:**
        - Loadout: {st.session_state.current_loadout}
        - Adversary: {adv}
        - HPTL/TSS: {"Loaded" if st.session_state.hptl_data else "Not loaded"}
        - Target List: {len(st.session_state.tlws_data)} targets
        - EDL: {"Loaded" if st.session_state.edl_data else "Not loaded"}
        
        **Capabilities:**
        - 🎯 Weapons-target matching with TSS integration
        - 📊 Salvo calculations (Pk-based weaponeering)
        - ⚓ Naval engagement analysis (Hughes Salvo Model)
        - 🚁 OPF-M Hero-120 employment (20km std / 60km extended)
        - 📄 AGM/TSS/HPTL Matrix parsing & creation
        - 🎯 Target List Worksheet management
        - 📦 Equipment Density List parsing
        
        **To get started:**
        1. Upload your AGM/TSS/HPTL, TLWS, or EDL from the sidebar
        2. Select your adversary type
        3. Choose a mission loadout
        4. Ask fires planning questions!
        
        **Example queries:**
        - *"What are my HPTL priorities?"*
        - *"Recommend fires against a 2S19 battery at 35km"*
        - *"Add target AO0025: T-90 platoon at 18S TJ 550 100"*
        - *"Analyze engagement: 2 DDGs vs Type 054A SAG"*
        ---
        """)
    
    render_chat()


if __name__ == "__main__":
    main()
