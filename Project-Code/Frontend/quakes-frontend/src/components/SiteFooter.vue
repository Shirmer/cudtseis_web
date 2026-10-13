<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { SITE, localizedPath, type Locale } from '../config/site'

const props = defineProps<{ locale: Locale }>()

const route = useRoute()
const router = useRouter()
const currentYear = new Date().getFullYear()

const copy = computed(() => props.locale === 'zh'
  ? {
      tagline: '地球科学数据产品与智能工具',
      product: '产品',
      company: '公司',
      legal: '法律条款',
      features: '功能介绍',
      scenarios: '应用场景',
      download: '下载 GeoCamera',
      about: '关于我们',
      contact: '联系我们',
      privacy: '隐私政策',
      terms: '用户协议',
      email: '联系邮箱',
      address: '地址',
      rights: '保留所有权利'
    }
  : {
      tagline: 'Geoscience data products and intelligent tools',
      product: 'Product',
      company: 'Company',
      legal: 'Legal',
      features: 'Features',
      scenarios: 'Scenarios',
      download: 'Get GeoCamera',
      about: 'About us',
      contact: 'Contact',
      privacy: 'Privacy Policy',
      terms: 'Terms of Service',
      email: 'Email',
      address: 'Address',
      rights: 'All rights reserved'
    })

const homePath = computed(() => localizedPath(props.locale, '/'))

function goSection(id: string) {
  const onHome = route.path === homePath.value || route.path === `${homePath.value}/`
  if (onHome) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } else {
    router.push({ path: homePath.value, hash: `#${id}` })
  }
}

function go(path: string) {
  router.push(localizedPath(props.locale, path))
}
</script>

<template>
  <footer class="site-footer">
    <div class="footer-inner">
      <div class="footer-brand">
        <div class="brand-row">
          <img src="/brand/geocamera-icon.png" :alt="SITE.productName" />
          <strong>{{ locale === 'zh' ? SITE.brandZh : SITE.brandEn }}</strong>
        </div>
        <p class="tagline">{{ copy.tagline }}</p>
        <p class="company">{{ locale === 'zh' ? SITE.companyZh : SITE.companyEn }}</p>
        <dl class="contact-list">
          <div>
            <dt>{{ copy.email }}</dt>
            <dd><a :href="`mailto:${SITE.contact.email}`">{{ SITE.contact.email }}</a></dd>
          </div>
          <div>
            <dt>{{ copy.address }}</dt>
            <dd>{{ locale === 'zh' ? SITE.contact.addressZh : SITE.contact.addressEn }}</dd>
          </div>
        </dl>
      </div>

      <div class="footer-columns">
        <div class="footer-column">
          <h3>{{ copy.product }}</h3>
          <button type="button" @click="goSection('product')">{{ copy.features }}</button>
          <button type="button" @click="goSection('scenarios')">{{ copy.scenarios }}</button>
          <button type="button" @click="goSection('download')">{{ copy.download }}</button>
        </div>
        <div class="footer-column">
          <h3>{{ copy.company }}</h3>
          <button type="button" @click="goSection('about')">{{ copy.about }}</button>
          <button type="button" @click="go('/contact')">{{ copy.contact }}</button>
        </div>
        <div class="footer-column">
          <h3>{{ copy.legal }}</h3>
          <button type="button" @click="go('/privacy')">{{ copy.privacy }}</button>
          <button type="button" @click="go('/terms')">{{ copy.terms }}</button>
        </div>
      </div>
    </div>

    <div class="footer-bottom">
      <p>© {{ currentYear }} {{ locale === 'zh' ? SITE.companyZh : SITE.companyEn }} · {{ copy.rights }}</p>
      <a class="icp" :href="SITE.icpUrl" target="_blank" rel="noopener noreferrer">{{ SITE.icp }}</a>
    </div>
  </footer>
</template>

<style scoped>
.site-footer {
  color: rgba(255, 255, 255, 0.82);
  background: #10181d;
}

.footer-inner {
  width: min(1480px, calc(100% - 48px));
  margin: 0 auto;
  padding: 72px 0 48px;
  display: grid;
  grid-template-columns: minmax(280px, 1.3fr) 2fr;
  gap: 64px;
}

.brand-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-row img {
  width: 44px;
  height: 44px;
  border-radius: 10px;
}

.brand-row strong {
  color: #fff;
  font-size: 18px;
  letter-spacing: 0.08em;
}

.tagline {
  margin: 18px 0 6px;
  color: rgba(255, 255, 255, 0.66);
  font-size: 14px;
}

.company {
  margin: 0 0 22px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  font-weight: 600;
}

.contact-list {
  margin: 0;
  display: grid;
  gap: 12px;
}

.contact-list div {
  display: grid;
  gap: 3px;
}

.contact-list dt {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  letter-spacing: 0.1em;
}

.contact-list dd {
  margin: 0;
  font-size: 14px;
}

.contact-list a {
  color: inherit;
  text-decoration: none;
}

.contact-list a:hover {
  color: #f0a54c;
}

.footer-columns {
  display: grid;
  grid-template-columns: repeat(3, minmax(120px, 1fr));
  gap: 32px;
}

.footer-column {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.footer-column h3 {
  margin: 0 0 12px;
  color: #fff;
  font-size: 13px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.footer-column button {
  padding: 6px 0;
  border: 0;
  color: rgba(255, 255, 255, 0.66);
  background: transparent;
  font-size: 14px;
  cursor: pointer;
  transition: color 160ms ease;
}

.footer-column button:hover {
  color: #f0a54c;
}

.footer-bottom {
  border-top: 1px solid rgba(255, 255, 255, 0.12);
}

.footer-bottom {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: min(1480px, calc(100% - 48px));
  margin: 0 auto;
  padding: 22px 0 28px;
}

.footer-bottom p {
  margin: 0;
  color: rgba(255, 255, 255, 0.55);
  font-size: 13px;
}

.icp {
  color: rgba(255, 255, 255, 0.55);
  font-size: 13px;
  text-decoration: none;
}

.icp:hover {
  color: #f0a54c;
}

@media (max-width: 960px) {
  .footer-inner {
    grid-template-columns: 1fr;
    gap: 44px;
    padding-top: 56px;
  }
}

@media (max-width: 560px) {
  .footer-columns {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
