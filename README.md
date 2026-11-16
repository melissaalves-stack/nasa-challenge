# ASTROKATU

**Behavioral health monitoring that travels with the crew.**

Team Pindorama · NASA Space Apps Challenge 2026 · Challenge: *Create Health Monitoring Software for Astronauts on Space Missions*

> *Katu* comes from Tupi and carries the sense of "good, well". AstroKatu is well-being for those who go farthest.

| | |
|---|---|
| **Live prototype** | LINK_VERCEL_AQUI |
| **30-second demo** | [`[media/AstroKatu_demo_30s.mp4](https://youtu.be/P_3E3ZMBsng)`] |
| **Backend** | [`backend/`](backend/README.md) |
| **Data pipeline and NASA data** | [`dados/`](dados/README.md) |
| **Research** | [`docs/research/`](docs/research) |

---

## The problem

On a Mars transit, a signal needs up to **22 minutes to reach Earth and 22 more to come back**. Behavioral health support for astronauts today relies on live conversations with specialists on the ground. With a 44-minute round trip, that model stops working exactly when a crew member needs it most.

Long missions also mean isolation, confinement, disrupted sleep and sustained workload. The crew ends up responsible for noticing changes in themselves.

## What AstroKatu does

AstroKatu runs on board and needs no link to Earth.

1. **Collect.** Wearable sleep and vital signs, a reaction-time tap test, and a three-question daily check-in led by Katu, a small companion character.
2. **Extract on the device.** A local language model turns the diary entry into a few structured features. The text is destroyed and never leaves the device.
3. **Compare with you.** Every value is scored against the crew member's own adaptive baseline, not a crew average.
4. **Apply readable rules.** Rules written in YAML look for trends that last several days. One bad night never raises an alert.
5. **A human decides.** Alerts carry their evidence to a flight surgeon's review queue. Suggested actions come from a curated library, and nothing is executed automatically.

AstroKatu supports decisions. It does not diagnose.

## Real NASA data

The data module applies the same idea to real astronaut data. `dados/nasa_osdr.py` downloads the blood panels of the **Inspiration4** crew from NASA's Open Science Data Repository, study [OSD-575](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575) (metabolic, immune and cardiovascular panels, before and after flight). It compares each crew member's post-flight values with **their own pre-flight baseline** and measures how long each change takes to return to normal.

The same module also simulates a 180-day mission with 7 crew members and hidden problems, then checks whether the detector finds them (`simulate.py`, `report.py`, `evaluate.py`).

## Design rules

- **Trend, not event.** Every rule needs several days of evidence.
- **Deterioration never becomes the new normal.** The baseline freezes while an alert is open and ignores high-workload days.
- **Privacy by design.** Only structured features are stored.
- **Explainable and auditable.** Each alert shows the numbers behind it, and every clinical review is logged.

## Try it

**Prototype (no install):** open `index.html` in a browser.

- *Crew* tab: complete a check-in and read the privacy receipt.
- *Mission simulator* bar: pick "Sustained deterioration" and press Auto-play.
- *Flight surgeon* tab: review the queue, the evidence and the audit log.

**Data pipeline:**

```bash
cd dados
pip install -r requirements.txt
python simulate.py           # create the mission data
python report.py --dia 46    # analyse and write one report per crew member
python evaluate.py           # check whether the hidden problems were found
python nasa_osdr.py          # download and analyse NASA OSD-575 (needs internet)
```

**Backend:**

```bash
cd backend
pip install -r requirements-dev.txt
python -m app.seed
uvicorn app.main:app --reload
```

Then open `http://localhost:8000/demo` or `http://localhost:8000/docs`.

**Deploy:** import this repository in Vercel with the framework preset "Other". `index.html` at the root is served as a static site.

## Repository map

| Path | Contents |
|---|---|
| `index.html` | Interactive prototype: companion, check-in, baseline, rules engine, review queue |
| `backend/` | FastAPI service: adaptive baseline, YAML rules engine, action library, scenario simulator, tests |
| `dados/` | Data pipeline: mission simulation, individual baseline, detection, evaluation, and analysis of NASA OSDR study OSD-575 |
| `docs/research/` | Literature review on mental health in spaceflight, the gap argument, problem mapping, references |
| `docs/architecture/` | Technical stack, hardware study, local inference test |
| `docs/pitch/` | Pitch scripts in English and Portuguese |
| `docs/submission_text.md` | Text submitted to the Space Apps project page |
| `media/` | Demo video |

## Technology

Python · pandas · NumPy · FastAPI · SQLite · YAML rules engine · pytest · Ollama with Gemma 3 1B (local inference) · HTML, CSS and JavaScript · Figma · Miro

## Current state

This is a hackathon prototype, and all data is synthetic.

- The baseline, rules engine, action library and scenarios are implemented in the backend and mirrored in the web prototype.
- Sensor readings are simulated.
- In the web prototype, the diary feature extractor is a keyword model standing in for Gemma 3 1B. Local inference with Gemma through Ollama was tested separately (see `docs/architecture/TESTE_INFERENCIA.md`).
- The rules still need clinical validation.

## Team Pindorama

| Member | Role |
|---|---|
| **Melissa Alves** | Team lead. Functional prototype, demo video, pitch, and research on computational references |
| **Joaquim Moreira** | Backend: API, adaptive baseline, rules engine, simulator |
| **Guilherme Aredes** | Data: mission simulation, detection and evaluation pipeline, analysis of NASA OSDR data |
| **Victoria Tambasco** | Visual prototype and interface design (Figma) |
| **Otavio Oliveira** | Infrastructure and technical architecture |
| **Isabela** | Health and behavioral science research |

## NASA resources

- NASA Open Science Data Repository, study OSD-575 (Inspiration4): https://osdr.nasa.gov/bio/repo/data/studies/OSD-575
- NASA Human Research Program: https://www.nasa.gov/hrp/
- Bell, S. et al. *Behavioral Health and Performance for Future Space Exploration 2024.* NASA Technical Reports Server: https://ntrs.nasa.gov/api/citations/20240014687/downloads/BHP%20for%20Future%20Space%20Exploration%202024.pdf
- NASA Twins Study (2019), as cited in the literature review.

The full reference list is in [`docs/research/saude_mental_em_missoes_espaciais.md`](docs/research/saude_mental_em_missoes_espaciais.md).

## Use of AI

We used AI assistants (Claude) to help write code, edit text and produce the demo video. The narration voice and the music in the video are AI-generated, and the video carries a visible notice. Gemma 3 1B is a component of the system design itself. The idea, the research direction and the design decisions are the team's.

## Disclaimer

AstroKatu is a decision-support prototype. It is not a medical device and does not provide diagnosis or treatment.
