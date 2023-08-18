import os
from environs import Env

envfile = os.environ.get("MOVEBANK_ENVFILE", None)

env = Env()

if envfile:
    env.read_env(envfile)
else:
    # Default behavior
    env.read_env()


MOVEBANK_USERNAME = env.str("MOVEBANK_USERNAME", None)
MOVEBANK_PASSWORD = env.str("MOVEBANK_PASSWORD", None)
MOVEBANK_API_BASE_URL = env.str("MOVEBANK_API_BASE_URL", None)
MOVEBANK_SSL_VERIFY = env.bool("MOVEBANK_SSL_VERIFY", True)

LOG_LEVEL = env.log_level("LOG_LEVEL", "INFO")
