from datetime import date, datetime, time


def combine_date_time(day: date, value: time) -> datetime:
    return datetime.combine(day, value)


def interval_overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and end_a > start_b


def interval_contains(window_start: datetime, window_end: datetime, request_start: datetime, request_end: datetime) -> bool:
    return window_start <= request_start and window_end >= request_end


def duration_hours(start_value: datetime, end_value: datetime) -> float:
    return (end_value - start_value).total_seconds() / 3600