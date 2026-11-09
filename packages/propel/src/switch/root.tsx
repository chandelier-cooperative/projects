/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";
import { Switch as BaseSwitch } from "@base-ui-components/react/switch";
import { cn } from "../utils/classname";
import { useSpectrumColor } from "./use-spectrum-color";

export interface IToggleSwitchProps {
  value: boolean;
  onChange: (value: boolean) => void;
  label?: string;
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  className?: string;
}

function Switch({ value, onChange, label, size = "sm", disabled, className }: IToggleSwitchProps) {
  const { ref, color: activeColor } = useSpectrumColor();
  return (
    <BaseSwitch.Root
      ref={ref}
      checked={value}
      disabled={disabled}
      onCheckedChange={onChange}
      aria-label={label}
      style={value ? { backgroundColor: activeColor } : undefined}
      className={cn(
        "relative inline-flex flex-shrink-0 cursor-pointer rounded-full border border-subtle transition-colors duration-200 ease-in-out focus:outline-none",
        // size
        size === "sm" ? "h-4 w-6" : size === "md" ? "h-5 w-8" : "h-6 w-10",
        // state
        disabled
          ? value
            ? "cursor-not-allowed opacity-50"
            : "cursor-not-allowed bg-layer-1"
          : value
            ? "cursor-pointer"
            : "cursor-pointer bg-surface-2",
        className
      )}
    >
      {label && <span className="sr-only">{label}</span>}
      <BaseSwitch.Thumb
        aria-hidden="true"
        style={value ? { backgroundColor: "var(--ch-bg)" } : undefined}
        className={cn(
          "shadow inline-block self-center rounded-full ring-0 transition-transform duration-200 ease-in-out",
          // size
          size === "sm" ? "h-3 w-3" : size === "md" ? "h-4 w-4" : "h-5 w-5",
          // position + color by state
          value
            ? size === "sm"
              ? "translate-x-3"
              : size === "md"
                ? "translate-x-4"
                : "translate-x-5"
            : "translate-x-0.5 bg-surface-2",
          // disabled
          disabled && !value && "cursor-not-allowed bg-surface-2"
        )}
      />
    </BaseSwitch.Root>
  );
}

Switch.displayName = "plane-ui-switch";

export { Switch };
