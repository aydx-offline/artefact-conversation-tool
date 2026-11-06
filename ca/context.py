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
    birthday_note: str | None
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


def _birthday_offset(birthday, today):
    month, day = map(int, birthday.split("-"))
    return min(((date(year, month, day) - today).days for year in (today.year - 1, today.year, today.year + 1)), key=abs)


def _birthday_note(offset, greeting):
    wish = "要" if greeting else "可以顺带"
    if offset == 0:
        return f"今天是她的生日，{wish}写生日快乐"
    if 0 < offset <= 7:
        return f"她的生日还有{offset}天，{wish}提前送上生日祝福"
    if -2 <= offset < 0:
        return f"她的生日刚过{-offset}天，{wish}补一句生日快乐"
    return "她的生日不在这几天，不要提生日"


def _months_between(start, end):
    months = (end.year - start.year) * 12 + end.month - start.month
    return months - (end.day < start.day)


YEARS = ("", "一", "两", "三", "四", "五", "六", "七", "八", "九")


def span_words(months):
    if months < 1:
        return "不到一个月"
    if months < 12:
        return f"{months}个月"
    years, rest = divmod(months, 12)
    return f"{YEARS[min(years, 9)]}年{'多' if rest else ''}"


def age_words(start, today):
    days = (date.fromisoformat(today) - date.fromisoformat(start)).days
    if days < 30:
        return f"{days}天前"
    return span_words(_months_between(date.fromisoformat(start), date.fromisoformat(today))) + "前"


def resolve_context(timestamp, client, festivals, occasion, last_message=None, greeting=False):
    today = _message_date(timestamp)
    festival = next((f["name"] for f in festivals if _in_window(date.fromisoformat(f["date"]), today)), None)
    offset = _birthday_offset(client["birthday"], today) if client.get("birthday") else None
    birthday = offset is not None and -2 <= offset <= 7
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
        _birthday_note(offset, greeting) if offset is not None else None,
        (today - _message_date(last_message)).days if last_message else None,
        upcoming,
        past,
    )
