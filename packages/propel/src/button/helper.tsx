/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { VariantProps } from "class-variance-authority";
import { cva } from "class-variance-authority";

export const buttonVariants = cva(
  "ch-halo inline-flex items-center justify-center gap-1 whitespace-nowrap transition-colors focus-visible:outline-none disabled:pointer-events-none",
  {
    variants: {
      variant: {
        primary: "ch-primary text-primary",
        "error-fill": "ch-btn ch-btn-danger",
        "error-outline": "ch-btn ch-btn-danger",
        secondary: "ch-btn",
        tertiary: "ch-btn",
        ghost: "ch-btn",
        link: "px-0 text-link-primary underline hover:text-link-primary-hover focus:text-link-primary-hover active:text-link-primary-hover disabled:opacity-40",
      },
      size: {
        sm: "h-5 rounded-sm px-1.5 text-caption-md-medium",
        base: "h-6 rounded-md px-2 text-body-xs-medium",
        lg: "h-7 rounded-md px-2 text-body-xs-medium",
        xl: "h-8 rounded-md px-2 text-body-sm-medium",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "base",
    },
  }
);

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    appendIcon?: React.ReactElement;
    loading?: boolean;
    prependIcon?: React.ReactElement;
  };

export type TButtonVariant = NonNullable<ButtonProps["variant"]>;
export type TButtonSize = NonNullable<ButtonProps["size"]>;

const buttonIconStyling: Record<TButtonSize, string> = {
  sm: "size-3.5",
  base: "size-3.5",
  lg: "size-4",
  xl: "size-4 ",
};

export function getIconStyling(size: TButtonSize): string {
  return buttonIconStyling[size];
}

export function getButtonStyling(variant: TButtonVariant, size: TButtonSize): string {
  return buttonVariants({ variant, size });
}
