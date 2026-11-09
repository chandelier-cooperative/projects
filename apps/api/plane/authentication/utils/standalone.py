# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from functools import wraps

# Django imports
from django.http import HttpResponseRedirect, JsonResponse

# Third party imports
from rest_framework.views import APIView

# Module imports
from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES, AuthenticationException
from plane.authentication.provider.chandelier import is_chandelier_enabled
from plane.authentication.utils.host import base_host
from plane.utils.path_validator import get_safe_redirect_url


def standalone_only(view, *, is_admin=False):
    """Make a sign-in view usable only while Chandelier Auth is off.

    Projects runs in two modes. Inside Chandelier (CHANDELIER_AUTH_AUDIENCE set) the person is
    identified by the signed assertion and no other way in exists. Outside it (running the project
    on its own) the usual email, password, magic code and OAuth sign-in apply. This wraps the
    result of ``as_view()`` so each of those views refuses to run in the first mode.

    API views answer 403 with the error payload; redirect-flow views send the person back to the
    sign-in page with ``error_code`` so it can say why.
    """
    view_class = getattr(view, "view_class", None)
    is_api = bool(view_class and issubclass(view_class, APIView))

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not is_chandelier_enabled():
            return view(request, *args, **kwargs)

        exc = AuthenticationException(
            error_code=AUTHENTICATION_ERROR_CODES["SIGN_IN_METHOD_DISABLED"],
            error_message="SIGN_IN_METHOD_DISABLED",
        )
        if is_api:
            return JsonResponse(exc.get_error_dict(), status=403)
        url = get_safe_redirect_url(
            base_url=base_host(request=request, is_app=not is_admin, is_admin=is_admin),
            next_path=None,
            params=exc.get_error_dict(),
        )
        return HttpResponseRedirect(url)

    return wrapped
