# Hughes Salvo Model Reference
## UNCLASSIFIED Naval Combat Analysis for EWS Training
## Based on "Missile Math for Marines" (MCA Gazette, January 2023)

---

## OVERVIEW

The Hughes Salvo Model, developed by Captain Wayne P. Hughes Jr., USN (Ret.), provides a mathematical framework for analyzing naval surface combat. It models the exchange of salvos between opposing forces to estimate casualties and predict engagement outcomes.

**Key Principle:** Modern naval combat often resolves in a small number of salvos due to the lethality of anti-ship missiles. The force that achieves effective first salvo often gains decisive advantage.

**Key Insight:** "Firing effectively first is critical in naval combat." - The force that can fire first and effectively dramatically changes the outcome.

---

## FULL SALVO EQUATIONS

### Damage to Blue/A Force (Friendly)
```
ΔA = ((σᵦ × β × B) - (τₐ × z × A)) / a
```

### Damage to Red/B Force (Enemy)
```
ΔB = ((σₐ × α × A) - (τᵦ × y × B)) / b
```

**INTERPRETATION:** A Force ships out of combat = (B Force offensive missiles *minus* B Force missiles defeated by A Force) *divided by* hits required to put a single A Force ship out of action.

### Variable Definitions

| Variable | Article Notation | Description | Range/Units |
|----------|------------------|-------------|-------------|
| A | A | Blue force ship count | Ships |
| B | B | Red force ship count | Ships |
| α | a₂ | Blue striking power (missiles per ship per salvo) | Missiles/ship |
| β | b₂ | Red striking power (missiles per ship per salvo) | Missiles/ship |
| σₐ | σₐ | Blue targeting effectiveness (Pk) | 0 to 1 |
| σᵦ | σᵦ | Red targeting effectiveness (Pk) | 0 to 1 |
| τₐ | τₐ | Blue alertness/defensive readiness | 0 to 1 |
| τᵦ | τᵦ | Red alertness/defensive readiness | 0 to 1 |
| z | a₃ | Blue defensive power (intercepts per ship) | Intercepts/ship |
| y | b₃ | Red defensive power (intercepts per ship) | Intercepts/ship |
| a | a₁ | Blue staying power | Hits to mission-kill |
| b | b₁ | Red staying power | Hits to mission-kill |
| ΔA | ΔA | Blue casualties | Ships mission-killed |
| ΔB | ΔB | Red casualties | Ships mission-killed |
### ⚠️ CRITICAL: Using α/β and σ Correctly

**α and β represent RAW missile counts per ship.** Targeting effectiveness (σ) is applied separately in the equation.

| Approach | Example (Type 055) | Correct? |
|----------|-------------------|----------|
| β = 24 (raw), σ = 0.4 | σ × β = 9.6 | ✅ YES |
| β = 9.6 (pre-multiplied), σ = 1.0 | σ × β = 9.6 | ✅ YES |
| β = 9.6 (pre-multiplied), σ = 0.4 | σ × β = 3.84 | ❌ DOUBLE-COUNTED |

**Rule:** If using values from the "Offensive Power" column in Section 3, set σ = 1.0 (Pk already included). If using raw missile counts, apply σ separately.
---

## PARAMETER DEFINITIONS

### Striking Power (α, β)
Missiles fired per ship per salvo.

**Example:** Each DDG fires 4 missiles → α = 4

### Targeting Effectiveness (σ)
Probability that a fired missile hits the target (Pk). Represents missile quality, targeting accuracy, and engagement conditions.

| Missile/Condition | Target Type | Targeting Effectiveness (σ) |
|-------------------|-------------|----------------------------|
| LRASM | vs defended | 0.6-0.8 |
| NSM | vs defended | 0.5-0.7 |
| Harpoon | vs defended | 0.4-0.6 |
| Harpoon | vs undefended | 0.7-0.85 |
| YJ-18 | vs AEGIS DDG | 0.25-0.35 |
| YJ-18 | vs FFG (less capable) | 0.40-0.50 |
| YJ-18 | vs undefended | 0.70-0.85 |
| YJ-83 | vs AEGIS DDG | 0.15-0.25 |
| YJ-83 | vs FFG | 0.30-0.40 |
| Any ASCM | Degraded conditions (EW, poor targeting) | 0.2-0.4 |

