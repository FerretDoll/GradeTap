import { defineStore } from "pinia";

import { createOffering, listOfferings } from "../api/offerings";

export const useOfferingStore = defineStore("offerings", {
  state: () => ({
    items: [],
    loading: false,
    loaded: false,
  }),
  getters: {
    byId: (state) => (offeringId) => state.items.find((item) => item.id === Number(offeringId)),
    creatable: (state) => state.items.filter((item) => item.allowed_actions?.includes("create_task")),
  },
  actions: {
    async fetchOfferings({ force = false } = {}) {
      if (this.loaded && !force) return this.items;
      this.loading = true;
      try {
        this.items = await listOfferings();
        this.loaded = true;
      } finally {
        this.loading = false;
      }
      return this.items;
    },
    async createOffering(payload) {
      const offering = await createOffering(payload);
      this.items = [...this.items, offering];
      return offering;
    },
  },
});
