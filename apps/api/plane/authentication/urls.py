# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from .utils.standalone import standalone_only
from .views import (
    ChandelierAuthEndpoint,
    ChangePasswordEndpoint,
    CSRFTokenEndpoint,
    EmailCheckEndpoint,
    ForgotPasswordEndpoint,
    GiteaCallbackEndpoint,
    GiteaOauthInitiateEndpoint,
    GitHubCallbackEndpoint,
    GitHubOauthInitiateEndpoint,
    GitLabCallbackEndpoint,
    GitLabOauthInitiateEndpoint,
    GoogleCallbackEndpoint,
    GoogleOauthInitiateEndpoint,
    MagicGenerateEndpoint,
    MagicSignInEndpoint,
    MagicSignUpEndpoint,
    ResetPasswordEndpoint,
    SetUserPasswordEndpoint,
    SignInAuthEndpoint,
    SignOutAuthEndpoint,
    SignUpAuthEndpoint,
)

# Every sign-in method except Chandelier Auth only works while Chandelier Auth is off, so the
# project can also run on its own. `standalone_only` makes each of them refuse when it is on.
urlpatterns = [
    # Sign in with Chandelier Auth: identity comes from the signed assertion, there is no password
    path("chandelier/", ChandelierAuthEndpoint.as_view(), name="chandelier-sign-in"),
    # credentials
    path("sign-in/", standalone_only(SignInAuthEndpoint.as_view()), name="sign-in"),
    path("sign-up/", standalone_only(SignUpAuthEndpoint.as_view()), name="sign-up"),
    # signout
    path("sign-out/", SignOutAuthEndpoint.as_view(), name="sign-out"),
    # csrf token
    path("get-csrf-token/", CSRFTokenEndpoint.as_view(), name="get_csrf_token"),
    # Magic sign in
    path("magic-generate/", standalone_only(MagicGenerateEndpoint.as_view()), name="magic-generate"),
    path("magic-sign-in/", standalone_only(MagicSignInEndpoint.as_view()), name="magic-sign-in"),
    path("magic-sign-up/", standalone_only(MagicSignUpEndpoint.as_view()), name="magic-sign-up"),
    ## Google Oauth
    path("google/", standalone_only(GoogleOauthInitiateEndpoint.as_view()), name="google-initiate"),
    path("google/callback/", standalone_only(GoogleCallbackEndpoint.as_view()), name="google-callback"),
    ## Github Oauth
    path("github/", standalone_only(GitHubOauthInitiateEndpoint.as_view()), name="github-initiate"),
    path("github/callback/", standalone_only(GitHubCallbackEndpoint.as_view()), name="github-callback"),
    ## Gitlab Oauth
    path("gitlab/", standalone_only(GitLabOauthInitiateEndpoint.as_view()), name="gitlab-initiate"),
    path("gitlab/callback/", standalone_only(GitLabCallbackEndpoint.as_view()), name="gitlab-callback"),
    ## Gitea Oauth
    path("gitea/", standalone_only(GiteaOauthInitiateEndpoint.as_view()), name="gitea-initiate"),
    path("gitea/callback/", standalone_only(GiteaCallbackEndpoint.as_view()), name="gitea-callback"),
    # Email Check
    path("email-check/", standalone_only(EmailCheckEndpoint.as_view()), name="email-check"),
    # Password
    path("forgot-password/", standalone_only(ForgotPasswordEndpoint.as_view()), name="forgot-password"),
    path(
        "reset-password/<uidb64>/<token>/",
        standalone_only(ResetPasswordEndpoint.as_view()),
        name="forgot-password",
    ),
    path("change-password/", standalone_only(ChangePasswordEndpoint.as_view()), name="forgot-password"),
    path("set-password/", standalone_only(SetUserPasswordEndpoint.as_view()), name="set-password"),
]
