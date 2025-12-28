# Hughes Salvo Model Reference
## UNCLASSIFIED Naval Combat Analysis for EWS Training

---

## OVERVIEW

The Hughes Salvo Model, developed by Captain Wayne P. Hughes Jr., USN (Ret.), provides a mathematical framework for analyzing naval surface combat. It models the exchange of salvos between opposing forces to estimate casualties and predict engagement outcomes.

**Key Principle:** Modern naval combat often resolves in a small number of salvos due to the lethality of anti-ship missiles. The force that achieves effective first salvo often gains decisive advantage.

---

## BASIC SALVO EQUATIONS

### Damage to Enemy (Red/B Side)
```
ΔB = max(0, αA - yB) / b
```

### Damage to Friendly (Blue/A Side)
```
ΔA = max(0, βB - zA) / a
```

### Variable Definitions

| Variable | Description | Units |
|----------|-------------|-------|
| A | Blue force ship count | Ships |
| B | Red force ship count | Ships |
| α | Blue offensive power per ship | Effective missiles/ship |
| β | Red offensive power per ship | Effective missiles/ship |
| y | Red defensive power per ship | Intercepts/ship |
| z | Blue defensive power per ship | Intercepts/ship |
| a | Blue staying power | Hits to mission-kill |
| b | Red staying power | Hits to mission-kill |
| ΔA | Blue casualties | Ships lost |
| ΔB | Red casualties | Ships lost |

---

## COMPONENT CALCULATIONS

### Offensive Power (α, β)
```
α = (Missiles per ship) × (Pk per missile)
```

**Example:** DDG with 8 Harpoons at Pk 0.3 vs defended target
```
α = 8 × 0.3 = 2.4 effective missiles per ship
```

### Defensive Power (y, z)
```
z = (Soft-kill capacity) + (Hard-kill capacity)
```

**Components:**
- **Soft kill:** Chaff, decoys, ECM (typically 0.5-2.0 intercepts equivalent)
- **Hard kill:** SAMs, CIWS (varies by system and salvo size)

**Planning Estimates:**
| Ship Class | Defensive Power (z or y) |
|------------|-------------------------|
| DDG (Aegis) | 6-12 intercepts |
| CG (Aegis) | 8-15 intercepts |
| FFG | 2-4 intercepts |
| Type 055 | 8-14 intercepts |
| Type 052D | 6-10 intercepts |
| Type 054A | 3-5 intercepts |

### Staying Power (a, b)
Hits required to achieve mission-kill (not necessarily sink).

| Ship Type | Staying Power | Notes |
|-----------|---------------|-------|
| Carrier | 6-10 hits | Large, compartmentalized |
| Cruiser | 3-5 hits | Heavy construction |
| Destroyer | 2-3 hits | Modern design |
| Frigate | 1-2 hits | Smaller, less redundancy |
| Corvette | 1 hit | Minimal staying power |

---

## ENGAGEMENT ANALYSIS PROCEDURE

### Step 1: Define Forces
List ships by type for each side:
- Blue (A): Ship types and quantities
- Red (B): Ship types and quantities

### Step 2: Calculate Aggregate Parameters
For mixed forces, sum offensive contributions:
```
Total Blue Offensive = Σ (αᵢ × nᵢ)
```
Where αᵢ = offensive power of ship type i, nᵢ = number of that type

### Step 3: Apply Salvo Equations
Calculate expected damage to each side.

### Step 4: Assess Outcome
Compare casualties to determine:
- Decisive victory (one side eliminated)
- Tactical victory (significant advantage)
- Mutual attrition (both sides damaged)
- Stalemate (neither achieves significant damage)

---

## WORKED EXAMPLES

### Example 1: Simple Engagement

**Scenario:** 3 DDGs vs 4 Type 054A frigates

**Blue (A) - 3 × DDG:**
- Offensive: 8 Harpoon × 0.3 Pk = 2.4 per ship
- Defensive: z = 8 intercepts per ship
- Staying power: a = 2.5 hits

**Red (B) - 4 × Type 054A:**
- Offensive: 8 YJ-83 × 0.25 Pk = 2.0 per ship
- Defensive: y = 4 intercepts per ship
- Staying power: b = 1.5 hits

**Calculations:**

