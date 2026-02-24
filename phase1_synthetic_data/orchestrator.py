"""Orchestrator: runs all generators in dependency order and validates output."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel

from phase1_synthetic_data.generators.shared_state import SharedState
from phase1_synthetic_data.generators.hris_generator import HRISGenerator
from phase1_synthetic_data.generators.compensation_generator import CompensationGenerator
from phase1_synthetic_data.generators.ats_generator import ATSGenerator
from phase1_synthetic_data.generators.performance_generator import PerformanceGenerator

console = Console()


def run_phase1() -> bool:
    """Execute the full Phase 1 synthetic data generation pipeline."""

    console.print(Panel.fit(
        "[bold green]Phase 1: Synthetic Data Generation[/bold green]\n"
        "Generating data for Meridian Technologies (750 employees)",
        title="HR Ontology",
    ))

    # Initialize shared state (singleton, seeded for reproducibility)
    state = SharedState.reset()

    # Generator pipeline in dependency order
    generators = [
        HRISGenerator(state),        # Layer 0: Foundation
        CompensationGenerator(state), # Layer 1: Depends on HRIS positions/levels
        ATSGenerator(state),          # Layer 2: Depends on HRIS employees/positions
        PerformanceGenerator(state),  # Layer 3: Depends on HRIS + compensation context
    ]

    all_passed = True
    for gen in generators:
        success = gen.run()
        if not success:
            console.print(f"[bold red]FAILED: {gen.name}[/bold red]")
            all_passed = False
            break

    if all_passed:
        # Print overall summary
        total_active = len(state.active_employees())
        total_termed = len(state.terminated_employees())
        total_depts = len(state.departments)
        total_positions = len(state.positions)

        console.print()
        console.print(Panel.fit(
            f"[bold green]Generation Complete![/bold green]\n\n"
            f"Active employees:     {total_active}\n"
            f"Terminated employees: {total_termed}\n"
            f"Total employees:      {total_active + total_termed}\n"
            f"Departments:          {total_depts}\n"
            f"Positions:            {total_positions}\n"
            f"Skills in catalog:    {len(state.skill_catalog)}",
            title="Summary",
        ))
    else:
        console.print(Panel.fit(
            "[bold red]Generation failed. See errors above.[/bold red]",
            title="FAILED",
        ))

    return all_passed


if __name__ == "__main__":
    success = run_phase1()
    sys.exit(0 if success else 1)
