/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { EIconSize } from "@plane/constants";
import type { TIntakeStateGroups } from "@plane/types";

export interface IStateGroupIcon {
  className?: string;
  color?: string;
  stateGroup: TStateGroups;
  size?: EIconSize;
  percentage?: number;
}

export interface IIntakeStateGroupIcon {
  className?: string;
  color?: string;
  stateGroup: TIntakeStateGroups;
  size?: EIconSize;
  percentage?: number;
}

export type TStateGroups = "backlog" | "unstarted" | "started" | "completed" | "cancelled";

export const STATE_GROUP_COLORS: {
  [key in TStateGroups]: string;
} = {
  backlog: "#5c5c5c",
  unstarted: "#5c5c5c",
  started: "#ffd60a",
  completed: "#30d158",
  cancelled: "#9a9a9a",
};

export const INTAKE_STATE_GROUP_COLORS: { [key in TIntakeStateGroups]: string } = { triage: "#5c5c5c" };

export const STATE_GROUP_SIZES: {
  [key in EIconSize]: string;
} = {
  [EIconSize.XS]: "10px",
  [EIconSize.SM]: "12px",
  [EIconSize.MD]: "14px",
  [EIconSize.LG]: "16px",
  [EIconSize.XL]: "18px",
};
