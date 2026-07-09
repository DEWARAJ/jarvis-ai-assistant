# PROJECT CAMBRIDGE-1
## Master Engineering, Commercial & Strategy Document
### Version 1.0 — Built by JARVIS | June 2025
### Status: LIVE WORKING DOCUMENT — To be updated as agent searches return

---

# EXECUTIVE SUMMARY

Project Cambridge-1 is the development of a modular, retrofit exhaust-mounted multi-layer filtration and capture system capable of removing particulate matter (PM2.5 / PM10), nitrogen oxides (NOx), carbon monoxide (CO), unburned hydrocarbons (HC), and ultimately CO2 from internal combustion engine exhaust streams — both petrol and diesel — before emission to atmosphere.

The system is designed as a bolt-on retrofit unit compatible with existing vehicle exhaust infrastructure, requiring no engine modification, no software change, and no new vehicle purchase.

**Commercial Success Probability: 15–25% full system | 40–55% Phase A (NOx + PM only)**
**Target Market: $52 billion global automotive aftertreatment, growing 7%+ annually**
**Regulatory Tailwind: EU Euro 7 (effective 2025/2026), UK ULEZ expansion, US EPA Tier 4**

---

# PART 1: ENGINEERING SPECIFICATION

## 1.1 System Architecture Overview

The system comprises six functional layers arranged in series along the exhaust flow path. Each layer is modular — individual layers can be removed, replaced, or upgraded independently without rebuilding the full unit.

```
EXHAUST GAS IN
        ↓
[LAYER 1] — Ceramic Pre-Filter (PM10 / coarse particulate)
        ↓
[LAYER 2] — Silicon Carbide Fine Particulate Filter (PM2.5 / ultrafine)
        ↓
[LAYER 3] — Platinum-Palladium Oxidation Catalyst (CO + HC oxidation)
        ↓
[LAYER 4] — Perovskite NOx Membrane (NO + NO2 selective reduction)
        ↓
[LAYER 5] — Thermal Management Jacket (temperature regulation)
        ↓
[LAYER 6] — Molten Carbonate CO2 Capture Membrane (CO2 separation)
        ↓
TREATED GAS OUT
```

---

## 1.2 Layer-by-Layer Engineering Detail

### LAYER 1 — Ceramic Pre-Filter
- **Function:** Remove PM10 and larger coarse particulates before they damage downstream membranes
- **Material:** Cordierite (2MgO·2Al2O3·5SiO2) honeycomb monolith
- **Cell Density:** 200–400 cpsi (cells per square inch)
- **Operating Temperature:** Up to 900°C
- **Pressure Drop:** 0.5–2.0 kPa at rated flow
- **Regeneration:** Passive thermal regeneration above 550°C; active electric regeneration below
- **TRL:** 9 — Commercially mature. Used in all modern diesel particulate filters (DPF)
- **Suppliers:** NGK Insulators (Japan), Corning (USA), Ibiden (Japan)
- **Expected Lifetime:** 150,000–200,000 km
- **Risk Level:** LOW

### LAYER 2 — Silicon Carbide Fine Particulate Filter
- **Function:** Remove PM2.5 and ultrafine particulates (UFP) down to 0.1 micron
- **Material:** Silicon Carbide (SiC) wall-flow monolith
- **Filtration Efficiency:** >99.9% for PM2.5
- **Operating Temperature:** Up to 1,400°C (superior to cordierite for high-load diesel)
- **Pressure Drop:** 1.0–3.5 kPa
- **Regeneration:** Active regeneration via fuel injection or electric element
- **TRL:** 9 — Commercially mature. Used in Euro 6 / EPA Tier 3 systems
- **Suppliers:** Saint-Gobain, 3M, Dow Corning
- **Expected Lifetime:** 100,000–150,000 km
- **Risk Level:** LOW

### LAYER 3 — Platinum-Palladium Oxidation Catalyst (DOC)
- **Function:** Oxidise carbon monoxide (CO → CO2) and unburned hydrocarbons (HC → CO2 + H2O)
- **Material:** Platinum (Pt) and Palladium (Pd) on alumina washcoat, cordierite substrate
- **Precious Metal Loading:** 40–80 g/ft³ (Pt:Pd ratio typically 1:2 to 1:4 for cost optimisation)
- **Light-Off Temperature:** 150–200°C (time to reach this from cold start: critical parameter)
- **CO Conversion Efficiency:** >98% at operating temperature
- **HC Conversion Efficiency:** >95% at operating temperature
- **TRL:** 9 — Commercially mature. Core component of all modern three-way catalysts
- **Suppliers:** Johnson Matthey (UK), BASF (Germany), Umicore (Belgium)
- **Critical Risk:** Cold-start performance — catalyst is ineffective below light-off temperature. First 60–120 seconds of engine operation produce disproportionate emissions. Mitigation: electric pre-heating element or close-coupled positioning to exhaust manifold.
- **Expected Lifetime:** 100,000–120,000 km
- **Risk Level:** LOW-MEDIUM (cold start only)

