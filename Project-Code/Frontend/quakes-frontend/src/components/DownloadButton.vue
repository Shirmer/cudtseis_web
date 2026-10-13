<script setup lang="ts">
import { computed } from 'vue'
import { useApkDownload, useLatestRelease } from '../composables/useLatestRelease'
import type { Locale } from '../config/site'

const props = withDefaults(defineProps<{
  locale: Locale
  variant?: 'primary' | 'dark' | 'light'
}>(), {
  variant: 'primary'
})

const { loading, failed, release } = useLatestRelease()
const { download } = useApkDownload()

const label = computed(() => {
  if (props.locale === 'zh') {
    if (loading.value) return '正在获取最新版本…'
    if (failed.value && !release.value) return '点击重试下载'
    return '下载安卓版 APK'
  }
  if (loading.value) return 'Fetching latest version…'
  if (failed.value && !release.value) return 'Retry download'
  return 'Download Android APK'
})

async function handleClick() {
  if (loading.value) return
  await download()
}
</script>

<template>
  <button
    class="download-button"
    :class="[`variant-${variant}`, { busy: loading }]"
    type="button"
    :disabled="loading"
    @click="handleClick"
  >
    <span class="icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 3v12" />
        <polyline points="7 10 12 15 17 10" />
        <path d="M5 19h14" />
      </svg>
    </span>
    <span>{{ label }}</span>
  </button>
</template>

<style scoped>
.download-button {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 14px 26px;
  border: 0;
  border-radius: 999px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 180ms ease, background 180ms ease, color 180ms ease, box-shadow 180ms ease;
}

.download-button:disabled {
  cursor: wait;
  opacity: 0.72;
}

.download-button:not(:disabled):hover {
  transform: translateY(-2px);
}

.icon {
  display: inline-flex;
  width: 18px;
  height: 18px;
}

.icon svg {
  width: 100%;
  height: 100%;
}

.variant-primary {
  color: #fff;
  background: #d97a1c;
  box-shadow: 0 14px 30px rgba(217, 122, 28, 0.28);
}

.variant-primary:not(:disabled):hover {
  background: #b9620e;
}

.variant-dark {
  color: #fff;
  background: #10181d;
}

.variant-dark:not(:disabled):hover {
  background: #d97a1c;
}

.variant-light {
  color: #10181d;
  background: #fff;
}

.variant-light:not(:disabled):hover {
  color: #fff;
  background: #d97a1c;
}
</style>
