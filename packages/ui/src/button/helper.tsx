/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TButtonVariant =
  | "primary"
  | "accent-primary"
  | "outline-primary"
  | "neutral-primary"
  | "link-primary"
  | "danger"
  | "accent-danger"
  | "outline-danger"
  | "link-danger"
  | "tertiary-danger"
  | "link-neutral";

export type TButtonSizes = "sm" | "md" | "lg" | "xl";

export interface IButtonStyling {
  [key: string]: {
    default: string;
    hover: string;
    pressed: string;
    disabled: string;
  };
}

enum buttonSizeStyling {
  sm = `px-3 py-1.5 font-medium text-11 rounded-sm flex items-center gap-1.5 whitespace-nowrap transition-all justify-center`,
  md = `px-4 py-1.5 font-medium text-13 rounded-sm flex items-center gap-1.5 whitespace-nowrap transition-all justify-center`,
  lg = `px-5 py-2 font-medium text-13 rounded-sm flex items-center gap-1.5 whitespace-nowrap transition-all justify-center`,
  xl = `px-5 py-3.5 font-medium text-13 rounded-sm flex items-center gap-1.5 whitespace-nowrap transition-all justify-center`,
}

enum buttonIconStyling {
  sm = "h-3 w-3 flex justify-center items-center overflow-hidden my-0.5 flex-shrink-0",
  md = "h-3.5 w-3.5 flex justify-center items-center overflow-hidden my-0.5 flex-shrink-0",
  lg = "h-4 w-4 flex justify-center items-center overflow-hidden my-0.5 flex-shrink-0",
  xl = "h-4 w-4 flex justify-center items-center overflow-hidden my-0.5 flex-shrink-0 ",
}

export const buttonStyling: IButtonStyling = {
  // Chandelier (regla 2): botones blancos, borde arcoíris en hover, deshabilitado = blanco con opacidad .4.
  primary: {
    default: `ch-primary text-primary`,
    hover: ``,
    pressed: ``,
    disabled: `cursor-not-allowed`,
  },
  "accent-primary": {
    default: `ch-btn`,
    hover: ``,
    pressed: ``,
    disabled: `cursor-not-allowed`,
  },
  "outline-primary": {
    default: `ch-btn`,
    hover: ``,
    pressed: ``,
    disabled: `cursor-not-allowed`,
  },
  "neutral-primary": {
    default: `ch-btn`,
    hover: ``,
    pressed: ``,
    disabled: `cursor-not-allowed`,
  },
  "link-primary": {
    default: `text-accent-primary bg-surface-1`,
    hover: `hover:text-accent-secondary`,
    pressed: `focus:text-accent-primary/80 `,
    disabled: `cursor-not-allowed opacity-40`,
  },
  danger: {
    default: `ch-btn ch-btn-danger`,
    hover: ``,
    pressed: ``,
    disabled: `cursor-not-allowed`,
  },
  "accent-danger": {
    default: `ch-btn ch-btn-danger`,
    hover: ``,
    pressed: ``,
    disabled: `cursor-not-allowed`,
  },
  "outline-danger": {
    default: `ch-btn ch-btn-danger`,
    hover: ``,
    pressed: ``,
    disabled: `cursor-not-allowed`,
  },
  "link-danger": {
    default: `text-danger-primary bg-surface-1`,
    hover: `hover:text-danger-primary`,
    pressed: `focus:text-danger-primary`,
    disabled: `cursor-not-allowed opacity-40`,
  },
  "tertiary-danger": {
    default: `ch-btn ch-btn-danger`,
    hover: ``,
    pressed: ``,
    disabled: `cursor-not-allowed`,
  },
  "link-neutral": {
    default: `text-primary`,
    hover: `hover:underline`,
    pressed: `focus:underline`,
    disabled: `cursor-not-allowed opacity-40`,
  },
};

export const getButtonStyling = (variant: TButtonVariant, size: TButtonSizes, disabled: boolean = false): string => {
  let tempVariant: string = ``;
  const currentVariant = buttonStyling[variant];

  tempVariant = `${currentVariant.default} ${disabled ? currentVariant.disabled : currentVariant.hover} ${
    currentVariant.pressed
  }`;

  let tempSize: string = ``;
  if (size) tempSize = buttonSizeStyling[size];
  return `${tempVariant} ${tempSize}`;
};

export const getIconStyling = (size: TButtonSizes): string => {
  let icon: string = ``;
  if (size) icon = buttonIconStyling[size];
  return icon;
};
