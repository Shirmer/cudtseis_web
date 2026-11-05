<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SiteHeader from '../components/SiteHeader.vue'
import SiteFooter from '../components/SiteFooter.vue'
import PlanetHero from '../components/PlanetHero.vue'
import { SITE, localeFromPath, productUrl } from '../config/site'
import { usePageMeta } from '../composables/usePageMeta'

const route = useRoute()
const router = useRouter()
const locale = computed(() => localeFromPath(route.path))

usePageMeta(() => locale.value, () => ({
  title: locale.value === 'zh' ? '深视地球 | 地球科学数据与软件' : 'DeepSeek Earth | Geoscience Data & Software',
  description:
    locale.value === 'zh'
      ? '深视地球专注地球科学领域的数据产品与专业软件，连接野外观测、数据管理与研究应用。'
      : 'DeepSeek Earth develops geoscience data products and professional software, connecting field observations, data management and research.'
}))



function goEarth() {
  router.push(locale.value === 'en' ? '/en/earth' : '/earth')
}

const copy = {
  zh: {
    hero: {
      eyebrow: 'DEEPSEEK EARTH · 深视地球',
      titleA: '探索地球的深度',
      titleB: '连接数据的价值',
      text: '深视地球专注地球科学领域的数据产品与专业软件，连接野外观测、数据管理与研究应用。',
      primary: '了解我们的业务',
      secondary: '旗下产品',
      marker: '四川 · 成都',
      discipline: '地球科学 / 数据应用 / 专业软件'
    },
    ticker: ['GEOSCIENCE', '地球科学', 'DATA', '数据应用', 'SOFTWARE', '专业软件'],
    scenarios: {
      label: '02 / SCENARIOS',
      title: '为真实野外工作而设计',
      text: '无论在山地、戈壁还是城市工区，规范的数据从采集源头开始。',
      mediaCaption: '野外观测场景示意',
      items: [
        { no: '01', title: '地质调查', text: '露头、剖面与构造现象的影像记录与位置归档。' },
        { no: '02', title: '工程勘察', text: '勘察点位照片与坐标一一对应，现场记录可追溯。' },
        { no: '03', title: '科研考察', text: '按项目组织考察路线，为后续研究保留完整原始数据。' },
        { no: '04', title: '教学实习', text: '标准化的记录流程，让学生在实践中建立数据规范意识。' }
      ]
    },
    about: {
      label: '03 / ABOUT',
      title: '关于深视地球',
      lead: '深视地球（成都）信息技术有限公司专注于地球科学领域的数据产品与智能工具。',
      body: '我们面向地质调查、工程勘察、地震研究等场景，提供从野外采集、云端管理到数据应用的工具链，让专业数据在采集环节就保持规范、完整、可用。我们重视与高校、科研团队和行业单位的交流合作。',
      values: [
        { title: '专业可靠', text: '扎根地球科学场景，产品贴合野外工作流程。' },
        { title: '数据安全', text: '加密传输与云端存储，数据权限清晰可控。' },
        { title: '开放协作', text: '与高校、科研院所和行业单位保持开放合作。' }
      ],
      identityA: '学术合作',
      identityAText: '成都理工大学地震研究中心',
      identityB: '公司主体',
      identityBText: '深视地球（成都）信息技术有限公司',
      visual: '研发场景示意'
    },
    contact: {
      title: '与我们讨论你的项目',
      text: '欢迎就专业工具开发、数据可视化与团队产品部署和我们交流。',
      action: '联系我们',
      emailPrefix: '或发邮件至'
    }
  },
  en: {
    hero: {
      eyebrow: 'DEEPSEEK EARTH · CHENGDU',
      titleA: 'Explore the Earth.',
      titleB: 'Connect the data.',
      text: 'We build geoscience data products and professional software, connecting field observations, data management and research.',
      primary: 'Explore our work',
      secondary: 'Our products',
      marker: 'Chengdu, Sichuan',
      discipline: 'Geoscience / Data / Software'
    },
    ticker: ['GEOSCIENCE', 'FIELD OBSERVATION', 'SPATIAL DATA', 'VISUALIZATION', 'SOFTWARE'],
    scenarios: {
      label: '02 / SCENARIOS',
      title: 'Designed for real field work',
      text: 'Mountains, deserts or urban sites — standardized data starts at the moment of capture.',
      mediaCaption: 'Illustrative field-observation scene',
      items: [
        { no: '01', title: 'Geological survey', text: 'Image records and location archiving for outcrops, sections and structures.' },
        { no: '02', title: 'Engineering investigation', text: 'Survey points with photos matched to coordinates, fully traceable on site.' },
        { no: '03', title: 'Research expeditions', text: 'Organize expedition routes by project and preserve complete raw data for research.' },
        { no: '04', title: 'Field teaching', text: 'A standardized recording workflow that builds data discipline in practice.' }
      ]
    },
    about: {
      label: '03 / ABOUT',
      title: 'About DeepSeek Earth',
      lead: 'DeepSeek Earth (Chengdu) Information Technology Co., Ltd. focuses on geoscience data products and intelligent tools.',
      body: 'For geological surveys, engineering investigation and seismological research, we provide a toolchain from field capture to cloud management and data application, keeping professional data standardized, complete and usable from the very first step. We welcome collaboration with universities, research teams and industry partners.',
      values: [
        { title: 'Professional', text: 'Rooted in geoscience scenarios and field workflows.' },
        { title: 'Secure', text: 'Encrypted transfer, cloud storage and clear data permissions.' },
        { title: 'Collaborative', text: 'Open cooperation with universities, institutes and industry partners.' }
      ],
      identityA: 'Academic partner',
      identityAText: 'CDUT Earthquake Research Center',
      identityB: 'Company',
      identityBText: 'DeepSeek Earth (Chengdu) Information Technology Co., Ltd.',
      visual: 'Illustrative R&D scene'
    },
    contact: {
      title: 'Need a product demo or a partnership?',
      text: 'Contact us for product materials, trial accounts and team deployment plans.',
      action: 'Contact us',
      emailPrefix: 'Or email us at'
    }
  }
} as const

