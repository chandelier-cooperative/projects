/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// hooks
import { useInstance } from "@/hooks/store";
// local imports
import { coreSidebarMenuLinks } from "./core";
import type { TSidebarMenuItem } from "./types";

export function useSidebarMenu(): TSidebarMenuItem[] {
  const { config } = useInstance();
  // Chandelier Auth is the only way in while it is on: there are no sign-in methods to configure
  const isChandelierEnabled = Boolean(config?.is_chandelier_enabled);

  return [
    coreSidebarMenuLinks.general,
    coreSidebarMenuLinks.email,
    ...(isChandelierEnabled ? [] : [coreSidebarMenuLinks.authentication]),
    coreSidebarMenuLinks.workspace,
    coreSidebarMenuLinks.ai,
    coreSidebarMenuLinks.image,
  ];
}
