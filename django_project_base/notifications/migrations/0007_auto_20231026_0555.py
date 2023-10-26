# Generated by Django 4.2.4 on 2023-10-26 05:55
from gettext import gettext

import swapper
from django.db import migrations

from django_project_base.constants import USE_EMAIL_IF_RECIPIENT_HAS_NO_PHONE_NUBER


def forwards_func(apps, schema_editor):
    project_sett = swapper.load_model("django_project_base", "ProjectSettings")
    for project in swapper.load_model("django_project_base", "Project").objects.all():
        project_sett.objects.get_or_create(
            project=project,
            name=USE_EMAIL_IF_RECIPIENT_HAS_NO_PHONE_NUBER,
            defaults=dict(
                description=gettext("Send notification via EMail if user has no phone number"),
                value=False,
                value_type="bool",
            ),
        )


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0006_djangoprojectbasenotification_send_notification_sms"),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
