/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

import type { ISvgIcons } from "../type";

// Mantiene el nombre PlaneLockup para no tocar a quienes lo importan; ahora es solo el texto "Projects".
export function PlaneLockup({ height, className }: ISvgIcons) {
  const px = height === undefined ? undefined : Number(height);
  return (
    <span
      className={["inline-flex items-center leading-none font-medium tracking-tight", className]
        .filter(Boolean)
        .join(" ")}
      style={{ fontSize: px && !Number.isNaN(px) ? `${Math.round(px * 0.9)}px` : "1.5rem" }}
    >
      Projects
    </span>
  );
}
