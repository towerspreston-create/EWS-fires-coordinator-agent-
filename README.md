# Fires Coordinator Agent

**EWS MAGTF Operations Afloat Training Tool**

A Streamlit-based AI assistant for USMC Expeditionary Warfare School students during MAGTF operations afloat planning exercises. The application provides fires planning support including weapons-target matching, salvo calculations, naval engagement analysis using the Hughes Salvo Model, and ammunition tracking.

## ⚠️ Classification

**UNCLASSIFIED** - This is a training tool using publicly available data only. Do not input CUI or classified information.

---

## Features

- 🎯 **Weapons-Target Matching** - Recommendations based on range, target type, and available systems
- 📊 **Salvo Calculations** - Pk-based weaponeering with shown work
- ⚓ **Hughes Salvo Model** - Naval surface engagement analysis
- 📦 **Ammunition Tracking** - Session-persistent tracking with visual status indicators
- 💬 **Chat Interface** - Natural language interaction with conversation history

---

## Project Structure

```
fires_coordinator_app/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── .streamlit/
│   └── config.toml          # Streamlit configuration
├── prompts/
│   ├── __init__.py
│   └── system_prompt.py     # System prompt and context builder
└── data/
    ├── weapons_reference.md # Weapons specifications and Pk estimates
    └── hughes_salvo_model.md # Naval engagement model reference
```

---

## Local Development Setup

### Prerequisites

- Python 3.9 or higher
- pip package manager
- Anthropic API key

### Installation

1. **Clone or download the repository**

```bash
cd fires_coordinator_app
```

2. **Create a virtual environment (recommended)**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up secrets for local development**

Create a secrets file (DO NOT COMMIT THIS FILE):

```bash
mkdir -p .streamlit
```

Create `.streamlit/secrets.toml`:

```toml
ANTHROPIC_API_KEY = "sk-ant-your-api-key-here"
```

5. **Run the application**

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## Streamlit Cloud Deployment

### Step 1: Prepare Repository

1. Create a new GitHub repository
2. Push all files to the repository
3. **IMPORTANT:** Do NOT include `.streamlit/secrets.toml` in your repository

Add to `.gitignore`:
```
.streamlit/secrets.toml
__pycache__/
*.pyc
venv/
.env
```

### Step 2: Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository
5. Set the main file path: `app.py`
6. Click "Deploy"

### Step 3: Configure Secrets

1. In the Streamlit Cloud dashboard, click on your app
2. Click "Settings" (gear icon)
3. Go to "Secrets" section
4. Add your secret:

```toml
ANTHROPIC_API_KEY = "sk-ant-your-api-key-here"
```

5. Click "Save"
6. Your app will automatically restart with the new secrets

### Step 4: Share with Students

Your app will be available at:
```
https://your-app-name.streamlit.app
```

Share this URL with students. No login required.

---

## API Cost Estimation

Using Claude claude-sonnet-4-20250514 (Sonnet):
- Input: $3 / million tokens
- Output: $15 / million tokens

**Estimated costs for EWS event:**

| Scenario | Est. Tokens | Est. Cost |
|----------|-------------|-----------|
| Single query (with full context) | ~5,000 input + ~1,000 output | ~$0.03 |
| Student session (20 queries) | ~100,000 input + ~20,000 output | ~$0.60 |
| Full event (15 students × 20 queries) | ~1.5M input + ~300K output | ~$9.00 |

**Budget recommendation:** $20-30 should be more than sufficient for a 1-week event with 15 students.

### Cost Optimization Tips

1. The app tracks token usage in the sidebar
2. Clear conversations when starting new planning scenarios
3. Be specific in queries to reduce back-and-forth
4. The reference documents are cached in context, so longer conversations are more efficient

---

## Usage Guide

### Example Queries

**Weapons-Target Matching:**
```
Recommend a weapon system to engage a mechanized infantry company in the open at 45km. 
Consider we need 90% Pk and have full ammunition available.
```

**Salvo Calculations:**
```
Calculate the number of 155mm HE rounds required to achieve 80% Pk against 
a soft target in the open, assuming standard Pk of 0.12 per round.
```

**Hughes Salvo Model:**
```
Analyze this surface engagement:
Blue: 2 DDGs with 8 LRASM each (Pk 0.5), defensive power 8, staying power 2.5
Red: 3 Type 054A with 8 YJ-83 each (Pk 0.25), defensive power 4, staying power 1.5
```

**Ammunition Updates:**
```
Update ammunition: We expended 12 GMLRS rockets and 2 ATACMS missiles 
in support of the regiment's attack.
```

### Ammunition Tracking

The sidebar displays current ammunition status:
- **GREEN (>50%):** Adequate supply
- **AMBER (25-50%):** Consider resupply planning
- **RED (<25%):** Critical - immediate resupply required

You can:
- Manually adjust values using the "Manual Adjustment" expander
- Reset all ammunition with the "Reset Ammo" button
- Let the AI track expenditure automatically when you describe fires missions

---

## Troubleshooting

### "API key not found" Error

- Ensure `ANTHROPIC_API_KEY` is set in `.streamlit/secrets.toml` (local) or Streamlit Cloud secrets
- Check for typos in the key
- Verify the key is active in your Anthropic console

### "Rate limit exceeded" Error

- Wait a few minutes and retry
- Consider upgrading your Anthropic API tier for higher rate limits

### App not loading on Streamlit Cloud

- Check the app logs in the Streamlit Cloud dashboard
- Verify all files are committed to GitHub
- Ensure `requirements.txt` is present and correct

### Ammunition not updating

- The AI outputs ammunition updates in a specific format `[AMMO_UPDATE]`
- If auto-update fails, use manual adjustment in the sidebar
- Clear conversation and try again with explicit expenditure reporting

---

## Customization

### Modifying Default Ammunition Loads

Edit `DEFAULT_AMMO` in `app.py`:

```python
DEFAULT_AMMO = {
    "GMLRS": {"current": 108, "max": 108, "unit": "rockets"},
    # Add or modify ammunition types...
}
```

### Adding New Weapon Systems

1. Add to `data/weapons_reference.md`
2. Update `AMMO_ALIASES` in `app.py` for auto-parsing
3. Add to `DEFAULT_AMMO` if tracking is needed

### Modifying the System Prompt

Edit `prompts/system_prompt.py` to change:
- Output format requirements
- Scope limitations
- Calculation formulas
- Tone and style

---

## Support

For issues with this application, contact:
- EWS Conference Group 13
- Faculty Advisor: Major Ross Ochs

For Anthropic API issues:
- [Anthropic Support](https://support.anthropic.com)
- [API Documentation](https://docs.anthropic.com)

---

## License

This is an educational tool developed for USMC training purposes. All weapons data is derived from unclassified, publicly available sources.

---

*Developed for EWS AY26 MAGTF Operations Afloat Planning Event*
