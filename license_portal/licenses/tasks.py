from datetime import datetime, timedelta
from typing import Optional

from celery import shared_task, group
from celery.signals import task_success

from .models import License, Client, Package, LicenseType, Notification
from .notifications import EmailNotification


def check_conditions(license: License) -> bool:
    print("Checking conditions for license {}".format(license.id))
    return (license.expiration_datetime.date() == datetime.now().date() + timedelta(days=120)) \
           or (license.expiration_datetime.date() <= datetime.now().date() + timedelta(
        days=30) and datetime.now().weekday() == 0) \
           or license.expiration_datetime.date() <= datetime.now().date() + timedelta(days=7)


@shared_task(name="send_mails_task")
def send_mails_task() -> None:
    print("Started sending mails...")
    subject = "License expiration notification"
    email_list = []
    for client in Client.objects.all():
        should_send = False  # if there is at least one license that should be sent, this will be set to True
        licenses = []
        for license in client.license_set.all():
            if check_conditions(license):
                should_send = True
                license_info = {'license_type': LicenseType(license.license_type).name,
                                'package': Package(license.package).name,
                                'expiration_date': license.expiration_datetime}
                licenses.append(license_info)

        """if there are no licenses that meet the conditions, don't send any email"""
        if should_send:
            """The information will be serialized into json format and will be sent to message broker (redis) as a 
            job, which is to be forwarded to celery worker """
            email_list.append(
                {'subject': subject, 'to': client.admin_poc.email, 'client_name': client.client_name,
                 'client_poc_mail': client.poc_contact_email,
                 'licenses': licenses
                 })

    """send mails as individual async group jobs"""
    jobs = [send_mail_task.s(email) for email in email_list]
    jobs = group(jobs)
    jobs.apply_async()


@shared_task(name='send_mail_task')
def send_mail_task(email: dict) -> Optional[dict]:
    """create email message from the email dict and send it"""
    print("Sending mail to {}".format(email['to']))
    EmailNotification.subject = email['subject']
    EmailNotification.template_path = 'licenses/email_template.html'
    context = email
    EmailNotification.send_notification([email['to']], context)
    return email


@task_success.connect(sender=send_mail_task)
def create_notification(**kwargs):
    """ on successful notification sending result, create a notification instance and save it to database"""
    print("Summarizing notification...")
    email = kwargs['result']
    client_name = email['client_name']
    notification = Notification.objects.create(client=Client.objects.get(client_name=client_name), sent=True,
                                               sent_datetime=datetime.now(), sent_to=email['to'])
    return None
