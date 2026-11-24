import { onBeforeUnmount, ref } from "vue";

import { mockEnabled } from "../api/mock";

export function useMockMail() {
  const mockMailLink = ref(null);
  if (!mockEnabled) return { mockMailLink };

  function handleMail(event) {
    mockMailLink.value = { name: "verifyEmail", query: { token: event.detail.token } };
  }

  window.addEventListener("gradetap:mock-mail", handleMail);
  onBeforeUnmount(() => window.removeEventListener("gradetap:mock-mail", handleMail));
  return { mockMailLink };
}
