const BUSINESS_STORAGE_PREFIX = "gradetap.";

const memory = new Map();

// Storage-compatible cache that only lives for the current signed-in session.
// Business data must never be persisted to localStorage, otherwise it leaks across teacher accounts.
export const sessionCache = {
  getItem(key) {
    return memory.has(key) ? memory.get(key) : null;
  },
  setItem(key, value) {
    memory.set(key, String(value));
  },
  removeItem(key) {
    memory.delete(key);
  },
  clear() {
    memory.clear();
  },
};

export function clearBusinessStorage() {
  sessionCache.clear();
  for (const storage of [window.localStorage, window.sessionStorage]) {
    Object.keys(storage)
      .filter((key) => key.startsWith(BUSINESS_STORAGE_PREFIX))
      .forEach((key) => storage.removeItem(key));
  }
}
