from django.urls import path

from . import views

app_name = "moderation"

urlpatterns = [
    path("denunciar/<int:user_id>/", views.ReportUserCreateView.as_view(), name="report-user"),
    path("meus-casos/", views.MyModerationCasesListView.as_view(), name="my-cases"),
    path("caso/<int:pk>/recorrer/", views.AppealCaseView.as_view(), name="appeal-case"),
    path("verificacao/solicitar/", views.VerificationRequestCreateView.as_view(), name="verification-request"),
]
