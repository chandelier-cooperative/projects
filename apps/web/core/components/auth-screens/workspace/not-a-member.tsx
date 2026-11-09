/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// layouts
import DefaultLayout from "@/layouts/default-layout";

export function NotAWorkspaceMember() {
  return (
    <DefaultLayout>
      <div className="grid h-full place-items-center p-4">
        <div className="space-y-8 text-center">
          <div className="space-y-2">
            <h3 className="text-16 font-medium">Not Authorized!</h3>
            <p className="mx-auto w-1/2 text-13 text-secondary">
              You{"'"}re not a member of this workspace. Please contact the workspace admin to be added.
            </p>
          </div>
        </div>
      </div>
    </DefaultLayout>
  );
}
