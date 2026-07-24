from django.contrib import admin

from company_calendar.models import CalendarEntry


@admin.register(CalendarEntry)
class CalendarEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "event_type", "is_active", "created_by", "created_at")
    list_filter = ("event_type", "is_active", "date")
    search_fields = ("title", "description")
    date_hierarchy = "date"
    raw_id_fields = ("created_by",)
