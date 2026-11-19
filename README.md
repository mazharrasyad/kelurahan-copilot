# Kelurahan Copilot: one question, two legacy systems, zero personal data

**Track 3: A copilot that works across two systems.** Vibe-a-thon 2026 (2nd Brain Labs × Geek Room), Team HackRasaz.

Live: **https://mazharrasyad.tech/kelurahan-copilot**

## The problem

A district health office in Indonesia has to decide every week **which villages (kelurahan) need action first**: home visits for malnourished toddlers, larva eradication, fogging. The evidence sits in two legacy systems that were never built to talk to each other:

- **SIPOS Posyandu**: toddler health posts. Monthly weighings give each child a nutrition status (normal, gizi kurang, gizi buruk, stunting). Villages are stored as **free-text names**.
- **SI-DBD**: dengue fever surveillance. Cases and weekly larva inspections are recorded per **official village code** (`kode_kelurahan`).

Today a planner exports two spreadsheets, fixes village names by hand and builds the picture in Excel. Merging the systems would take months.

## The solution

Leave both systems as they are. **Synapse turns each existing API into an MCP server**, and one agent uses both:

```
SIPOS Posyandu (FastAPI) --synapse build--> MCP server A ─┐
                                                          ├─> Kelurahan Copilot (LLM + tool calling) ─> web UI
SI-DBD (FastAPI)         --synapse build--> MCP server B ─┘
```

The agent bridges the two systems by mapping SIPOS village names to SI-DBD village codes (`list_wilayah`), then combines nutrition risk, dengue activity and larva-free index per village. Every answer shows the MCP tool calls it made and which system each fact came from.

Questions it answers (each needs both systems):

1. Which villages should the health office prioritise this week? (share of at-risk toddlers + active dengue cases)
2. In villages whose latest larva-free index (ABJ) is below 95%, how many toddlers are at risk and how many dengue cases are active?
3. Is Tegal Parang getting worse? (monthly at-risk trend vs weekly new dengue cases)
4. *(after the live update)* When is fogging scheduled for the priority villages, and does any priority village have no fogging planned?

## Privacy by design (UU PDP)

Health data and national ID numbers (NIK) are *specific personal data* under Indonesia's Personal Data Protection Law (UU 27/2022). The copilot does not need them, so it never gets them:

- **Only village-level recap endpoints are exposed through Synapse.** Record-level routes (`/api/balita`, `/api/kasus`) exist for each agency's own staff, but are deliberately left out of the MCP servers (data minimisation).
- The LLM only ever sees counts and percentages per village, never a person.
- The demo data is synthetic and de-identified: random internal ids, no NIK, names or addresses.

## How Synapse is used

Each legacy codebase was made agent-ready with **no changes to its code**:

```bash
cd systems/sipos-posyandu
synapse build --local --auto --endpoints "GET /api/posyandu,GET /api/rekap/gizi,GET /api/rekap/gizi/tren,GET /api/rekap/penimbangan"

cd ../si-dbd
synapse build --local --auto --endpoints "GET /api/wilayah,GET /api/rekap/kasus,GET /api/rekap/kasus/mingguan,GET /api/jentik"
```

Synapse detected the FastAPI routes (7 and 6) and wrote `synapse_auto_server.py` in each project with the 4 + 4 tools we selected. Local Auto mode generates passthrough tools, so no code leaves the machine and no model call is needed to build them.

**Which endpoints are exposed, and why:**

| System | Exposed tool | Why the agent needs it |
|---|---|---|
| SIPOS | `rekap_gizi` | At-risk toddlers per village (latest weighing): the nutrition signal |
| SIPOS | `rekap_gizi_tren` | Monthly trend, to tell "getting worse" from "always high" |
| SIPOS | `rekap_penimbangan` | Attendance (D/S): low attendance means the nutrition data is incomplete |
| SIPOS | `list_posyandu` | Which health post serves which village, for the action plan |
| SI-DBD | `list_wilayah` | **The bridge**: village names ↔ official codes |
| SI-DBD | `rekap_kasus` | Active and new (14-day) dengue cases per village: the outbreak signal |
| SI-DBD | `rekap_kasus_mingguan` | Weekly new cases, for trends |
| SI-DBD | `list_jentik` | Larva-free index (ABJ, target ≥ 95%): the vector-risk signal |
| both | *not exposed:* `/api/balita`, `/api/balita/{id}/penimbangan`, `/api/kasus`, `/health` | Record-level personal health data (UU PDP) and infrastructure noise |

All exposed tools are read-only: the copilot advises, it never changes clinical records.

### Live update with `synapse build --discover`

SI-DBD already stores fogging (insecticide spraying) schedules, but no API exposes them. In the demo we add one endpoint, `GET /api/fogging`, to SI-DBD and rebuild:

```bash
cd systems/si-dbd
synapse build --local --auto --discover --endpoints "GET /api/wilayah,GET /api/rekap/kasus,GET /api/rekap/kasus/mingguan,GET /api/jentik,GET /api/fogging"
```

The agent opens fresh MCP sessions and lists tools on every question, and always uses the newest server file Synapse generated. The next question can use `list_fogging` straight away, with no restart and no client config change.

## Run it

Needs Docker, plus an OpenAI-compatible LLM key with tool calling (Groq free tier by default).

```bash
cp .env.example .env      # set GROQ_API_KEY
docker compose up -d --build
# open http://127.0.0.1:3180
```

Without Docker: run each system with `uvicorn app:app --port 8101|8102` from its folder, then `cd agent && uvicorn server:app --port 8103`.

## Repository

- `systems/sipos-posyandu/`, `systems/si-dbd/`: the two legacy FastAPI apps, each with its Synapse output (`synapse_auto_server.py`, `.synapse/`)
- `agent/`: the copilot (`agent.py` MCP client + tool-calling loop; `server.py` + `index.html` web UI)
- `tools/make_data.py`: deterministic, de-identified synthetic data; `tools/expected.py`: ground-truth answers used to check the agent

Village codes follow the official format, but all villages' data is fictional.