const companyCopy = {
  zh: {
    label: '01 / WHAT WE DO', title: '围绕地学场景，构建专业工具',
    text: '从现场记录到数据应用，让软件服务于真实的科研与业务需求。',
    features: [
      { title: '野外数据采集', text: '组织影像、位置与路线信息，让地质调查与野外观测形成清晰、可追溯的项目记录。' },
      { title: '地学数据可视化', text: '通过地图与三维地球呈现空间信息，为理解地质构造与地震活动提供直观入口。' },
      { title: '专业软件开发', text: '围绕团队实际工作，开展科研工具开发、数据管理与服务集成。' }
    ],
    productLabel: '04 / OUR PRODUCT', productTitle: 'GeoCamera 地质相机',
    productText: '把野外照片、位置与路线汇集为有条理的地质记录。了解功能、版本与下载，请访问独立产品官网。',
    productAction: '访问 GeoCamera 官网', identityA: '业务领域', identityAText: '地球科学 · 数据应用 · 软件开发'
  },
  en: {
    label: '01 / WHAT WE DO', title: 'Practical tools for geoscience',
    text: 'From observations to applications, software built around scientific and operational needs.',
    features: [
      { title: 'Field data collection', text: 'Organize images, locations and routes into traceable project records for surveys and field observations.' },
      { title: 'Geoscience visualization', text: 'Use maps and a 3D Earth to explore spatial information, geological structures and earthquake activity.' },
      { title: 'Professional software', text: 'Develop research tools, data workflows and service integrations around the way your team works.' }
    ],
    productLabel: '04 / OUR PRODUCT', productTitle: 'GeoCamera',
    productText: 'Bring field photos, locations and routes together as organized geological records. Explore features, releases and downloads on our dedicated product website.',
    productAction: 'Visit the GeoCamera website', identityA: 'Our focus', identityAText: 'Geoscience · Data · Software'
  }
} as const
const company = computed(() => companyCopy[locale.value])

const c = computed(() => copy[locale.value])

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function goContact() {
  router.push(locale.value === 'zh' ? '/contact' : '/en/contact')
}

