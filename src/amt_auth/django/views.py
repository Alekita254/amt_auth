from __future__ import annotations

import hmac

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from amt_auth.core.sync import consume_event
from amt_auth.django.repository import DjangoMirrorRepository
from amt_auth.exceptions import SyncError

WEBHOOK_SECRET_HEADER = "X-AMT-Webhook-Secret"


class KeycloakWebhookView(APIView):
    """Receives Keycloak org events and writes them to the mirror tables.

    The caller must send `settings.AMT_WEBHOOK_SECRET` in the
    `X-AMT-Webhook-Secret` header.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        secret = settings.AMT_WEBHOOK_SECRET
        sent = request.headers.get(WEBHOOK_SECRET_HEADER, "")
        if not secret or not hmac.compare_digest(sent.encode(), secret.encode()):
            raise PermissionDenied("Invalid webhook secret.")
        if not isinstance(request.data, dict):
            raise ValidationError("Event must be a JSON object.")
        try:
            with transaction.atomic():
                consume_event(request.data, DjangoMirrorRepository())
        except SyncError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(status=204)
