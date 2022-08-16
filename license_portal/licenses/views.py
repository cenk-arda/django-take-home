# Create your views here.
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
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

        """order by date"""
        notifications = Notification.objects.all().order_by('sent_datetime')

        return render(request, 'licenses/index.html', context={'notifications': Notification.objects.all()})

    def post(self, request):
        """trigger the task"""
        try:
            send_mails_task.delay()
            return JsonResponse({"status": 200, "msg": "Mails sent"})
        except Exception as e:
            return JsonResponse({"status": 500, "msg": "Error sending mails"})


class ApiView(View):
    def get(self, request):
        notifications = Notification.objects.all()
        summary = []
        for notification in notifications:
            info = {'client_name': notification.client.client_name,
                    'poc_name': notification.client.poc_contact_name,
                    'poc_email': notification.client.poc_contact_email,
                    'admin_poc_email': notification.client.admin_poc.email,
                    'sent_date': notification.sent_datetime.strftime('%Y-%m-%d')}
            summary.append(info)
        data = json.dumps(summary)
        return JsonResponse(data, content_type='application/json', safe=False)
