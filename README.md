# NIK Copilot: one question, two legacy government systems

**Track 3: A copilot that works across two systems.** Vibe-a-thon 2026 (2nd Brain Labs × Geek Room), Team HackRasaz.

Live: **https://mazharrasyad.tech/nik-copilot**

## The problem

In Indonesia the same family lives in many government databases that were never designed to talk to each other. A district health office typically runs:

- **SIPOS Posyandu**: toddler health posts. Toddlers are registered under the **mother's NIK** (16-digit national ID), villages are stored as **free-text names**, and monthly weighings give each child a nutrition status (normal, gizi kurang, gizi buruk, stunting).
- **SI-DBD**: dengue fever surveillance. Cases are recorded by the **patient's NIK** and by the **official village code** (`kode_kelurahan`), with weekly larva inspections.

A real question for the health office, such as *"which malnourished toddlers have a mother who currently has dengue?"*, needs both systems. Today someone exports two spreadsheets and matches them by hand. Rewriting or merging the systems takes months, and nobody owns that budget.

## The solution

Leave both systems as they are. **Synapse turns each existing API into an MCP server**, and one agent uses both:

```
SIPOS Posyandu (FastAPI) --synapse build--> MCP server A ─┐
                                                          ├─> NIK Copilot agent (LLM + tool calling) ─> web UI
SI-DBD (FastAPI)         --synapse build--> MCP server B ─┘
```

The agent joins **people by NIK** (`nik_ibu` in SIPOS = `nik` in SI-DBD) and **villages by code** (SIPOS's village name is mapped to SI-DBD's `kode_kelurahan` through `list_wilayah`). Every answer shows which tool calls it made and which system each fact came from.

Questions it answers (each needs both systems):

1. Which at-risk toddlers have a mother who is an active dengue case?
2. Which villages have both at-risk toddlers and active dengue cases, with counts per village?
3. For villages with active dengue, how many toddlers are registered and what is the latest larva-free index?
4. *(after the live update)* When is fogging scheduled in villages that have at-risk toddlers?

## How Synapse is used

Each legacy codebase was made agent-ready with **no changes to its code**:

```bash
cd systems/sipos-posyandu
synapse build --local --auto --endpoints "GET /api/posyandu,GET /api/balita,GET /api/balita-berisiko,GET /api/balita/{balita_id},GET /api/balita/{balita_id}/penimbangan,GET /api/ibu/{nik_ibu}/balita"

cd ../si-dbd
synapse build --local --auto --endpoints "GET /api/wilayah,GET /api/kasus,GET /api/kasus/nik/{nik},GET /api/kasus/{kasus_id},GET /api/jentik"
```

Synapse detected the FastAPI routes and wrote `synapse_auto_server.py` in each project: 6 tools for SIPOS and 5 for SI-DBD.

**Which endpoints are exposed, and why:**

| Exposed | Why the agent needs it |
|---|---|
| SIPOS `list_balita_berisiko`, `list_balita`, `get_balita_by_ibu`, `get_penimbangan` | Find at-risk children, their mothers' NIK and the evidence (weighing history) |
| SIPOS `list_posyandu`, `get_balita` | Village and health-post context, single-record lookups |
| SI-DBD `get_kasus_by_nik`, `list_kasus` | Check a person by NIK; list active cases per village |
| SI-DBD `list_wilayah` | The bridge: village names ↔ official codes |
| SI-DBD `list_jentik` | Larva-free index (ABJ) as the vector-risk signal |
| **Not exposed:** `/health` | Infrastructure only, not useful for the agent and only adds noise |

Both systems are read-only on purpose: the copilot advises, it never writes to clinical records.

### Live update with `synapse build --discover`

SI-DBD already stores fogging (insecticide spraying) schedules, but no API exposes them. In the demo we add one endpoint to SI-DBD, `GET /api/fogging`, then run:

```bash
cd systems/si-dbd
synapse build --local --auto --discover --endpoints "GET /api/wilayah,GET /api/kasus,GET /api/kasus/nik/{nik},GET /api/kasus/{kasus_id},GET /api/jentik,GET /api/fogging"
```

The agent opens fresh MCP sessions and lists tools on every question, and it always uses the newest file Synapse generated. The next question can use `list_fogging` straight away, with no restart and no client config change.

## Run it

Needs Docker, plus an OpenAI-compatible LLM key with tool calling (Groq free tier by default).

```bash
cp .env.example .env      # set GROQ_API_KEY
docker compose up -d --build
# open http://127.0.0.1:3180
```

Locally without Docker: run each system with `uvicorn app:app --port 8101|8102`, then `cd agent && uvicorn server:app --port 8103`.

## Repository

- `systems/sipos-posyandu/`, `systems/si-dbd/`: the two legacy FastAPI apps, each with its Synapse output (`synapse_auto_server.py`, `.synapse/`)
- `agent/`: the copilot (`agent.py` MCP client + tool-calling loop; `server.py` + `index.html` web UI)
- `tools/make_data.py`: deterministic synthetic population shared by both systems; `tools/expected.py`: ground-truth answers used to check the agent

All people, NIKs and records are **synthetic**. Village codes follow the official format but the data is fictional.
