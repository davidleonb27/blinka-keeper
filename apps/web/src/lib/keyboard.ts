import type { KeyboardEvent } from "react";

/** In a textarea, Enter submits its form and Shift+Enter writes a new line. */
export function submitOnEnter(event: KeyboardEvent<HTMLTextAreaElement>) {
  if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
  event.preventDefault();
  event.currentTarget.form?.requestSubmit();
}
