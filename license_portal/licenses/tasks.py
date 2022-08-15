from datetime import datetime, timedelta
from typing import Optional

from celery import shared_task, group, Task
from celery.signals import task_success

from .models import License, Client, Package, LicenseType, Notification
from django.core.mail import EmailMessage


def check_conditions(license: License) -> bool:
    print("Checking conditions for license {}".format(license.id))
    return (license.expiration_datetime.date() == datetime.now().date() + timedelta(days=120)) \
           or (license.expiration_datetime.date() <= datetime.now().date() + timedelta(
        days=30) and datetime.now().weekday() == 0) \
           or license.expiration_datetime.date() <= datetime.now().date() + timedelta(days=7)


class BaseTask(Task):
    def run(self, *args, **kwargs):
        email = kwargs['email']
        print("Sending mail to {}".format(email['to']))
        msg = EmailMessage(email['subject'], email['body'], to=[email['to']])
        msg.send()

    def on_success(self, retval, task_id, args, kwargs):
        print("Task {} succeeded".format(task_id))
        email = kwargs['email']
        """Save a Notification data with email"""
        notification = Notification(
            client=Client.objects.get(client_name=email['client']),
        )
        notification.save()


@shared_task(name="send_mails_task")
def send_mails_task() -> None:
    print("Started sending mails...")
    subject = "License expiration notification"

    """for each client, find all licenses that satisfies the conditions and add them to the body of the email, 
    then add the email to the email_list, which will be sent at once at the end of the task"""

    email_list = []
    for client in Client.objects.all():
        body = "Hello, The following licenses are eligible and require your attention:\n"
        should_send = False  # if there is at least one license that should be sent, this will be set to True
        for license in client.license_set.all():
            if check_conditions(license):
                should_send = True
                body += "\n Licence id: {}\n" \
                        "License type: {}\n " \
                        "Package name: {}\n" \
                        "Expiration date: {}\n" \
                        "Client's POC name: {}\n" \
                        "Client's POC email: {}\n" \
                    .format(license.id,
                            LicenseType(license.license_type).name,
                            Package(license.package).name,
                            license.expiration_datetime,
                            license.client.poc_contact_name,
                            license.client.poc_contact_email)

        """if there are no licenses that meet the conditions, don't send any email"""
        if should_send:
            """The information will be serialized into json format and will be sent to message broker (redis) as a 
            job, which is to be forwarded to celery worker """
            email_list.append(
                {'subject': subject, 'body': body, 'to': client.admin_poc.email, 'client_name': client.client_name,
                 })

    "send mails as a group ob jobs to send_mail_task, if successful, save the notification after async task is done"
    "use chain to send the notification after the mail is sent"
    print("length of email_list: {}".format(len(email_list)))
    jobs = [send_mail_task.s(email) for email in email_list]
    jobs = group(jobs)
    jobs.apply_async()


@shared_task(name='send_mail_task')
def send_mail_task(email: dict) -> Optional[dict]:
    """create email message from the email dict and send it"""
    print("Sending mail to {}".format(email['to']))
    msg = EmailMessage(email['subject'], email['body'], to=[email['to']])
    msg.send()
    return email


@task_success.connect(sender=send_mail_task)
def create_notification(**kwargs):
    print("Summarizing notification...")
    email = kwargs['result']
    client_name = email['client_name']
    notification = Notification.objects.create(client=Client.objects.get(client_name=client_name),
                                               mail_body=email['body'], sent=True, sent_datetime=datetime.now())
    return None
