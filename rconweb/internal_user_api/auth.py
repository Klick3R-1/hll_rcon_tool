import hmac
import logging
from functools import wraps

from django.conf import settings

from .utils import get_client_ip, json_error

logger = logging.getLogger("rconweb")


def require_internal_token(view_func):
    @wraps(view_func)
    def inner(request, *args, **kwargs):
        source_ip = get_client_ip(request)

        if not settings.ENABLE_INTERNAL_USER_API:
            logger.warning(
                "internal_user_api rejected disabled request source_ip=%s path=%s",
                source_ip,
                request.path,
            )
            return json_error("internal_user_api_disabled", status=404)

        allowed_ips = settings.INTERNAL_USER_API_ALLOWED_IPS
        if allowed_ips and source_ip not in allowed_ips:
            logger.warning(
                "internal_user_api rejected disallowed_ip source_ip=%s path=%s",
                source_ip,
                request.path,
            )
            return json_error("ip_not_allowed", status=403)

        expected_token = settings.INTERNAL_USER_API_TOKEN
        supplied_token = request.headers.get("X-Internal-Token", "")
        if not expected_token or not hmac.compare_digest(
            supplied_token, expected_token
        ):
            logger.warning(
                "internal_user_api rejected invalid_token source_ip=%s path=%s",
                source_ip,
                request.path,
            )
            return json_error("invalid_token", status=403)

        return view_func(request, *args, **kwargs)

    return inner
