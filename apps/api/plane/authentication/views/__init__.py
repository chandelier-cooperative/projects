# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from .common import ChangePasswordEndpoint, CSRFTokenEndpoint, SetUserPasswordEndpoint

from .app.check import EmailCheckEndpoint

from .app.email import SignInAuthEndpoint, SignUpAuthEndpoint
from .app.github import GitHubCallbackEndpoint, GitHubOauthInitiateEndpoint
from .app.gitlab import GitLabCallbackEndpoint, GitLabOauthInitiateEndpoint
from .app.gitea import GiteaCallbackEndpoint, GiteaOauthInitiateEndpoint
from .app.chandelier import ChandelierAdminAuthEndpoint, ChandelierAuthEndpoint
from .app.google import GoogleCallbackEndpoint, GoogleOauthInitiateEndpoint
from .app.magic import MagicGenerateEndpoint, MagicSignInEndpoint, MagicSignUpEndpoint

from .app.signout import SignOutAuthEndpoint

from .app.password_management import ForgotPasswordEndpoint, ResetPasswordEndpoint
