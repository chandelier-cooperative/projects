# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from urllib.parse import urlencode, urljoin

# Django imports
from django.http import Http404, HttpResponseRedirect
from django.views import View

# Module imports
from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES, AuthenticationException
from plane.authentication.provider.chandelier import (
    ChandelierProvider,
    admin_subs,
    find_user_by_sub,
    get_claims,
    is_chandelier_enabled,
    is_instance_admin,
    promote_instance_admin,
)
from plane.authentication.utils.host import base_host
from plane.authentication.utils.login import user_login
from plane.authentication.utils.redirection_path import get_redirection_path
from plane.license.models import Instance
from plane.utils.cache import invalidate_cache
from plane.utils.path_validator import validate_next_path


def _error_redirect(host, exc, next_path=None):
    params = exc.get_error_dict()
    if next_path:
        params["next_path"] = str(next_path)
    return HttpResponseRedirect(urljoin(host, "?" + urlencode(params)))


def _not_configured():
    return AuthenticationException(
        error_code=AUTHENTICATION_ERROR_CODES["INSTANCE_NOT_CONFIGURED"],
        error_message="INSTANCE_NOT_CONFIGURED",
    )


class ChandelierAuthEndpoint(View):
    """Signs the person in to the app from the Chandelier Auth assertion. No form, no password."""

    @invalidate_cache(path="/api/instances/", user=False)
    def get(self, request):
        if not is_chandelier_enabled():
            raise Http404

        host = base_host(request=request, is_app=True)
        next_path = request.GET.get("next_path")
        next_path = str(validate_next_path(next_path)) if next_path else None

        instance = Instance.objects.first()
        if instance is None:
            return _error_redirect(host, _not_configured(), next_path)

        try:
            claims = get_claims(request)
            sub = str(claims["sub"])
            is_admin = sub in admin_subs()

            # Until the instance is set up only an instance admin may enter: they finish the setup.
            if not instance.is_setup_done and not is_admin:
                raise _not_configured()

            user = ChandelierProvider(request=request, claims=claims).authenticate(
                provision=is_admin
            )
            if is_admin:
                promote_instance_admin(user, instance)

            user_login(request=request, user=user, is_app=True)
            path = next_path or get_redirection_path(user=user)
            return HttpResponseRedirect(urljoin(host, path))
        except AuthenticationException as e:
            return _error_redirect(host, e, next_path)


class ChandelierAdminAuthEndpoint(View):
    """Signs an instance admin in to god-mode. It replaces the email/password setup of the instance.

    Lives under /api/instances/ because that path selects the separate admin session cookie.
    """

    @invalidate_cache(path="/api/instances/", user=False)
    def get(self, request):
        if not is_chandelier_enabled():
            raise Http404

        host = base_host(request=request, is_admin=True)

        instance = Instance.objects.first()
        if instance is None:
            return _error_redirect(host, _not_configured())

        try:
            claims = get_claims(request)
            sub = str(claims["sub"])
            is_admin = sub in admin_subs()

            if is_admin:
                provider = ChandelierProvider(request=request, claims=claims)
                user = provider.authenticate(provision=True)
                promote_instance_admin(user, instance)
            else:
                # Not an admin by configuration: never create anybody here, only let existing admins in.
                user = find_user_by_sub(sub)
                if user is None or not user.is_active or user.is_bot or not is_instance_admin(user):
                    raise AuthenticationException(
                        error_code=AUTHENTICATION_ERROR_CODES["ADMIN_AUTHENTICATION_FAILED"],
                        error_message="ADMIN_AUTHENTICATION_FAILED",
                    )

            user_login(request=request, user=user, is_admin=True)
            return HttpResponseRedirect(urljoin(host, "general/"))
        except AuthenticationException as e:
            return _error_redirect(host, e)