### Alertness (τ)
Defensive readiness of the force. Represents crew readiness, early warning, and ability to employ defensive systems.

| Condition | Alertness (τ) |
|-----------|---------------|
| Fully alert, expecting attack | 1.0 |
| Normal readiness | 0.7-0.9 |
| Surprised, partial response | 0.3-0.5 |
| Complete surprise, no defense | 0 |

**Key Insight:** When τ = 0 (complete surprise), the defensive term becomes zero, and ALL offensive missiles that hit will cause damage.

### Defensive Power (y, z)
Missiles each ship can defeat through hard-kill (SAMs, CIWS) and soft-kill (decoys, ECM).

**Blue Force (z):**
| Ship Class | Defensive Power | Notes |
|------------|-----------------|-------|
| DDG-51 (Aegis) | 4-8 intercepts | SM-2/SM-6, ESSM, CIWS |
| CG-47 (Aegis) | 6-10 intercepts | Larger magazine |
| FFG-62 | 4-6 intercepts | EASR, SM-2, ESSM, RAM |
| LCS | 1-2 intercepts | RAM/SeaRAM only |
**Default Assumption:** When DDG-51 Flight variant is unspecified, use Flight IIA values (z = 6-10) as the most common deployed configuration.

**Olvana/Red Force (y):**
| Ship Class | Defensive Power | Notes |
|------------|-----------------|-------|
| Type 055 Cruiser | 8-12 intercepts | HQ-9, HQ-16, Type 1130 CIWS |
| Type 052D Destroyer | 6-8 intercepts | HQ-9, Type 1130 CIWS |
| Type 054A Frigate | 3-5 intercepts | HQ-16, Type 730 CIWS |
| Type 056 Corvette | 1-2 intercepts | FL-3000N only |
| Type 022 FAC | 0 intercepts | No defensive missiles/CIWS |

### Staying Power (a, b)
Hits required to achieve mission-kill (ship can no longer contribute to combat).

| Ship Type | Staying Power | Notes |
|-----------|---------------|-------|
| Carrier | 6-10 hits | Large, compartmentalized |
| Cruiser (CG-47/Type 055) | 2-4 hits | Heavy construction |
| Destroyer (DDG-51) | 1-2 hits | Modern design, per MCA article |
| Destroyer (Type 052D) | 1-2 hits | Comparable to DDG |
| Frigate (FFG-62/Type 054A) | 1-2 hits | Smaller |
| Type 022 (FAC) | 2 hits | Per MCA article assumption |
| Corvette (Type 056) | 1 hit | Minimal staying power |
| LCS | 1 hit | Minimal armor/redundancy |

---

## WORKED EXAMPLE: USN vs PLAN SAG (from MCA Article)

**Scenario:** 2 USN DDGs vs 5 PLAN Type 022 missile boats

### Parameters (Table 1 from Article)

| Parameter | USN (A Force) | PLAN (B Force) |
|-----------|---------------|----------------|
| Ships (A, B) | 2 | 5 |
| Striking Power (α, β) | 4 | 8 |
| Alertness (τₐ, τᵦ) | 1 | 1 |
| Staying Power (a, b) | 1 | 2 |
| Defensive Power (z, y) | 4 | 0 |
| Targeting Effectiveness (σₐ, σᵦ) | 1 | 0.5 |

