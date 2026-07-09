import logging
from datetime import datetime, timezone
from pathlib import Path


class RunIdFilter(logging.Filter):
    def __init__(self, run_id: str):
        super().__init__()
        self.run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "run_id"):
            record.run_id = self.run_id
        return True


def _append_run_separator(log_path: Path, run_id: str) -> None:
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    separator = "=" * 100
    header = f"START {run_id} | {timestamp}"

    with log_path.open("a", encoding="utf-8") as log_file:
        if log_path.exists() and log_path.stat().st_size > 0:
            log_file.write("\n")
        log_file.write(f"{separator}\n")
        log_file.write(f"{header}\n")
        log_file.write(f"{separator}\n")


def setup_logging(run_id: str, log_to_file: bool = True) -> None:
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(run_id)s | %(name)s | %(message)s"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if root_logger.handlers:
        root_logger.handlers.clear()

    run_id_filter = RunIdFilter(run_id)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(run_id_filter)
    root_logger.addHandler(console_handler)

    if log_to_file:
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        pipeline_log_path = logs_dir / "pipeline.log"
        latest_log_path = logs_dir / "latest.log"

        _append_run_separator(pipeline_log_path, run_id)

        file_handler = logging.FileHandler(pipeline_log_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(run_id_filter)
        root_logger.addHandler(file_handler)

        latest_file_handler = logging.FileHandler(
            latest_log_path,
            mode="w",
            encoding="utf-8",
        )
        latest_file_handler.setLevel(logging.INFO)
        latest_file_handler.setFormatter(formatter)
        latest_file_handler.addFilter(run_id_filter)
        root_logger.addHandler(latest_file_handler)
