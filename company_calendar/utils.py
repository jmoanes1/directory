"""Helpers for building monthly calendar grids and display items."""

import calendar as cal_module
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Q

from company_calendar.models import CalendarEntry
from employees.models import Employee


@dataclass
class CalendarDisplayItem:
    """Unified calendar row for holidays, company events, and birthdays."""

    kind: str
    title: str
    date: date
    description: str = ""
    entry_id: int | None = None
    employee_id: int | None = None
    icon: str = ""

    @property
    def type_css_class(self):
        return f"cal-event--{self.kind}"

    @property
    def type_label(self):
        labels = {
            "holiday": "Holiday",
            "company_event": "Company Event",
            "birthday": "Birthday",
        }
        return labels.get(self.kind, self.kind.replace("_", " ").title())

    @property
    def is_editable(self):
        return self.entry_id is not None

    @property
    def sort_key(self):
        kind_order = {"holiday": 0, "company_event": 1, "birthday": 2}
        return (self.date, kind_order.get(self.kind, 9), self.title.lower())


def birthday_on_date(dob: date, year: int, month: int) -> date | None:
    """Map an employee DOB to a calendar date in the given month/year."""
    if dob.month != month:
        return None
    try:
        return date(year, month, dob.day)
    except ValueError:
        # Feb 29 birthdays appear on Feb 28 in non-leap years.
        if month == 2 and dob.month == 2 and dob.day == 29:
            return date(year, 2, 28)
    return None


def next_birthday_date(dob: date, from_date: date) -> date:
    """Next occurrence of a birthday on or after from_date."""
    for year in (from_date.year, from_date.year + 1):
        try:
            candidate = date(year, dob.month, dob.day)
        except ValueError:
            candidate = date(year, 2, 28)
        if candidate >= from_date:
            return candidate
    return date(from_date.year + 1, dob.month, min(dob.day, 28))


def entry_to_display(entry: CalendarEntry) -> CalendarDisplayItem:
    return CalendarDisplayItem(
        kind=entry.event_type,
        title=entry.title,
        date=entry.date,
        description=entry.description or "",
        entry_id=entry.pk,
    )


def birthday_to_display(employee: Employee, on_date: date) -> CalendarDisplayItem:
    return CalendarDisplayItem(
        kind="birthday",
        title=f"{employee.first_name}'s Birthday",
        date=on_date,
        description=f"Birthday celebration for {employee.full_name}",
        employee_id=employee.pk,
        icon="🎂",
    )


def get_employees_with_birthdays(search: str = ""):
    """Active employees who have a birth date on file."""
    qs = Employee.objects.filter(is_active=True, date_of_birth__isnull=False)
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search)
            | Q(middle_name__icontains=search)
            | Q(last_name__icontains=search)
        )
    return qs.order_by("first_name", "last_name")


def get_birthday_items_for_month(year: int, month: int, search: str = "") -> list[CalendarDisplayItem]:
    items = []
    for employee in get_employees_with_birthdays(search):
        on_date = birthday_on_date(employee.date_of_birth, year, month)
        if on_date:
            items.append(birthday_to_display(employee, on_date))
    return items


def get_calendar_items_for_month(
    year: int,
    month: int,
    entries: list[CalendarEntry],
    search: str = "",
) -> list[CalendarDisplayItem]:
    """Merge manual entries and employee birthdays for one month."""
    items = [entry_to_display(entry) for entry in entries]
    items.extend(get_birthday_items_for_month(year, month, search))
    items.sort(key=lambda item: item.sort_key)
    return items


def build_month_grid(year: int, month: int, items: list[CalendarDisplayItem]):
    """Build a month grid for templates."""
    items_by_date = defaultdict(list)
    for item in items:
        items_by_date[item.date].append(item)

    today = date.today()
    weeks = []
    for week in cal_module.Calendar(firstweekday=0).monthdatescalendar(year, month):
        week_days = []
        for day in week:
            day_items = sorted(items_by_date.get(day, []), key=lambda i: i.sort_key)
            week_days.append({
                "date": day,
                "day": day.day,
                "is_current_month": day.month == month,
                "is_today": day == today,
                "events": day_items,
            })
        weeks.append(week_days)
    return weeks


def shift_month(year: int, month: int, delta: int):
    """Return (year, month) after moving by delta months."""
    month += delta
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return year, month


def get_todays_events(today: date, entries_qs, search: str = "") -> list[CalendarDisplayItem]:
    """Holidays, company events, and birthdays occurring today."""
    items = [
        entry_to_display(entry)
        for entry in entries_qs.filter(date=today).order_by("title")
    ]
    for employee in get_employees_with_birthdays(search):
        if employee.date_of_birth.month == today.month and employee.date_of_birth.day == today.day:
            items.append(birthday_to_display(employee, today))
    items.sort(key=lambda item: item.sort_key)
    return items


def get_upcoming_events(
    today: date,
    entries_qs,
    *,
    search: str = "",
    days_ahead: int = 45,
    limit: int = 12,
) -> list[CalendarDisplayItem]:
    """Upcoming holidays, events, and birthdays after today."""
    end_date = today + timedelta(days=days_ahead)
    items = [
        entry_to_display(entry)
        for entry in entries_qs.filter(date__gt=today, date__lte=end_date).order_by("date", "title")
    ]

    for employee in get_employees_with_birthdays(search):
        next_date = next_birthday_date(employee.date_of_birth, today + timedelta(days=1))
        if next_date <= end_date:
            items.append(birthday_to_display(employee, next_date))

    items.sort(key=lambda item: item.sort_key)
    return items[:limit]


def search_calendar_items(search: str, *, limit: int = 50) -> list[CalendarDisplayItem]:
    """Search holidays, events, and employee birthdays by keyword."""
    if not search:
        return []

    today = date.today()
    year = today.year

    entries = CalendarEntry.objects.filter(is_active=True).filter(
        Q(title__icontains=search) | Q(description__icontains=search)
    )

    items = [entry_to_display(entry) for entry in entries]

    for employee in get_employees_with_birthdays(search):
        on_date = birthday_on_date(employee.date_of_birth, year, employee.date_of_birth.month)
        if on_date:
            items.append(birthday_to_display(employee, on_date))
        # Also include next year's date when searching near year end.
        on_date_next = birthday_on_date(employee.date_of_birth, year + 1, employee.date_of_birth.month)
        if on_date_next and on_date_next != on_date:
            items.append(birthday_to_display(employee, on_date_next))

    items.sort(key=lambda item: item.sort_key)
    return items[:limit]
