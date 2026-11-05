<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { SITE, productUrl, localizedPath, type Locale } from '../config/site'

const props = defineProps<{ locale: Locale }>()

const route = useRoute()
const router = useRouter()
const mobileOpen = ref(false)
const solid = ref(false)

const copy = computed(() => props.locale === 'zh'
  ? {
      product: '业务方向',
      scenarios: '应用场景',
      about: '关于我们',
      contact: '联系我们',
      download: 'GeoCamera 官网',
      openNav: '打开导航',
      navLabel: '主导航',
      mobileNavLabel: '移动端导航',
      localeLabel: '语言切换',
      brandSub: '地球科学数据与软件'
    }
  : {
      product: 'Our work',
      scenarios: 'Scenarios',
      about: 'About',
      contact: 'Contact',
      download: 'GeoCamera',
      openNav: 'Open navigation',
      navLabel: 'Primary navigation',
      mobileNavLabel: 'Mobile navigation',
      localeLabel: 'Language switch',
      brandSub: 'GEOSCIENCE DATA & SOFTWARE'
    })

const homePath = computed(() => localizedPath(props.locale, '/'))

function goSection(id: string) {
  mobileOpen.value = false
  const onHome = route.path === homePath.value || route.path === `${homePath.value}/`
  if (onHome) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } else {
    router.push({ path: homePath.value, hash: `#${id}` })
  }
}

function goContact() {
  mobileOpen.value = false
  router.push(localizedPath(props.locale, '/contact'))
}

function goHome() {
  mobileOpen.value = false
  router.push(homePath.value)
}

function switchLocale(next: Locale) {
  if (next === props.locale) return
  mobileOpen.value = false
  router.push(localizedPath(next, route.path))
}

function updateScroll() {
  solid.value = window.scrollY > 28
  const max = document.documentElement.scrollHeight - window.innerHeight
  const progress = max > 0 ? Math.min(1, window.scrollY / max) : 0
  document.documentElement.style.setProperty('--page-progress', `${progress * 100}%`)
}

onMounted(() => {
  updateScroll()
  window.addEventListener('scroll', updateScroll, { passive: true })
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', updateScroll)
})
</script>

<template>
  <header class="site-header" :class="{ solid, open: mobileOpen }">
    <div class="scroll-progress" aria-hidden="true"></div>
    <div class="header-inner">
      <button class="brand" type="button" :aria-label="locale === 'zh' ? '返回首页' : 'Back to home'" @click="goHome">
        <span class="company-logo"><img src="/brand/deepseek-earth-logo.png" alt="深视地球" /></span>
        <span class="brand-copy">
          <strong>{{ locale === 'zh' ? '深视地球' : 'DeepSeek Earth' }}</strong>
          <span>{{ copy.brandSub }}</span>
        </span>
      </button>

      <nav class="desktop-nav" :aria-label="copy.navLabel">
        <button type="button" @click="goSection('capabilities')">{{ copy.product }}</button>
        <button type="button" @click="goSection('scenarios')">{{ copy.scenarios }}</button>
        <button type="button" @click="goSection('about')">{{ copy.about }}</button>
        <button type="button" @click="goContact">{{ copy.contact }}</button>
      </nav>

      <div class="header-actions">
        <div class="locale-switch" :aria-label="copy.localeLabel">
          <button type="button" :class="{ active: locale === 'zh' }" @click="switchLocale('zh')">中</button>
          <button type="button" :class="{ active: locale === 'en' }" @click="switchLocale('en')">EN</button>
        </div>
        <a class="download-link" :href="productUrl(locale)" :aria-label="copy.download">
          <span>{{ copy.download }}</span><span aria-hidden="true">↗</span>
        </a>
        <button
          class="menu-button"
          type="button"
          :aria-expanded="mobileOpen"
          :aria-label="copy.openNav"
          @click="mobileOpen = !mobileOpen"
        >
          <span></span><span></span>
        </button>
      </div>
    </div>

    <nav class="mobile-nav" :aria-label="copy.mobileNavLabel">
      <button type="button" @click="goSection('capabilities')">{{ copy.product }}</button>
      <button type="button" @click="goSection('scenarios')">{{ copy.scenarios }}</button>
      <button type="button" @click="goSection('about')">{{ copy.about }}</button>
      <button type="button" @click="goContact">{{ copy.contact }}</button>
      <a class="company-link" :href="productUrl(locale)">{{ copy.download }} ↗</a>
    </nav>
  </header>
</template>

