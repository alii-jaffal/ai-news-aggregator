import logging
import sys
from datetime import datetime

from app.daily_runner import run_daily_pipeline
from app.logging_config import setup_logging


logger = logging.getLogger(__name__)


def main(hours: int = 24, top_n: int | None = None):
    return run_daily_pipeline(hours=hours, top_n=top_n)


if __name__ == "__main__":
    run_id = datetime.now().strftime("run-%Y%m%d-%H%M%S")
    setup_logging(run_id)

    hours = 24
    top_n = None

    if len(sys.argv) > 1:
        hours = int(sys.argv[1])
    if len(sys.argv) > 2:
        top_n = int(sys.argv[2])

    logger.info(
        "Initialized pipeline run with hours=%s top_n=%s",
        hours,
        top_n if top_n is not None else "profile_default",
    )

    result = main(hours=hours, top_n=top_n)
    raise SystemExit(0 if result["success"] else 1)