### Assumptions from Article:
- Type 022's targeting capability is ½ that of DDGs (σ = 0.5 vs 1.0)
- Both forces fire at the same time, both in range
- DDGs fire 4 missiles per salvo; Type 022s fire 8 missiles (entire magazine)
- DDGs can shoot down 4 SSMs each in defense
- Type 022s have NO defensive missiles or countermeasures (y = 0)
- 2 SM-2s to mission-kill a Type 022; 1 Chinese SSM to mission-kill a DDG
- Both sides equally alert and trained

### Calculation

**Damage to USN (ΔA):**
```
ΔA = ((σᵦ × β × B) - (τₐ × z × A)) / a
ΔA = ((0.5 × 8 × 5) - (1 × 4 × 2)) / 1
ΔA = (20 - 8) / 1
ΔA = 12 mission kills on DDGs
```

**Damage to PLAN (ΔB):**
```
ΔB = ((σₐ × α × A) - (τᵦ × y × B)) / b
ΔB = ((1 × 4 × 2) - (1 × 0 × 5)) / 2
ΔB = (8 - 0) / 2
ΔB = 4 Type 022s mission-killed
```

### Result Interpretation
- **PLAN inflicts 12 mission kills** but USN only has 2 DDGs → Both DDGs destroyed with **massive overkill**
- **USN destroys 4 of 5 Type 022s** → 1 Type 022 survives
- **Outcome:** Pyrrhic PLAN victory—they destroy the USN SAG but lose 80% of their force

---

## KEY INSIGHTS FROM THE ARTICLE

### Insight 1: Force Size Matters
"Numerical superiority is the force attribute that is consistently most advantageous." The technologically inferior but numerically superior PLAN SAG easily overpowers the U.S. Navy SAG.

- At A = 3 DDGs: Both SAGs annihilated (draw)
- At A = 5 DDGs: PLAN annihilated, no USN losses

### Insight 2: Staying Power Is Key
Ships must be able to keep fighting after getting hit. In the example:
- DDG mission-killed after 1 hit (a = 1)
- Type 022 survives until 2 hits (b = 2)

Even quadrupling USN staying power (a = 4) doesn't change the outcome due to PLAN's numerical and striking power advantage.

| Staying Power (a) | USN Attrition (ΔA) |
|-------------------|-------------------|
| 1 (base case) | 12 |
| 2 | 6 |
| 3 | 4 |
| 4 | 3 |

### Insight 3: Fire Effectively First
If USN fires one effective salvo BEFORE PLAN can respond (τᵦ for PLAN's defense irrelevant, and PLAN hasn't fired yet):

| Salvo | A Force | B Force | ΔA | ΔB |
|-------|---------|---------|----|----|
| Salvo 1 (USN fires first) | 2 | 5 | 0 | 4 |
| Salvo 2 (simultaneous) | 2 | 1 | 4 (overkill) | 4 (overkill on 1 Type 22) |

**Result:** USN wins decisively by firing first, destroying 4 Type 022s before they can launch.

---

## SECTION 3: PLANNING ESTIMATES (ODIN-Sourced)

### 3.1 Offensive Power Estimates

**U.S. / Allied Surface Combatants:**

| Platform | ASCM Type | Quantity | Est. Pk (σ) | α (Offensive Power) | Source |
|----------|-----------|----------|-------------|---------------------|--------|
| DDG-51 Flight I/II | Harpoon | 8 | 0.4-0.5 | 3.2-4.0 | Blue Threat Guide |
| DDG-51 Flight IIA/III | Harpoon/LRASM | 8 | 0.5-0.7 | 4.0-5.6 | Blue Threat Guide |
| CG-47 | Harpoon | 8 | 0.4-0.5 | 3.2-4.0 | Blue Threat Guide |
| LCS (Freedom/Independence) | NSM | 8 | 0.5-0.6 | 4.0-4.8 | Blue Threat Guide |
| FFG-62 Constellation | NSM | 16 | 0.5-0.6 | 8.0-9.6 | Blue Threat Guide |
| NMESIS (Ground) | NSM | 2 | 0.5-0.6 | 1.0-1.2 | Blue Threat Guide |

