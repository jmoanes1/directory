"""Company calendar views."""

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.permissions import calendar_manager_required
from company_calendar.forms import CalendarEntryForm
from company_calendar.models import CalendarEntry
from company_calendar.utils import (
    build_month_grid,
    get_calendar_items_for_month,
    get_todays_events,
    get_upcoming_events,
    search_calendar_items,
    shift_month,
)
from employees.utils import log_activity


def _parse_month_year(request):
    """Read year/month from query params with sane fallbacks."""
    today = date.today()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
    except (TypeError, ValueError):
        return today.year, today.month

    if month < 1 or month > 12:
        return today.year, today.month
    return year, month


def _calendar_querystring(year, month, search=""):
    """Build query string preserving search when navigating months."""
    params = f"year={year}&month={month}"
    if search:
        params += f"&q={search}"
    return params


@login_required
def calendar_view(request):
    """Monthly calendar — read-only for employees; managers see edit actions."""
    year, month = _parse_month_year(request)
    search = request.GET.get("q", "").strip()
    today = date.today()

    entries_qs = CalendarEntry.objects.filter(is_active=True).select_related("created_by")
    if search:
        entries_qs = entries_qs.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    month_entries = list(
        entries_qs.filter(date__year=year, date__month=month).order_by("date", "title")
    )
    month_items = get_calendar_items_for_month(year, month, month_entries, search)
    weeks = build_month_grid(year, month, month_items)

    prev_year, prev_month = shift_month(year, month, -1)
    next_year, next_month = shift_month(year, month, 1)

    search_results = search_calendar_items(search) if search else []
    todays_events = get_todays_events(today, CalendarEntry.objects.filter(is_active=True), search)
    upcoming_events = get_upcoming_events(
        today,
        CalendarEntry.objects.filter(is_active=True),
        search=search,
    )

    month_label = date(year, month, 1).strftime("%B %Y")
    can_manage = request.user.can_manage_calendar()

    birthday_count = sum(1 for item in month_items if item.kind == "birthday")
    holiday_count = sum(1 for item in month_items if item.kind == CalendarEntry.EventType.HOLIDAY)
    event_count = sum(1 for item in month_items if item.kind == CalendarEntry.EventType.COMPANY_EVENT)

    return render(request, "company_calendar/calendar.html", {
        "year": year,
        "month": month,
        "month_label": month_label,
        "weeks": weeks,
        "search": search,
        "search_results": search_results,
        "todays_events": todays_events,
        "upcoming_events": upcoming_events,
        "can_manage": can_manage,
        "prev_url": f"?{_calendar_querystring(prev_year, prev_month, search)}",
        "next_url": f"?{_calendar_querystring(next_year, next_month, search)}",
        "today_url": f"?year={today.year}&month={today.month}",
        "holiday_count": holiday_count,
        "event_count": event_count,
        "birthday_count": birthday_count,
    })


@calendar_manager_required
def calendar_entry_create_view(request):
    form = CalendarEntryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.created_by = request.user
        entry.save()
        log_activity(
            request, "create", f"Created calendar entry {entry.title}",
            "CalendarEntry", entry.pk, entry.title,
        )
        messages.success(request, f"“{entry.title}” added to the company calendar.")
        return redirect(f"{reverse('company_calendar:home')}?year={entry.date.year}&month={entry.date.month}")

    return render(request, "company_calendar/form.html", {
        "form": form,
        "title": "Add calendar entry",
    })


@calendar_manager_required
def calendar_entry_edit_view(request, pk):
    entry = get_object_or_404(CalendarEntry, pk=pk)
    form = CalendarEntryForm(request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        entry = form.save()
        log_activity(
            request, "update", f"Updated calendar entry {entry.title}",
            "CalendarEntry", entry.pk, entry.title,
        )
        messages.success(request, f"“{entry.title}” updated successfully.")
        return redirect(f"{reverse('company_calendar:home')}?year={entry.date.year}&month={entry.date.month}")

    return render(request, "company_calendar/form.html", {
        "form": form,
        "entry": entry,
        "title": "Edit calendar entry",
    })


@calendar_manager_required
@require_POST
def calendar_entry_delete_view(request, pk):
    entry = get_object_or_404(CalendarEntry, pk=pk)
    title = entry.title
    entry_id = entry.pk
    entry_date = entry.date
    entry.delete()
    log_activity(
        request, "delete", f"Deleted calendar entry {title}",
        "CalendarEntry", entry_id, title,
    )
    messages.success(request, f"“{title}” removed from the calendar.")
    return redirect(f"{reverse('company_calendar:home')}?year={entry_date.year}&month={entry_date.month}")
