/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { useSearchParams } from "next/navigation";
// plane internal packages
import { API_BASE_URL } from "@plane/constants";
import { Button } from "@plane/propel/button";
// components
import { LogoSpinner } from "@/components/common/logo-spinner";
import { InstanceFailureView } from "@/components/instance/failure";
import { InstanceSetupForm } from "@/components/instance/setup-form";
// hooks
import { useInstance } from "@/hooks/store";
// components
import type { Route } from "./+types/page";
import { AuthHeader } from "./auth-header";
import { InstanceSignInForm } from "./sign-in-form";

function HomePage() {
  // store hooks
  const { instance, config, error } = useInstance();
  const searchParams = useSearchParams();
  // While Chandelier Auth is on it is the only way in. After a failed attempt we stop and say so
  // instead of looping on redirects. With it off (running the project on its own) the usual setup
  // and sign-in forms apply.
  const hasAuthError = Boolean(searchParams.get("error_code"));
  const isChandelierEnabled = Boolean(config?.is_chandelier_enabled);
  const shouldUseChandelier = isChandelierEnabled && !hasAuthError;

  // Chandelier Auth identifies the admin: no setup form and no password.
  useEffect(() => {
    if (shouldUseChandelier) window.location.assign(`${API_BASE_URL}/api/instances/admins/chandelier/`);
  }, [shouldUseChandelier]);

  // if instance is not fetched (or we are handing over to Chandelier Auth), show loading
  if ((!instance && !error) || shouldUseChandelier) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <LogoSpinner />
      </div>
    );
  }

  // if instance fetch fails, show failure view
  if (error) {
    return <InstanceFailureView />;
  }

  // Chandelier could not confirm the admin
  if (isChandelierEnabled) {
    return (
      <>
        <AuthHeader />
        <div className="mt-10 flex w-full flex-grow flex-col items-center justify-center py-6">
          <div className="flex max-w-[22.5rem] flex-col items-center gap-4 text-center">
            <h3 className="text-20 font-medium text-on-color">Could not sign you in</h3>
            <p className="text-14 font-medium">Chandelier could not confirm that you administer this instance.</p>
            <Button onClick={() => window.location.assign(window.location.pathname)}>Try again</Button>
          </div>
        </div>
      </>
    );
  }

  // if instance is fetched and setup is not done, show setup form
  if (instance && !instance?.is_setup_done) {
    return <InstanceSetupForm />;
  }

  // if instance is fetched and setup is done, show sign in form
  return <InstanceSignInForm />;
}

export default observer(HomePage);

export const meta: Route.MetaFunction = () => [
  { title: "Admin – Instance Setup & Sign-In" },
  { name: "description", content: "Configure your Projects instance or sign in to the admin portal." },
];
