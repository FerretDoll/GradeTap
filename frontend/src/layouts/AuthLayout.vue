<template>
  <div class="auth-shell">
    <aside class="auth-brand">
      <img class="auth-brand-logo" src="/brand/gradetap-sidebar-logo.svg" alt="GradeTap AI 作业批改助手" />
      <div class="auth-brand-copy">
        <h2>AI 初批，教师定分</h2>
        <p>上传作业，确认评分量规，按证据统一评分，复核后导出成绩。</p>
      </div>
      <span class="auth-brand-footer">© 2026 武汉软件工程职业学院 信息学院</span>
    </aside>
    <main class="auth-main">
      <div class="auth-card">
        <router-view />
      </div>
    </main>
  </div>
</template>
