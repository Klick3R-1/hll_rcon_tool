from django.urls import path

from . import views

urlpatterns = [
    path("", views.users, name="internal_users"),
    path("<int:user_id>/", views.user_detail, name="internal_user_detail"),
    path("<int:user_id>/disable/", views.disable_user, name="internal_user_disable"),
    path(
        "<int:user_id>/set-password/",
        views.set_password,
        name="internal_user_set_password",
    ),
    path("<int:user_id>/groups/", views.update_groups, name="internal_user_groups"),
]
