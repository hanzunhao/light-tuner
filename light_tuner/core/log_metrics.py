import os
from datetime import datetime
from typing import Dict, Any, Optional

# Local module imports
from light_tuner.storage.sqlite_manager import SQLiteManager
from light_tuner.utils.context import get_test_id, get_console_test_id
from light_tuner.utils.config import CONSOLE_PRINT_METRICS


def log_metrics(
        metrics: Dict[str, Any],
        epoch: int,
        step: int = 0,
        tag: Optional[str] = None,
        data_type: Optional[str] = None
) -> None:
    """
    Log training metrics with automatic identification of scalars and complex data structures.

    Args:
        metrics: Dictionary of metrics, e.g., {"loss": 0.1, "cm": [[1,0],[0,1]]}
        epoch: Current training epoch.
        step: Current iteration step.
        tag: Custom tag for grouping or identifying specific logs.
        data_type: Force specify the data type. If None, the type is inferred automatically.
    """

    # Initialize database connection using environment-stored path
    db = SQLiteManager(os.getenv('LIGHT_TUNER_DB_PATH'))
    console_test_id = get_console_test_id()
    test_id = get_test_id()
    record_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Console Logging Logic
    if CONSOLE_PRINT_METRICS:
        print(f"\n{'=' * 30} Test {console_test_id} | Epoch {epoch} | Step {step} {'=' * 30}")

        for k, v in metrics.items():
            # Optimization for printing different data types
            if isinstance(v, (list, dict)):
                val_display = f"[Complex Data: {type(v).__name__}]"
            elif isinstance(v, (float, int)):
                if "lr" in k.lower():
                    # Scientific notation for learning rates
                    val_display = f"{v:.6e}"
                else:
                    # Standard float formatting
                    val_display = f"{v:.6f}"
            else:
                val_display = str(v)

            print(f"🔹 {k:<20}: {val_display:>15}")

    # 2. Database Persistence Logic
    for k, v in metrics.items():
        # --- Automatic data_type Inference ---
        current_type = data_type
        if not current_type:
            if isinstance(v, (int, float)):
                current_type = 'scalar'
            elif isinstance(v, list):
                # Simple check for nested lists (matrix vs array)
                current_type = 'matrix' if (len(v) > 0 and isinstance(v[0], list)) else 'array'
            elif isinstance(v, dict):
                current_type = 'json'
            else:
                current_type = 'scalar'

        db.insert_metric(
            test_id=test_id,
            epoch=epoch,
            step=step,
            metric_name=k,
            metric_val=v,
            data_type=current_type,
            tag=tag,
            record_time=record_time
        )