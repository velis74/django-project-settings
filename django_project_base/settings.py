from pathlib import Path

from django.contrib.auth.hashers import make_password

from django_project_base.settings_parser import parse_settings

DJANGO_PROJECT_BASE_SETTINGS = (
    {
        "name": "DJANGO_PROJECT_BASE_BASE_REQUEST_URL_VARIABLES",
        "default": {'project': {'value_name': 'current_project_slug', 'url_part': 'project-'},
                    'language': {'value_name': 'current_language', 'url_part': 'language-'}},
    },
    {
        "name": "DJANGO_PROJECT_BASE_SLUG_FIELD_NAME",
        "default": "slug",
    },
)

USER_CACHE_KEY = 'django-user-{id}'
CACHE_IMPERSONATE_USER = 'impersonate-user-%d'

PROFILER_LOG_LONG_REQUESTS_COUNT = 50

PROFILE_REVERSE_FULL_NAME_ORDER = False

DELETE_PROFILE_TIMEDELTA = 0

DOCUMENTATION_DIRECTORY: str = str(Path().resolve()) + '/docs/build/'

TEST_USER_ONE_DATA = dict(username='miha', last_name='Novak', first_name='Miha', email='user1@user1.si',
                          password='mihamiha')
TEST_USER_TWO_DATA = dict(username='janez', last_name='Novak', first_name='Janez', email='user2@user2.si',
                          password='janezjanez')


def set_django_project_base_settings():
    parse_settings(DJANGO_PROJECT_BASE_SETTINGS)
