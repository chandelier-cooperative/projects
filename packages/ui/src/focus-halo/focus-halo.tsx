/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";

/**
 * Marca la "caja" del campo de texto que tiene el foco para que chandelier.css le dibuje el halo arcoíris.
 *
 * - `data-ch-focus="self"`: el propio input/textarea tiene borde visible.
 * - `data-ch-focus="wrap"`: el borde visible es de un contenedor cercano (login, buscadores, editores de texto).
 * - `data-ch-static`: el contenedor es `position: static` y necesita volverse `relative` mientras dure el foco.
 * - `data-ch-inset`: el contenedor recorta su contenido (`overflow` distinto de `visible`), el halo se dibuja por dentro.
 * - `data-ch-focus-field`: el campo enfocado (para quitarle el anillo blanco).
 *
 * Si no se encuentra una caja con borde, no se marca nada y queda el anillo blanco de accesibilidad.
 */

const NON_TEXT_INPUT_TYPES = new Set([
  "checkbox",
  "radio",
  "range",
  "button",
  "submit",
  "reset",
  "file",
  "color",
  "image",
  "hidden",
]);
// El halo no debe subir más allá de un popover o diálogo.
const BOUNDARY_SELECTOR =
  "dialog, [role='dialog'], [role='listbox'], [role='menu'], [data-radix-popper-content-wrapper]";
const MAX_DEPTH_INPUT = 3;
const MAX_DEPTH_EDITOR = 6;
// Un input sin borde propio solo adopta un contenedor que lo rodee de cerca.
const MAX_EXTRA_HEIGHT_INPUT = 48;

const FOCUS_ATTRS = ["data-ch-focus", "data-ch-static", "data-ch-inset", "data-ch-focus-field"] as const;

const isTransparent = (color: string) =>
  color === "transparent" || /^rgba\([^)]*,\s*0\)$/.test(color) || /\/\s*0(\.0+)?\s*\)$/.test(color);

const hasVisibleBorder = (style: CSSStyleDeclaration) =>
  [
    [style.borderTopWidth, style.borderTopStyle, style.borderTopColor],
    [style.borderRightWidth, style.borderRightStyle, style.borderRightColor],
    [style.borderBottomWidth, style.borderBottomStyle, style.borderBottomColor],
    [style.borderLeftWidth, style.borderLeftStyle, style.borderLeftColor],
  ].every(
    ([width, borderStyle, color]) =>
      parseFloat(width) > 0 && borderStyle !== "none" && borderStyle !== "hidden" && !isTransparent(color)
  );

const getFieldKind = (el: Element | null): "input" | "textarea" | "editor" | null => {
  if (el instanceof HTMLInputElement) return NON_TEXT_INPUT_TYPES.has(el.type) || el.readOnly ? null : "input";
  if (el instanceof HTMLTextAreaElement) return el.readOnly ? null : "textarea";
  if (el instanceof HTMLElement && el.getAttribute("contenteditable") === "true") return "editor";
  return null;
};

type TFocusBox = { element: HTMLElement; mode: "self" | "wrap" };

const findFocusBox = (field: HTMLElement, kind: "input" | "textarea" | "editor"): TFocusBox | null => {
  const fieldStyle = getComputedStyle(field);
  if (hasVisibleBorder(fieldStyle)) {
    return { element: field, mode: kind === "editor" ? "wrap" : "self" };
  }

  const fieldHeight = field.getBoundingClientRect().height;
  const maxDepth = kind === "editor" ? MAX_DEPTH_EDITOR : MAX_DEPTH_INPUT;
  let current = field.parentElement;
  for (let depth = 0; current && depth < maxDepth; depth++) {
    if (current === document.body || current.matches(BOUNDARY_SELECTOR)) return null;
    if (hasVisibleBorder(getComputedStyle(current))) {
      if (kind === "input" && current.getBoundingClientRect().height > fieldHeight + MAX_EXTRA_HEIGHT_INPUT)
        return null;
      return { element: current, mode: "wrap" };
    }
    current = current.parentElement;
  }
  return null;
};

const clearMarks = () => {
  document.querySelectorAll(FOCUS_ATTRS.map((attr) => `[${attr}]`).join(",")).forEach((el) => {
    FOCUS_ATTRS.forEach((attr) => el.removeAttribute(attr));
    (el as HTMLElement).style.removeProperty("--ch-halo-r");
  });
};

const markFocus = (field: HTMLElement) => {
  clearMarks();
  const kind = getFieldKind(field);
  if (!kind) return;
  const box = findFocusBox(field, kind);
  if (!box) return;

  const style = getComputedStyle(box.element);
  field.setAttribute("data-ch-focus-field", "");
  box.element.setAttribute("data-ch-focus", box.mode);
  box.element.style.setProperty("--ch-halo-r", `${Math.max(parseFloat(style.borderTopLeftRadius) || 0, 4) + 4}px`);
  if (box.mode === "wrap") {
    if (style.position === "static") box.element.setAttribute("data-ch-static", "");
    if (style.overflow !== "visible") box.element.setAttribute("data-ch-inset", "");
  }
};

export function FocusHalo() {
  useEffect(() => {
    const handleFocusIn = (event: FocusEvent) => {
      if (event.target instanceof HTMLElement) markFocus(event.target);
    };
    const handleFocusOut = () => clearMarks();

    document.addEventListener("focusin", handleFocusIn);
    document.addEventListener("focusout", handleFocusOut);
    return () => {
      document.removeEventListener("focusin", handleFocusIn);
      document.removeEventListener("focusout", handleFocusOut);
      clearMarks();
    };
  }, []);

  return null;
}
