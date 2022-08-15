import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("app")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.timezone ='Europe/Istanbul'
# app.conf.beat_schedule = {
#     "check_license_expiration": {
#         "task": "licenses.tasks.check_licenses_expiration",
#         "schedule": 5.0,
#         "args": (),
#     }
# }
