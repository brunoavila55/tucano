from django.urls import path

from . import views

app_name = "subscriptions"

urlpatterns = [
    path("", views.PlanView.as_view(), name="plan"),
    path("assinar/", views.SubscribeView.as_view(), name="subscribe"),
    path("cancelar/", views.CancelSubscriptionView.as_view(), name="cancel"),
    path("boost/ativar/", views.BoostActivateView.as_view(), name="boost-activate"),
    path("webhook/mercadopago/", views.MercadoPagoWebhookView.as_view(), name="mercadopago-webhook"),
]
