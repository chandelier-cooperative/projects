# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third Party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from .base import BaseAPIView
from plane.app.permissions import allow_permission, ROLE
from plane.db.models import (
    ProjectMember,
    WorkspaceMember,
    Project,
    ProjectUserProperty,
)
from plane.db.models.project import ProjectNetwork


class UserProjectJoinEndpoint(BaseAPIView):
    """Join one or more projects of a workspace as yourself."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def post(self, request, slug):
        project_ids = request.data.get("project_ids", [])

        # Get the workspace user role
        workspace_member = WorkspaceMember.objects.get(member=request.user, workspace__slug=slug, is_active=True)

        # Get all the projects
        projects = Project.objects.filter(id__in=project_ids, workspace__slug=slug).only("id", "network")
        # Check if user has permission to join each project
        for project in projects:
            if project.network == ProjectNetwork.SECRET.value and workspace_member.role != ROLE.ADMIN.value:
                return Response(
                    {"error": "Only workspace admins can join private project"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        workspace_role = workspace_member.role
        workspace = workspace_member.workspace

        # Use the workspace-scoped, network-validated project IDs only.
        # Raw project_ids may contain UUIDs from other workspaces; those are
        # absent from the `projects` queryset and therefore bypass the SECRET
        # network check above (GHSA-45hc-q4mw-jhxm).
        validated_project_ids = [str(p.id) for p in projects]

        # If the user was already part of workspace
        _ = ProjectMember.objects.filter(
            workspace__slug=slug, project_id__in=validated_project_ids, member=request.user
        ).update(is_active=True)

        ProjectMember.objects.bulk_create(
            [
                ProjectMember(
                    project_id=project_id,
                    member=request.user,
                    role=workspace_role,
                    workspace=workspace,
                    created_by=request.user,
                )
                for project_id in validated_project_ids
            ],
            ignore_conflicts=True,
        )

        ProjectUserProperty.objects.bulk_create(
            [
                ProjectUserProperty(
                    project_id=project_id,
                    user=request.user,
                    workspace=workspace,
                    created_by=request.user,
                )
                for project_id in validated_project_ids
            ],
            ignore_conflicts=True,
        )

        return Response({"message": "Projects joined successfully"}, status=status.HTTP_201_CREATED)
