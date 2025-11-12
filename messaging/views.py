from uuid import uuid4
from datetime import datetime, timedelta
from django.utils import timezone
import pytz
from django.contrib import auth
from rest_framework import generics, permissions, serializers, status
from rest_framework import viewsets, mixins
from rest_framework.response import Response


class ArolitecSMSAckView(generics.GenericAPIView):
    permission_classes = [
        permissions.AllowAny,
    ]

    def get(self, request):
        msgid = None
        dlr = None
        ack_date = None
        message = None
        ack_type = None
        climsgid = None
        ack_status = None
        if "msgid" in request.GET:
            msgid = request.GET["msgid"]
        if "dlr" in request.GET:
            dlr = request.GET["dlr"]
        if "date" in request.GET:
            ack_date = request.GET["date"]
        if "message" in request.GET:
            message = request.GET["message"]
        if "type" in request.GET:
            ack_type = request.GET["type"]
        if "climsgid" in request.GET:
            climsgid = request.GET["climsgid"]
        if "status" in request.GET:
            ack_status = request.GET["status"]
        return Response({"Data": "OK"})


class ArolitecSMSMoView(generics.GenericAPIView):
    permission_classes = [
        permissions.AllowAny,
    ]

    def get(self, request):
        msgid = None
        sender = None
        ack_date = None
        content = None
        receiver = None
        mo_type = None

        if "msgid" in request.GET:
            msgid = request.GET["msgid"]
        if "sender" in request.GET:
            sender = request.GET["sender"]
        if "date" in request.GET:
            ack_date = request.GET["date"]
        if "content" in request.GET:
            content = request.GET["content"]
        if "type" in request.GET:
            mo_type = request.GET["type"]
        if "receiver" in request.GET:
            receiver = request.GET["receiver"]
        return Response({"Data": "OK"})