let revealObserver: IntersectionObserver | null = null

function observeReveals() {
  revealObserver?.disconnect()
  revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible')
        revealObserver?.unobserve(entry.target)
      }
    })
  }, { threshold: 0.14 })
  document.querySelectorAll('[data-reveal]').forEach((element) => revealObserver?.observe(element))
}

onMounted(() => {
  observeReveals()
})

onBeforeUnmount(() => {
  revealObserver?.disconnect()
})
</script>

<template>
  <div class="site-page" :class="{ 'locale-en': locale === 'en' }">
    <SiteHeader :locale="locale" />

    <main>
      <section class="hero">
        <PlanetHero :locale="locale" @expand="goEarth" />
        <div class="hero-overlay"></div>
        <div class="hero-grid" aria-hidden="true"></div>

        <div class="hero-content">
          <div class="hero-copy" data-reveal>
            <p class="eyebrow"><span></span>{{ c.hero.eyebrow }}</p>
            <h1><span>{{ c.hero.titleA }}</span><span>{{ c.hero.titleB }}</span></h1>
            <p class="hero-text">{{ c.hero.text }}</p>
            <div class="hero-actions">
              <button class="button primary" type="button" @click="scrollToSection('capabilities')">
                {{ c.hero.primary }} <span aria-hidden="true">↓</span>
              </button>
              <button class="button text" type="button" @click="scrollToSection('products')">
                {{ c.hero.secondary }} <span aria-hidden="true">↓</span>
              </button>
            </div>
          </div>

          <div class="hero-coordinates" data-reveal>
            <span>{{ c.hero.marker }}</span>
            <span>{{ c.hero.discipline }}</span>
          </div>
        </div>

        <svg class="hero-strata" viewBox="0 0 1440 220" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0,118 C240,76 480,158 720,116 C960,76 1200,148 1440,106 L1440,220 L0,220 Z" fill="rgba(217,122,28,0.82)" />
          <path d="M0,152 C260,120 520,182 780,146 C1040,112 1240,170 1440,140 L1440,220 L0,220 Z" fill="rgba(138,90,43,0.88)" />
          <path d="M0,184 C280,160 560,208 840,178 C1120,150 1300,196 1440,172 L1440,220 L0,220 Z" fill="rgba(46,127,168,0.86)" />
        </svg>
      </section>

      <div class="signal-strip" aria-hidden="true">
        <div class="signal-track">
          <template v-for="(word, index) in c.ticker" :key="word">
            <span>{{ word }}</span><i v-if="index < c.ticker.length - 1"></i>
          </template>
        </div>
      </div>

      <section id="capabilities" class="section product-section">
        <div class="product-heading section-grid">
          <div class="section-index" data-reveal>{{ company.label }}</div>
          <div data-reveal>
            <h2>{{ company.title }}</h2>
            <p>{{ company.text }}</p>
          </div>
        </div>

        <div class="product-body">
          <div class="feature-grid">
            <article v-for="(feature, index) in company.features" :key="feature.title" class="feature-card" data-reveal>
              <span class="feature-icon" aria-hidden="true">
                <svg v-if="index === 0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 10c0 7-9 12-9 12S3 17 3 10a9 9 0 0 1 18 0Z" />
                  <circle cx="12" cy="10" r="3" />
                </svg>
                <svg v-else-if="index === 1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="5" cy="6" r="2.4" />
                  <circle cx="19" cy="18" r="2.4" />
                  <path d="M7.2 7.2 16.8 16.8" stroke-dasharray="4 3" />
                </svg>
                <svg v-else-if="index === 2" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <path d="m9 4-5 1.5v14L9 18l6 2 5-1.5v-14L15 6 9 4Z" />
                  <path d="M9 4v14" />
                  <path d="M15 6v14" />
                </svg>
                <svg v-else-if="index === 3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17.5 19a4.5 4.5 0 0 0 .4-9A6.5 6.5 0 0 0 5.3 8.6 4 4 0 0 0 6 16.5" />
                  <path d="M12 12v8" />
                  <path d="m8.8 16.8 3.2 3.2 3.2-3.2" />
                </svg>
                <svg v-else-if="index === 4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z" />
                  <path d="M14 3v6h6" />
                  <path d="M9 14h6" />
                  <path d="M9 17.5h4" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="9" cy="8" r="3.2" />
                  <path d="M3.5 19.5c.8-3 3-4.6 5.5-4.6s4.7 1.6 5.5 4.6" />
                  <circle cx="17" cy="9.5" r="2.4" />
                  <path d="M15.6 14.6c2.3.2 4.1 1.6 4.9 4.4" />
                </svg>
              </span>
              <h3>{{ feature.title }}</h3>
              <p>{{ feature.text }}</p>
            </article>
          </div>
        </div>
      </section>

      <section id="scenarios" class="section scenarios-section">
        <div class="scenarios-heading section-grid">
          <div class="section-index light" data-reveal>{{ c.scenarios.label }}</div>
          <div data-reveal>
            <h2>{{ c.scenarios.title }}</h2>
            <p>{{ c.scenarios.text }}</p>
          </div>
        </div>

        <div class="scenarios-media" data-reveal>
          <img src="/media/field-observation-concept.jpg" alt="" loading="lazy" />
          <span>{{ c.scenarios.mediaCaption }}</span>
        </div>

        <div class="scenario-grid">
          <article v-for="item in c.scenarios.items" :key="item.no" class="scenario-card" data-reveal>
            <span class="scenario-no">{{ item.no }}</span>
            <h3>{{ item.title }}</h3>
            <p>{{ item.text }}</p>
          </article>
        </div>
      </section>

      <section id="about" class="section about-section">
        <div class="about-copy" data-reveal>
          <div class="section-index light">{{ c.about.label }}</div>
          <h2>{{ c.about.title }}</h2>
          <p class="about-lead">{{ c.about.lead }}</p>
          <p class="about-body">{{ c.about.body }}</p>

          <div class="value-list">
            <div v-for="value in c.about.values" :key="value.title" class="value-item">
              <h3>{{ value.title }}</h3>
              <p>{{ value.text }}</p>
            </div>
          </div>
        </div>

        <div class="about-side" data-reveal>
          <div class="about-visual">
            <img src="/media/deepseek-earth-lab.jpg" alt="" loading="lazy" />
            <span>{{ c.about.visual }}</span>
          </div>
          <div class="identity-list">
            <div class="identity-row">
              <span>{{ company.identityA }}</span>
              <strong>{{ company.identityAText }}</strong>
            </div>
            <div class="identity-row">
              <span>{{ c.about.identityB }}</span>
              <strong>{{ c.about.identityBText }}</strong>
            </div>
          </div>
        </div>
      </section>

      <section id="products" class="download-section">
        <img class="download-bg" src="/media/deep-structure-concept.jpg" alt="" loading="lazy" />
        <div class="download-overlay"></div>
        <div class="download-inner" data-reveal>
          <div class="section-index light">{{ company.productLabel }}</div>
          <img class="download-icon" src="/brand/geocamera-icon.png" alt="GeoCamera" />
          <h2>{{ company.productTitle }}</h2>
          <p class="download-text">{{ company.productText }}</p>
          <a class="button primary" :href="productUrl(locale)">{{ company.productAction }} <span aria-hidden="true">↗</span></a>
        </div>
      </section>

      <section class="contact-band">
        <div class="contact-inner" data-reveal>
          <div>
            <h2>{{ c.contact.title }}</h2>
            <p>{{ c.contact.text }}</p>
            <p class="contact-email">{{ c.contact.emailPrefix }} <a :href="`mailto:${SITE.contact.email}`">{{ SITE.contact.email }}</a></p>
          </div>
          <button class="button dark" type="button" @click="goContact">
            {{ c.contact.action }} <span aria-hidden="true">→</span>
          </button>
        </div>
      </section>
    </main>

    <SiteFooter :locale="locale" />
  </div>
