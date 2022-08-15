import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("app")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.timezone ='Europe/Istanbul'

# each day on 18:00

app.conf.beat_schedule = {
    "send_mails_task": {
        "task": "send_mails_task",
        "schedule": crontab(hour=18, minute=25),
        "args": (),
    }
}