**Adversary (Olvana/Chinese-type) Surface Combatants:**

| Platform | ASCM Type | Quantity | Est. Pk (σ) | β (Offensive Power) | Source |
|----------|-----------|----------|-------------|---------------------|--------|
| Type 055 Cruiser | YJ-18 | 24 | 0.4-0.6 | 9.6-14.4 | ODIN |
| Type 052D Destroyer | YJ-18 | 8 | 0.4-0.6 | 3.2-4.8 | ODIN |
| Type 052C Destroyer | YJ-62 | 8 | 0.3-0.5 | 2.4-4.0 | ODIN |
| Type 054A Frigate | YJ-83 | 8 | 0.3-0.5 | 2.4-4.0 | ODIN |
| Type 056 Corvette | YJ-83 | 4 | 0.3-0.5 | 1.2-2.0 | ODIN |
| Type 022 FAC | YJ-83 | 8 | 0.3-0.5 | 2.4-4.0 | MCA Article |

**Notes on Pk:**
- Lower Pk values assume engagement against AEGIS-equipped or defended targets
- Higher Pk values assume engagement against less capable defenses or achieved surprise
- LRASM Pk higher due to low observability and autonomous terminal guidance
- NSM Pk benefits from passive IR seeker (no EW warning to target)
- YJ-18 terminal sprint (Mach 3) reduces reaction time, increasing effective Pk

### 3.2 Defensive Power Estimates

**U.S. / Allied Surface Combatants:**

| Platform | Primary SAM | Secondary | CIWS | z (Defensive Power) | Source |
|----------|-------------|-----------|------|---------------------|--------|
| DDG-51 Flight I/II | SM-2 | ESSM | Phalanx (2) | 4-8 | Blue Threat Guide |
| DDG-51 Flight IIA | SM-2/SM-6 | ESSM | Phalanx (2) | 6-10 | Blue Threat Guide |
| DDG-51 Flight III | SM-6 | ESSM | Phalanx (2) | 8-12 | Blue Threat Guide |
| CG-47 | SM-2/SM-6 | ESSM | Phalanx (2) | 6-10 | Blue Threat Guide |
| LCS | — | RAM (21) | — | 1-2 | Blue Threat Guide |
| FFG-62 Constellation | SM-2 | ESSM | RAM | 4-6 | Navy Fact File |

**Adversary (Olvana/Chinese-type) Surface Combatants:**

| Platform | Primary SAM | Secondary | CIWS | y (Defensive Power) | Source |
|----------|-------------|-----------|------|---------------------|--------|
| Type 055 Cruiser | HQ-9 | HQ-16, HHQ-10 | Type 1130 (2) | 6-10 | ODIN |
| Type 052D Destroyer | HQ-9 | HHQ-10 | Type 1130 (1) | 4-8 | ODIN |
| Type 052C Destroyer | HQ-9 | — | Type 730 (2) | 4-6 | ODIN |
| Type 054A Frigate | HQ-16 | — | Type 730 (2) | 3-5 | ODIN |
| Type 056 Corvette | FL-3000N | — | — | 1-2 | ODIN |
| Type 022 FAC | — | — | — | 0 | MCA Article |

**Defensive Power Caveats:**
- Values assume adequate warning and reaction time
- Saturation attacks reduce per-missile intercept probability
- Multi-axis attacks stress defense more than single-axis
- Defensive power degrades as magazine depletes across salvos

### 3.3 Staying Power Estimates