</template>

<style scoped>
.site-page {
  --ink: #10181d;
  --paper: #f6f4ef;
  --white: #ffffff;
  --amber: #d97a1c;
  --amber-dark: #a85a0e;
  --green: #57923a;
  --blue: #2e7fa8;
  --brown: #8a5a2b;
  --muted: #667072;
  --line: rgba(16, 24, 29, 0.14);
  --page-progress: 0%;
  min-width: 320px;
  color: var(--ink);
  background: var(--paper);
  font-family: Inter, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
  overflow: hidden;
}

.site-page *,
.site-page *::before,
.site-page *::after {
  box-sizing: border-box;
  letter-spacing: 0;
}

button {
  font: inherit;
}

button:focus-visible,
a:focus-visible {
  outline: 2px solid var(--amber);
  outline-offset: 3px;
}

main {
  padding-top: 0;
}

/* ---------- Hero ---------- */

.hero {
  position: relative;
  min-height: min(92vh, 940px);
  display: flex;
  align-items: flex-end;
  overflow: hidden;
  background: #02040a;
}

.hero-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(88deg, rgba(3, 6, 12, 0.93) 6%, rgba(3, 6, 12, 0.6) 36%, rgba(3, 6, 12, 0.08) 58%, transparent 78%),
    linear-gradient(0deg, rgba(3, 6, 12, 0.84) 0%, rgba(3, 6, 12, 0.2) 42%, transparent 64%);
}

