# Generated by Django 3.1.5 on 2021-02-10 07:35

from django.conf import settings
import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='auth.user')),
                ('bio', models.TextField(blank=True, max_length=500, null=True)),
                ('phone_number', models.CharField(blank=True, max_length=20, null=True)),
                ('language', models.CharField(blank=True, max_length=10, null=True)),
                ('theme', models.CharField(blank=True, max_length=10, null=True)),
                ('avatar', models.FileField(upload_to='')),
            ],
            options={
                'abstract': False,
            },
            bases=('auth.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=80)),
                ('slug', models.SlugField(max_length=80)),
                ('description', models.TextField(blank=True, null=True)),
                ('logo', models.FileField(upload_to='')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_profiles', to=settings.DJANGO_PROJECT_BASE_PROFILE_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
