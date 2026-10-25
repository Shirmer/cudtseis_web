<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PlanetHero from '../components/PlanetHero.vue'
import { SITE, localeFromPath } from '../config/site'
import { usePageMeta } from '../composables/usePageMeta'

const route = useRoute()
const router = useRouter()
const locale = computed(() => localeFromPath(route.path))

const copy = computed(() => locale.value === 'zh'
  ? { back: '返回首页', brand: '深视地球', tip: '拖动旋转 · 点击点位聚焦 · ⌘/Ctrl + 滚轮缩放 · Esc 返回' }
  : { back: 'Back home', brand: SITE.brandEn, tip: 'Drag to rotate · Click a marker to focus · ⌘/Ctrl + wheel to zoom · Esc to exit' })

usePageMeta(() => locale.value, () => ({
  title: locale.value === 'zh' ? `交互式地球 | ${SITE.brandZh}` : `Interactive Earth | ${SITE.brandEn}`,
  description:
    locale.value === 'zh'
      ? '一个可以拖动、缩放的三维地球：云层、天气系统、地震事件、洋流与地质构造数据的可视化演示。'
      : 'A draggable, zoomable 3D Earth visualising cloud cover, weather systems, earthquakes, ocean currents and geological structures.'
}))

function close() {
  router.push(locale.value === 'en' ? '/en' : '/')
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') close()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="earth-page">
    <!-- 顶栏放在最前面，保证 Tab 顺序先到「返回」 -->
    <header class="earth-bar">
      <button type="button" class="earth-back" @click="close">
        <span aria-hidden="true">←</span>{{ copy.back }}
      </button>
      <span class="earth-brand">{{ copy.brand }}<i>/</i>ORBITAL VIEW</span>
    </header>

    <PlanetHero variant="full" :locale="locale" />

    <p class="earth-tip">{{ copy.tip }}</p>

    <!-- 后续业务 UI（点位、图例、数据图层、侧栏等）叠加在这一层，z-index 高于 3 即可 -->
  </div>
</template>

<style scoped>
.earth-page {
  position: fixed;
  inset: 0;
  overflow: hidden;
  background: #02040a;
  animation: earth-enter 700ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.earth-page::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  background: linear-gradient(180deg, rgba(3, 6, 12, 0.55) 0%, transparent 18%, transparent 78%, rgba(3, 6, 12, 0.6) 100%);
}

.earth-bar {
  animation: bar-in 520ms cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: 80ms;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 4;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px clamp(16px, 3vw, 40px);
  pointer-events: none;
}

.earth-back {
  pointer-events: auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding: 0 18px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  background: rgba(6, 12, 20, 0.6);
  backdrop-filter: blur(10px);
  color: rgba(255, 255, 255, 0.86);
  font-size: 13px;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: background 180ms ease, border-color 180ms ease, color 180ms ease;
}

.earth-back:focus-visible {
  outline: 2px solid #d97a1c;
  outline-offset: 2px;
}

.earth-back:hover {
  border-color: rgba(217, 122, 28, 0.7);
  background: rgba(217, 122, 28, 0.85);
  color: #fff;
}

.earth-brand {
  font-size: 11px;
  letter-spacing: 0.32em;
  color: rgba(255, 255, 255, 0.55);
  white-space: nowrap;
}

.earth-brand i {
  margin: 0 10px;
  font-style: normal;
  color: rgba(217, 122, 28, 0.9);
}

.earth-tip {
  position: absolute;
  left: clamp(16px, 3vw, 40px);
  bottom: clamp(18px, 3vh, 34px);
  z-index: 4;
  margin: 0;
  color: rgba(255, 255, 255, 0.42);
  font-size: 12px;
  letter-spacing: 0.08em;
}

@keyframes bar-in {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: none; }
}

@keyframes earth-enter {
  from {
    opacity: 0;
    transform: scale(1.07);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@media (max-width: 720px) {
  .earth-brand {
    display: none;
  }

  .earth-tip {
    display: none;
  }
}

/* 窄屏放不下底部提示（会和右下工具条撞），首次引导已经承担了说明职责 */
@media (max-width: 900px), (max-height: 520px) and (orientation: landscape) {
  .earth-tip {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .earth-page,
  .earth-bar {
    animation: none;
  }
}
</style>