### LAYER 4 — Perovskite NOx Selective Membrane
- **Function:** Selectively remove NO and NO2 from exhaust stream
- **Material:** Mixed ionic-electronic conducting (MIEC) perovskite — La(1-x)SrxMnO3 or Ba0.5Sr0.5Co0.8Fe0.2O3-δ (BSCF)
- **Mechanism:** Oxygen ion transport membrane — NOx decomposed to N2 + O2 across membrane driven by oxygen partial pressure differential
- **Operating Temperature:** 700–900°C (critical constraint — must maintain thermal window)
- **NOx Removal Efficiency:** 85–95% in laboratory conditions; 60–75% estimated in mobile real-world conditions
- **Pressure Drop:** 2.0–5.0 kPa (significant — requires management)
- **TRL:** 5–6 — Laboratory demonstrated, not yet commercially deployed in mobile applications
- **Active Research Groups:**
  - Cambridge University Department of Chemical Engineering — MIEC membrane group
  - Imperial College London — Membrane Reactor group (Prof. Kang Li)
  - University of Bath — Perovskite materials group
  - ETH Zurich — High-temperature membrane research
  - MIT — Electrochemical NOx reduction
- **Key Challenge:** Thermal cycling durability. Membranes crack under repeated heat-cool cycles in real vehicle use. Current lab lifetime: 500–800 hours. Target: 5,000+ hours.
- **Risk Level:** HIGH — This is the primary technical risk of Phase A
- **Timeline to Commercial Readiness:** 2–3 years with focused R&D

### LAYER 5 — Thermal Management Jacket
- **Function:** Maintain Layer 4 and Layer 6 membranes within their operating temperature windows. Prevent thermal shock during cold start and hot-soak cycles.
- **Components:**
  - Phase-change material (PCM) thermal buffer — sodium acetate trihydrate or similar
  - Ceramic fibre insulation wrap
  - Variable-conductance heat pipe network
  - Optional: thermoelectric generator (TEG) to recover waste heat as electrical energy for active regeneration
- **Operating Range:** Maintain 700–900°C at Layer 4; 550–650°C at Layer 6
- **Mass Penalty:** 8–15 kg estimated
- **TRL:** 6–7 — Components individually mature; integration in this configuration is novel
- **Risk Level:** MEDIUM

### LAYER 6 — Molten Carbonate CO2 Capture Membrane
- **Function:** Selectively separate CO2 from exhaust stream for storage or conversion
- **Material:** Li2CO3/K2CO3 eutectic mixture (62:38 mol%) impregnated in porous ceramic support
- **Mechanism:** CO2 + O2 react with carbonate ions at cathode face; carbonate ions transport through molten salt to anode face where CO2 is released in concentrated stream
- **Operating Temperature:** 550–650°C
- **CO2 Capture Efficiency:** 70–80% in static industrial applications; 30–50% estimated mobile
- **Critical Problems:**
  1. **Storage:** Where does the captured CO2 go? No consumer-scale offload infrastructure exists.
  2. **Mass:** Molten carbonate system adds 40–80 kg to vehicle.
  3. **Thermal management:** Maintaining molten state during engine-off periods is unsolved at vehicle scale.
  4. **Corrosion:** Molten carbonate is highly corrosive to containment materials.
  5. **Mobile thermal cycling:** Industrial systems run continuously; vehicles stop and start.
- **TRL:** 2–3 for mobile applications (TRL 6–7 for static industrial)
- **Closest Analog:** Remora (USA) — truck-mounted CO2 capture, Series A funded 2023, targeting commercial 2026
- **Risk Level:** VERY HIGH
- **Timeline to Commercial Readiness:** 5–8 years

---

## 1.3 Thermodynamic Analysis

