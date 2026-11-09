/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// components
import { LogoSpinner } from "@/components/common/logo-spinner";
// helpers
import { EAuthModes } from "@/helpers/authentication.helper";
// hooks
import { useInstance } from "@/hooks/store/use-instance";
// local imports
import { AuthBase } from "./auth-base";
import { ChandelierAutoSignIn } from "./chandelier-auto-sign-in";

/**
 * Projects runs in two modes. Inside Chandelier (Chandelier Auth on) the person is identified by the
 * network and is sent straight through. Running on its own, the usual email, magic code and OAuth
 * sign-in applies.
 */
type Props = {
  authType?: EAuthModes;
};

export const SignInScreen = observer(function SignInScreen({ authType = EAuthModes.SIGN_IN }: Props) {
  const { config } = useInstance();

  // instance configuration is still loading
  if (!config)
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-surface-1">
        <LogoSpinner />
      </div>
    );

  if (config.is_chandelier_enabled) return <ChandelierAutoSignIn />;
  return <AuthBase authType={authType} />;
});
