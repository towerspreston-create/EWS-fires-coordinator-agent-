"""
Fires Coordinator Agent
EWS MAGTF Operations Afloat Training Tool

A Streamlit application that provides AI-assisted fires planning support
for USMC Expeditionary Warfare School students.
"""

import streamlit as st
import anthropic
import re
from pathlib import Path
import sys

# Add prompts directory to path
sys.path.insert(0, str(Path(__file__).parent))
from prompts.system_prompt import get_system_prompt_with_context

# =============================================================================
# CONFIGURATION
# =============================================================================

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096

# Default ammunition loads
DEFAULT_AMMO = {
    "GMLRS": {"current": 108, "max": 108, "unit": "rockets"},
    "ATACMS": {"current": 12, "max": 12, "unit": "missiles"},
    "PrSM": {"current": 24, "max": 24, "unit": "missiles"},
    "155mm_HE": {"current": 600, "max": 600, "unit": "rounds"},
    "Excalibur": {"current": 36, "max": 36, "unit": "rounds"},
    "5in_Naval": {"current": 600, "max": 600, "unit": "rounds"},
    "VLS_Cells": {"current": 96, "max": 96, "unit": "cells"},
    "Harpoon_LRASM": {"current": 8, "max": 8, "unit": "missiles"},
    "Mortar_HE": {"current": 200, "max": 200, "unit": "rounds"},
    "Mortar_Illum": {"current": 48, "max": 48, "unit": "rounds"},
    "Mortar_Smoke": {"current": 24, "max": 24, "unit": "rounds"},
}