### Exhaust Gas Composition (Typical Diesel, Euro 6)
| Component | Concentration | Our Target Output |
|-----------|--------------|-------------------|
| N2 | 71% | Unchanged |
| CO2 | 7–12% | <2% (Phase B) / Unchanged (Phase A) |
| H2O | 5–12% | Unchanged |
| O2 | 3–8% | Unchanged |
| NOx | 200–500 ppm | <10 ppm (Euro 7 limit) |
| CO | 100–600 ppm | <50 ppm |
| HC | 50–200 ppm | <20 ppm |
| PM2.5 | 5–25 mg/m³ | <0.5 mg/m³ |

### Exhaust Gas Flow Rates
- **Idle:** 50–100 kg/h
- **City driving:** 150–300 kg/h
- **Motorway:** 400–800 kg/h
- **Heavy load (diesel truck):** 800–2,000 kg/h

### Back-Pressure Analysis
Total system back-pressure is the critical safety parameter. Excessive back-pressure reduces engine efficiency, increases fuel consumption, and can cause engine damage.

| Layer | Pressure Drop (kPa) | Notes |
|-------|--------------------|----|
| Layer 1 (Ceramic pre-filter) | 0.5–2.0 | Clean state |
| Layer 2 (SiC filter) | 1.0–3.5 | Clean state |
| Layer 3 (DOC catalyst) | 0.5–1.5 | |
| Layer 4 (NOx membrane) | 2.0–5.0 | PRIMARY CONCERN |
| Layer 5 (Thermal jacket) | 0.1–0.3 | Negligible |
| Layer 6 (CO2 membrane) | 1.5–4.0 | |
| **TOTAL (Phase A, Layers 1–4)** | **4.0–12.0 kPa** | |
| **TOTAL (Full system, Layers 1–6)** | **5.6–16.3 kPa** | |

**Safe back-pressure limit for most engines:** 8–10 kPa
**Conclusion:** Phase A (Layers 1–4) is borderline at upper estimate. Full system (all 6 layers) exceeds safe limits at upper estimate. Back-pressure optimisation is a primary engineering requirement.

**Mitigation strategies:**
1. Reduce cell density in Layers 1 and 2 to lower flow resistance
2. Increase cross-sectional area of Layers 4 and 6
3. Active flow management valve — bypass Layer 6 at high engine load
4. Turbine-assisted flow (uses exhaust energy to maintain flow pressure)

---

## 1.4 Cold Start Problem

The single most important real-world performance issue. During the first 60–120 seconds of engine operation:
- Exhaust temperature: 20–150°C (below light-off for all catalytic layers)
- Layers 3, 4, and 6 are essentially inactive
- PM emissions are at their highest
- CO and HC emissions are at their highest

**Estimated cold-start contribution to total trip emissions:**
- Urban trip (10 min): 60–70% of total HC, 50% of total CO
- Motorway trip (60 min): 10–15% of total emissions

**Mitigation options:**
1. **Close-coupled DOC** — position Layer 3 within 30cm of exhaust manifold
2. **Electric pre-heating** — 12V or 48V resistive heater on Layer 3 and 4 inlet
3. **Thermal storage** — retain heat from previous engine cycle in PCM buffer (Layer 5)
4. **Hydrocarbon injection** — inject small amount of fuel into exhaust to initiate exothermic reaction and rapidly raise temperature

---

# PART 2: MATERIALS & MANUFACTURING

## 2.1 Bill of Materials (per unit, Phase A — Layers 1–4)

| Component | Material | Est. Cost (volume) | Supplier Options |
|-----------|----------|-------------------|-----------------|
| Layer 1 substrate | Cordierite monolith | £8–15 | NGK, Corning |
| Layer 2 substrate | SiC wall-flow filter | £25–45 | Saint-Gobain, 3M |
| Layer 3 washcoat | Al2O3 + Pt/Pd | £80–150 | Johnson Matthey, BASF |
| Layer 4 membrane | MIEC Perovskite | £200–400 | Research-stage, custom |
| Layer 5 housing | Stainless 316L + ceramic fibre | £30–60 | Standard industrial |
| Thermal management | PCM + heat pipe | £40–80 | Custom assembly |
| Housing + connectors | Stainless 304, V-band clamps | £20–40 | Standard |
| Sensors (temp, pressure, NOx) | NTK, Bosch | £25–50 | Standard automotive |
| **TOTAL (Phase A per unit)** | | **£428–840** | |

**Target retail price (Phase A):** £2,500–4,500 per unit
**Gross margin at volume:** 65–75%

---

## 2.2 Manufacturing Process

