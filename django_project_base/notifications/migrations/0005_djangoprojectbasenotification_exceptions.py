# Generated by Django 3.1.14 on 2023-07-21 12:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0004_auto_20230714_0919'),
    ]

    operations = [
        migrations.AddField(
            model_name='djangoprojectbasenotification',
            name='exceptions',
            field=models.TextField(null=True),
        ),
    ]