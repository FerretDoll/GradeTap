import { createPinia } from "pinia";

import { clearBusinessStorage } from "../utils/sessionCache";

const registeredStores = new Set();

export const pinia = createPinia();

pinia.use(({ store }) => {
  registeredStores.add(store);
});

export function clearSessionData() {
  registeredStores.forEach((store) => store.$reset());
  clearBusinessStorage();
}
