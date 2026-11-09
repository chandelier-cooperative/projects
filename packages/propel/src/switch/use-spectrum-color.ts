/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useLayoutEffect, useRef, useState } from "react";

// Chandelier (regla 3): la pista de un switch encendido usa un color del espectro.
// Los switches de una pantalla recorren el arcoíris en orden, de arriba abajo (rojo, naranja, amarillo...).
const SPECTRUM_TOKENS = [
  "var(--ch-red)",
  "var(--ch-orange)",
  "var(--ch-yellow)",
  "var(--ch-green)",
  "var(--ch-blue)",
  "var(--ch-indigo)",
  "var(--ch-violet)",
] as const;

export function useSpectrumColor<T extends HTMLElement = HTMLButtonElement>() {
  const ref = useRef<T>(null);
  const [index, setIndex] = useState(0);

  // Antes de pintar: posición de este switch entre todos los switches del documento
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const all = Array.from(document.querySelectorAll('[role="switch"]'));
    const position = all.indexOf(el);
    if (position >= 0) setIndex(position % SPECTRUM_TOKENS.length);
  }, []);

  return { ref, color: SPECTRUM_TOKENS[index] };
}