| Ship Type | Displacement | Staying Power (a or b) | Notes | Source |
|-----------|--------------|------------------------|-------|--------|
| Aircraft Carrier | 100,000 tons | 6-10 hits | Highly compartmentalized | Planning Est |
| Cruiser (CG-47) | 10,000 tons | 2-4 hits | Good damage control | Planning Est |
| Cruiser (Type 055) | 12,000 tons | 2-4 hits | Large, modern | ODIN |
| Destroyer (DDG-51) | 9,000 tons | 1-2 hits | Per MCA article | MCA Article |
| Destroyer (Type 052D) | 7,500 tons | 1-2 hits | Modern construction | ODIN |
| Frigate (FFG-62) | 7,300 tons | 1-2 hits | Smaller, less redundancy | Planning Est |
| Frigate (Type 054A) | 4,000 tons | 1-2 hits | Smaller combatant | ODIN |
| LCS | 3,500 tons | 1 hit | Minimal armor/redundancy | Blue Threat Guide |
| Corvette (Type 056) | 1,500 tons | 1 hit | Single hit mission-kill | ODIN |
| FAC (Type 022) | 224 tons | 2 hits | Per MCA article | MCA Article |

**Staying Power Notes:**
- Values represent hits to "mission kill" (loss of combat effectiveness)
- Actual sinking may require more hits
- Hit location matters significantly (engineering, bridge, magazines)
- Modern warships generally less survivable than WWII counterparts due to reduced armor and increased system complexity

---

## SECTION 4: NMESIS AND LAND-SEA ENGAGEMENTS

### 4.1 NMESIS System Overview

The Navy Marine Expeditionary Ship Interdiction System (NMESIS) is a ground-based anti-ship missile system integral to the Marine Littoral Regiment (MLR) concept.

**System Specifications (from Blue Threat Guide/ODIN):**
| Parameter | Value |
|-----------|-------|
| Missile | RGM-184A Naval Strike Missile (NSM) |
| Range | 100 nm (185 km) |
| Speed | Subsonic (~Mach 0.9) |
| Guidance | INS/GPS, terrain-following, passive dual-band IR terminal |
| Warhead | 500 lb class unitary (titanium-cased penetrating blast/fragmentation) |
| Missiles per Launcher | 2 |
| Platform | ROGUE-Fires Carrier (unmanned JLTV) |
| Organization | Platoon = 9 launchers (3 sections × 3), command vehicle, leader vehicle |
| IOC | 2021 (operational handoff to 3rd MLR: November 2024) |

**Salvo Model Parameters for NMESIS:**
| Parameter | Value | Notes |
|-----------|-------|-------|
| α (per launcher) | 1.0-1.2 | 2 missiles × 0.5-0.6 Pk |
| α (per platoon, 9 launchers) | 9.0-10.8 | 18 missiles total |
| z (defensive power) | N/A | Land-based, area target |
| Staying power | High | Dispersed, mobile, hard to target |

### 4.2 Fractional Exchange Ratio (FER)

From LT Casey Mahon's thesis on land-sea missile engagements:

```
FER = (ΔA/A) / (ΔB/B)
```

- **FER > 1:** Land-based forces (NMESIS) will eventually win
- **FER < 1:** Sea-based forces will eventually win
- **FER = 1:** Stalemate

**Key Advantages of NMESIS (from MCA Article):**
- Land-based forces are **area targets** (harder to hit with naval missiles)
- Naval forces are **point targets** (easier to hit with precision ASCMs)
- Cluttered terrain provides cover/concealment
- Can fire first if naval force location is known
- Ground-based launchers are difficult to detect and track

### 4.3 NSM Employment Considerations (from Blue Threat Guide)

**Recommended Salvo Size vs Target Type:**
| Target | Recommended NSM | Notes |
|--------|-----------------|-------|
| CG/DDG | 5+ missiles | AEGIS-defended, requires saturation |
| L-Class Ships (LHA/LPD) | 3+ missiles | Less robust defense |
| FFG | 3-4 missiles | Moderate defense |
| Undefended Auxiliary | 1-2 missiles | |

**Employment Notes:**
- Incorporating other lethal or non-lethal capabilities can increase Pk for NSM
- Passive IR seeker allows engagement without triggering EW systems
- Sea-skimming profile reduces detection time
- Stealth features (S-ducted inlet, flush panels) reduce radar cross-section

---

