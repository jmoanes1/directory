from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0004_alter_attendancerecord_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="leaverequest",
            name="approval_email_sent_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp when approved-notification email was triggered.",
                null=True,
            ),
        ),
    ]
