# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Adding people to a workspace from the people Auth knows. There are no invitations."""

from unittest import mock

import pytest
import requests

from plane.db.models import Account, User, WorkspaceMember

SUB = "44444444-4444-4444-8444-444444444444"
OTHER_SUB = "55555555-5555-4555-8555-555555555555"
ASSERTION = "assertion.of.the.caller"
GET = "plane.authentication.utils.chandelier_directory.requests.get"


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no body")
        return self._body


def person(sub=SUB, name="Ana Lopez", status="active"):
    return {"id": sub, "display_name": name, "status": status, "logins": ["ana@github"]}


def auth_says(*people, status=200):
    return FakeResponse(status, {"users": list(people)})


@pytest.fixture(autouse=True)
def chandelier_on(monkeypatch):
    monkeypatch.setenv("CHANDELIER_AUTH_AUDIENCE", "projects.chandelier.test")
    monkeypatch.setenv("CHANDELIER_AUTH_MODE", "required")


@pytest.fixture
def members_url(workspace):
    return f"/api/workspaces/{workspace.slug}/members/"


@pytest.fixture
def directory_url(workspace):
    return f"/api/workspaces/{workspace.slug}/directory/"


def add(client, url, **body):
    return client.post(url, body, format="json", HTTP_X_CHANDELIER_ASSERTION=ASSERTION)


@pytest.mark.contract
@pytest.mark.django_db
class TestAddMember:
    def test_admin_adds_a_person_from_auth(self, session_client, workspace, members_url):
        with mock.patch(GET, return_value=auth_says(person())) as get:
            res = add(session_client, members_url, sub=SUB, role=15)
        assert res.status_code == 201
        # Auth is asked with exactly the assertion of this request, and for exactly this person.
        _, kwargs = get.call_args
        assert {k.lower(): v for k, v in kwargs["headers"].items()} == {"x-chandelier-assertion": ASSERTION}
        assert "id=" + SUB in get.call_args[0][0]
        user = Account.objects.get(provider="chandelier", provider_account_id=SUB).user
        assert (user.first_name, user.last_name) == ("Ana", "Lopez")
        assert user.email == f"{SUB}@chandelier.local"
        assert WorkspaceMember.objects.get(workspace=workspace, member=user).role == 15

    def test_the_person_can_be_added_as_admin(self, session_client, workspace, members_url):
        with mock.patch(GET, return_value=auth_says(person())):
            assert add(session_client, members_url, sub=SUB, role=20).status_code == 201
        assert WorkspaceMember.objects.get(workspace=workspace, member__accounts__provider_account_id=SUB).role == 20

    def test_only_admin_or_member_roles(self, session_client, members_url):
        with mock.patch(GET, return_value=auth_says(person())) as get:
            assert add(session_client, members_url, sub=SUB, role=5).status_code == 400
            assert add(session_client, members_url, sub=SUB, role=99).status_code == 400
        get.assert_not_called()

    def test_sub_must_be_an_id(self, session_client, members_url):
        with mock.patch(GET) as get:
            assert add(session_client, members_url, sub="ana@example.com", role=15).status_code == 400
            assert add(session_client, members_url, role=15).status_code == 400
        get.assert_not_called()

    def test_auth_must_confirm_the_person(self, session_client, members_url):
        with mock.patch(GET, return_value=auth_says()):
            assert add(session_client, members_url, sub=SUB, role=15).status_code == 404
        assert not Account.objects.filter(provider_account_id=SUB).exists()

    def test_a_suspended_person_is_not_added(self, session_client, members_url):
        with mock.patch(GET, return_value=auth_says(person(status="suspended"))):
            assert add(session_client, members_url, sub=SUB, role=15).status_code == 404
        assert not User.objects.filter(email=f"{SUB}@chandelier.local").exists()

    def test_an_answer_for_someone_else_is_not_trusted(self, session_client, members_url):
        with mock.patch(GET, return_value=auth_says(person(sub=OTHER_SUB))):
            assert add(session_client, members_url, sub=SUB, role=15).status_code == 404
        assert not Account.objects.filter(provider_account_id__in=[SUB, OTHER_SUB]).exists()

    def test_the_workspace_admin_check_comes_first(self, api_client, workspace, members_url):
        member = User.objects.create(email="m@example.com", username="m")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15)
        api_client.force_authenticate(user=member)
        with mock.patch(GET) as get:
            assert add(api_client, members_url, sub=SUB, role=15).status_code == 403
        get.assert_not_called()

    def test_not_available_outside_chandelier(self, session_client, members_url, monkeypatch):
        monkeypatch.delenv("CHANDELIER_AUTH_AUDIENCE")
        monkeypatch.delenv("CHANDELIER_AUTH_MODE")
        with mock.patch(GET) as get:
            assert add(session_client, members_url, sub=SUB, role=15).status_code == 404
        get.assert_not_called()

    @pytest.mark.parametrize("answer,expected", [(401, 401), (403, 403), (500, 502)])
    def test_what_auth_refuses_is_reported(self, session_client, members_url, answer, expected):
        with mock.patch(GET, return_value=FakeResponse(answer)):
            assert add(session_client, members_url, sub=SUB, role=15).status_code == expected

    def test_auth_unreachable_is_502(self, session_client, members_url):
        with mock.patch(GET, side_effect=requests.ConnectionError()):
            assert add(session_client, members_url, sub=SUB, role=15).status_code == 502

    def test_a_garbled_answer_is_502(self, session_client, members_url):
        with mock.patch(GET, return_value=FakeResponse(200, {"nope": 1})):
            assert add(session_client, members_url, sub=SUB, role=15).status_code == 502

    def test_no_assertion_is_401_without_calling_auth(self, session_client, members_url):
        with mock.patch(GET) as get:
            res = session_client.post(members_url, {"sub": SUB, "role": 15}, format="json")
        assert res.status_code == 401
        get.assert_not_called()

    def test_already_a_member_is_409(self, session_client, members_url):
        with mock.patch(GET, return_value=auth_says(person())):
            assert add(session_client, members_url, sub=SUB, role=15).status_code == 201
            assert add(session_client, members_url, sub=SUB, role=20).status_code == 409

    def test_someone_who_left_comes_back_with_the_new_role(self, session_client, workspace, members_url):
        with mock.patch(GET, return_value=auth_says(person())):
            add(session_client, members_url, sub=SUB, role=15)
            WorkspaceMember.objects.filter(workspace=workspace, member__accounts__provider_account_id=SUB).update(
                is_active=False
            )
            assert add(session_client, members_url, sub=SUB, role=20).status_code == 201
        member = WorkspaceMember.objects.get(workspace=workspace, member__accounts__provider_account_id=SUB)
        assert (member.is_active, member.role) == (True, 20)

    def test_a_person_who_already_signed_in_keeps_their_user(self, session_client, workspace, members_url):
        user = User.objects.create(email="ana@example.com", username="ana")
        Account.objects.create(
            user=user, provider="chandelier", provider_account_id=SUB, access_token="", metadata={}
        )
        with mock.patch(GET, return_value=auth_says(person())):
            assert add(session_client, members_url, sub=SUB, role=15).status_code == 201
        assert WorkspaceMember.objects.get(workspace=workspace, member=user).role == 15
        assert User.objects.filter(accounts__provider_account_id=SUB).count() == 1


