from datetime import date

from patchdiff.models.patch import Patch
from patchdiff.models.row import BEGINNING_OF_TIME, END_OF_TIME
from patchdiff.utils import determine_periods

BOT = BEGINNING_OF_TIME
EOT = END_OF_TIME


def patch(begin, end):
    return Patch(begin_date=begin, end_date=end, key_value="k", values={})


def test_single_open_ended_patch_is_one_period():
    periods = determine_periods([patch(BOT, EOT)])

    assert periods == [(BOT, EOT)]


def test_splits_into_contiguous_non_overlapping_periods():
    periods = determine_periods(
        [patch(BOT, EOT), patch(date(2024, 2, 1), EOT)]
    )

    assert periods == [
        (BOT, date(2024, 1, 31)),
        (date(2024, 2, 1), EOT),
    ]


def test_trailing_period_added_when_last_date_is_not_open_ended():
    periods = determine_periods(
        [patch(date(2024, 1, 1), date(2024, 1, 31))]
    )

    assert periods == [
        (date(2024, 1, 1), date(2024, 1, 30)),
        (date(2024, 1, 31), EOT),
    ]
