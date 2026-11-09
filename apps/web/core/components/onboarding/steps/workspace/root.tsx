/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import { observer } from "mobx-react";
// plane imports
import { EOnboardingSteps } from "@plane/types";
// hooks
import { useUser } from "@/hooks/store/user";
// local components
import { WorkspaceCreateStep } from "./";

type Props = {
  handleStepChange: (step: EOnboardingSteps) => void;
};

export const WorkspaceSetupStep = observer(function WorkspaceSetupStep({ handleStepChange }: Props) {
  // store hooks
  const { data: user } = useUser();

  return (
    <WorkspaceCreateStep user={user} onComplete={() => handleStepChange(EOnboardingSteps.WORKSPACE_CREATE_OR_JOIN)} />
  );
});