.hero-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 84px 84px;
  mask-image: linear-gradient(0deg, rgba(0, 0, 0, 0.7), transparent 70%);
  pointer-events: none;
}

.hero-content {
  position: relative;
  z-index: 2;
  width: min(1480px, calc(100% - 48px));
  margin: 0 auto;
  padding: 150px 0 190px;
  color: #fff;
  /* 让右侧地球可以拖拽：容器不拦截指针，只有文案本身可选中 */
  pointer-events: none;
}

.hero-copy {
  max-width: 940px;
  pointer-events: auto;
}

.hero-coordinates {
  pointer-events: auto;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 26px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 14px;
  letter-spacing: 0.12em;
}

.eyebrow span {
  width: 34px;
  height: 1px;
  background: var(--amber);
}

.hero h1 {
  margin: 0;
  max-width: 900px;
  font-size: clamp(40px, 6.4vw, 84px);
  line-height: 1.04;
  letter-spacing: -0.015em;
}

.locale-en .hero h1 {
  font-size: clamp(34px, 5.2vw, 68px);
}

.hero h1 span {
  display: block;
}

.hero h1 span:last-child {
  color: #f0a54c;
}

.hero-text {
  max-width: 620px;
  margin: 28px 0 0;
  color: rgba(255, 255, 255, 0.82);
  font-size: 17px;
  line-height: 1.9;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 40px;
}

.button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 26px;
  border: 0;
  border-radius: 999px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 180ms ease, background 180ms ease, color 180ms ease;
}

.button:hover {
  transform: translateY(-2px);
}

.button.primary {
  color: var(--ink);
  background: #f0a54c;
}

.button.primary:hover {
  background: #fff;
}

.button.text {
  color: #fff;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.4);
}

.button.text:hover {
  background: rgba(255, 255, 255, 0.12);
}

.button.dark {
  color: #fff;
  background: var(--ink);
}

.button.dark:hover {
  background: var(--amber-dark);
}

.hero-coordinates {
  display: flex;
  flex-wrap: wrap;
  gap: 26px;
  margin-top: 56px;
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.hero-strata {
  position: absolute;
  inset: auto 0 0;
  z-index: 1;
  width: 100%;
  height: 150px;
  pointer-events: none;
}

/* ---------- Ticker ---------- */

.signal-strip {
  overflow: hidden;
  padding: 18px 0;
  color: #fff;
  background: var(--ink);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.signal-track {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 26px;
  flex-wrap: wrap;
  font-size: 12px;
  letter-spacing: 0.3em;
  opacity: 0.7;
}

.signal-track i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--amber);
}

/* ---------- Shared section scaffolding ---------- */

.section {
  position: relative;
  width: min(1480px, calc(100% - 48px));
  margin: 0 auto;
  padding: 110px 0 0;
}

.section-grid {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 40px;
  align-items: start;
}