## SECTION 5: APPLYING THE MODEL

### 5.1 Simultaneous Engagement

In a **simultaneous engagement**, both sides detect each other and launch ASCMs at approximately the same time. Both salvos are calculated against the full, undamaged enemy force.

**Process:**
1. Calculate Blue's attack on Red: ΔB = max(0, (σₐ × α × A) - (τᵦ × y × B)) / b
2. Calculate Red's attack on Blue: ΔA = max(0, (σᵦ × β × B) - (τₐ × z × A)) / a
3. Both results apply simultaneously
4. If ΔA > A, report "all A Force destroyed with overkill"
5. If ΔB > B, report "all B Force destroyed with overkill"

### 5.2 Sequential Engagement (Fire Effectively First)

If one side fires an effective salvo before the other can respond:

**Salvo 1 (Attacker fires first):**
- ΔB = max(0, (σₐ × α × A)) / b (no defensive term if surprise)
- OR use full equation if defender has partial warning

**Salvo 2 (Defender responds with survivors):**
- B₁ = B₀ - min(ΔB₀, B₀)
- Recalculate with reduced B Force

### 5.3 Multi-Salvo Analysis

After first salvo, recalculate with surviving ships:

```
A₁ = A₀ - min(ΔA₀, A₀)    [Cannot lose more ships than you have]
B₁ = B₀ - min(ΔB₀, B₀)
```

Continue until one side eliminated or forces disengage.

---

## SECTION 6: COMMON CALCULATION ERRORS

1. **Forgetting alertness (τ):** Full formula includes τ × z × A, not just z × A
2. **Forgetting targeting effectiveness (σ):** Full formula is σ × α × A, not just α × A
3. **Wrong order of operations:** Calculate (σ × α × A) and (τ × z × A) first, then subtract, then divide
4. **Ignoring max(0, ...):** If defense > offense, result is 0, not negative
5. **Exceeding available ships:** If ΔA > A, report "all destroyed with overkill"

---

## SECTION 7: SIMPLIFIED FORMULA (When τ = 1 and σ = 1)

When both sides are fully alert (τ = 1) and have perfect targeting (σ = 1), the formula simplifies to:
```
ΔA = (β × B - z × A) / a
ΔB = (α × A - y × B) / b
```

This is a useful starting point but **should not be used for realistic planning** as it overestimates effectiveness.

---

## SECTION 8: TACTICAL IMPLICATIONS FOR MARINES

### Keys to Success
1. **Win the counter-reconnaissance fight** - Find them before they find you
2. **Fire effectively first** - Initiative is decisive
3. **Numerical advantage** - More shooters = more missiles = saturation
4. **Reduce enemy targeting effectiveness** - Camouflage, deception, EMCON
5. **Exploit NMESIS advantages** - Dispersion, mobility, terrain masking

### NMESIS Battery Doctrine
- Deploy in dispersed positions to complicate enemy targeting
- Use terrain for cover and concealment
- Maintain EMCON until engagement
- Coordinate with naval and air assets for OTH targeting
- Exploit passive sensors to avoid EW detection

---

## REFERENCES

- Mirsch, Maj Andrew. "Missile Math for Marines." *Marine Corps Gazette*, January 2023.
- Hughes, W.P. & Girrier, R. (2018). *Fleet Tactics and Naval Operations, Third Edition*
- Mahon, Casey. "A Littoral Combat Model for Land-Sea Missile Engagements." NPS Thesis, 2007.
- Faucett, Joshua. "Shore-Based Anti-Ship Missile Capability and Employment Concept Exploration." NPS Thesis, 2019.
- AY26 Blue Threat Guide (EWS Training Document)
- ODIN Ship Class Technical Data Sheets
- NMESIS System Specifications (Army-Technology)
- Naval News Articles (NMESIS, NSM)

---

*This reference is UNCLASSIFIED and derived from publicly available academic and doctrinal sources.*
*Last Updated: 16 January 2026*
