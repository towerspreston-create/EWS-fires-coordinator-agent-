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

---

## PARAMETER DEFINITIONS

### Striking Power (α, β)
Missiles fired per ship per salvo.

**Example:** Each DDG fires 4 missiles → α = 4

### Targeting Effectiveness (σ)
Probability that a fired missile hits the target (Pk). Represents missile quality, targeting accuracy, and engagement conditions.

| Missile/Condition | Targeting Effectiveness (σ) |
|-------------------|----------------------------|
| High-end PGM (LRASM) | 0.7-0.9 |
| Modern ASCM (Harpoon, NSM) | 0.5-0.7 |
| Older/less accurate ASCM | 0.3-0.5 |
| Degraded conditions (EW, poor targeting) | 0.2-0.4 |

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

| Ship Class | Defensive Power |
|------------|-----------------|
| DDG (Aegis) | 4-8 intercepts |
| CG (Aegis) | 6-10 intercepts |
| FFG | 2-4 intercepts |
| Type 055 | 6-10 intercepts |
| Type 052D | 4-8 intercepts |
| Type 022 (FAC) | 0 intercepts |

### Staying Power (a, b)
Hits required to achieve mission-kill (ship can no longer contribute to combat).

| Ship Type | Staying Power | Notes |
|-----------|---------------|-------|
| Carrier | 6-10 hits | Large, compartmentalized |
| Cruiser | 3-5 hits | Heavy construction |
| Destroyer (DDG) | 1-2 hits | Modern design, less redundancy |
| Frigate | 1-2 hits | Smaller |
| Type 022 (FAC) | 2 hits | Small but can take 2 hits |
| Corvette | 1 hit | Minimal staying power |

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

## FRACTIONAL EXCHANGE RATIO (FER)

From LT Casey Mahon's thesis on land-sea missile engagements:

```
FER = (ΔA/A) / (ΔB/B)
```

- **FER > 1:** Land-based forces (NMESIS) will eventually win
- **FER < 1:** Sea-based forces will eventually win
- **FER = 1:** Stalemate

This metric is useful for evaluating NMESIS battery effectiveness against naval forces.

---

## MULTI-SALVO ANALYSIS

After first salvo, recalculate with surviving ships:

```
A₁ = A₀ - min(ΔA₀, A₀)    [Cannot lose more ships than you have]
B₁ = B₀ - min(ΔB₀, B₀)
```

Continue until one side eliminated or forces disengage.

---

## TACTICAL IMPLICATIONS FOR MARINES

### NMESIS Battery Advantages
- Land-based forces are **area targets** (harder to hit with naval missiles)
- Naval forces are **point targets** (easier to hit with precision ASCMs)
- Cluttered terrain provides cover/concealment
- Can fire first if naval force location is known

### Keys to Success
1. **Win the counter-reconnaissance fight** - Find them before they find you
2. **Fire effectively first** - Initiative is decisive
3. **Numerical advantage** - More shooters = more missiles = saturation
4. **Reduce enemy targeting effectiveness** - Camouflage, deception, EMCON

---

## COMMON CALCULATION ERRORS

1. **Forgetting alertness (τ):** Full formula includes τ × z × A, not just z × A
2. **Forgetting targeting effectiveness (σ):** Full formula is σ × α × A, not just α × A
3. **Wrong order of operations:** Calculate (σ × α × A) and (τ × z × A) first, then subtract, then divide
4. **Ignoring max(0, ...):** If defense > offense, result is 0, not negative
5. **Exceeding available ships:** If ΔA > A, report "all destroyed with overkill"

---

## SIMPLIFIED FORMULA (When τ = 1)

When both sides are fully alert (τ = 1), the formula simplifies to:
```
ΔA = ((σᵦ × β × B) - (z × A)) / a
ΔB = ((σₐ × α × A) - (y × B)) / b
```

This is the most common case for planning purposes.

---

## REFERENCES

- Mirsch, Maj Andrew. "Missile Math for Marines." *Marine Corps Gazette*, January 2023.
- Hughes, W.P. & Girrier, R. (2018). *Fleet Tactics and Naval Operations, Third Edition*
- Mahon, Casey. "A Littoral Combat Model for Land-Sea Missile Engagements." NPS Thesis, 2007.
- Faucett, Joshua. "Shore-Based Anti-Ship Missile Capability and Employment." NPS Thesis, 2019.

---

*This reference is UNCLASSIFIED and derived from publicly available academic and doctrinal sources.*
