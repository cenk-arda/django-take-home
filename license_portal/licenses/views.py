# Create your views here.
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
# The class view that triggers the task
from django.views.generic import View
from django.http import JsonResponse
from .tasks import send_mails_task
from .models import Notification
import json


@method_decorator(csrf_exempt, name='dispatch')
class Index(View):
    def get(self, request):
        """render the page"""

        """ find the clients of notifications and return their info """
        notifications = Notification.objects.all()
        summary = []
        for notification in notifications:
            info = {}
            info['client_name'] = notification.client.client_name
            info['poc_name'] = notification.client.poc_contact_name
            info['poc_email'] = notification.client.poc_contact_email
            info['admin_poc_email'] = notification.client.admin_poc.email
            summary.append(info)
        data = json.dumps(summary)
        return JsonResponse(data, content_type='application/json', safe=False)

    def post(self, request):
        """trigger the task"""
        send_mails_task.delay()
        return JsonResponse({"status": 200, "msg": "Mails sent"})
