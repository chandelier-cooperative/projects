/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// ui
import { Button } from "@plane/propel/button";
// layouts
import DefaultLayout from "@/layouts/default-layout";

/**
 * Shown to a signed-in person who does not belong to any workspace yet.
 * People are added to workspaces from Chandelier, so there is nothing to create or accept here.
 */
export function NoWorkspace() {
  return (
    <DefaultLayout>
      <div className="grid h-full place-items-center p-4">
        <div className="space-y-8 text-center">
          <div className="space-y-2">
            <h3 className="text-16 font-medium">No workspace yet</h3>
            <p className="mx-auto max-w-md text-13 text-secondary">
              You are not part of any workspace. Ask your Chandelier administrator to add you, then check again.
            </p>
          </div>
          <div className="flex items-center justify-center gap-2">
            <Button variant="primary" onClick={() => window.location.reload()}>
              Check again
            </Button>
          </div>
        </div>
      </div>
    </DefaultLayout>
  );
}
