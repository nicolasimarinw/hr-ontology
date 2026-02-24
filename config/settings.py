"""Central configuration for the HR Ontology project."""

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Data paths
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
LAKE_DATA_DIR = DATA_DIR / "lake"
EXPORTS_DIR = DATA_DIR / "exports"

# Ensure data directories exist
for d in [RAW_DATA_DIR, LAKE_DATA_DIR, EXPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "hr-ontology-dev")

# Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Random seed for reproducibility
RANDOM_SEED = 42
