"""
Settings for running the test suite only — never used by the running app.

  python manage.py test --settings=cmms_instanta.test_settings --keepdb --parallel

Same settings as normal, except passwords are hashed with a fast algorithm.
The real hasher is deliberately slow (good for production, very slow when every
test creates several users); test passwords are throwaway, so speed wins here.
"""
from cmms_instanta.settings import *  # noqa: F401,F403

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
