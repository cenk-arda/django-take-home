from celery import shared_task
from .models import License


@shared_task
def check_licenses_expiration():

    print("Checking license expiration...")
    return True