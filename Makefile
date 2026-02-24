.PHONY: generate lake ontology graph ui test clean all

# Phase 1: Generate synthetic data
generate:
	python -m phase1_synthetic_data.orchestrator

# Phase 2: Build data lake
lake:
	python -m phase2_data_lake.lake_builder

# Phase 3: Validate ontology
ontology:
	python -m phase3_ontology.constraints

# Phase 4: Load graph + run analytics
graph:
	python -m phase4_graph.loader.load_orchestrator

# Phase 5: Launch Streamlit UI
ui:
	streamlit run phase5_ai_interface/app.py

# Run tests
test:
	pytest tests/ -v

# Clean generated data
clean:
	rm -rf data/raw/* data/lake/* data/exports/*

# Run full pipeline
all: generate lake ontology graph
