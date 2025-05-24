 
from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env from the parent directory
env_path = Path(__file__).resolve().parent.parent / '.env'
print(env_path)
load_dotenv(dotenv_path=env_path)

MAIL_SERVER = os.getenv('MAIL_SERVER')
MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False') == 'True'
MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER') 
SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
DEBUG = True

# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USE_SSL'] = False
# app.config['MAIL_USERNAME'] = 'samirram007@gmail.com'
# app.config['MAIL_PASSWORD'] = 'naqd tdpa cwpx knep' 
# app.config['MAIL_DEFAULT_SENDER'] = 'samirram007@gmail.com'
# app.config['MAIL_DEBUG'] = True