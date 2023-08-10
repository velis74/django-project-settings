# Generated by Django 3.1.14 on 2023-08-07 08:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0007_auto_20230725_1421'),
    ]

    operations = [
        migrations.CreateModel(
            name='SearchItems',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveBigIntegerField()),
                ('name', models.CharField(max_length=256)),
            ],
            options={
                'abstract': False,
                'managed': False,
            },
        ),
        migrations.AlterField(
            model_name='djangoprojectbasenotification',
            name='delayed_to',
            field=models.BigIntegerField(blank=True, null=True, verbose_name='Delayed to'),
        ),
    ]