@pytest.mark.contract
@pytest.mark.django_db
class TestDirectory:
    def get(self, client, url, **kw):
        return client.get(url, HTTP_X_CHANDELIER_ASSERTION=ASSERTION, **kw)

    def test_lists_people_and_marks_who_is_in_the_workspace(self, session_client, workspace, directory_url):
        user = User.objects.create(email=f"{SUB}@chandelier.local", username="ana")
        Account.objects.create(user=user, provider="chandelier", provider_account_id=SUB, access_token="", metadata={})
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
        body = {"users": [person(), person(sub=OTHER_SUB, name="Beto")], "next_cursor": "c2"}
        with mock.patch(GET, return_value=FakeResponse(200, body)) as get:
            res = self.get(session_client, directory_url + "?q=an&limit=10")
        assert res.status_code == 200
        data = res.json()
        assert [(u["id"], u["is_member"]) for u in data["users"]] == [(SUB, True), (OTHER_SUB, False)]
        assert data["next_cursor"] == "c2"
        url = get.call_args[0][0]
        assert "q=an" in url and "limit=10" in url

    def test_never_shows_suspended_people(self, session_client, directory_url):
        body = {"users": [person(), person(sub=OTHER_SUB, status="suspended")]}
        with mock.patch(GET, return_value=FakeResponse(200, body)):
            res = self.get(session_client, directory_url)
        assert [u["id"] for u in res.json()["users"]] == [SUB]

    def test_only_workspace_admins(self, api_client, workspace, directory_url):
        member = User.objects.create(email="m@example.com", username="m")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15)
        api_client.force_authenticate(user=member)
        with mock.patch(GET) as get:
            assert self.get(api_client, directory_url).status_code == 403
        get.assert_not_called()

    def test_auth_not_allowing_the_directory_is_explained(self, session_client, directory_url):
        with mock.patch(GET, return_value=FakeResponse(403)):
            res = self.get(session_client, directory_url)
        assert res.status_code == 403
        assert res.json()["error_code"] == 403

    def test_not_available_outside_chandelier(self, session_client, directory_url, monkeypatch):
        monkeypatch.delenv("CHANDELIER_AUTH_AUDIENCE")
        monkeypatch.delenv("CHANDELIER_AUTH_MODE")
        assert self.get(session_client, directory_url).status_code == 404

    def test_bad_limit_is_400(self, session_client, directory_url):
        with mock.patch(GET, return_value=auth_says()):
            assert self.get(session_client, directory_url + "?limit=many").status_code == 400
