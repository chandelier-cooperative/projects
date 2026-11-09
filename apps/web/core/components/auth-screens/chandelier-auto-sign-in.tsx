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
import { Button } from "@plane/propel/button";
// components
import { LogoSpinner } from "@/components/common/logo-spinner";
// helpers
import { authErrorHandler } from "@/helpers/authentication.helper";
import type { EAuthenticationErrorCodes } from "@/helpers/authentication.helper";
// hooks
import { useInstance } from "@/hooks/store/use-instance";

/**
 * Sign-in screen while Chandelier Auth is on (see `SignInScreen`). People are identified outside
 * Projects, so there is nothing to type: hand over to the backend, which verifies the signed
 * assertion and opens a session. After a failed attempt (`error_code` in the URL) it stops and says
 * what happened instead of retrying in a loop.
 */
export const ChandelierAutoSignIn = observer(function ChandelierAutoSignIn() {
  const { config } = useInstance();
  const searchParams = useSearchParams();
  const nextPath = searchParams.get("next_path");
  const errorCode = searchParams.get("error_code");
  const shouldRedirect = Boolean(config?.is_chandelier_enabled) && !errorCode;

  useEffect(() => {
    if (!shouldRedirect) return;
    const query = nextPath ? `?next_path=${encodeURIComponent(nextPath)}` : "";
    window.location.assign(`${API_BASE_URL}/auth/chandelier/${query}`);
  }, [shouldRedirect, nextPath]);

  // instance configuration is still loading
  if (!config || shouldRedirect) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-surface-1">
        <LogoSpinner />
      </div>
    );
  }

  const message = errorCode ? authErrorHandler(errorCode as EAuthenticationErrorCodes)?.message : undefined;

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-surface-1 p-4">
      <div className="space-y-6 text-center">
        <div className="space-y-2">
          <h3 className="text-16 font-medium">Could not sign you in</h3>
          <p className="mx-auto max-w-md text-13 text-secondary">
            {message ?? "Chandelier could not confirm who you are. Try again."}
          </p>
        </div>
        <Button variant="primary" onClick={() => window.location.assign("/")}>
          Try again
        </Button>
      </div>
    </div>
  );
});
