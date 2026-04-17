import os
from dotenv import load_dotenv


# loads .env file, will not overide already set enviroment variables (will do nothing when testing, building and deploying)
load_dotenv()


DEBUG = os.getenv('DEBUG', 'False') in ['True', 'true']
PORT = os.getenv('PORT', '8080')
POD_NAME = os.getenv('POD_NAME', 'pod_name_not_set')

TESTING = os.getenv('TESTING', 'False') in ['True', 'true']
TEST_CPR_NUMBER = os.getenv('TEST_CPR_NUMBER', '').strip()

if TESTING:
    SBSYS_URL = os.getenv('SBSYS_URL_TEST', '').strip()
    SBSIP_URL = os.getenv('SBSIP_URL_TEST', '').strip()

    SBSYS_USERNAME = os.getenv('SBSYS_USERNAME_TEST', '').strip()
    SBSYS_PASSWORD = os.getenv('SBSYS_PASSWORD_TEST', '').strip()

    SBSIP_CLIENT_ID = os.getenv('SBSIP_CLIENT_ID_TEST', '').strip()
    SBSIP_CLIENT_SECRET = os.getenv('SBSIP_CLIENT_SECRET_TEST', '').strip()
else:
    SBSYS_URL = os.getenv('SBSYS_URL', '').strip()
    SBSIP_URL = os.getenv('SBSIP_URL', '').strip()

    SBSYS_USERNAME = os.getenv('SBSYS_USERNAME', '').strip()
    SBSYS_PASSWORD = os.getenv('SBSYS_PASSWORD', '').strip()

    SBSIP_CLIENT_ID = os.getenv('SBSIP_CLIENT_ID', '').strip()
    SBSIP_CLIENT_SECRET = os.getenv('SBSIP_CLIENT_SECRET', '').strip()


DELTA_URL = os.getenv('DELTA_URL', '').strip()
DELTA_AUTH_URL = os.getenv('DELTA_AUTH_URL', '').strip()
DELTA_REALM = os.getenv('DELTA_REALM', '').strip()
DELTA_CLIENT_ID = os.getenv('DELTA_CLIENT_ID', '').strip()
DELTA_CLIENT_SECRET = os.getenv('DELTA_CLIENT_SECRET', '').strip()
