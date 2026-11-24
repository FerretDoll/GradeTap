import { defineStore } from "pinia";

import * as authApi from "../api/auth";
import { clearSessionData } from "./index";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    me: null,
    resolved: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.me),
    isActive: (state) => state.me?.account_status === "active",
    isAdmin: (state) => state.me?.platform_role === "admin" && state.me?.account_status === "active",
    homeRoute() {
      if (!this.me) return { name: "login" };
      if (!this.isActive) return { name: "accountStatus" };
      return this.isAdmin ? { name: "adminTeachers" } : { name: "offerings" };
    },
  },
  actions: {
    async resolveSession() {
      if (this.resolved) return this.me;
      await this.refreshMe();
      return this.me;
    },
    async refreshMe() {
      try {
        this.setMe(await authApi.getMe());
      } catch (error) {
        if (error?.response?.status !== 401) throw error;
        this.setMe(null);
      } finally {
        this.resolved = true;
      }
      return this.me;
    },
    setMe(me) {
      if (this.me && me?.user_id !== this.me.user_id) {
        clearSessionData();
        this.resolved = true;
      }
      this.me = me;
    },
    async login(payload) {
      clearSessionData();
      this.setMe(await authApi.login(payload));
      this.resolved = true;
      return this.me;
    },
    async logout() {
      try {
        await authApi.logout();
      } catch {
        // The session is cleared locally even if the server already revoked it.
      }
      this.expireSession();
    },
    expireSession() {
      clearSessionData();
      this.resolved = true;
    },
    async resubmit(payload) {
      this.setMe(await authApi.resubmitApplication(payload));
      return this.me;
    },
  },
});
