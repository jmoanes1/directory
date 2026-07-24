"""Rename check-in/out fields and add lunch/noon attendance slots."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="attendancerecord",
            old_name="check_in",
            new_name="time_in_morning",
        ),
        migrations.RenameField(
            model_name="attendancerecord",
            old_name="check_out",
            new_name="time_out_afternoon",
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="break_lunch",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="time_in_noon",
            field=models.TimeField(blank=True, null=True),
        ),
    ]
