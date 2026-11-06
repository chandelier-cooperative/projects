/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

type TPoweredBy = {
  disabled?: boolean;
};

// Insignia "Powered by" retirada en el rebranding: no se muestra ninguna marca de terceros.
export function PoweredBy(_props: TPoweredBy) {
  return null;
}
