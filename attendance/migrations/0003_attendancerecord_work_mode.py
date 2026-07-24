"""Add work mode (Office / WFH) to attendance records."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0002_attendance_time_slots"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancerecord",
            name="work_mode",
            field=models.CharField(
                choices=[("office", "Office"), ("wfh", "Work From Home")],
                db_index=True,
                default="office",
                max_length=20,
            ),
        ),
    ]