.section-index {
  color: var(--amber-dark);
  font-size: 13px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  padding-top: 10px;
}

.section-index.light {
  color: #f0a54c;
}

.section h2 {
  margin: 0;
  font-size: clamp(30px, 3.6vw, 46px);
  line-height: 1.16;
  letter-spacing: -0.01em;
}

.section-grid p {
  max-width: 640px;
  margin: 16px 0 0;
  color: var(--muted);
  font-size: 16px;
  line-height: 1.85;
}

/* ---------- Product ---------- */

.product-section {
  padding-bottom: 120px;
}

.product-body {
  display: grid;
  grid-template-columns: minmax(300px, 420px) 1fr;
  gap: clamp(40px, 6vw, 96px);
  align-items: center;
  margin-top: 72px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.feature-card {
  padding: 26px 24px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--white);
  transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
}

.feature-card:hover {
  transform: translateY(-4px);
  border-color: rgba(217, 122, 28, 0.45);
  box-shadow: 0 18px 40px rgba(16, 24, 29, 0.1);
}

.feature-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  margin-bottom: 18px;
  border-radius: 12px;
  color: var(--amber-dark);
  background: rgba(217, 122, 28, 0.12);
}

.feature-icon svg {
  width: 22px;
  height: 22px;
}

.feature-card h3 {
  margin: 0 0 8px;
  font-size: 17px;
}

.feature-card p {
  margin: 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.75;
}

/* ---------- Scenarios ---------- */

.scenarios-section {
  padding-bottom: 120px;
}

.scenarios-media {
  position: relative;
  margin-top: 64px;
  border-radius: 24px;
  overflow: hidden;
}

.scenarios-media img {
  display: block;
  width: 100%;
  height: clamp(260px, 38vw, 440px);
  object-fit: cover;
}

.scenarios-media::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(0deg, rgba(10, 16, 20, 0.55), transparent 55%);
}

.scenarios-media span {
  position: absolute;
  left: 24px;
  bottom: 20px;
  z-index: 1;
  color: rgba(255, 255, 255, 0.82);
  font-size: 12px;
  letter-spacing: 0.12em;
}

.scenario-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin-top: 40px;
}

.scenario-card {
  padding: 30px 24px;
  border-top: 3px solid var(--line);
  background: transparent;
  transition: border-color 220ms ease, background 220ms ease, transform 220ms ease;
}

.scenario-card:hover {
  border-top-color: var(--amber);
  background: var(--white);
  transform: translateY(-3px);
}

.scenario-no {
  color: var(--amber-dark);
  font-size: 13px;
  letter-spacing: 0.2em;
}

.scenario-card h3 {
  margin: 18px 0 10px;
  font-size: 19px;
}

.scenario-card p {
  margin: 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.75;
}

/* ---------- About ---------- */

.about-section {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 1fr);
  gap: clamp(40px, 6vw, 96px);
  align-items: start;
  width: 100%;
  max-width: none;
  margin-top: 40px;
  padding: 110px max(24px, calc((100% - 1480px) / 2));
  color: #fff;
  background: var(--ink);
}

.about-section .section-index {
  padding-top: 0;
  margin-bottom: 26px;
}

.about-section h2 {
  max-width: 560px;
}

.about-lead {
  max-width: 620px;
  margin: 24px 0 0;
  color: rgba(255, 255, 255, 0.88);
  font-size: 18px;
  line-height: 1.8;
}

.about-body {
  max-width: 620px;
  margin: 18px 0 0;
  color: rgba(255, 255, 255, 0.62);
  font-size: 15px;
  line-height: 1.95;
}

.value-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24px;
  margin-top: 52px;
}

.value-item h3 {
  margin: 0 0 8px;
  color: #f0a54c;
  font-size: 16px;
}

.value-item p {
  margin: 0;
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
  line-height: 1.75;
}

.about-copy {
  max-width: 680px;
}

.about-side {
  width: 100%;
  margin-top: 10px;
}

.about-visual {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
}

.about-visual img {
  display: block;
  width: 100%;
  height: clamp(240px, 26vw, 360px);
  object-fit: cover;
}

