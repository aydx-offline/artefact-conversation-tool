from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")
WINDOW_DAYS = 3


@dataclass
class Context:
    occasion: str
    festival: str | None
    birthday: bool
    days_since_purchase: int | None
    months_since_visit: int | None
    today: str
    days_to_birthday: int | None
    days_since_message: int | None
    next_festival: tuple | None
    last_festival: tuple | None


def _message_date(timestamp):
    moment = datetime.fromisoformat(timestamp)
    if moment.tzinfo is None:
        return moment.date()
    return moment.astimezone(SHANGHAI).date()


def _in_window(day, today):
    return 0 <= (day - today).days <= WINDOW_DAYS


def _birthday_in_window(birthday, today):
    month, day = map(int, birthday.split("-"))
    return any(_in_window(date(year, month, day), today) for year in (today.year, today.year + 1))


def _months_between(start, end):
    months = (end.year - start.year) * 12 + end.month - start.month
    return months - (end.day < start.day)


def _days_to_birthday(birthday, today):
    month, day = map(int, birthday.split("-"))
    return min((date(year, month, day) - today).days for year in (today.year, today.year + 1) if date(year, month, day) >= today)


def resolve_context(timestamp, client, festivals, occasion, last_message=None):
    today = _message_date(timestamp)
    festival = next((f["name"] for f in festivals if _in_window(date.fromisoformat(f["date"]), today)), None)
    birthday = bool(client.get("birthday")) and _birthday_in_window(client["birthday"], today)
    if not occasion:
        occasion = "和".join(filter(None, ["生日" if birthday else "", festival]))
    gaps = [(f["name"], (date.fromisoformat(f["date"]) - today).days) for f in festivals]
    upcoming = min(((n, d) for n, d in gaps if d >= 0), key=lambda g: g[1], default=None)
    past = min(((n, -d) for n, d in gaps if d < 0), key=lambda g: g[1], default=None)
    purchases = [date.fromisoformat(p["date"]) for p in client.get("purchases", [])]
    last_visit = client.get("last_visit")
    return Context(
        occasion,
        festival,
        birthday,
        (today - max(purchases)).days if purchases else None,
        _months_between(date.fromisoformat(last_visit), today) if last_visit else None,
        today.isoformat(),
        _days_to_birthday(client["birthday"], today) if client.get("birthday") else None,
        (today - _message_date(last_message)).days if last_message else None,
        upcoming,
        past,
    )