Damage to Red:
```
ΔB = max(0, αA - yB) / b
ΔB = max(0, (2.4 × 3) - (4 × 4)) / 1.5
ΔB = max(0, 7.2 - 16) / 1.5
ΔB = 0  (Blue offensive absorbed by Red defense)
```

Damage to Blue:
```
ΔA = max(0, βB - zA) / a
ΔA = max(0, (2.0 × 4) - (8 × 3)) / 2.5
ΔA = max(0, 8 - 24) / 2.5
ΔA = 0  (Red offensive absorbed by Blue defense)
```

**Result:** Stalemate - defenses exceed offenses on both sides. Neither side achieves hits in first salvo.

---

### Example 2: Concentrated Strike

**Scenario:** 2 DDGs with LRASM vs 2 Type 052D

**Blue (A) - 2 × DDG:**
- Offensive: 8 LRASM × 0.5 Pk = 4.0 per ship
- Defensive: z = 8 intercepts per ship
- Staying power: a = 2.5 hits

**Red (B) - 2 × Type 052D:**
- Offensive: 8 YJ-18 × 0.4 Pk = 3.2 per ship
- Defensive: y = 8 intercepts per ship
- Staying power: b = 2.5 hits

**Calculations:**

Damage to Red:
```
ΔB = max(0, (4.0 × 2) - (8 × 2)) / 2.5
ΔB = max(0, 8 - 16) / 2.5
ΔB = 0
```

Damage to Blue:
```
ΔA = max(0, (3.2 × 2) - (8 × 2)) / 2.5
ΔA = max(0, 6.4 - 16) / 2.5
ΔA = 0
```

**Result:** Another stalemate. This illustrates why modern naval combat often requires either:
1. Achieving surprise (enemy defensive value = 0)
2. Overwhelming salvo size
3. Multi-axis attacks to saturate defenses

---

### Example 3: Surprise Attack

**Scenario:** Same as Example 2, but Blue achieves tactical surprise

**Modified:** Red defensive power y = 2 (reduced reaction time)

**Damage to Red:**
```
ΔB = max(0, (4.0 × 2) - (2 × 2)) / 2.5
ΔB = max(0, 8 - 4) / 2.5
ΔB = 4 / 2.5 = 1.6 ships
```

**Result:** Blue mission-kills 1-2 Red destroyers in first salvo. Surprise provides decisive advantage.

---

## MULTI-SALVO ANALYSIS

For engagements extending beyond first salvo:

```
A₁ = A₀ - ΔA₀
B₁ = B₀ - ΔB₀
```

Then recalculate with new force levels. Continue until:
- One side eliminated
- Forces disengage
- Ammunition exhausted

---

## TACTICAL IMPLICATIONS

### Achieving Offensive Superiority
1. **Mass:** Concentrate more shooters
2. **Quality:** Use higher-Pk weapons (LRASM > Harpoon)
3. **Saturation:** Overwhelm defensive capacity
4. **Surprise:** Reduce enemy defensive effectiveness

### Defensive Considerations
1. **Layered defense:** SAMs + CIWS + soft-kill
2. **Distributed force:** Harder to concentrate fires against
3. **Mutual support:** Ships defend each other
4. **Terrain:** Use islands, weather for concealment

### Planning Factors
| Factor | Effect |
|--------|--------|
| EW degradation | β reduced by 20-40% |
| Targeting uncertainty | Pk reduced |
| Coordination failure | Offense reduced |
| Battle damage | Staying power matters more |

---

## LIMITATIONS

The Hughes Salvo Model is a simplified analytical tool. It does NOT account for:
- Timing and initiative
- Command and control
- Submarine threats
- Air attacks
- Cyber/EW effects
- Morale and training
- Logistics and sustainment

**Use for:** Initial planning estimates, force comparison, understanding relationships
**Do not use for:** Detailed predictions, operational planning without additional analysis

---

## REFERENCES

- Hughes, W.P. (1995). *Fleet Tactics: Theory and Practice*
- Hughes, W.P. & Girrier, R. (2018). *Fleet Tactics and Naval Operations, Third Edition*
- MCDP 1-0, Marine Corps Operations
- NDP 1, Naval Warfare

---

*This reference is UNCLASSIFIED and derived from publicly available academic and doctrinal sources.*
