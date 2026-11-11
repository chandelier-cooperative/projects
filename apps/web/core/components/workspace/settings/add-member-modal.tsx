/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { ROLE } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { ChevronDownIcon, SearchIcon } from "@plane/propel/icons";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Avatar, CustomSelect, EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
// hooks
import { useMember } from "@/hooks/store/use-member";
// services
import type { TAuthDirectoryError, TAuthPerson } from "@/services/workspace.service";
import { WorkspaceService } from "@/services/workspace.service";

const workspaceService = new WorkspaceService();

const ADDABLE_ROLES = [20, 15] as const;
type TAddableRole = (typeof ADDABLE_ROLES)[number];

type Props = {
  isOpen: boolean;
  onClose: () => void;
  workspaceSlug: string;
};

/**
 * Add people to the workspace from the people Auth knows. Nobody is invited by email: the list comes from Auth
 * (through the API, never straight from the browser), and adding someone makes them a member right away.
 */
export const AddWorkspaceMemberModal = observer(function AddWorkspaceMemberModal(props: Props) {
  const { isOpen, onClose, workspaceSlug } = props;
  // plane hooks
  const { t } = useTranslation();
  // store hooks
  const {
    workspace: { fetchWorkspaceMembers },
  } = useMember();
  // states
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [role, setRole] = useState<TAddableRole>(15);
  const [people, setPeople] = useState<TAuthPerson[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [addingId, setAddingId] = useState<string | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  // an answer that arrives after a newer search started is dropped
  const lastRequest = useRef(0);

  const describe = useCallback((error: TAuthDirectoryError, fallback: string) => {
    if (error?.status === 403 && error?.error_code === 403) return "not_allowed";
    if (error?.status === 401) return "session_over";
    if (error?.status === 502) return "unreachable";
    return fallback;
  }, []);

  // debounce what is typed
  useEffect(() => {
    const timeout = setTimeout(() => setSearch(query.trim()), 300);
    return () => clearTimeout(timeout);
  }, [query]);

  // first page, whenever the modal opens or the search changes
  useEffect(() => {
    if (!isOpen) return;
    const request = ++lastRequest.current;
    const load = async () => {
      setIsLoading(true);
      setErrorKey(null);
      try {
        const page = await workspaceService.fetchAuthPeople(workspaceSlug, { q: search || undefined });
        if (request !== lastRequest.current) return;
        setPeople(page.users);
        setNextCursor(page.next_cursor);
      } catch (error) {
        if (request !== lastRequest.current) return;
        setPeople([]);
        setNextCursor(null);
        setErrorKey(describe(error as TAuthDirectoryError, "unreachable"));
      } finally {
        if (request === lastRequest.current) setIsLoading(false);
      }
    };
    void load();
  }, [isOpen, search, workspaceSlug, describe]);

  const handleLoadMore = async () => {
    if (!nextCursor || isLoadingMore) return;
    const request = lastRequest.current;
    setIsLoadingMore(true);
    try {
      const page = await workspaceService.fetchAuthPeople(workspaceSlug, {
        q: search || undefined,
        cursor: nextCursor,
      });
      if (request !== lastRequest.current) return;
      setPeople((current) => [...current, ...page.users]);
      setNextCursor(page.next_cursor);
    } catch (error) {
      setErrorKey(describe(error as TAuthDirectoryError, "unreachable"));
    } finally {
      setIsLoadingMore(false);
    }
  };

  const markAsMember = (id: string) =>
    setPeople((current) => current.map((p) => (p.id === id ? { ...p, is_member: true } : p)));

  const handleAdd = async (person: TAuthPerson) => {
    if (addingId) return;
    setAddingId(person.id);
    try {
      await workspaceService.addWorkspaceMember(workspaceSlug, { sub: person.id, role });
      markAsMember(person.id);
      await fetchWorkspaceMembers(workspaceSlug);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("success"),
        message: t("workspace_settings.settings.members.directory.added_success", { name: person.display_name }),
      });
    } catch (e) {
      const error = e as TAuthDirectoryError;
      if (error?.status === 409) {
        // they were added in the meantime
        markAsMember(person.id);
        return;
      }
      const key = describe(error, "add_error") as "add_error" | "not_allowed" | "session_over" | "unreachable";
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("error"),
        message: t(`workspace_settings.settings.members.directory.${key}`),
      });
    } finally {
      setAddingId(null);
    }
  };

  const handleClose = () => {
    onClose();
    // keep what was on screen while the modal fades out
    const timeout = setTimeout(() => {
      setQuery("");
      setSearch("");
      setPeople([]);
      setNextCursor(null);
      setErrorKey(null);
      clearTimeout(timeout);
    }, 300);
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={handleClose} position={EModalPosition.CENTER} width={EModalWidth.XXL}>
      <div className="p-5">
        <h3 className="text-16 leading-6 font-medium text-primary">
          {t("workspace_settings.settings.members.directory.title")}
        </h3>
        <p className="mt-2 text-13 text-secondary">{t("workspace_settings.settings.members.directory.description")}</p>

        <div className="mt-4 flex items-center gap-2">
          <div className="flex grow items-center gap-1.5 rounded-md border border-subtle bg-surface-1 px-2.5 py-1.5">
            <SearchIcon className="h-3.5 w-3.5 text-placeholder" />
            <input
              className="w-full border-none bg-transparent text-13 outline-none placeholder:text-placeholder"
              placeholder={t("workspace_settings.settings.members.directory.search_placeholder")}
              value={query}
              // eslint-disable-next-line jsx-a11y/no-autofocus
              autoFocus
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <CustomSelect
            value={role}
            onChange={(value: string) => setRole(parseInt(value) as TAddableRole)}
            customButton={
              <div
                className="flex w-28 items-center justify-between gap-1 rounded-md border border-subtle px-3 py-2 text-left text-13 text-secondary duration-300 hover:bg-layer-1 hover:text-primary focus:outline-none"
                aria-label={t("workspace_settings.settings.members.directory.role")}
              >
                <span className="capitalize">{ROLE[role]}</span>
                <ChevronDownIcon className="h-3 w-3" aria-hidden="true" />
              </div>
            }
            input
          >
            {ADDABLE_ROLES.map((value) => (
              <CustomSelect.Option key={value} value={value}>
                {ROLE[value]}
              </CustomSelect.Option>
            ))}
          </CustomSelect>
        </div>

        <div className="mt-4 max-h-80 min-h-32 divide-y-[0.5px] divide-subtle overflow-y-auto">
          {errorKey && (
            <p className="py-6 text-center text-13 text-danger-primary">
              {t(
                `workspace_settings.settings.members.directory.${errorKey as "not_allowed" | "session_over" | "unreachable"}`
              )}
            </p>
          )}
          {!errorKey && !isLoading && people.length === 0 && (
            <p className="py-6 text-center text-13 text-placeholder">
              {t("workspace_settings.settings.members.directory.empty")}
            </p>
          )}
          {!errorKey &&
            people.map((person) => (
              <div key={person.id} className="flex items-center justify-between gap-3 py-2.5">
                <div className="flex min-w-0 items-center gap-2.5">
                  <Avatar name={person.display_name} />
                  <div className="min-w-0">
                    <p className="truncate text-13 text-primary">{person.display_name}</p>
                    {person.logins.length > 0 && (
                      <p className="truncate text-11 text-tertiary">{person.logins.join(", ")}</p>
                    )}
                  </div>
                </div>
                {person.is_member ? (
                  <span className="shrink-0 text-12 text-placeholder">
                    {t("workspace_settings.settings.members.directory.already_member")}
                  </span>
                ) : (
                  <Button
                    variant="secondary"
                    size="sm"
                    loading={addingId === person.id}
                    disabled={addingId !== null}
                    onClick={() => handleAdd(person)}
                  >
                    {t("workspace_settings.settings.members.directory.add")}
                  </Button>
                )}
              </div>
            ))}
          {!errorKey && nextCursor && (
            <div className="flex justify-center py-3">
              <Button variant="secondary" size="sm" loading={isLoadingMore} onClick={handleLoadMore}>
                {t("workspace_settings.settings.members.directory.load_more")}
              </Button>
            </div>
          )}
        </div>

        <div className="mt-5 flex justify-end">
          <Button variant="secondary" size="lg" onClick={handleClose}>
            {t("cancel")}
          </Button>
        </div>
      </div>
    </ModalCore>
  );
});