.about-visual::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(0deg, rgba(10, 16, 20, 0.5), transparent 50%);
}

.about-visual span {
  position: absolute;
  left: 18px;
  bottom: 14px;
  z-index: 1;
  color: rgba(255, 255, 255, 0.78);
  font-size: 12px;
  letter-spacing: 0.1em;
}

.identity-list {
  margin-top: 22px;
  display: grid;
  gap: 12px;
}

.identity-row {
  display: grid;
  gap: 4px;
  padding: 16px 18px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
}

.identity-row span {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  letter-spacing: 0.14em;
}

.identity-row strong {
  font-size: 15px;
  font-weight: 600;
}

/* ---------- Download ---------- */

.download-section {
  position: relative;
  overflow: hidden;
  margin-top: 120px;
  color: #fff;
  background: var(--ink);
}

.download-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.34;
}

.download-overlay {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 10%, rgba(217, 122, 28, 0.28), transparent 55%),
    linear-gradient(0deg, rgba(10, 16, 20, 0.92), rgba(10, 16, 20, 0.68));
}

.download-inner {
  position: relative;
  z-index: 1;
  width: min(760px, calc(100% - 48px));
  margin: 0 auto;
  padding: 96px 0 104px;
  text-align: center;
}

.download-inner .section-index {
  padding: 0;
  margin-bottom: 30px;
}

.download-icon {
  width: 84px;
  height: 84px;
  border-radius: 20px;
  box-shadow: 0 24px 50px rgba(0, 0, 0, 0.4);
}

.download-inner h2 {
  margin: 24px 0 0;
  font-size: clamp(30px, 4vw, 44px);
}

.download-text {
  margin: 16px auto 0;
  max-width: 520px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 16px;
  line-height: 1.85;
}

.release-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  margin: 34px 0 30px;
}

.release-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  border: 1px solid rgba(240, 165, 76, 0.5);
  border-radius: 999px;
  color: #f0a54c;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.release-date {
  color: rgba(255, 255, 255, 0.55);
  font-size: 13px;
}

.release-changelog {
  max-width: 620px;
  margin: 4px 0 0;
  color: rgba(255, 255, 255, 0.62);
  font-size: 13px;
  line-height: 1.8;
}

.release-changelog strong {
  color: rgba(255, 255, 255, 0.82);
}

.release-changelog.muted {
  color: rgba(255, 255, 255, 0.45);
}

.download-note {
  max-width: 560px;
  margin: 26px auto 0;
  color: rgba(255, 255, 255, 0.45);
  font-size: 13px;
  line-height: 1.8;
}

/* ---------- Contact band ---------- */

.contact-band {
  background: #f0a54c;
}

.contact-inner {
  width: min(1480px, calc(100% - 48px));
  margin: 0 auto;
  padding: 64px 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  color: #10181d;
}

.contact-inner h2 {
  margin: 0;
  font-size: clamp(24px, 3vw, 34px);
}

.contact-inner p {
  margin: 10px 0 0;
  color: rgba(16, 24, 29, 0.75);
  font-size: 15px;
}

.contact-email a {
  color: #10181d;
  font-weight: 600;
}

/* ---------- Reveal ---------- */

[data-reveal] {
  opacity: 0;
  transform: translateY(26px);
  transition: opacity 700ms ease, transform 700ms cubic-bezier(0.22, 1, 0.36, 1);
}

[data-reveal].is-visible {
  opacity: 1;
  transform: none;
}

@media (prefers-reduced-motion: reduce) {
  [data-reveal] {
    opacity: 1;
    transform: none;
    transition: none;
  }

  .map-ring {
    animation: none;
  }
}

/* ---------- Responsive ---------- */

/* 手机横屏：竖向空间很紧，压缩首屏留白与字号，别让标题被裁到首屏外 */
@media (max-height: 520px) and (orientation: landscape) {
  .hero {
    min-height: auto;
  }

  .hero-content {
    width: min(1480px, calc(100% - 32px));
    /* 顶栏是固定定位，留够高度别让标题钻到它下面 */
    padding: 92px 0 44px;
  }

  .eyebrow {
    margin-bottom: 12px;
    font-size: 12px;
  }

  .hero h1 {
    font-size: clamp(24px, 4.4vw, 38px);
  }

  .locale-en .hero h1 {
    font-size: clamp(21px, 3.8vw, 32px);
  }

  .hero-text {
    max-width: 520px;
    margin-top: 12px;
    font-size: 13px;
    line-height: 1.65;
  }

  .hero-actions {
    margin-top: 16px;
  }
}

