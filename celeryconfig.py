from config import settings

BROKER_URL = 'mongodb://localhost:27017/%s' % settings.database_name
CELERY_RESULT_BACKEND = 'mongodb'
CELERY_MONGODB_BACKEND_SETTINGS = {
    'host': 'localhost',
    'port': 27017,
    'database': settings.database_name,
    'taskmeta_collection': 'celery_tasks',
}
CELERY_IMPORTS = ('lib.calculator', )
CELERY_ALWAYS_EAGER = True
