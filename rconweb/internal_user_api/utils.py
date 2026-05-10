import json
import logging
from functools import wraps

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.http import JsonResponse

logger = logging.getLogger("rconweb")


def get_client_ip(request):
    return request.META.get("REMOTE_ADDR", "")


def json_error(error, status=400, details=None):
    payload = {"ok": False, "error": error}
    if details:
        payload["details"] = details
    return JsonResponse(payload, status=status)


def json_success(data=None, status=200):
    payload = {"ok": True}
    if data is not None:
        payload["data"] = data
    return JsonResponse(payload, status=status)


def require_json_methods(methods):
    allowed_methods = tuple(method.upper() for method in methods)

    def decorator(view_func):
        @wraps(view_func)
        def inner(request, *args, **kwargs):
            if request.method not in allowed_methods:
                response = json_error("method_not_allowed", status=405)
                response["Allow"] = ", ".join(allowed_methods)
                return response
            return view_func(request, *args, **kwargs)

        return inner

    return decorator


def parse_json_body(request):
    if not request.body:
        return {}

    if request.content_type != "application/json":
        raise ValidationError("content_type_must_be_application_json")

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        raise ValidationError("invalid_json")

    if not isinstance(data, dict):
        raise ValidationError("json_body_must_be_an_object")

    return data


def serialize_user(user):
    return {
        "id": user.id,
        "username": user.get_username(),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "groups": list(user.groups.order_by("name").values_list("name", flat=True)),
        "date_joined": user.date_joined.isoformat() if user.date_joined else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


def get_user_or_error(user_id):
    User = get_user_model()
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None


def get_groups_by_name(group_names):
    if not isinstance(group_names, list):
        raise ValidationError("groups_must_be_a_list")

    if not all(isinstance(name, str) and name.strip() for name in group_names):
        raise ValidationError("groups_must_be_non_empty_strings")

    requested_names = [name.strip() for name in group_names]
    groups = list(Group.objects.filter(name__in=requested_names))
    found_names = {group.name for group in groups}
    missing_names = sorted(set(requested_names) - found_names)
    if missing_names:
        raise ValidationError({"unknown_groups": missing_names})

    return groups


def audit_action(action, username, request, extra=None):
    logger.info(
        "internal_user_api action=%s username=%s source_ip=%s extra=%s",
        action,
        username,
        get_client_ip(request),
        extra or {},
    )
