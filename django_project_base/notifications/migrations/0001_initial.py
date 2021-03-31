# Generated by Django 3.1.5 on 2021-03-31 12:06

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_project_base.notifications.utils
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DjangoProjectBaseMessage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('subject', models.TextField(blank=True, null=True)),
                ('body', models.TextField()),
                ('footer', models.TextField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DjangoProjectBaseNotification',
            fields=[
                ('locale', models.CharField(blank=True, max_length=8, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('level', models.CharField(choices=[('success', 'Success'), ('info', 'Info'), ('warning', 'Warning'), ('error', 'Error')], max_length=16)),
                ('required_channels', models.CharField(blank=True, max_length=32, null=True)),
                ('sent_channels', models.CharField(blank=True, max_length=32, null=True)),
                ('failed_channels', models.CharField(blank=True, max_length=32, null=True)),
                ('created_at', models.DateTimeField(default=django_project_base.notifications.utils._utc_now, editable=False)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('delayed_to', models.DateTimeField(blank=True, null=True)),
                ('type', models.CharField(choices=[('maintenance', 'Maintenance'), ('standard', 'Standard')], default='standard', max_length=16)),
                ('message', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='notifications.djangoprojectbasemessage')),
                ('recipients', models.ManyToManyField(blank=True, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
