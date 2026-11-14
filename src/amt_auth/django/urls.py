from django.urls import path

from amt_auth.django.views import KeycloakWebhookView

app_name = "amt_auth"

urlpatterns = [
    path("webhook/", KeycloakWebhookView.as_view(), name="webhook"),
]