@media (max-width: 1180px) {
  .about-section {
    grid-template-columns: 1fr;
    padding: 96px 24px;
  }

  .about-copy {
    max-width: none;
  }

  .scenario-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1024px) {
  .section-grid {
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .section-index {
    padding-top: 0;
  }

  .product-body {
    grid-template-columns: 1fr;
  }

  .feature-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .hero-content {
    width: calc(100% - 40px);
    padding: 130px 0 210px;
  }

  .section {
    width: calc(100% - 40px);
    padding-top: 84px;
  }

  .product-section,
  .scenarios-section {
    padding-bottom: 84px;
  }

  .feature-grid {
    grid-template-columns: 1fr;
  }

  .scenario-grid {
    grid-template-columns: 1fr;
  }

  .value-list {
    grid-template-columns: 1fr;
    gap: 18px;
  }

  .download-section {
    margin-top: 84px;
  }

  .download-inner {
    width: calc(100% - 40px);
    padding: 72px 0 80px;
  }

  .contact-inner {
    width: calc(100% - 40px);
    padding: 52px 0;
  }
}
/* Company overview uses the original page rhythm without a product phone demo. */
.product-body { display: block; }
.feature-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.feature-card { padding: 32px; }
a.button { text-decoration: none; }
@media (max-width: 760px) { .feature-grid { grid-template-columns: 1fr; } }
/* A quieter company identity, built around the interactive Earth. */
.hero { min-height: 780px; min-height: min(94svh, 900px); }
.hero-content, .section, .contact-inner { width: min(1280px, calc(100% - 80px)); }
.hero-content { padding: 164px 0 170px; }
.hero-copy { max-width: 700px; }
.hero h1 { font-size: clamp(42px, 5.2vw, 72px); line-height: 1.16; }
.hero h1 span:last-child { color: #e8ba7b; }
.hero-text { max-width: 520px; font-size: 16px; }
.hero-strata { height: 86px; opacity: .55; }
.hero-coordinates { margin-top: 44px; font-size: 12px; }
.signal-strip { padding: 22px 0; }
.section-grid { grid-template-columns: 240px minmax(0,1fr); }
.section h2 { font-size: clamp(28px, 3vw, 40px); line-height: 1.3; }
.product-body { margin-top: 48px; }
.feature-card { border-radius: 10px; padding: 32px; box-shadow: none; }
.feature-card:hover { transform: translateY(-3px); box-shadow: 0 12px 30px #10181d08; }
.about-section { width: 100%; padding-inline: max(40px, calc((100vw - 1280px) / 2)); }
.scenarios-media { margin-top: 40px; border-radius: 10px; }
.download-section { margin-top: 0; }
.download-inner { padding: 90px 0; }
.contact-band { background: #eae5dc; }
.button { border-radius: 8px; }
@media(max-width:1024px) { .section-grid { grid-template-columns: 1fr; } }
@media(max-width:720px) {
 .hero { min-height: 760px; }
 .hero-content,.section,.contact-inner { width: calc(100% - 40px); }
 .hero-content { padding: 132px 0 180px; }
 .hero h1 { font-size: clamp(34px,8.4vw,48px); }
 .hero-text { font-size: 15px; }
 .hero-strata { height: 70px; }
 .hero-actions { margin-top: 28px; gap: 10px; }
 .hero-actions .button { padding: 13px 18px; font-size: 14px; }
 .about-section { width: 100%; padding-inline: 20px; }
 .feature-card { padding: 26px; }
}
@media(max-height:520px) and (orientation:landscape) {
 .hero { min-height: auto; }
 .hero-content { padding: 108px 0 112px; }
 .hero h1 { font-size: 34px; }
}
</style>
