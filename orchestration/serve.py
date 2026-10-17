"""Serve the pipeline on a local schedule: weekdays at 13:00 Sydney time.

The ABS publishes at 11:30 Canberra time, so a 13:00 run picks up a release
the same day. Needs a running Prefect server and this process; see
docs/operations.md.
"""
from __future__ import annotations

import os

# Set before Prefect is imported below (flow.py sets it too, but later).
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
