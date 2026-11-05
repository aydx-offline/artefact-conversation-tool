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


def resolve_context(timestamp, client, festivals, occasion):
    today = _message_date(timestamp)
    festival = next((f["name"] for f in festivals if _in_window(date.fromisoformat(f["date"]), today)), None)
    birthday = bool(client.get("birthday")) and _birthday_in_window(client["birthday"], today)
    if not occasion:
        occasion = "和".join(filter(None, ["生日" if birthday else "", festival]))
    purchases = [date.fromisoformat(p["date"]) for p in client.get("purchases", [])]
    last_visit = client.get("last_visit")
    return Context(
        occasion,
        festival,
        birthday,
        (today - max(purchases)).days if purchases else None,
        _months_between(date.fromisoformat(last_visit), today) if last_visit else None,
    )
