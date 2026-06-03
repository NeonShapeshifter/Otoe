from __future__ import annotations


LIVE_SCRIPT = r"""
(() => {
  const root = document.getElementById("otoe-root");
  let lastFocusOutsideScope = null;
  let latestEventRequest = 0;
  const liveClientId = globalThis.crypto?.randomUUID?.()
    || `${Date.now()}-${Math.random()}`;

  const escapeSelector = (value) => {
    if (window.CSS && CSS.escape) {
      return CSS.escape(value);
    }
    return value.replace(/["\\]/g, "\\$&");
  };

  const focusSelectorFor = (target) => {
    if (!target?.dataset) {
      return null;
    }
    if (target.dataset.otoeChange) {
      return `[data-otoe-change="${escapeSelector(target.dataset.otoeChange)}"]`;
    }
    if (target.dataset.otoeKeydown) {
      return `[data-otoe-keydown="${escapeSelector(target.dataset.otoeKeydown)}"]`;
    }
    if (target.dataset.otoeClick) {
      return `[data-otoe-click="${escapeSelector(target.dataset.otoeClick)}"]`;
    }
    return null;
  };

  const focusAutoTarget = () => {
    const target = root.querySelector("[data-otoe-autofocus]");
    if (!target || typeof target.focus !== "function") {
      return;
    }
    target.focus();
    if (typeof target.select === "function") {
      target.select();
    }
  };

  const restoreFocusTarget = (selector) => {
    if (!selector) {
      return false;
    }
    const target = root.querySelector(selector);
    if (!target || typeof target.focus !== "function") {
      return false;
    }
    target.focus();
    return true;
  };

  const replaceRoot = (html, activeTarget = null, selectionStart, selectionEnd, restoreSelector = null) => {
    root.innerHTML = html;
    const focusSelector = focusSelectorFor(activeTarget);
    if (!focusSelector) {
      focusAutoTarget();
      return;
    }
    const nextTarget = root.querySelector(focusSelector);
    if (!nextTarget) {
      if (restoreFocusTarget(restoreSelector)) {
        return;
      }
      focusAutoTarget();
      return;
    }
    nextTarget.focus();
    if (
      typeof nextTarget.setSelectionRange === "function"
      && typeof selectionStart === "number"
      && typeof selectionEnd === "number"
    ) {
      nextTarget.setSelectionRange(selectionStart, selectionEnd);
    }
  };

  const focusableSelector = [
    "button:not([disabled])",
    "input:not([disabled])",
    "select:not([disabled])",
    "textarea:not([disabled])",
    "a[href]",
    "[tabindex]:not([tabindex='-1'])",
  ].join(",");

  const visibleFocusable = (scope) => {
    return Array.from(scope.querySelectorAll(focusableSelector)).filter((node) => {
      return node.offsetParent !== null || node === document.activeElement;
    });
  };

  const trapFocus = (event) => {
    if (event.key !== "Tab") {
      return false;
    }
    const scope = event.target.closest("[data-otoe-focus-scope='trap']");
    if (!scope) {
      return false;
    }
    const focusable = visibleFocusable(scope);
    if (!focusable.length) {
      event.preventDefault();
      return true;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
      return true;
    }
    if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
      return true;
    }
    return false;
  };

  const isInsideRestoringScope = (target) => {
    if (!target) {
      return false;
    }
    return Boolean(target.closest("[data-otoe-focus-scope='trap'][data-otoe-restore-focus='true']"));
  };

  const sendEvent = async (id, args, activeInput = null) => {
    const requestId = ++latestEventRequest;
    const restoreSelector = activeInput && isInsideRestoringScope(activeInput)
      ? lastFocusOutsideScope
      : null;
    if (activeInput && !isInsideRestoringScope(activeInput)) {
      lastFocusOutsideScope = focusSelectorFor(activeInput) || lastFocusOutsideScope;
    }
    try {
      const response = await fetch("/event", {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          id,
          args,
          clientId: liveClientId,
          sequence: requestId,
        }),
      });
      const payload = await response.json();
      if (requestId !== latestEventRequest) {
        return;
      }
      if (!payload.ok) {
        throw new Error(payload.error || "Otoe event failed");
      }
      replaceRoot(
        payload.html,
        activeInput,
        activeInput?.selectionStart,
        activeInput?.selectionEnd,
        restoreSelector,
      );
    } catch (error) {
      if (requestId === latestEventRequest) {
        throw error;
      }
    }
  };

  const keyPayload = (event) => ({
    key: event.key,
    ctrlKey: event.ctrlKey,
    metaKey: event.metaKey,
    altKey: event.altKey,
    shiftKey: event.shiftKey,
  });

  const isEditableTarget = (target) => {
    if (!target) {
      return false;
    }
    return target.matches("input, textarea, [contenteditable='true']");
  };

  const shouldSendGlobalKey = (event) => {
    if (event.ctrlKey || event.metaKey || event.key === "Escape") {
      return true;
    }
    return event.key.length === 1 && !isEditableTarget(event.target);
  };

  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-otoe-click]");
    if (!target) {
      return;
    }
    event.preventDefault();
    sendEvent(target.dataset.otoeClick, [], target);
  });

  document.addEventListener("focusin", (event) => {
    if (!isInsideRestoringScope(event.target)) {
      lastFocusOutsideScope = focusSelectorFor(event.target);
    }
  });

  document.addEventListener("input", (event) => {
    const target = event.target.closest("[data-otoe-change]");
    if (!target) {
      return;
    }
    sendEvent(target.dataset.otoeChange, [target.value], target);
  });

  document.addEventListener("keydown", (event) => {
    if (trapFocus(event)) {
      return;
    }
    const target = event.target.closest("[data-otoe-keydown]");
    if (target) {
      sendEvent(target.dataset.otoeKeydown, [event.key], target);
    }
    const globalTarget = root.querySelector("[data-otoe-global-keydown]");
    if (!globalTarget || !shouldSendGlobalKey(event)) {
      return;
    }
    event.preventDefault();
    sendEvent(globalTarget.dataset.otoeGlobalKeydown, [keyPayload(event)]);
  });
})();
"""