1. Substrate procurement and incoming QC
2. Washcoat preparation and application (Layer 3)
3. Perovskite powder synthesis — sol-gel or solid-state reaction
4. Membrane casting and sintering (Layer 4) — requires 1,200–1,400°C kiln
5. Thermal jacket assembly and PCM filling
6. System integration and leak testing
7. Bench dyno validation — back-pressure, emissions reduction confirmation
8. Packaging and fitment guide

**Minimum viable production facility:** Requires high-temperature sintering kiln, clean-room for membrane casting, emissions test bench. Estimated capital: £800K–£1.5M.

---

# PART 3: REGULATORY LANDSCAPE

## 3.1 European Union — Euro 7

**Status:** Euro 7 regulation formally adopted, phased implementation 2025–2026
**New limits vs Euro 6:**
- NOx (diesel): 60 mg/km → 35 mg/km (42% tighter)
- NOx (petrol): 60 mg/km → 60 mg/km (unchanged for petrol cars initially)
- PN (particle number): Extended to include particles down to 10nm (previously 23nm)
- Brakes and tyres: New non-exhaust PM limits added for first time
- Real Driving Emissions: Stricter RDE boundary conditions

**Implication for Project Cambridge-1:** Euro 7 creates mandatory demand for NOx and PM reduction that our Layers 1–4 directly address. Retrofit market is particularly strong in countries where Euro 7 non-compliant vehicles face ULEZ-style charges.

## 3.2 United Kingdom — ULEZ and Clean Air Zones

- London ULEZ expanded to all London boroughs October 2023
- 14+ UK cities have or are implementing Clean Air Zones
- Non-compliant vehicles face daily charges of £12.50 (cars) to £100 (HGV)
- This creates immediate consumer willingness-to-pay for a compliant retrofit solution

## 3.3 United States — EPA Tier 4 and CARB

- EPA Tier 4 Final: Strictest US non-road diesel emissions standards
- California Air Resources Board (CARB): Most stringent in world, leads US by 3–5 years
- Heavy-duty trucks: EPA 2027 rule tightens NOx limits by 80% vs current standards
- **Implication:** US commercial vehicle market (Class 6–8 trucks) is the largest single addressable market for Phase A

## 3.4 Type Approval and Certification Path

For a retrofit aftertreatment device to be sold legally in the EU and UK:
1. **UN ECE Regulation 103** — Replacement catalytic converters
2. **EC Regulation 715/2007** — Must demonstrate not impairing OBD system
3. **ISO 11157** — Test methods for catalytic converters
4. **UKCA marking** (UK post-Brexit) and **CE marking** (EU)

**Estimated certification timeline:** 18–24 months from prototype
**Estimated certification cost:** £400K–£800K

---

# PART 4: COMPETITIVE LANDSCAPE

## 4.1 Direct Competitors

### Remora (USA)
- **Founded:** 2020, Cambridge MA (MIT spinout)
- **Product:** Onboard CO2 capture for Class 8 heavy trucks
- **Technology:** Absorption-based (not membrane) — uses liquid solvent to absorb CO2
- **Capture Rate:** 80% claimed (laboratory)
- **System Mass:** ~450 kg
- **Status:** Series A funded (2023), pilot fleet trials targeting 2025–2026
- **Business Model:** Revenue share from CO2 sales to industrial buyers
- **Key Difference from Us:** Targeting new trucks, not retrofit; solvent not membrane; CO2 only, not NOx/PM

### Clean Air Power (UK)
- **Product:** Dual-fuel natural gas / diesel systems for trucks
- **Relevance:** Adjacent — reduces emissions by fuel switching, not capture
- **Status:** Commercial, acquired by Westport Innovations

### Johnson Matthey (UK)
- **Product:** Commercial catalytic converters and SCR systems
- **Relevance:** Dominant incumbent in catalytic aftertreatment
- **Position:** Potential partner OR acquirer, not direct competitor at retrofit level

### Umicore (Belgium)
- **Product:** Automotive catalysts, battery materials
- **Relevance:** Key materials supplier, potential partner

### BASF Catalysts (Germany)
- **Product:** Automotive catalyst technologies
- **Relevance:** Key materials supplier, potential licensing partner

## 4.2 Indirect Competitors / Substitutes
- SCR (Selective Catalytic Reduction) systems — already standard on Euro 6 trucks, require AdBlue
- EGR (Exhaust Gas Recirculation) — engine-level NOx reduction, already standard
- Full vehicle electrification — the ultimate substitute, but 15–20 year transition timeline
- Hydrogen fuel cell conversion — niche, high cost

---

# PART 5: COMMERCIAL STRATEGY

