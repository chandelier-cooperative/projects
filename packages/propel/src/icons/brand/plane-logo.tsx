/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

import type { ISvgIcons } from "../type";
import { CHANDELIER_LOGO_DATA_URI } from "./chandelier-logo-data";

// Mantiene el nombre PlaneLogo para no tocar a quienes lo importan; dibuja el logotipo de Chandelier.
// Alto mínimo 22 px; por debajo, usar el favicon.
export function PlaneLogo({ width, height, className }: ISvgIcons) {
  return (
    <img
      src={CHANDELIER_LOGO_DATA_URI}
      width={width}
      height={height}
      className={className}
      alt="Chandelier"
      decoding="async"
      draggable={false}
    />
  );
}
