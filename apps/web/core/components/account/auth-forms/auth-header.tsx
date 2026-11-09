/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// helpers
import { EAuthModes, EAuthSteps } from "@/helpers/authentication.helper";

type TAuthHeader = {
  authMode: EAuthModes;
  currentAuthStep: EAuthSteps;
};

const Titles = {
  [EAuthModes.SIGN_IN]: {
    [EAuthSteps.EMAIL]: {
      header: "Work in all dimensions.",
      subHeader: "Welcome back to Projects.",
    },
    [EAuthSteps.PASSWORD]: {
      header: "Work in all dimensions.",
      subHeader: "Welcome back to Projects.",
    },
    [EAuthSteps.UNIQUE_CODE]: {
      header: "Work in all dimensions.",
      subHeader: "Welcome back to Projects.",
    },
  },
  [EAuthModes.SIGN_UP]: {
    [EAuthSteps.EMAIL]: {
      header: "Work in all dimensions.",
      subHeader: "Create your Projects account.",
    },
    [EAuthSteps.PASSWORD]: {
      header: "Work in all dimensions.",
      subHeader: "Create your Projects account.",
    },
    [EAuthSteps.UNIQUE_CODE]: {
      header: "Work in all dimensions.",
      subHeader: "Create your Projects account.",
    },
  },
};

export const AuthHeader = observer(function AuthHeader(props: TAuthHeader) {
  const { authMode, currentAuthStep } = props;

  const { header, subHeader } = Titles[authMode][currentAuthStep];

  return <AuthHeaderBase subHeader={subHeader} header={header} />;
});

type TAuthHeaderBase = {
  header: React.ReactNode;
  subHeader: string;
};

export function AuthHeaderBase(props: TAuthHeaderBase) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-h4-semibold text-primary">{props.header}</span>
      <span className="text-h4-semibold text-placeholder">{props.subHeader}</span>
    </div>
  );
}
