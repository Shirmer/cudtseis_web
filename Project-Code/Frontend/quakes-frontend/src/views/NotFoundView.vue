<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import PageShell from '../components/PageShell.vue'
import { localeFromPath, localizedPath, SITE } from '../config/site'
import { usePageMeta } from '../composables/usePageMeta'

const router = useRouter()
const locale = computed(() => localeFromPath(router.currentRoute.value.path))
const isZh = computed(() => locale.value === 'zh')

const copy = computed(() => (isZh.value
  ? {
      label: '404',
      title: '页面不存在',
      subtitle: '你访问的地址可能已经移动或被删除。可以从下面的入口继续浏览。',
      home: '返回首页',
      contact: '联系我们',
      earth: '看看交互式地球'
    }
  : {
      label: '404',
      title: 'Page not found',
      subtitle: 'The address you opened may have moved or been removed. Continue from one of the links below.',
      home: 'Back to home',
      contact: 'Contact us',
      earth: 'Explore the interactive Earth'
    }))

usePageMeta(() => locale.value, () => ({
  title: `${copy.value.title} | ${isZh.value ? SITE.brandZh : SITE.brandEn}`,
  description: copy.value.subtitle,
  noindex: true
}))

function go(path: string) {
  router.push(localizedPath(locale.value, path))
}
</script>

<template>
  <PageShell :locale="locale" :label="copy.label" :title="copy.title" :subtitle="copy.subtitle">
    <div class="not-found">
      <button class="nf-button primary" type="button" @click="go('/')">{{ copy.home }}</button>
      <button class="nf-button" type="button" @click="go('/earth')">{{ copy.earth }}</button>
      <button class="nf-button" type="button" @click="go('/contact')">{{ copy.contact }}</button>
    </div>
  </PageShell>
</template>

<style scoped>
.not-found {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 8px 0 40px;
}

.nf-button {
  height: 46px;
  padding: 0 22px;
  border: 1px solid rgba(16, 24, 29, 0.18);
  border-radius: 999px;
  background: transparent;
  color: #10181d;
  font: inherit;
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: background 180ms ease, color 180ms ease, border-color 180ms ease;
}

.nf-button:hover {
  border-color: #10181d;
}

.nf-button.primary {
  border-color: #d97a1c;
  background: #d97a1c;
  color: #fff;
}

.nf-button.primary:hover {
  background: #a85a0e;
  border-color: #a85a0e;
}
</style>
