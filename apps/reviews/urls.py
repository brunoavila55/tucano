from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("<int:interest_id>/", views.ConfirmationDetailView.as_view(), name="confirmation-detail"),
    path("<int:interest_id>/confirmar/", views.ConfirmServiceView.as_view(), name="confirm"),
    path("<int:interest_id>/avaliar/", views.ReviewCreateView.as_view(), name="review-create"),
    path("avaliacao/<int:pk>/contestar/", views.ReviewContestView.as_view(), name="review-contest"),
]
