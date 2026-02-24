"""Abstract base class for all synthetic data generators."""

from abc import ABC, abstractmethod
from pathlib import Path
import pandas as pd
from rich.console import Console
from rich.table import Table

from config.settings import RAW_DATA_DIR

console = Console()


class BaseGenerator(ABC):
    """Base class that all HR system generators must inherit from."""

    name: str = "base"

    def __init__(self, shared_state: "SharedState"):
        self.state = shared_state
        self._dataframes: dict[str, pd.DataFrame] = {}

    @abstractmethod
    def generate(self) -> None:
        """Generate all synthetic data for this system. Populate self._dataframes."""
        ...

    def validate(self) -> list[str]:
        """Validate generated data. Returns list of error messages (empty = pass)."""
        errors = []
        for name, df in self._dataframes.items():
            if df.empty:
                errors.append(f"{self.name}/{name}: DataFrame is empty")
        return errors

    def save(self) -> None:
        """Save all DataFrames as CSV files to data/raw/{system_name}/."""
        output_dir = RAW_DATA_DIR / self.name
        output_dir.mkdir(parents=True, exist_ok=True)

        for name, df in self._dataframes.items():
            path = output_dir / f"{name}.csv"
            df.to_csv(path, index=False)

    def register(self, name: str, df: pd.DataFrame) -> None:
        """Register a DataFrame for saving and validation."""
        self._dataframes[name] = df

    def summary(self) -> None:
        """Print a summary table of all generated DataFrames."""
        table = Table(title=f"{self.name} Generator Summary")
        table.add_column("Table", style="cyan")
        table.add_column("Rows", justify="right", style="green")
        table.add_column("Columns", justify="right")

        for name, df in self._dataframes.items():
            table.add_row(name, str(len(df)), str(len(df.columns)))

        console.print(table)

    def run(self) -> bool:
        """Full pipeline: generate -> validate -> save -> summary."""
        console.print(f"\n[bold blue]Generating {self.name}...[/bold blue]")
        self.generate()

        errors = self.validate()
        if errors:
            for err in errors:
                console.print(f"  [red]ERROR: {err}[/red]")
            return False

        self.save()
        self.summary()
        return True
