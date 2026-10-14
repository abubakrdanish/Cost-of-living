"""Serve the pipeline on a local schedule: weekdays at 13:00 Sydney time.

ABS releases at 11:30 Canberra time, so a 13:00 run picks up a release the
same day. Runs are idempotent: on a day with no release they make 4 small
requests and change nothing.

What must be running for the schedule to fire (all local, no cloud):
  1. A Prefect server:      prefect server start
     (with PREFECT_API_URL=http://127.0.0.1:4200/api set for the next step)
  2. This process:          python -m orchestration.serve
     It registers the deployment and polls for scheduled runs; runs execute
     inside this process. Stop it with Ctrl+C.
  3. The computer must be awake at 13:00. Missed runs are not caught up later;
     the next weekday's run picks up anything missed (ingestion is idempotent).

See docs/operations.md for the full instructions.
"""
from __future__ import annotations

import os

os.environ.setdefault("PREFECT_SERVER_ANALYTICS_ENABLED", "false")

from prefect.schedules import Cron  # noqa: E402

from orchestration.flow import cost_of_living_pipeline  # noqa: E402

DEPLOYMENT_NAME = "weekdays-1pm-sydney"
SCHEDULE = Cron("0 13 * * 1-5", timezone="Australia/Sydney")


def main() -> None:
    cost_of_living_pipeline.serve(
        name=DEPLOYMENT_NAME,
        schedules=[SCHEDULE],
        description="Download ABS CPI, rents and WPI; dbt build; quality report.",
        tags=["abs", "cost-of-living"],
    )


if __name__ == "__main__":
    main()
