/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

import { IconWrapper } from "../icon-wrapper";
import type { ISvgIcons } from "../type";

// Mantiene el nombre PlaneNewIcon para no tocar a quienes lo importan; ahora dibuja un icono genérico (columnas).
export function PlaneNewIcon({ color = "currentColor", ...rest }: ISvgIcons) {
  return (
    <IconWrapper color={color} {...rest}>
      <rect x="2" y="2" width="5" height="12" rx="1.2" fill={color} />
      <rect x="9" y="2" width="5" height="7" rx="1.2" fill={color} />
    </IconWrapper>
  );
}