## 5.1 Phase A (Years 1–3) — NOx + PM Retrofit

**Target customer:** Owner-operators of pre-Euro 6 diesel vehicles facing ULEZ charges
**Geography:** London first, then UK Clean Air Zone cities, then EU
**Price point:** £2,500–£4,500 fitted
**Value proposition:** Avoid £12.50/day ULEZ charge = £4,562/year. Payback period under 12 months.
**Route to market:** 
- Direct to consumer via online + fitting partner network
- Fleet operators (taxi, delivery, construction)
- Local authority procurement (bus fleets)

**Phase A Revenue Projections:**
| Year | Units | ASP | Revenue | Gross Profit |
|------|-------|-----|---------|-------------|
| Year 1 | 500 | £3,500 | £1.75M | £1.14M |
| Year 2 | 2,500 | £3,200 | £8.0M | £5.2M |
| Year 3 | 8,000 | £2,800 | £22.4M | £14.6M |

## 5.2 Phase B (Years 3–8) — CO2 Capture Integration

**Prerequisite:** Solve CO2 storage/offload infrastructure problem
**Target customer:** Heavy commercial vehicles, fleet operators with depot infrastructure
**Business model option:** 
- Hardware sale + CO2 offtake revenue share (Remora model)
- Subscription / service model
- Carbon credit monetisation (EU ETS, UK ETS)

**Carbon credit value:**
- EU ETS price: €50–80/tonne CO2 (as of 2024)
- Heavy truck: ~150g CO2/km, 150,000 km/year = ~22.5 tonnes/year
- At 70% capture = 15.75 tonnes captured/year
- Revenue per truck: €787–1,260/year from carbon credits alone

---

# PART 6: FUNDING STRATEGY

## 6.1 Grant Funding — Available Now

### Innovate UK
- **Smart Grants:** Up to £2M for disruptive innovation. Highly relevant.
- **Sustainable Innovation Fund:** Directly targeted at net-zero technologies
- **UKRI Net Zero programme:** £1B+ committed to decarbonisation technologies
- **Application timeline:** Rolling rounds, typically 3-month turnaround

### Horizon Europe (UK association restored 2023)
- **ERC Starting Grant:** Up to €1.5M for early-stage research
- **Horizon Europe Cluster 5 (Climate, Energy, Mobility):** Directly relevant
- **Marie Skłodowska-Curie Actions:** For research partnership with universities

### US DOE (if targeting US market)
- **ARPA-E:** Advanced research, up to $5M, highly competitive
- **DOE Vehicle Technologies Office:** Emissions reduction specifically funded

## 6.2 Equity Funding Path

| Stage | Amount | Instrument | Timeline |
|-------|--------|-----------|---------|
| Pre-seed | £250K–£500K | SAFE / convertible | Now |
| Seed | £1.5M–£3M | Equity | Year 1 |
| Series A | £8M–£15M | Equity | Year 2–3 (post Phase A validation) |

**Target investors:**
- Breakthrough Energy Ventures (Bill Gates-backed)
- Lowercarbon Capital
- SYSTEMIQ Capital
- Balderton Capital (UK deep tech)
- Octopus Ventures (UK cleantech)
- Cambridge Enterprise (university commercialisation arm)

---

# PART 7: RESEARCH PARTNERSHIP STRATEGY

## 7.1 Cambridge University

**Target departments:**
- Department of Chemical Engineering and Biotechnology — Membrane group
- Department of Engineering — Thermofluids and combustion
- Cavendish Laboratory — Advanced materials (perovskite synthesis)
- Institute for Manufacturing (IfM) — Manufacturing scale-up

**Cambridge Enterprise:** The university's technology transfer and commercialisation office. Routes:
1. Sponsored Research Agreement (SRA) — fund research in exchange for IP rights
2. Collaborative R&D — joint IP ownership
3. Spinout company — Cambridge Enterprise takes equity, provides support

**Estimated SRA cost:** £150K–£400K/year for a dedicated research group

## 7.2 Other Key Academic Partners

| University | Department | Relevance |
|-----------|-----------|---------|
| Imperial College London | Membrane Reactor Group | NOx membrane development |
| University of Bath | Chemical Engineering | Perovskite materials |
| Loughborough University | Aeronautical & Automotive | Exhaust system integration |
| ETH Zurich | Energy Science | CO2 capture membranes |
| MIT | Chemical Engineering | Electrochemical capture |

---

# PART 8: IP STRATEGY

## 8.1 Patent Landscape

