from django.urls import path

from . import views

app_name = "requests"

urlpatterns = [
    path("novo/", views.ServiceRequestCreateView.as_view(), name="create"),
    path("compativeis/", views.ServiceRequestCompatibleListView.as_view(), name="compatible-list"),
    path("<int:pk>/", views.ServiceRequestDetailView.as_view(), name="detail"),
    path("<int:pk>/interesses/", views.ServiceRequestInterestsPartialView.as_view(), name="interests-partial"),
    path("<int:pk>/interessar/", views.InterestCreateView.as_view(), name="interest-create"),
    path("<int:pk>/encerrar/", views.EndRequestView.as_view(), name="end"),
    path("<int:pk>/cancelar/", views.CancelRequestView.as_view(), name="cancel"),
    path("interesse/<int:pk>/retirar/", views.InterestWithdrawView.as_view(), name="interest-withdraw"),
    path("interesse/<int:pk>/selecionar/", views.SelectInterestView.as_view(), name="interest-select"),
]
