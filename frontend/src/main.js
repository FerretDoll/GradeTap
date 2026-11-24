import { createApp } from "vue";
import ElementPlus, { ElMessage } from "element-plus";
import "element-plus/dist/index.css";

import App from "./App.vue";
import { apiErrorMessage, onAuthError } from "./api/client";
import { router } from "./router";
import { pinia } from "./stores";
import { useAuthStore } from "./stores/authStore";
import { clearBusinessStorage } from "./utils/sessionCache";
import "./styles.css";

clearBusinessStorage();

const app = createApp(App);

app.use(pinia);
app.use(router);
app.use(ElementPlus);

const auth = useAuthStore(pinia);

onAuthError("sessionExpired", (error) => {
  if (!auth.isAuthenticated) return;
  auth.expireSession();
  ElMessage.warning(apiErrorMessage(error, "登录已失效，请重新登录"));
  router.replace({ name: "login" });
});

onAuthError("approvalRequired", async () => {
  await auth.refreshMe().catch(() => null);
  if (!auth.isActive) router.replace({ name: "accountStatus" });
});

app.mount("#app");
