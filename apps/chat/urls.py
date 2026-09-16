from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("<int:interest_id>/", views.ConversationDetailView.as_view(), name="detail"),
    path("<int:interest_id>/bloquear/", views.BlockUserView.as_view(), name="block"),
]