<style scoped>
.site-header {
  position: fixed;
  inset: 0 0 auto;
  z-index: 100;
  height: 78px;
  color: #10181d;
  background: rgba(247, 246, 242, 0.84);
  border-bottom: 1px solid rgba(16, 24, 29, 0.12);
  backdrop-filter: blur(16px);
  transition: background 220ms ease, box-shadow 220ms ease;
}

.site-header.solid {
  background: rgba(247, 246, 242, 0.97);
  box-shadow: 0 8px 26px rgba(16, 24, 29, 0.08);
}

.scroll-progress {
  position: absolute;
  inset: auto auto -1px 0;
  width: var(--page-progress, 0%);
  height: 2px;
  background: #d97a1c;
}

.header-inner {
  width: min(1480px, calc(100% - 48px));
  height: 100%;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-width: 220px;
  padding: 0;
  border: 0;
  color: inherit;
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.brand img {
  width: 46px;
  height: 46px;
  object-fit: contain;
  border-radius: 10px;
}

.brand-copy {
  display: grid;
  gap: 2px;
}

.brand-copy strong {
  font-size: 17px;
  letter-spacing: 0.08em;
}

.brand-copy span {
  font-size: 11px;
  color: #667072;
  letter-spacing: 0.16em;
}

.desktop-nav {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
}

.company-link { color: inherit; text-decoration: none; padding: 9px 15px; font-size: 14px; }

.desktop-nav button {
  padding: 9px 15px;
  border: 0;
  border-radius: 999px;
  color: #3a4448;
  background: transparent;
  font-size: 14px;
  cursor: pointer;
  transition: background 180ms ease, color 180ms ease;
}

.desktop-nav button:hover {
  color: #10181d;
  background: rgba(16, 24, 29, 0.07);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.locale-switch {
  display: inline-flex;
  padding: 2px;
  border: 1px solid rgba(16, 24, 29, 0.18);
  border-radius: 999px;
}

.locale-switch button {
  min-width: 34px;
  padding: 5px 8px;
  border: 0;
  border-radius: 999px;
  color: #667072;
  background: transparent;
  font-size: 12px;
  cursor: pointer;
}

.locale-switch button.active {
  color: #fff;
  background: #10181d;
}

.download-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border: 0;
  border-radius: 999px;
  color: #fff;
  background: #10181d;
  font-size: 14px;
  cursor: pointer;
  transition: background 180ms ease, transform 180ms ease;
}

.download-link:hover {
  background: #d97a1c;
  transform: translateY(-1px);
}

.menu-button {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
  width: 42px;
  height: 42px;
  padding: 10px;
  border: 1px solid rgba(16, 24, 29, 0.2);
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
}

.menu-button span {
  display: block;
  height: 2px;
  background: #10181d;
  transition: transform 220ms ease, opacity 220ms ease;
}

.site-header.open .menu-button span:first-child {
  transform: translateY(4px) rotate(45deg);
}

.site-header.open .menu-button span:last-child {
  transform: translateY(-4px) rotate(-45deg);
}

.mobile-nav {
  display: none;
  flex-direction: column;
  gap: 4px;
  padding: 12px 20px 22px;
  background: rgba(247, 246, 242, 0.98);
  border-bottom: 1px solid rgba(16, 24, 29, 0.12);
}

.mobile-nav button {
  padding: 13px 10px;
  border: 0;
  border-radius: 10px;
  color: #10181d;
  background: transparent;
  text-align: left;
  font-size: 15px;
  cursor: pointer;
}

.mobile-nav button:hover {
  background: rgba(16, 24, 29, 0.06);
}

@media (max-width: 1080px) {
  .desktop-nav {
    display: none;
  }

  .menu-button {
    display: flex;
  }

  .site-header.open .mobile-nav {
    display: flex;
  }
}

@media (max-width: 720px) {
  .header-inner {
    width: calc(100% - 32px);
    gap: 12px;
  }

  .brand {
    min-width: 0;
  }

  .brand-copy span {
    display: none;
  }

  .download-link span:first-child {
    display: none;
  }

  .download-link {
    padding: 10px 14px;
  }
}
.company-logo { display: block; width: 50px; height: 50px; overflow: hidden; flex-shrink: 0; }
.company-logo img { width: 90px; height: 60px; max-width: none; transform: translate(-19px, -5px); border-radius: 0; }
a.download-link { text-decoration: none; }
.header-inner { width: min(1280px, calc(100% - 80px)); gap: 20px; }
.site-header { background: rgba(250,249,246,.94); }
.download-link { border-radius: 8px; }
button:focus-visible, a:focus-visible { outline: 2px solid #a9793e; outline-offset: 4px; }
@media(max-width:800px) { .header-inner { width: calc(100% - 32px); gap: 10px; } .brand { min-width: 0; } }
</style>
