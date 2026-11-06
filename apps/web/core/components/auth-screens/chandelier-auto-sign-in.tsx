/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { useSearchParams } from "next/navigation";
// plane imports
import { API_BASE_URL } from "@plane/constants";
// components
import { LogoSpinner } from "@/components/common/logo-spinner";
// hooks
import { useInstance } from "@/hooks/store/use-instance";

/**
 * When Chandelier Auth is enabled the person is already identified by the network, so there is
 * nothing to type: hand over to the backend, which verifies the signed assertion and opens a session.
 * After a failed attempt (`error_code` in the URL) it steps aside so the usual form and the error show.
 */
export const ChandelierAutoSignIn = observer(function ChandelierAutoSignIn() {
  const { config } = useInstance();
  const searchParams = useSearchParams();
  const nextPath = searchParams.get("next_path");
  const shouldRedirect = Boolean(config?.is_chandelier_enabled) && !searchParams.get("error_code");

  useEffect(() => {
    if (!shouldRedirect) return;
    const query = nextPath ? `?next_path=${encodeURIComponent(nextPath)}` : "";
    window.location.assign(`${API_BASE_URL}/auth/chandelier/${query}`);
  }, [shouldRedirect, nextPath]);

  if (!shouldRedirect) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-surface-1">
      <LogoSpinner />
    </div>
  );
});
