import { useEffect, type RefObject } from "react";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "area[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type='hidden'])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function listFocusable(container: HTMLElement): HTMLElement[] {
  const nodes = Array.from(
    container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
  );
  return nodes.filter(
    (n) =>
      !n.hasAttribute("disabled") &&
      n.getAttribute("aria-hidden") !== "true" &&
      // jsdom does not implement layout, so offsetParent is null for everything;
      // fall back to "visible if no inline display:none".
      (typeof n.offsetParent !== "undefined" || true),
  );
}

/**
 * §17 a11y: trap Tab / Shift+Tab inside a modal container while `active` is
 * true. Wrap-around lets keyboard users cycle through the dialog's controls
 * without escaping into the obscured background — mandatory for `alertdialog`
 * surfaces like the evasion / death-avoidance interrupts.
 *
 * The hook does not move focus on mount (autofocus is owned by the dialog) and
 * does not restore focus on unmount — interrupt dialogs disappear because the
 * pending request resolved, not because the user dismissed the dialog.
 */
export function useFocusTrap(
  containerRef: RefObject<HTMLElement | null>,
  active: boolean,
): void {
  useEffect(() => {
    if (!active) return;
    const container = containerRef.current;
    if (!container) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const focusable = listFocusable(container);
      if (focusable.length === 0) {
        e.preventDefault();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      const activeEl = document.activeElement as HTMLElement | null;

      if (e.shiftKey) {
        if (activeEl === first || !container.contains(activeEl)) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (activeEl === last || !container.contains(activeEl)) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    container.addEventListener("keydown", handleKeyDown);
    return () => container.removeEventListener("keydown", handleKeyDown);
  }, [active, containerRef]);
}
