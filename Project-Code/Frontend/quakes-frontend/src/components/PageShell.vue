<script setup lang="ts">
import SiteHeader from './SiteHeader.vue'
import SiteFooter from './SiteFooter.vue'
import type { Locale } from '../config/site'

defineProps<{
  locale: Locale
  label: string
  title: string
  subtitle?: string
  meta?: string
}>()
</script>

<template>
  <div class="page-shell">
    <SiteHeader :locale="locale" />

    <main class="page-main">
      <section class="page-hero">
        <div class="page-hero-grid" aria-hidden="true"></div>
        <div class="page-hero-inner">
          <span class="page-label">{{ label }}</span>
          <h1>{{ title }}</h1>
          <p v-if="subtitle">{{ subtitle }}</p>
          <span v-if="meta" class="page-meta">{{ meta }}</span>
        </div>
      </section>

      <div class="page-content">
        <slot />
      </div>
    </main>

    <SiteFooter :locale="locale" />
  </div>
</template>

<style scoped>
.page-shell {
  min-width: 320px;
  min-height: 100vh;
  color: #10181d;
  background: #f6f4ef;
  font-family: Inter, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
}

.page-main {
  padding-top: 78px;
}

.page-hero {
  position: relative;
  overflow: hidden;
  color: #fff;
  background: #10181d;
}

.page-hero-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.045) 1px, transparent 1px);
  background-size: 72px 72px;
  pointer-events: none;
}

.page-hero::after {
  content: "";
  position: absolute;
  inset: auto -10% -60% auto;
  width: 520px;
  height: 520px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(217, 122, 28, 0.32), transparent 65%);
  pointer-events: none;
}

.page-hero-inner {
  position: relative;
  z-index: 1;
  width: min(1120px, calc(100% - 48px));
  margin: 0 auto;
  padding: 88px 0 64px;
}

.page-label {
  display: inline-block;
  padding: 6px 14px;
  border: 1px solid rgba(255, 255, 255, 0.26);
  border-radius: 999px;
  color: #f0a54c;
  font-size: 12px;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.page-hero-inner h1 {
  margin: 26px 0 14px;
  font-size: clamp(34px, 5vw, 54px);
  line-height: 1.12;
  letter-spacing: -0.01em;
}

.page-hero-inner p {
  max-width: 640px;
  margin: 0;
  color: rgba(255, 255, 255, 0.74);
  font-size: 16px;
  line-height: 1.8;
}

.page-meta {
  display: inline-block;
  margin-top: 22px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  letter-spacing: 0.06em;
}

.page-content {
  width: min(1120px, calc(100% - 48px));
  margin: 0 auto;
  padding: 56px 0 96px;
}

@media (max-width: 720px) {
  .page-hero-inner {
    width: calc(100% - 40px);
    padding: 64px 0 48px;
  }

  .page-content {
    width: calc(100% - 40px);
    padding: 40px 0 72px;
  }
}
</style>