# Ammo type aliases for parsing
AMMO_ALIASES = {
    "gmlrs": "GMLRS",
    "atacms": "ATACMS",
    "prsm": "PrSM",
    "precision strike missile": "PrSM",
    "155mm": "155mm_HE",
    "155mm he": "155mm_HE",
    "he 155": "155mm_HE",
    "excalibur": "Excalibur",
    "m982": "Excalibur",
    "5 inch": "5in_Naval",
    "5\"": "5in_Naval",
    "5in": "5in_Naval",
    "naval gun": "5in_Naval",
    "vls": "VLS_Cells",
    "tomahawk": "VLS_Cells",
    "tlam": "VLS_Cells",
    "sm-2": "VLS_Cells",
    "sm-6": "VLS_Cells",
    "harpoon": "Harpoon_LRASM",
    "lrasm": "Harpoon_LRASM",
    "mortar he": "Mortar_HE",
    "81mm he": "Mortar_HE",
    "mortar illum": "Mortar_Illum",
    "illumination": "Mortar_Illum",
    "illum": "Mortar_Illum",
    "mortar smoke": "Mortar_Smoke",
    "smoke": "Mortar_Smoke",
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
        display_name = ammo_type.replace("_", " ")
        lines.append(
            f"- {display_name}: {data['current']}/{data['max']} {data['unit']} "
            f"({pct:.0f}%) [{status}]"
        )
    
    return "\n".join(lines)


def get_status_label(percentage: float) -> str:
    """Get status label based on percentage."""
    if percentage > 50:
        return "GREEN"
    elif percentage > 25:
        return "AMBER"
    else:
        return "RED"


def get_status_color(percentage: float) -> str:
    """Get color code for status display."""
    if percentage > 50:
        return "#22c55e"  # Green
    elif percentage > 25:
        return "#f59e0b"  # Amber
    else:
        return "#ef4444"  # Red


def parse_ammo_updates(response: str) -> list[tuple[str, int]]:
    """Parse ammunition updates from assistant response."""
    updates = []
    
    # Pattern to match [AMMO_UPDATE] blocks
    pattern = r'\[AMMO_UPDATE\]\s*ITEM:\s*([^\n]+)\s*EXPENDED:\s*(\d+)\s*\[/AMMO_UPDATE\]'
    matches = re.findall(pattern, response, re.IGNORECASE)
    
    for item, amount in matches:
        item = item.strip().lower()
        amount = int(amount)
        
        # Try to match to known ammo type
        if item in AMMO_ALIASES:
            updates.append((AMMO_ALIASES[item], amount))
        else:
            # Try partial matching
            for alias, ammo_type in AMMO_ALIASES.items():
                if alias in item or item in alias:
                    updates.append((ammo_type, amount))
                    break
    
    return updates


def apply_ammo_updates(updates: list[tuple[str, int]]) -> list[str]:
    """Apply ammunition updates to session state."""
    messages = []
    
    for ammo_type, amount in updates:
        if ammo_type in st.session_state.ammo:
            old_val = st.session_state.ammo[ammo_type]["current"]
            new_val = max(0, old_val - amount)
            st.session_state.ammo[ammo_type]["current"] = new_val
            messages.append(f"Updated {ammo_type}: {old_val} → {new_val}")
    
    return messages


def reset_ammunition():
    """Reset all ammunition to default values."""
    st.session_state.ammo = {
        k: {"current": v["max"], "max": v["max"], "unit": v["unit"]}
        for k, v in DEFAULT_AMMO.items()
    }


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "ammo" not in st.session_state:
        reset_ammunition()
    
    if "total_tokens" not in st.session_state:
        st.session_state.total_tokens = 0


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_sidebar():
    """Render the sidebar with ammunition tracker and controls."""
    with st.sidebar:
        st.markdown("## 📊 Ammunition Status")
        st.markdown("---")
        
        # Group ammunition by category
        categories = {
            "HIMARS Battery": ["GMLRS", "ATACMS", "PrSM"],
            "Artillery Battery": ["155mm_HE", "Excalibur"],
            "DDG": ["5in_Naval", "VLS_Cells", "Harpoon_LRASM"],
            "Mortar Platoon": ["Mortar_HE", "Mortar_Illum", "Mortar_Smoke"],
        }
        
        for category, ammo_types in categories.items():
            st.markdown(f"**{category}**")
            
            for ammo_type in ammo_types:
                if ammo_type in st.session_state.ammo:
                    data = st.session_state.ammo[ammo_type]
                    pct = (data["current"] / data["max"]) * 100 if data["max"] > 0 else 0
                    color = get_status_color(pct)
                    display_name = ammo_type.replace("_", " ")
                    
                    # Progress bar with color
                    st.markdown(
                        f'<div style="margin-bottom: 4px;">'
                        f'<span style="font-size: 0.85em;">{display_name}</span>'
                        f'<span style="float: right; font-size: 0.85em; color: {color};">'
                        f'{data["current"]}/{data["max"]}</span></div>',
                        unsafe_allow_html=True
                    )
                    st.progress(pct / 100)
            
            st.markdown("")  # Spacer
        
        st.markdown("---")
        
        # Control buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Reset Ammo", use_container_width=True):
                reset_ammunition()
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.total_tokens = 0
                st.rerun()
        
        # Token usage
        if st.session_state.total_tokens > 0:
            st.markdown("---")
            st.markdown(f"**Token Usage:** {st.session_state.total_tokens:,}")
            est_cost = (st.session_state.total_tokens / 1000) * 0.003  # Rough estimate
            st.markdown(f"**Est. Cost:** ${est_cost:.4f}")
        
        # Manual ammo adjustment expander
        with st.expander("⚙️ Manual Adjustment"):
            ammo_select = st.selectbox(
                "Select Ammunition",
                options=list(st.session_state.ammo.keys()),
                format_func=lambda x: x.replace("_", " ")
            )
            
            if ammo_select:
                current = st.session_state.ammo[ammo_select]["current"]
                max_val = st.session_state.ammo[ammo_select]["max"]
                
                new_val = st.number_input(
                    "New Value",
                    min_value=0,
                    max_value=max_val,
                    value=current,
                    key="manual_ammo_input"
                )
                
                if st.button("Update"):
                    st.session_state.ammo[ammo_select]["current"] = new_val
                    st.rerun()
        
        # Disclaimer
        st.markdown("---")
        st.markdown(
            '<div style="font-size: 0.75em; color: #888; text-align: center;">'
            '⚠️ UNCLASSIFIED TRAINING TOOL<br>'
            'Do not input CUI or classified information<br><br>'
            'EWS AY26 | Conference Group 13'
            '</div>',
            unsafe_allow_html=True
        )


def render_chat():
    """Render the main chat interface."""
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Enter your fires planning query..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = get_assistant_response(prompt)
                st.markdown(response)
        
        # Parse and apply any ammo updates
        updates = parse_ammo_updates(response)
        if updates:
            apply_ammo_updates(updates)
        
        # Add assistant message to history
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Rerun to update sidebar
        if updates:
            st.rerun()


def get_assistant_response(user_message: str) -> str:
    """Get response from Claude API."""
    try:
        # Initialize client
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        
        # Load reference docs
        weapons_ref, hughes_ref = load_reference_docs()
        
        # Build system prompt with current context
        system_prompt = get_system_prompt_with_context(
            ammo_status=get_ammo_status_string(),
            weapons_ref=weapons_ref,
            hughes_ref=hughes_ref
        )
        
        # Build message history
        messages = []
        for msg in st.session_state.messages:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Call API
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=messages
        )
        
        # Track token usage
        if hasattr(response, 'usage'):
            st.session_state.total_tokens += (
                response.usage.input_tokens + response.usage.output_tokens
            )
        
        # Extract response text
        return response.content[0].text
    
    except anthropic.APIError as e:
        return f"⚠️ **API Error:** {str(e)}\n\nPlease try again or contact the administrator."
    
    except KeyError:
        return (
            "⚠️ **Configuration Error:** API key not found.\n\n"
            "Please ensure `ANTHROPIC_API_KEY` is set in Streamlit secrets."
        )
    
    except Exception as e:
        return f"⚠️ **Unexpected Error:** {str(e)}\n\nPlease try again."


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main application entry point."""
    # Page config
    st.set_page_config(
        page_title="Fires Coordinator Agent",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        /* Header styling */
        .main-header {
            text-align: center;
            padding: 1rem 0;
            border-bottom: 2px solid #1a365d;
            margin-bottom: 1rem;
        }
        .main-header h1 {
            color: #1a365d;
            margin-bottom: 0.25rem;
        }
        .main-header p {
            color: #4a5568;
            font-size: 1.1em;
            margin: 0;
        }
        
        /* Chat styling */
        .stChatMessage {
            background-color: #f8fafc;
            border-radius: 8px;
            padding: 0.5rem;
        }
        
        /* Sidebar styling */
        .css-1d391kg {
            background-color: #f1f5f9;
        }
        
        /* Progress bars */
        .stProgress > div > div {
            height: 8px;
            border-radius: 4px;
        }
        
        /* Code blocks in responses */
        pre {
            background-color: #1e293b;
            border-radius: 6px;
            padding: 1rem;
        }
        
        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        th {
            background-color: #f1f5f9;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    init_session_state()
    
    # Header
    st.markdown("""
        <div class="main-header">
            <h1>🎯 Fires Coordinator Agent</h1>
            <p>EWS MAGTF Operations Afloat Training Tool</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Render sidebar
    render_sidebar()
    
    # Welcome message if no chat history
    if not st.session_state.messages:
        st.markdown("""
        **Welcome to the Fires Coordinator Agent.**
        
        I can assist you with:
        - 🎯 **Weapons-target matching** recommendations
        - 📊 **Salvo calculations** using Pk-based weaponeering
        - ⚓ **Naval engagement analysis** using the Hughes Salvo Model
        - 📦 **Ammunition tracking** with status alerts
        
        **Example queries:**
        - *"Recommend a weapon system to engage a mechanized infantry company at 45km"*
        - *"Calculate rounds required for 90% Pk against a hardened bunker using Excalibur"*
        - *"Analyze a surface engagement: 2 DDGs vs 3 Type 054A frigates"*
        - *"Update ammo: expended 12 GMLRS and 2 ATACMS"*
        
        ---
        """)
    
    # Render chat interface
    render_chat()


if __name__ == "__main__":
    main()