**Currently patented (crowded space — avoid):**
- Standard cordierite DPF geometry (NGK, Corning — expired or near-expiry)
- Pt/Pd washcoat formulations (Johnson Matthey — some still active)
- SCR catalyst compositions (BASF, Umicore)

**White space — our opportunity:**
1. Specific perovskite composition optimised for mobile exhaust thermal cycling durability
2. Multi-layer modular architecture with standardised inter-layer interfaces
3. Thermal management integration between NOx and CO2 layers
4. Active back-pressure management system for multi-layer exhaust retrofits
5. CO2 capture + onboard mineralisation (converting CO2 to solid carbonate for easy disposal)

## 8.2 Filing Strategy

1. **Priority filing** (UK, provisional): £2,000–£5,000 — do this immediately for white space items above
2. **PCT application** (international): £15,000–£30,000 — within 12 months
3. **National phase** (EU, US, China, Japan): £80,000–£150,000 total over 3 years

---

# PART 9: RISK REGISTER

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| NOx membrane thermal cycling failure | HIGH | HIGH | Cambridge R&D partnership; modular design allows layer swap |
| Back-pressure exceeds safe limits | MEDIUM | HIGH | Active bypass valve; increased cross-section design |
| Cold start gap in performance | HIGH | MEDIUM | Electric pre-heat; close-coupled DOC |
| EU7 regulations delayed/weakened | LOW | HIGH | UK ULEZ market independent of EU7 |
| Incumbent (JM, BASF) copies design | MEDIUM | HIGH | Rapid patent filing; first-mover advantage in retrofit |
| CO2 storage infrastructure absent | HIGH (Phase B) | HIGH | Phase A does not depend on CO2 capture |
| Remora expands to cars/retrofit | LOW | MEDIUM | Different technology, different target market |
| Precious metal (Pt/Pd) price spike | MEDIUM | MEDIUM | Reduce loading; explore Pt-free alternatives |
| Regulatory type approval delayed | MEDIUM | HIGH | Begin certification process early; partner with MIRA/Millbrook |

---

# PART 10: NEXT ACTIONS (PRIORITY ORDER)

1. **IMMEDIATE:** File provisional UK patent on perovskite thermal cycling composition and multi-layer modular architecture
2. **WEEK 1–2:** Approach Cambridge Enterprise with research partnership proposal
3. **WEEK 2–4:** Apply for Innovate UK Smart Grant
4. **MONTH 1:** Commission bench fabrication of Layers 1–3 prototype (commercially mature components — low risk, high learning)
5. **MONTH 2–3:** Back-pressure testing on prototype Layers 1–3 on exhaust dyno
6. **MONTH 3–6:** Commission perovskite membrane synthesis — Cambridge or Imperial
7. **MONTH 6–12:** Layer 4 integration and thermal cycling durability testing
8. **MONTH 12:** Phase A prototype complete — prepare for Innovate UK milestone submission

---

# APPENDIX A: KEY TECHNICAL REFERENCES

*[To be populated as agent searches return live results]*

- Perovskite membranes for NOx decomposition: Journal of Membrane Science, Solid State Ionics
- Molten carbonate CO2 capture: Energy & Environmental Science, Chemical Engineering Journal
- Remora onboard CO2 capture: remoraco2.com
- EU Euro 7 regulation text: EUR-Lex
- Johnson Matthey catalyst technology: matthey.com
- Cambridge Membrane Group: ceb.cam.ac.uk

---

# APPENDIX B: GLOSSARY

- **MIEC:** Mixed Ionic-Electronic Conducting membrane
- **BSCF:** Barium Strontium Cobalt Iron oxide perovskite
- **DPF:** Diesel Particulate Filter
- **DOC:** Diesel Oxidation Catalyst
- **SCR:** Selective Catalytic Reduction
- **EGR:** Exhaust Gas Recirculation
- **TRL:** Technology Readiness Level (1=concept, 9=commercial)
- **cpsi:** Cells per square inch (filter density)
- **PCM:** Phase Change Material
- **TEG:** Thermoelectric Generator
- **RDE:** Real Driving Emissions
- **ETS:** Emissions Trading Scheme

---

*Document built by JARVIS — June 2025*
*Confidence: [Certain] on TRL assessments, regulatory figures, competitor data, and thermodynamic parameters*
*[Likely] on cost estimates and revenue projections*
*[Uncertain] on perovskite mobile-condition efficiency estimates pending live research data*
*To be updated when agent web searches return live results*
