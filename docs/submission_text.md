# AstroKatu — NASA Space Apps Challenge 2026
# Team Pindorama — Submission Text
# Challenge: Create Health Monitoring Software for Astronauts on Space Missions

---

## PROJECT NAME
AstroKatu

---

## HIGH-LEVEL SUMMARY

AstroKatu is an autonomous behavioral health monitoring system designed for astronauts on long-duration deep-space missions. On a Mars mission, communication delays of up to 44 minutes (22 each way) make real-time mental health support from Earth physically impossible — NASA's current Behavioral Health Program (BHP) depends entirely on live calls with Earth, which breaks down at interplanetary distances.

AstroKatu solves this by running entirely on-device, with no Earth connection required. It monitors behavioral health indicators passively — sleep quality, physiological signals, and daily self-reports collected through a friendly companion interface — and builds an adaptive individual baseline for each astronaut, detecting trends rather than isolated events. When a persistent pattern emerges, the system flags it for human review, never acting autonomously on mental health decisions.

---

## DETAILED PROJECT DESCRIPTION

### What exactly does it do?

AstroKatu monitors astronaut behavioral health across three data streams:
- **Physiological signals**: heart rate, HRV, SpO2, skin conductance, sleep duration and quality, body temperature, physical activity
- **Environmental context**: CO₂ concentration, noise levels, ambient conditions — to contextualize physiological changes
- **Daily self-reports**: collected through a Tamagotchi-style companion that asks 3 natural questions per day, replacing dry forms with a human interface

All text from diary entries is processed by a local AI (Gemma 3 1B via Ollama) that extracts only structured features — the raw text is destroyed on-device. The system stores features, not content.

### How does it work?

Data flows through five layers:

```
Sensors/Wearables → Local processing → Individual adaptive baseline
                                              ↓
                              Explainable rules engine (YAML)
                                              ↓
                    Alert levels: info · watch · review_required
                                              ↓
                    Clinical dashboard — human always in the loop
```

The core innovation is the **adaptive individual baseline**: instead of comparing astronauts to population averages, the system learns each person's normal across sleep, mood, stress, fatigue, and cognitive performance. A single bad night or one sad entry never triggers an alert — only persistent multi-day trends do.

### What benefits does it have?

1. **Works at Mars distance** — fully autonomous, no Earth connection required
2. **Privacy-preserving** — raw diary text never leaves the device; only structured features are stored
3. **Explainable** — every alert shows the evidence that triggered it; no black boxes
4. **Human in the loop** — the system flags, never diagnoses or acts; a clinician always makes the call
5. **Non-intrusive** — passive monitoring + 3 natural questions per day, minimizing cognitive burden on the astronaut at their most vulnerable moments

### What do we hope to achieve?

A complete on-device behavioral health monitoring system that could be integrated into NASA missions by 2035 — the current Mars launch window. We also aim to demonstrate that privacy-preserving AI inference at the edge is viable for safety-critical healthcare applications.

### What tools, coding languages, hardware, or software did you use?

| Component | Technology |
|---|---|
| Backend / API | Python, FastAPI |
| Database | SQLite |
| Rules engine | YAML-defined deterministic rules |
| Local AI inference | Ollama + Gemma 3 1B |
| Baseline & analytics | Custom Python (longitudinal series analysis) |
| Simulator | Python (synthetic data generation for testing) |
| Interactive web prototype | HTML, CSS, JavaScript (companion check-in, baseline, rules engine, flight surgeon queue), hosted on GitHub Pages |
| Prototyping | Figma |
| Architecture planning | Miro |
| Version control | Git / GitHub |

---

## USE OF SUPER INTELLIGENCE (SI) TOOLS

Yes. We used large language models (Claude) as development tools to accelerate ideation, drafting technical documentation, writing backend code, and structuring the submission. The core system logic — rules engine, baseline algorithm, privacy architecture — was designed and validated by the team. No SI-generated content appears in the product demo without team review.

We also use a local LLM (Gemma 3 1B via Ollama) as a component of the system itself, for on-device feature extraction from astronaut diary entries.

---

## NASA DATA AND RESOURCES

- **NASA Behavioral Health Program (BHP)**: Our solution directly addresses the gap identified by NASA's BHP — the dependency on real-time Earth communication that makes the program non-functional beyond low Earth orbit.
- **NASA Twin Study (Scott Kelly)**: We referenced findings from NASA's Year in Space study to ground our understanding of psychological stressors in long-duration missions.
- **NASA Human Research Program (HRP)**: The HRP's identified risks — behavioral conditions, psychiatric disorders, and team dynamics — defined the monitoring targets our system addresses.

---

## SPACE AGENCY PARTNER DATA AND OTHER REFERENCES

- NASA Human Research Program — Evidence Reports on Behavioral Health Risks
- NASA BHP Program documentation
- Scott Kelly, *Endurance* (Year in Space psychological documentation)
- FastAPI (open source, MIT license)
- Ollama (open source, MIT license)
- Gemma 3 1B by Google (open weights)
- SQLite (public domain)
- React (MIT license)
