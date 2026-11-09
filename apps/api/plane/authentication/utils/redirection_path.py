# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.authentication.provider.chandelier import is_chandelier_enabled
from plane.db.models import Profile, Workspace


def get_redirection_path(user):
    """Where a person lands after signing in.

    Inside Chandelier workspaces are managed there, so there is no onboarding or workspace creation
    page to send anyone to: without a workspace they land on the root, which tells them so. Running
    on its own, people finish onboarding and create their first workspace here.
    """
    standalone = not is_chandelier_enabled()
    profile, _ = Profile.objects.get_or_create(user=user)

    # Redirect to onboarding if the user is not onboarded yet
    if standalone and not profile.is_onboarded:
        return "onboarding"

    # Redirect to the last workspace if the user has last workspace
    if profile.last_workspace_id:
        workspace = Workspace.objects.filter(
            pk=profile.last_workspace_id,
            workspace_member__member_id=user.id,
            workspace_member__is_active=True,
        ).first()
        if workspace:
            return f"{workspace.slug}"

    fallback_workspace = (
        Workspace.objects.filter(workspace_member__member_id=user.id, workspace_member__is_active=True)
        .order_by("created_at")
        .first()
    )

    if fallback_workspace:
        return f"{fallback_workspace.slug}"

    # Redirect the user to create workspace
    return "create-workspace" if standalone else ""
