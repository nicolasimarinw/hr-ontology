# HR Ontology

A full-stack HR analytics platform that generates synthetic workforce data, models it as an OWL ontology, loads it into a Neo4j knowledge graph, and exposes it through a Streamlit AI chat interface powered by Claude.

Built around **Meridian Technologies**, a fictional 750-employee tech company with 5 divisions, 20 departments, and 4 office locations.

## Architecture

```
Phase 1: Synthetic Data ─── Faker + statistical distributions
    │                        750 employees, HRIS/ATS/Performance/Compensation
    ▼
Phase 2: Data Lake ──────── DuckDB + Parquet files
    │                        Schema registry, quality checks, cross-system views
    ▼
Phase 3: Ontology ───────── OWL/RDF (rdflib)
    │                        22 node types, 29 relationship types, SHACL constraints
    ▼
Phase 4: Knowledge Graph ── Neo4j + APOC + n10s
    │                        Graph analytics, community detection, PyVis visualizations
    ▼
Phase 5: AI Interface ───── Streamlit + Claude API
                             Natural language queries, tool use, interactive dashboards
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for Neo4j)
- Anthropic API key

### Setup

```bash
# Clone and install
git clone https://github.com/nicolasimarinw/hr-ontology.git
cd hr-ontology
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your Anthropic API key

# Start Neo4j
docker compose up -d

# Run the full pipeline
make all

# Launch the UI
make ui
```

### Make Targets

| Command | Description |
|---------|-------------|
| `make generate` | Phase 1 -- Generate synthetic HR data |
| `make lake` | Phase 2 -- Build DuckDB data lake from Parquet files |
| `make ontology` | Phase 3 -- Validate OWL ontology constraints |
| `make graph` | Phase 4 -- Load Neo4j graph + run analytics |
| `make ui` | Phase 5 -- Launch Streamlit interface |
| `make all` | Run phases 1-4 sequentially |
| `make test` | Run test suite |
| `make clean` | Remove all generated data |

## Data Model

### Synthetic Company Profile

- **750 employees** across Active/Terminated statuses (~15% annual turnover)
- **5 divisions**: Engineering, Product, Sales, Operations, Corporate
- **20 departments** with realistic headcount distributions
- **10 job levels**: IC I through C-Suite
- **25 skills** across Technical, Product, Business, and Leadership categories
- **4 locations**: San Francisco HQ, New York, London, Remote

### Generated Datasets

| System | Tables |
|--------|--------|
| HRIS | Employees, Departments, Positions, Locations, Employment History |
| ATS | Requisitions, Candidates, Applications, Interviews, Offers |
| Performance | Performance Cycles, Goals, Reviews, Competency Assessments |
| Compensation | Salary Bands, Base Salary, Bonuses, Equity Grants |

### Knowledge Graph

The Neo4j graph models relationships like:
- `Employee -[:BELONGS_TO]-> Department -[:PART_OF]-> Division`
- `Employee -[:HAS_SKILL]-> Skill`
- `Employee -[:REPORTS_TO]-> Employee`
- `Candidate -[:APPLIED_TO]-> Requisition`
- `Employee -[:REVIEWED_IN]-> PerformanceReview`

Graph analytics include centrality scoring, community detection, and path analysis.

## AI Interface

The Streamlit dashboard provides:

- **KPI bar** -- headcount, turnover rate, avg performance rating, open reqs, gender split
- **AI chat** -- natural language questions answered via Claude with tool use (Cypher queries, DuckDB SQL, visualization generation)
- **Collapsible Q&A history** -- older conversations collapse into tagged cards, latest response stays expanded
- **Interactive visualizations** -- org charts, department networks, skills graphs, ego graphs

### Example Questions

- "Who are the top flight risks in Engineering?"
- "Is there a pay equity gap by gender?"
- "Which recruiting sources produce the best hires?"
- "What happens if Jerry Hayes (EMP-00695) leaves?"
- "Which skills are most common among top performers?"
- "What's the average span of control?"

## Project Structure

```
hr-ontology/
├── config/                  # Settings, company profile
├── phase1_synthetic_data/   # Faker-based data generators
├── phase2_data_lake/        # DuckDB lake builder, schema registry
├── phase3_ontology/         # OWL ontology (TTL), mappings, constraints
├── phase4_graph/            # Neo4j loader, analytics, PyVis visualization
├── phase5_ai_interface/     # Streamlit app, Claude agent, tool definitions
│   ├── app.py               # Entry point
│   ├── claude_agent.py      # Agent with tool use
│   ├── pages/               # Dashboard, Employee Explorer
│   ├── prompts/             # System prompt, example queries
│   └── tools/               # Cypher, DuckDB, visualization, ontology tools
├── tests/                   # Validation tests
├── docker-compose.yml       # Neo4j container
├── Makefile                 # Pipeline commands
└── pyproject.toml           # Dependencies
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Generation | Faker, NumPy, Pandas |
| Data Lake | DuckDB, Apache Parquet |
| Ontology | RDFLib, OWL 2, SHACL |
| Knowledge Graph | Neo4j 5, APOC, n10s |
| Visualization | PyVis, Matplotlib, Seaborn |
| AI | Claude API (Anthropic), tool use |
| Frontend | Streamlit |

## License

MIT
