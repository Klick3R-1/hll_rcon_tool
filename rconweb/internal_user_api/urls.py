from django.urls import path

from . import views

urlpatterns = [
    path("groups/", views.groups, name="internal_groups"),
    path("users/", views.users, name="internal_users"),
    path("users/<int:user_id>/", views.user_detail, name="internal_user_detail"),
    path(
        "users/<int:user_id>/disable/",
        views.disable_user,
        name="internal_user_disable",
    ),
    path(
        "users/<int:user_id>/set-password/",
        views.set_password,
        name="internal_user_set_password",
    ),
    path(
        "users/<int:user_id>/groups/",
        views.update_groups,
        name="internal_user_groups",
    ),
]
