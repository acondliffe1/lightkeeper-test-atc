from datetime import timedelta

from patchdiff.models.patch import Patch
from patchdiff.models.row import END_OF_TIME


def determine_periods(patches: list[Patch]):
    dates = sorted({
            date
            for patch in patches
            for date in (patch.begin_date, patch.end_date)
    })

    periods = [
        (begin, end) if end == END_OF_TIME else (begin, end - timedelta(days=1))
        for begin, end in zip(dates, dates[1:])
    ]

    if dates[-1] != END_OF_TIME:
        periods.append((dates[-1], END_OF_TIME))

    return periods