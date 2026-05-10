from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.views.decorators.csrf import csrf_exempt

from .auth import require_internal_token
from .utils import (
    audit_action,
    get_groups_by_name,
    get_user_or_error,
    json_error,
    json_success,
    parse_json_body,
    require_json_methods,
    serialize_user,
)


USER_MUTABLE_FIELDS = {
    "username",
    "email",
    "first_name",
    "last_name",
    "is_staff",
    "is_active",
}
BOOLEAN_FIELDS = {"is_staff", "is_active"}


def _reject_superuser_payload(data):
    if "is_superuser" in data:
        raise ValidationError("is_superuser_cannot_be_set")


def _reject_superuser_target(user):
    if user.is_superuser:
        raise ValidationError("superusers_cannot_be_modified_by_internal_api")


def _validate_mutable_fields(data):
    unknown_fields = sorted(set(data) - USER_MUTABLE_FIELDS)
    if unknown_fields:
        raise ValidationError({"unknown_fields": unknown_fields})

    invalid_booleans = [
        field
        for field in BOOLEAN_FIELDS
        if field in data and not isinstance(data[field], bool)
    ]
    if invalid_booleans:
        raise ValidationError({"boolean_fields_required": invalid_booleans})


def _validation_error_response(error):
    if hasattr(error, "message_dict"):
        return json_error("validation_error", details=error.message_dict)
    return json_error("validation_error", details=error.messages)


@csrf_exempt
@require_internal_token
@require_json_methods(["GET", "POST"])
def users(request):
    if request.method == "GET":
        users_qs = (
            get_user_model()
            .objects.all()
            .prefetch_related("groups")
            .order_by("username")
        )
        audit_action("list_users", "*", request)
        return json_success([serialize_user(user) for user in users_qs])

    try:
        data = parse_json_body(request)
        _reject_superuser_payload(data)
        username = data.get("username")
        password = data.get("password")

        if not username:
            return json_error("username_required")
        if not password:
            return json_error("password_required")

        User = get_user_model()
        with transaction.atomic():
            user = User(username=username)
            user.email = data.get("email", "")
            user.first_name = data.get("first_name", "")
            user.last_name = data.get("last_name", "")
            if "is_staff" in data and not isinstance(data["is_staff"], bool):
                raise ValidationError({"boolean_fields_required": ["is_staff"]})
            if "is_active" in data and not isinstance(data["is_active"], bool):
                raise ValidationError({"boolean_fields_required": ["is_active"]})
            user.is_staff = data.get("is_staff", False)
            user.is_active = data.get("is_active", True)
            user.is_superuser = False
            validate_password(password, user=user)
            user.set_password(password)
            user.save()

            if "groups" in data:
                user.groups.set(get_groups_by_name(data["groups"]))

        audit_action("create_user", user.get_username(), request)
        return json_success(serialize_user(user), status=201)
    except ValidationError as error:
        return _validation_error_response(error)
    except IntegrityError:
        return json_error("username_already_exists", status=409)


@csrf_exempt
@require_internal_token
@require_json_methods(["PATCH"])
def user_detail(request, user_id):
    user = get_user_or_error(user_id)
    if not user:
        return json_error("user_not_found", status=404)

    try:
        _reject_superuser_target(user)
        data = parse_json_body(request)
        _reject_superuser_payload(data)
        _validate_mutable_fields(data)

        for field in USER_MUTABLE_FIELDS:
            if field in data:
                setattr(user, field, data[field])

        user.full_clean(exclude=["password"])
        update_fields = list(USER_MUTABLE_FIELDS & data.keys())
        if update_fields:
            user.save(update_fields=update_fields)
        audit_action(
            "update_user",
            user.get_username(),
            request,
            extra={"fields": sorted(data.keys())},
        )
        return json_success(serialize_user(user))
    except ValidationError as error:
        return _validation_error_response(error)
    except IntegrityError:
        return json_error("username_already_exists", status=409)


@csrf_exempt
@require_internal_token
@require_json_methods(["POST"])
def disable_user(request, user_id):
    user = get_user_or_error(user_id)
    if not user:
        return json_error("user_not_found", status=404)

    try:
        _reject_superuser_target(user)
        data = parse_json_body(request)
        if "disabled" in data and not isinstance(data["disabled"], bool):
            raise ValidationError({"boolean_fields_required": ["disabled"]})
    except ValidationError as error:
        return _validation_error_response(error)

    disabled = data.get("disabled", True)
    if disabled:
        user.is_active = False
        user.is_staff = False
        user.save(update_fields=["is_active", "is_staff"])
        user.groups.clear()
        action = "disable_user"
    else:
        user.is_active = True
        user.save(update_fields=["is_active"])
        action = "enable_user"

    audit_action(action, user.get_username(), request)
    return json_success(serialize_user(user))


@csrf_exempt
@require_internal_token
@require_json_methods(["POST"])
def set_password(request, user_id):
    user = get_user_or_error(user_id)
    if not user:
        return json_error("user_not_found", status=404)

    try:
        _reject_superuser_target(user)
        data = parse_json_body(request)
        password = data.get("password")
        if not password:
            return json_error("password_required")
        validate_password(password, user=user)
        user.set_password(password)
        user.save(update_fields=["password"])
        audit_action("set_password", user.get_username(), request)
        return json_success(serialize_user(user))
    except ValidationError as error:
        return _validation_error_response(error)


@csrf_exempt
@require_internal_token
@require_json_methods(["POST"])
def update_groups(request, user_id):
    user = get_user_or_error(user_id)
    if not user:
        return json_error("user_not_found", status=404)

    try:
        _reject_superuser_target(user)
        data = parse_json_body(request)

        if "groups" in data:
            groups = get_groups_by_name(data["groups"])
            user.groups.set(groups)
            action = "set_groups"
        else:
            add_groups = get_groups_by_name(data.get("add", []))
            remove_groups = get_groups_by_name(data.get("remove", []))
            if not add_groups and not remove_groups:
                return json_error("groups_add_or_remove_required")
            user.groups.add(*add_groups)
            user.groups.remove(*remove_groups)
            action = "update_groups"

        audit_action(action, user.get_username(), request, extra=data)
        return json_success(serialize_user(user))
    except ValidationError as error:
        return _validation_error_response(error)
