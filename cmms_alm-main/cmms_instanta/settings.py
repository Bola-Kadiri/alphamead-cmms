from decouple import config

DEV = config("DEV", default=False, cast=bool)
STAGING = config("STAGING", default=False, cast=bool)

if DEV:
    from config.development import *
else:
    from config.production import *
