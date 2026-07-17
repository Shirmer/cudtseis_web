<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

type Locale = 'zh' | 'en'

const props = withDefaults(defineProps<{ initialLocale?: Locale }>(), {
  initialLocale: 'zh'
})

const route = useRoute()
const router = useRouter()
const locale = ref<Locale>(props.initialLocale)
const mobileNavOpen = ref(false)
const navSolid = ref(false)
const heroEl = ref<HTMLElement | null>(null)
const currentYear = new Date().getFullYear()

const copy = {
  zh: {
    nav: {
      research: '科学研究',
      platform: '研究平台',
      team: '研究团队',
      translation: '技术转化',
      updates: '研究进展',
      workbench: '进入 Terra'
    },
    hero: {
      eyebrow: '成都理工大学地震实验室',
      titleA: '观测地球脉动',
      titleB: '探索深地结构',
      text: '连接地震观测、固体地球物理与智能分析方法，建设面向科研、教学和地球科学应用的开放平台。',
      primary: '进入地震目录',
      secondary: '了解实验室',
      marker: '四川 · 成都',
      discipline: '地震学 / 固体地球物理 / 科研智能'
    },
    intro: {
      label: '01 / ABOUT',
      title: '从地表观测到深部认识',
      lead: 'CDUT SEISLAB 立足成都理工大学地球物理学科基础，围绕地震活动、深部构造和地震数据智能处理开展研究。',
      body: '我们关注观测数据如何转化为对地球内部结构与动力过程的理解，也持续建设能够被研究人员、学生和合作伙伴真正使用的数据与智能工具。',
      identityA: '学术研究主体',
      identityB: '技术转化协作',
      identityAText: '成都理工大学地震实验室',
      identityBText: 'DeepSeek Earth / 深视地球（成都）信息技术有限公司'
    },
    research: {
      label: '02 / RESEARCH',
      title: '以观测为基础，以问题为牵引',
      text: '围绕区域地震学与深地探测，将现场观测、数据处理、结构成像和智能方法组织成连续的研究链条。',
      concept: '概念性科学视觉，不代表实测成像结果',
      fieldConcept: '野外观测场景示意',
      areas: [
        { no: '01', title: '区域地震活动', en: 'Regional Seismicity', text: '研究地震活动的时空分布、震源特征及其与活动构造之间的联系。' },
        { no: '02', title: '深部结构成像', en: 'Deep Earth Imaging', text: '利用地震波传播信息认识地壳与上地幔结构及其横向差异。' },
        { no: '03', title: '地震波形处理', en: 'Waveform Analysis', text: '面向连续波形与事件目录，开展数据整理、检测、分析与可视化。' },
        { no: '04', title: '科研智能方法', en: 'Research Intelligence', text: '探索人工智能在资料检索、数据分析与科研协作流程中的可靠应用。' }
      ]
    },
    platform: {
      label: '03 / PLATFORMS',
      title: '让研究基础设施真正可用',
      text: '现有地震目录、历史数据与 Terra 工作台继续保留，并作为组织官网最重要的数字入口。',
      catalog: {
        kicker: 'EARTHQUAKE CATALOG',
        title: '地震事件目录',
        text: '在地图中浏览地震事件，按震级、位置和时间认识区域与全球地震活动。',
        action: '打开地震目录',
        history: '检索历史数据'
      },
      terra: {
        kicker: 'RESEARCH WORKBENCH',
        title: 'Terra 科研工作台',
        text: '面向地球科学研究过程的统一工作界面，承载问答、研究笔记、资料整理与后续智能工具。',
        action: '进入工作台',
        greeting: '准备好开始深地探索了吗？',
        prompt: '输入研究问题或整理任务'
      }
    },
    translation: {
      label: '04 / TRANSLATION',
      title: '从科学问题走向可用技术',
      lead: 'DeepSeek Earth',
      company: '深视地球（成都）信息技术有限公司',
      text: '作为技术转化与应用协作主体，面向地球科学数据、科研软件和智能工具开展工程实现与合作探索。学术研究与商业活动将保持清晰边界，并分别遵循学校与企业的管理要求。',
      tags: ['地球科学数据', '科研软件', '智能工作流'],
      visual: '技术研发场景示意'
    },
    team: {
      label: '05 / PEOPLE',
      title: '研究团队',
      text: '围绕固体地球物理、地震学及相关智能方法开展研究与人才培养。',
      people: [
        { name: '梁春涛', role: '实验室主任', field: '固体地球物理学', image: '/lct.png' },
        { name: '范兴利', role: '教授', field: '固体地球物理学', image: '/fxl.png' },
        { name: '林弈', role: '副教授', field: '固体地球物理学', image: '/ly.png' },
        { name: '刘兴业', role: '教授', field: '固体地球物理学', image: '/lxy.png' }
      ]
    },
    updates: {
      label: '06 / CURRENT WORK',
      title: '当前建设',
      items: [
        { type: 'DATA', title: '地震目录与历史数据平台', text: '持续完善事件浏览、数据检索和科研展示体验。' },
        { type: 'RESEARCH', title: '区域地震与深部构造研究', text: '围绕四川盆地及邻区组织观测、分析与科学问题。' },
        { type: 'TERRA', title: '地球科学智能工作台', text: '逐步整合资料、笔记、写作与研究辅助能力。' }
      ]
    },
    contact: {
      label: 'CONTACT',
      title: '开放交流与合作',
      text: '欢迎围绕地震学研究、数据平台、科研工具与地球科学应用开展交流。',
      addressLabel: '地址',
      address: '四川省成都市成华区二仙桥东三路 1 号 · 成都理工大学',
      siteLabel: '网站',
      site: 'www.cdutseis.com',
      note: '具体联系方式将在确认后公开。'
    },
    footer: {
      lab: '成都理工大学地震实验室',
      company: '技术转化协作：DeepSeek Earth',
      rights: '保留所有权利'
    }
  },
  en: {
    nav: {
      research: 'Research',
      platform: 'Platforms',
      team: 'People',
      translation: 'Translation',
      updates: 'Updates',
      workbench: 'Open Terra'
    },
    hero: {
      eyebrow: 'CDUT Seismology Laboratory',
      titleA: 'Observe Earth in motion.',
      titleB: 'Understand the deep.',
      text: 'Connecting seismic observation, solid Earth geophysics and intelligent analysis to build useful infrastructure for research, education and geoscience applications.',
      primary: 'Earthquake catalog',
      secondary: 'About the lab',
      marker: 'Chengdu, Sichuan',
      discipline: 'Seismology / Solid Earth Geophysics / Research Intelligence'
    },
    intro: {
      label: '01 / ABOUT',
      title: 'From surface observations to the deep Earth',
      lead: 'CDUT SEISLAB builds on the geophysics discipline at Chengdu University of Technology, with research spanning seismicity, deep structure and intelligent seismic data processing.',
      body: 'We study how observations become evidence about Earth structure and dynamics, while building data and intelligent tools that researchers, students and partners can genuinely use.',
      identityA: 'Academic research',
      identityB: 'Technology translation',
      identityAText: 'CDUT Seismology Laboratory',
      identityBText: 'DeepSeek Earth (Chengdu) Information Technology Co., Ltd.'
    },
    research: {
      label: '02 / RESEARCH',
      title: 'Observation-led, question-driven',
      text: 'Our work connects field observations, data processing, structural imaging and intelligent methods across regional seismology and deep Earth exploration.',
      concept: 'Conceptual scientific visual; not measured tomography',
      fieldConcept: 'Illustrative field-observation scene',
      areas: [
        { no: '01', title: 'Regional Seismicity', en: 'EARTHQUAKE PROCESSES', text: 'Investigating the distribution and source characteristics of earthquakes and their relationship with active structures.' },
        { no: '02', title: 'Deep Earth Imaging', en: 'CRUST & UPPER MANTLE', text: 'Using seismic-wave propagation to understand crustal and upper-mantle structure and lateral variation.' },
        { no: '03', title: 'Waveform Analysis', en: 'SEISMIC DATA', text: 'Organizing, detecting, analyzing and visualizing continuous waveforms and earthquake catalogs.' },
        { no: '04', title: 'Research Intelligence', en: 'RELIABLE AI METHODS', text: 'Exploring reliable AI support for literature, data analysis and collaborative research workflows.' }
      ]
    },
    platform: {
      label: '03 / PLATFORMS',
      title: 'Research infrastructure made useful',
      text: 'The earthquake catalog, historical archive and Terra workbench remain the primary digital entrances of the organization website.',
      catalog: {
        kicker: 'EARTHQUAKE CATALOG',
        title: 'Seismic Event Explorer',
        text: 'Browse earthquakes on a map and investigate seismic activity through magnitude, location and time.',
        action: 'Open catalog',
        history: 'Search archive'
      },
      terra: {
        kicker: 'RESEARCH WORKBENCH',
        title: 'Terra Workbench',
        text: 'A unified workspace for geoscience research, bringing together questions, notes, document organization and future intelligent tools.',
        action: 'Open workbench',
        greeting: 'Ready to explore the deep Earth?',
        prompt: 'Ask a research question or organize a task'
      }
    },
    translation: {
      label: '04 / TRANSLATION',
      title: 'Turning scientific questions into usable technology',
      lead: 'DeepSeek Earth',
      company: 'DeepSeek Earth (Chengdu) Information Technology Co., Ltd.',
      text: 'As the technology translation and application partner, DeepSeek Earth explores engineering implementation in geoscience data, research software and intelligent tools. Academic and commercial activities will maintain clear boundaries and follow their respective governance requirements.',
      tags: ['Geoscience data', 'Research software', 'Intelligent workflows'],
      visual: 'Illustrative technology-development scene'
    },
    team: {
      label: '05 / PEOPLE',
      title: 'Research team',
      text: 'Research and education across solid Earth geophysics, seismology and related intelligent methods.',
      people: [
        { name: 'Chuntao Liang', role: 'Laboratory Director', field: 'Solid Earth Geophysics', image: '/lct.png' },
        { name: 'Xingli Fan', role: 'Professor', field: 'Solid Earth Geophysics', image: '/fxl.png' },
        { name: 'Yi Lin', role: 'Associate Professor', field: 'Solid Earth Geophysics', image: '/ly.png' },
        { name: 'Xingye Liu', role: 'Professor', field: 'Solid Earth Geophysics', image: '/lxy.png' }
      ]
    },
    updates: {
      label: '06 / CURRENT WORK',
      title: 'Work in progress',
      items: [
        { type: 'DATA', title: 'Earthquake catalog and archive', text: 'Improving event browsing, data retrieval and research communication.' },
        { type: 'RESEARCH', title: 'Regional seismicity and deep structure', text: 'Organizing observations and analysis around Sichuan Basin and adjacent regions.' },
        { type: 'TERRA', title: 'Geoscience research workbench', text: 'Integrating literature, notes, writing and research-assistance capabilities.' }
      ]
    },
    contact: {
      label: 'CONTACT',
      title: 'Open to dialogue and collaboration',
      text: 'We welcome conversations around seismology, data platforms, research tools and geoscience applications.',
      addressLabel: 'Address',
      address: 'No. 1, East Third Road, Erxianqiao, Chenghua District, Chengdu, Sichuan · Chengdu University of Technology',
      siteLabel: 'Website',
      site: 'www.cdutseis.com',
      note: 'Direct contact details will be published after confirmation.'
    },
    footer: {
      lab: 'CDUT Seismology Laboratory',
      company: 'Technology translation: DeepSeek Earth',
      rights: 'All rights reserved'
    }
  }
} as const

const c = computed(() => copy[locale.value])
const waveBars = [14, 20, 10, 24, 18, 30, 22, 42, 64, 38, 78, 52, 92, 68, 44, 72, 35, 58, 28, 48, 24, 38, 18, 30, 14, 24, 12, 19, 9, 15, 8, 12]

function navigate(path: string) {
  mobileNavOpen.value = false
  router.push(path)
}

function scrollToSection(id: string) {
  mobileNavOpen.value = false
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function setLocale(next: Locale) {
  locale.value = next
  mobileNavOpen.value = false
  document.documentElement.lang = next === 'zh' ? 'zh-CN' : 'en'
  router.replace(next === 'en' ? '/en/' : '/')
}

function updateScroll() {
  navSolid.value = window.scrollY > 28
  const max = document.documentElement.scrollHeight - window.innerHeight
  const progress = max > 0 ? Math.min(1, window.scrollY / max) : 0
  document.documentElement.style.setProperty('--page-progress', `${progress * 100}%`)
}

function moveHero(event: MouseEvent) {
  if (!heroEl.value || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const rect = heroEl.value.getBoundingClientRect()
  const x = (event.clientX - rect.left) / rect.width - 0.5
  const y = (event.clientY - rect.top) / rect.height - 0.5
  heroEl.value.style.setProperty('--hero-x', `${x * 10}px`)
  heroEl.value.style.setProperty('--hero-y', `${y * 7}px`)
}

function resetHero() {
  heroEl.value?.style.setProperty('--hero-x', '0px')
  heroEl.value?.style.setProperty('--hero-y', '0px')
}

let revealObserver: IntersectionObserver | null = null

onMounted(() => {
  document.documentElement.lang = locale.value === 'zh' ? 'zh-CN' : 'en'
  document.title = locale.value === 'zh'
    ? 'CDUT SEISLAB | 成都理工大学地震实验室'
    : 'CDUT SEISLAB | Seismology & Deep Earth Research'
  updateScroll()
  window.addEventListener('scroll', updateScroll, { passive: true })

  revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible')
        revealObserver?.unobserve(entry.target)
      }
    })
  }, { threshold: 0.14 })

  document.querySelectorAll('[data-reveal]').forEach((element) => revealObserver?.observe(element))
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', updateScroll)
  revealObserver?.disconnect()
})

watch(() => props.initialLocale, (next) => {
  locale.value = next
})

watch(locale, (next) => {
  document.title = next === 'zh'
    ? 'CDUT SEISLAB | 成都理工大学地震实验室'
    : 'CDUT SEISLAB | Seismology & Deep Earth Research'
})

watch(() => route.path, (path) => {
  locale.value = path.startsWith('/en') ? 'en' : 'zh'
})
</script>

<template>
  <div class="site-page" :class="{ 'locale-en': locale === 'en' }">
    <header class="site-header" :class="{ solid: navSolid, open: mobileNavOpen }">
      <div class="scroll-progress" aria-hidden="true"></div>
      <div class="header-inner">
        <button class="brand" type="button" aria-label="CDUT SEISLAB home" @click="navigate(locale === 'en' ? '/en/' : '/')">
          <img src="/brand/cdut-seislab-mark-512.png" alt="CDUT SEISLAB" />
          <span class="brand-copy">
            <strong>CDUT SEISLAB</strong>
            <span>{{ locale === 'zh' ? '成都理工大学地震实验室' : 'Seismology Laboratory' }}</span>
          </span>
        </button>

        <nav class="desktop-nav" :aria-label="locale === 'zh' ? '主导航' : 'Primary navigation'">
          <button type="button" @click="scrollToSection('research')">{{ c.nav.research }}</button>
          <button type="button" @click="scrollToSection('platforms')">{{ c.nav.platform }}</button>
          <button type="button" @click="scrollToSection('team')">{{ c.nav.team }}</button>
          <button type="button" @click="scrollToSection('translation')">{{ c.nav.translation }}</button>
          <button type="button" @click="scrollToSection('updates')">{{ c.nav.updates }}</button>
        </nav>

        <div class="header-actions">
          <div class="locale-switch" :aria-label="locale === 'zh' ? '语言切换' : 'Language switch'">
            <button type="button" :class="{ active: locale === 'zh' }" @click="setLocale('zh')">中</button>
            <button type="button" :class="{ active: locale === 'en' }" @click="setLocale('en')">EN</button>
          </div>
          <button class="workbench-link" type="button" @click="navigate('/terra/chat')">
            <span>{{ c.nav.workbench }}</span><span aria-hidden="true">↗</span>
          </button>
          <button
            class="menu-button"
            type="button"
            :aria-expanded="mobileNavOpen"
            :aria-label="locale === 'zh' ? '打开导航' : 'Open navigation'"
            @click="mobileNavOpen = !mobileNavOpen"
          >
            <span></span><span></span>
          </button>
        </div>
      </div>

      <nav class="mobile-nav" :aria-label="locale === 'zh' ? '移动端导航' : 'Mobile navigation'">
        <button type="button" @click="scrollToSection('research')">{{ c.nav.research }}</button>
        <button type="button" @click="scrollToSection('platforms')">{{ c.nav.platform }}</button>
        <button type="button" @click="scrollToSection('team')">{{ c.nav.team }}</button>
        <button type="button" @click="scrollToSection('translation')">{{ c.nav.translation }}</button>
        <button type="button" @click="scrollToSection('updates')">{{ c.nav.updates }}</button>
        <button type="button" @click="navigate('/terra/chat')">{{ c.nav.workbench }} ↗</button>
      </nav>
    </header>

    <main>
      <section
        ref="heroEl"
        class="hero"
        @mousemove="moveHero"
        @mouseleave="resetHero"
      >
        <picture class="hero-media">
          <source media="(max-width: 720px)" srcset="/media/hero-deep-earth-mobile.jpg" />
          <img src="/media/hero-deep-earth-desktop.jpg" alt="Mountain landscape and conceptual seismic-wave visualization" />
        </picture>
        <div class="hero-overlay"></div>
        <div class="hero-grid" aria-hidden="true"></div>

        <div class="hero-content">
          <div class="hero-copy" data-reveal>
            <p class="eyebrow"><span></span>{{ c.hero.eyebrow }}</p>
            <h1><span>{{ c.hero.titleA }}</span><span>{{ c.hero.titleB }}</span></h1>
            <p class="hero-text">{{ c.hero.text }}</p>
            <div class="hero-actions">
              <button class="button primary" type="button" @click="navigate('/dashboard')">
                {{ c.hero.primary }} <span aria-hidden="true">↗</span>
              </button>
              <button class="button text" type="button" @click="scrollToSection('about')">
                {{ c.hero.secondary }} <span aria-hidden="true">↓</span>
              </button>
            </div>
          </div>

          <div class="hero-coordinates" data-reveal>
            <span>{{ c.hero.marker }}</span>
            <span>{{ c.hero.discipline }}</span>
          </div>
        </div>

        <div class="hero-wave" aria-hidden="true">
          <span
            v-for="(height, index) in waveBars"
            :key="index"
            :style="{ '--bar-height': `${height}%`, '--bar-delay': `${index * 38}ms` }"
          ></span>
        </div>
      </section>

      <div class="signal-strip" aria-hidden="true">
        <div class="signal-track">
          <span>SEISMOLOGY</span><i></i><span>DEEP EARTH</span><i></i><span>OBSERVATION</span><i></i><span>DATA INTELLIGENCE</span>
        </div>
      </div>

      <section id="about" class="section intro-section">
        <div class="section-grid">
          <div class="section-index" data-reveal>{{ c.intro.label }}</div>
          <div class="intro-main" data-reveal>
            <h2>{{ c.intro.title }}</h2>
            <p class="intro-lead">{{ c.intro.lead }}</p>
            <p class="body-copy">{{ c.intro.body }}</p>
          </div>
          <div class="identity-list" data-reveal>
            <div class="identity-row">
              <span>{{ c.intro.identityA }}</span>
              <strong>{{ c.intro.identityAText }}</strong>
            </div>
            <div class="identity-row">
              <span>{{ c.intro.identityB }}</span>
              <strong>{{ c.intro.identityBText }}</strong>
            </div>
          </div>
        </div>
      </section>

      <section id="research" class="section research-section">
        <div class="research-heading section-grid">
          <div class="section-index light" data-reveal>{{ c.research.label }}</div>
          <div class="research-title" data-reveal>
            <h2>{{ c.research.title }}</h2>
            <p>{{ c.research.text }}</p>
          </div>
        </div>

        <div class="research-visual" data-reveal>
          <img src="/media/seismic-fault-editorial.jpg" alt="Conceptual seismic waveform and fault cross-section" loading="lazy" />
          <div class="research-scan" aria-hidden="true"></div>
          <span class="visual-note">{{ c.research.concept }}</span>
        </div>

        <div class="research-content">
          <div class="field-visual" data-reveal>
            <img src="/media/field-observation-concept.jpg" alt="Illustrative field seismic observation scene" loading="lazy" />
            <span>{{ c.research.fieldConcept }}</span>
          </div>
          <div class="research-list">
            <article v-for="area in c.research.areas" :key="area.no" class="research-row" data-reveal>
              <span class="research-no">{{ area.no }}</span>
              <div>
                <h3>{{ area.title }}</h3>
                <small>{{ area.en }}</small>
              </div>
              <p>{{ area.text }}</p>
            </article>
          </div>
        </div>
      </section>

      <section id="platforms" class="section platform-section">
        <div class="platform-heading section-grid">
          <div class="section-index" data-reveal>{{ c.platform.label }}</div>
          <div data-reveal>
            <h2>{{ c.platform.title }}</h2>
            <p>{{ c.platform.text }}</p>
          </div>
        </div>

        <article class="platform-feature catalog-feature">
          <div class="platform-copy" data-reveal>
            <span class="platform-kicker">{{ c.platform.catalog.kicker }}</span>
            <h3>{{ c.platform.catalog.title }}</h3>
            <p>{{ c.platform.catalog.text }}</p>
            <div class="platform-actions">
              <button class="button dark" type="button" @click="navigate('/dashboard')">{{ c.platform.catalog.action }} ↗</button>
              <button class="button text-dark" type="button" @click="navigate('/history')">{{ c.platform.catalog.history }} →</button>
            </div>
          </div>
          <button class="catalog-preview" type="button" :aria-label="c.platform.catalog.action" @click="navigate('/dashboard')" data-reveal>
            <div class="map-toolbar">
              <span>CDUT SEIS</span><span>CATALOG / MAP</span>
            </div>
            <div class="map-field">
              <span v-for="n in 18" :key="n" class="quake-dot" :class="`dot-${n}`"></span>
              <div class="map-line line-a"></div>
              <div class="map-line line-b"></div>
              <div class="map-readout"><strong>M 5.2</strong><span>31.14° N / 103.42° E</span></div>
            </div>
          </button>
        </article>

        <article class="platform-feature terra-feature">
          <button class="terra-preview" type="button" :aria-label="c.platform.terra.action" @click="navigate('/terra/chat')" data-reveal>
            <div class="terra-rail">
              <strong>T</strong>
              <span class="active"></span><span></span><span></span><span></span>
            </div>
            <div class="terra-screen">
              <div class="terra-top"><span>Terra</span><i></i></div>
              <div class="terra-greeting"><span>T</span><p>{{ c.platform.terra.greeting }}</p></div>
              <div class="terra-input"><span>{{ c.platform.terra.prompt }}</span><b>↑</b></div>
            </div>
          </button>
          <div class="platform-copy" data-reveal>
            <span class="platform-kicker">{{ c.platform.terra.kicker }}</span>
            <h3>{{ c.platform.terra.title }}</h3>
            <p>{{ c.platform.terra.text }}</p>
            <button class="button dark" type="button" @click="navigate('/terra/chat')">{{ c.platform.terra.action }} ↗</button>
          </div>
        </article>
      </section>

      <section id="translation" class="translation-section">
        <div class="translation-copy" data-reveal>
          <span class="section-index light">{{ c.translation.label }}</span>
          <h2>{{ c.translation.title }}</h2>
          <p class="translation-lead">{{ c.translation.lead }}</p>
          <h3>{{ c.translation.company }}</h3>
          <p class="translation-text">{{ c.translation.text }}</p>
          <div class="tag-list">
            <span v-for="tag in c.translation.tags" :key="tag">{{ tag }}</span>
          </div>
        </div>
        <div class="translation-visual" data-reveal>
          <img src="/media/deepseek-earth-lab.jpg" alt="Illustrative geoscience technology development workspace" loading="lazy" />
          <span>{{ c.translation.visual }}</span>
        </div>
      </section>

      <section id="team" class="section team-section">
        <div class="team-heading section-grid">
          <div class="section-index" data-reveal>{{ c.team.label }}</div>
          <div data-reveal>
            <h2>{{ c.team.title }}</h2>
            <p>{{ c.team.text }}</p>
          </div>
        </div>
        <div class="team-list">
          <article v-for="(person, index) in c.team.people" :key="person.name" class="person" data-reveal>
            <div class="person-image"><img :src="person.image" :alt="person.name" loading="lazy" /></div>
            <span class="person-index">0{{ index + 1 }}</span>
            <h3>{{ person.name }}</h3>
            <p>{{ person.role }}</p>
            <small>{{ person.field }}</small>
          </article>
        </div>
      </section>

      <section id="updates" class="section updates-section">
        <div class="updates-heading section-grid">
          <div class="section-index" data-reveal>{{ c.updates.label }}</div>
          <h2 data-reveal>{{ c.updates.title }}</h2>
        </div>
        <div class="updates-list">
          <article v-for="(item, index) in c.updates.items" :key="item.type" data-reveal>
            <span class="update-no">0{{ index + 1 }}</span>
            <span class="update-type">{{ item.type }}</span>
            <h3>{{ item.title }}</h3>
            <p>{{ item.text }}</p>
          </article>
        </div>
      </section>

      <section class="contact-section">
        <div class="contact-inner" data-reveal>
          <span class="section-index light">{{ c.contact.label }}</span>
          <h2>{{ c.contact.title }}</h2>
          <p class="contact-lead">{{ c.contact.text }}</p>
          <div class="contact-grid">
            <div><span>{{ c.contact.addressLabel }}</span><p>{{ c.contact.address }}</p></div>
            <div><span>{{ c.contact.siteLabel }}</span><p>{{ c.contact.site }}</p></div>
          </div>
          <p class="contact-note">{{ c.contact.note }}</p>
        </div>
      </section>
    </main>

    <footer class="site-footer">
      <div>
        <img src="/brand/cdut-seislab-mark-512.png" alt="CDUT SEISLAB" />
        <strong>CDUT SEISLAB</strong>
      </div>
      <div class="footer-meta">
        <span>{{ c.footer.lab }}</span>
        <span>{{ c.footer.company }}</span>
      </div>
      <p>© {{ currentYear }} · {{ c.footer.rights }}</p>
    </footer>
  </div>
</template>

<style scoped>
.site-page {
  --ink: #111719;
  --paper: #f5f6f3;
  --white: #ffffff;
  --red: #d44335;
  --red-dark: #9f2c24;
  --teal: #167c7a;
  --ice: #b9dde0;
  --muted: #697173;
  --line: rgba(17, 23, 25, 0.16);
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

button,
a {
  font: inherit;
}

button:focus-visible,
a:focus-visible {
  outline: 2px solid var(--red);
  outline-offset: 3px;
}

.site-header {
  position: fixed;
  inset: 0 0 auto;
  z-index: 100;
  height: 78px;
  color: var(--ink);
  background: rgba(247, 248, 246, 0.82);
  border-bottom: 1px solid rgba(17, 23, 25, 0.12);
  backdrop-filter: blur(16px);
  transition: background 220ms ease, box-shadow 220ms ease;
}

.site-header.solid {
  background: rgba(247, 248, 246, 0.96);
  box-shadow: 0 8px 26px rgba(17, 23, 25, 0.08);
}

.scroll-progress {
  position: absolute;
  inset: auto auto -1px 0;
  width: var(--page-progress);
  height: 2px;
  background: var(--red);
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
  min-width: 250px;
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
}

.brand-copy {
  display: grid;
  gap: 2px;
}

.brand-copy strong {
  font-size: 16px;
  line-height: 1.1;
}

.brand-copy span {
  color: var(--muted);
  font-size: 11px;
  line-height: 1.25;
}

.desktop-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  flex: 1;
}

.desktop-nav button,
.mobile-nav button {
  padding: 8px 0;
  border: 0;
  color: #42494b;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  font-weight: 650;
}

.desktop-nav button {
  position: relative;
}

.desktop-nav button::after {
  content: "";
  position: absolute;
  inset: auto 50% 2px;
  width: 0;
  height: 1px;
  background: var(--red);
  transition: width 180ms ease, inset 180ms ease;
}

.desktop-nav button:hover::after {
  inset-inline: 0;
  width: 100%;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.locale-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  width: 76px;
  height: 34px;
  padding: 3px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.62);
}

.locale-switch button {
  border: 0;
  border-radius: 4px;
  color: var(--muted);
  background: transparent;
  cursor: pointer;
  font-size: 11px;
  font-weight: 800;
}

.locale-switch button.active {
  color: var(--white);
  background: var(--ink);
}

.workbench-link,
.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 42px;
  padding: 0 18px;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 750;
  font-size: 13px;
  transition: transform 180ms ease, background 180ms ease, color 180ms ease, border-color 180ms ease;
}

.workbench-link {
  color: white;
  background: var(--ink);
}

.workbench-link:hover,
.button:hover {
  transform: translateY(-2px);
}

.menu-button,
.mobile-nav {
  display: none;
}

.hero {
  --hero-x: 0px;
  --hero-y: 0px;
  position: relative;
  height: calc(100svh - 130px);
  min-height: 560px;
  max-height: 920px;
  margin-top: 78px;
  overflow: hidden;
  isolation: isolate;
}

.hero-media,
.hero-media img,
.hero-overlay,
.hero-grid {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.hero-media {
  z-index: -3;
  overflow: hidden;
  background: #c7d1d4;
}

.hero-media img {
  inset: -10px;
  width: calc(100% + 20px);
  height: calc(100% + 20px);
  object-fit: cover;
  object-position: center;
  transform: translate3d(var(--hero-x), var(--hero-y), 0) scale(1.025);
  animation: hero-breathe 16s ease-in-out infinite alternate;
  transition: transform 240ms ease-out;
}

.hero-overlay {
  z-index: -2;
  background:
    linear-gradient(90deg, rgba(245, 247, 245, 0.98) 0%, rgba(245, 247, 245, 0.9) 28%, rgba(245, 247, 245, 0.35) 52%, rgba(8, 14, 16, 0.08) 100%),
    linear-gradient(0deg, rgba(11, 17, 18, 0.34) 0%, transparent 38%);
}

.hero-grid {
  z-index: -1;
  opacity: 0.26;
  background-image:
    linear-gradient(rgba(17, 23, 25, 0.16) 1px, transparent 1px),
    linear-gradient(90deg, rgba(17, 23, 25, 0.16) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: linear-gradient(90deg, black, transparent 68%);
}

.hero-content {
  position: relative;
  width: min(1480px, calc(100% - 96px));
  height: 100%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 44px 0 86px;
}

.hero-copy {
  width: min(700px, 60%);
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 11px;
  margin: 0 0 24px;
  color: #31383a;
  font-size: 13px;
  font-weight: 800;
}

.eyebrow span {
  width: 32px;
  height: 2px;
  background: var(--red);
}

.hero h1,
.section h2,
.translation-section h2,
.contact-section h2 {
  font-family: "Iowan Old Style", "Noto Serif SC", "Songti SC", Georgia, serif;
  font-weight: 700;
}

.hero h1 {
  margin: 0;
  font-size: 76px;
  line-height: 1.05;
  color: #101617;
}

.hero h1 span {
  display: block;
}

.hero h1 span:last-child {
  color: var(--red-dark);
}

.hero-text {
  max-width: 620px;
  margin: 28px 0 30px;
  color: #3b4445;
  font-size: 17px;
  line-height: 1.8;
}

.hero-actions,
.platform-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.button.primary {
  color: white;
  background: var(--red-dark);
}

.button.text,
.button.text-dark {
  color: var(--ink);
  background: rgba(255, 255, 255, 0.42);
  border-color: var(--line);
}

.button.dark {
  color: white;
  background: var(--ink);
}

.hero-coordinates {
  position: absolute;
  inset: auto 0 32px;
  display: flex;
  justify-content: space-between;
  gap: 24px;
  color: rgba(255, 255, 255, 0.88);
  font-family: "Fira Code", monospace;
  font-size: 11px;
  text-transform: uppercase;
}

.hero-wave {
  position: absolute;
  right: 6%;
  bottom: 64px;
  width: min(36vw, 520px);
  height: 92px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  opacity: 0.72;
  pointer-events: none;
}

.hero-wave::after {
  content: "";
  position: absolute;
  inset: 50% 0 auto;
  height: 1px;
  background: rgba(255, 255, 255, 0.46);
}

.hero-wave span {
  width: 2px;
  height: var(--bar-height);
  min-height: 5px;
  background: var(--red);
  animation: wave-pulse 2.4s ease-in-out var(--bar-delay) infinite alternate;
}

.signal-strip {
  height: 52px;
  overflow: hidden;
  color: #d9e6e6;
  background: var(--ink);
}

.signal-track {
  width: min(1480px, calc(100% - 48px));
  height: 100%;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  font-family: "Fira Code", monospace;
  font-size: 10px;
}

.signal-track i {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--teal), var(--red), transparent);
}

.section {
  position: relative;
  padding: 120px max(48px, calc((100vw - 1480px) / 2));
  scroll-margin-top: 78px;
}

.section-grid {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 42px;
}

.section-index {
  color: var(--red-dark);
  font-family: "Fira Code", monospace;
  font-size: 11px;
  font-weight: 700;
}

.section-index.light {
  color: #9cd1d1;
}

.intro-section {
  background: var(--paper);
}

.intro-main {
  max-width: 980px;
}

.intro-main h2,
.research-title h2,
.platform-heading h2,
.team-heading h2,
.updates-heading h2 {
  margin: 0;
  font-size: 52px;
  line-height: 1.16;
}

.intro-lead {
  max-width: 920px;
  margin: 38px 0 20px;
  color: #20292b;
  font-size: 24px;
  line-height: 1.65;
}

.body-copy {
  max-width: 760px;
  margin: 0;
  color: var(--muted);
  font-size: 16px;
  line-height: 1.9;
}

.identity-list {
  grid-column: 2;
  margin-top: 56px;
  border-top: 1px solid var(--line);
}

.identity-row {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 28px;
  padding: 20px 0;
  border-bottom: 1px solid var(--line);
}

.identity-row span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}

.identity-row strong {
  font-size: 15px;
  line-height: 1.5;
}

.research-section {
  padding-inline: 0;
  color: white;
  background: #11191a;
}

.research-heading,
.research-content {
  width: min(1480px, calc(100% - 96px));
  margin: 0 auto;
}

.research-title {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 0.65fr);
  align-items: end;
  gap: 72px;
}

.research-title h2 {
  color: white;
}

.research-title p {
  margin: 0;
  color: #aebabb;
  line-height: 1.8;
}

.research-visual {
  position: relative;
  width: 100%;
  height: min(58vw, 760px);
  min-height: 460px;
  margin-top: 72px;
  overflow: hidden;
  background: white;
}

.research-visual img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.research-scan {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(41, 161, 158, 0.15) 48%, rgba(212, 67, 53, 0.18) 51%, transparent 54%);
  transform: translateX(-100%);
  animation: scan 8s ease-in-out infinite;
}

.visual-note,
.field-visual span,
.translation-visual span {
  position: absolute;
  inset: auto 18px 16px auto;
  padding: 7px 10px;
  color: rgba(255, 255, 255, 0.88);
  background: rgba(10, 16, 17, 0.74);
  border-radius: 4px;
  font-size: 10px;
  backdrop-filter: blur(8px);
}

.research-content {
  display: grid;
  grid-template-columns: minmax(320px, 0.8fr) minmax(0, 1.2fr);
  gap: 72px;
  align-items: start;
  padding-top: 92px;
}

.field-visual {
  position: sticky;
  top: 110px;
  height: 520px;
  overflow: hidden;
  border-radius: 6px;
}

.field-visual img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.research-list {
  border-top: 1px solid rgba(255, 255, 255, 0.22);
}

.research-row {
  display: grid;
  grid-template-columns: 42px minmax(190px, 0.7fr) minmax(260px, 1fr);
  gap: 24px;
  padding: 30px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.18);
}

.research-no {
  color: #72b7b5;
  font-family: "Fira Code", monospace;
  font-size: 11px;
}

.research-row h3 {
  margin: 0 0 8px;
  font-size: 22px;
}

.research-row small {
  color: #85aaa9;
  font-family: "Fira Code", monospace;
  font-size: 9px;
}

.research-row p {
  margin: 0;
  color: #aebabb;
  font-size: 14px;
  line-height: 1.75;
}

.platform-section {
  background: #f8f9f7;
}

.platform-heading > div:last-child,
.team-heading > div:last-child {
  display: grid;
  grid-template-columns: 1fr minmax(320px, 0.55fr);
  gap: 72px;
  align-items: end;
}

.platform-heading p,
.team-heading p {
  margin: 0;
  color: var(--muted);
  line-height: 1.8;
}

.platform-feature {
  display: grid;
  grid-template-columns: minmax(320px, 0.72fr) minmax(0, 1.28fr);
  gap: 72px;
  align-items: center;
  margin-top: 96px;
}

.platform-feature.terra-feature {
  grid-template-columns: minmax(0, 1.28fr) minmax(320px, 0.72fr);
  padding-top: 96px;
  border-top: 1px solid var(--line);
}

.platform-kicker {
  display: block;
  margin-bottom: 18px;
  color: var(--teal);
  font-family: "Fira Code", monospace;
  font-size: 10px;
  font-weight: 700;
}

.platform-copy h3 {
  margin: 0;
  font-family: "Iowan Old Style", "Noto Serif SC", "Songti SC", Georgia, serif;
  font-size: 42px;
  line-height: 1.2;
}

.platform-copy > p {
  max-width: 520px;
  margin: 24px 0 30px;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.85;
}

.catalog-preview,
.terra-preview {
  width: 100%;
  height: 500px;
  padding: 0;
  border: 0;
  border-radius: 7px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 24px 54px rgba(17, 23, 25, 0.14);
  transition: transform 220ms ease, box-shadow 220ms ease;
}

.catalog-preview:hover,
.terra-preview:hover {
  transform: translateY(-5px);
  box-shadow: 0 30px 64px rgba(17, 23, 25, 0.2);
}

.catalog-preview {
  display: grid;
  grid-template-rows: 48px 1fr;
  color: white;
  background: #11191a;
}

.map-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.14);
  font-family: "Fira Code", monospace;
  font-size: 9px;
}

.map-field {
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(rgba(121, 164, 164, 0.13) 1px, transparent 1px),
    linear-gradient(90deg, rgba(121, 164, 164, 0.13) 1px, transparent 1px),
    radial-gradient(ellipse at 62% 46%, #365354 0%, #1a292b 36%, #101719 72%);
  background-size: 46px 46px, 46px 46px, auto;
}

.map-field::before,
.map-field::after {
  content: "";
  position: absolute;
  width: 64%;
  height: 36%;
  border: 1px solid rgba(152, 196, 194, 0.28);
  border-radius: 48% 52% 42% 58%;
  transform: rotate(-16deg);
}

.map-field::before { left: 8%; top: 16%; }
.map-field::after { right: -8%; bottom: 10%; transform: rotate(21deg); }

.quake-dot {
  position: absolute;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #e05445;
  box-shadow: 0 0 0 0 rgba(224, 84, 69, 0.46);
  animation: quake-pulse 2.8s ease-out infinite;
}

.dot-1 { left: 18%; top: 31%; }.dot-2 { left: 28%; top: 58%; }.dot-3 { left: 36%; top: 42%; }
.dot-4 { left: 44%; top: 69%; }.dot-5 { left: 51%; top: 34%; }.dot-6 { left: 61%; top: 49%; }
.dot-7 { left: 69%; top: 29%; }.dot-8 { left: 77%; top: 61%; }.dot-9 { left: 83%; top: 38%; }
.dot-10 { left: 24%; top: 76%; }.dot-11 { left: 56%; top: 79%; }.dot-12 { left: 72%; top: 73%; }
.dot-13 { left: 14%; top: 51%; }.dot-14 { left: 39%; top: 24%; }.dot-15 { left: 88%; top: 75%; }
.dot-16 { left: 64%; top: 16%; }.dot-17 { left: 47%; top: 54%; }.dot-18 { left: 31%; top: 36%; }
.dot-3, .dot-6, .dot-11 { width: 11px; height: 11px; background: #f0a34a; animation-delay: 500ms; }
.dot-5, .dot-8 { width: 13px; height: 13px; animation-delay: 1100ms; }

.map-line {
  position: absolute;
  width: 62%;
  height: 1px;
  background: linear-gradient(90deg, transparent, #66aaa8, transparent);
  transform-origin: center;
}

.line-a { left: 12%; top: 48%; transform: rotate(18deg); }
.line-b { right: 2%; top: 58%; transform: rotate(-26deg); }

.map-readout {
  position: absolute;
  right: 18px;
  bottom: 18px;
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  color: white;
  background: rgba(8, 13, 14, 0.76);
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 4px;
  text-align: left;
  backdrop-filter: blur(10px);
}

.map-readout strong { color: #f06a59; font-size: 18px; }
.map-readout span { color: #9fb1b2; font-family: "Fira Code", monospace; font-size: 8px; }

.terra-preview {
  display: grid;
  grid-template-columns: 82px 1fr;
  color: var(--ink);
  background: white;
  border: 1px solid var(--line);
  text-align: left;
}

.terra-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 28px;
  padding: 24px 0;
  background: #eef1ef;
  border-right: 1px solid var(--line);
}

.terra-rail strong {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  color: white;
  background: var(--teal);
  border-radius: 5px;
}

.terra-rail span {
  width: 22px;
  height: 2px;
  background: #a9b2b1;
}

.terra-rail span.active {
  width: 30px;
  background: var(--red);
}

.terra-screen {
  position: relative;
  padding: 26px 30px;
}

.terra-top {
  display: flex;
  justify-content: space-between;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--line);
  font-weight: 800;
}

.terra-top i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3f9e75;
}

.terra-greeting {
  display: flex;
  gap: 16px;
  margin-top: 46px;
}

.terra-greeting > span {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  color: white;
  background: var(--teal);
  border-radius: 50%;
  flex: 0 0 auto;
  font-size: 12px;
}

.terra-greeting p {
  margin: 4px 0;
  font-family: "Iowan Old Style", "Noto Serif SC", "Songti SC", Georgia, serif;
  font-size: 24px;
}

.terra-input {
  position: absolute;
  inset: auto 30px 30px;
  min-height: 76px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 20px;
  color: #8b9495;
  border: 1px solid var(--line);
  border-radius: 7px;
}

.terra-input b {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  color: white;
  background: var(--ink);
  border-radius: 5px;
}

.translation-section {
  display: grid;
  grid-template-columns: minmax(360px, 0.78fr) minmax(0, 1.22fr);
  min-height: 760px;
  scroll-margin-top: 78px;
  color: white;
  background: #101718;
}

.translation-copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 92px max(48px, calc((100vw - 1480px) / 2));
}

.translation-copy h2 {
  max-width: 600px;
  margin: 28px 0 56px;
  font-size: 50px;
  line-height: 1.18;
}

.translation-lead {
  margin: 0 0 8px;
  color: #7fc4c2;
  font-family: "Fira Code", monospace;
  font-size: 15px;
  font-weight: 800;
}

.translation-copy h3 {
  max-width: 560px;
  margin: 0;
  font-size: 19px;
  line-height: 1.5;
}

.translation-text {
  max-width: 580px;
  margin: 24px 0 30px;
  color: #aebabb;
  font-size: 14px;
  line-height: 1.85;
}

.tag-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag-list span {
  padding: 8px 10px;
  color: #d9e5e5;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 4px;
  font-size: 11px;
}

.translation-visual {
  position: relative;
  min-height: 620px;
  overflow: hidden;
}

.translation-visual::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(16, 23, 24, 0.58), transparent 30%);
}

.translation-visual img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.translation-visual span { z-index: 1; }

.team-section {
  background: var(--paper);
}

.team-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin-top: 76px;
}

.person {
  position: relative;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--line);
}

.person-image {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 5;
  overflow: hidden;
  background: #dfe2df;
}

.person-image::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(0deg, rgba(17, 23, 25, 0.18), transparent 42%);
  opacity: 0;
  transition: opacity 220ms ease;
}

.person:hover .person-image::after { opacity: 1; }

.person img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
  filter: saturate(0.86);
  transition: transform 420ms ease, filter 220ms ease;
}

.person:hover img {
  transform: scale(1.025);
  filter: saturate(1);
}

.person-index {
  display: block;
  margin-top: 18px;
  color: var(--red-dark);
  font-family: "Fira Code", monospace;
  font-size: 10px;
}

.person h3 {
  margin: 10px 0 8px;
  font-size: 22px;
}

.person p,
.person small {
  display: block;
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
}

.updates-section {
  padding-top: 48px;
  background: var(--paper);
}

.updates-heading h2 {
  font-size: 42px;
}

.updates-list {
  margin-top: 48px;
  border-top: 1px solid var(--ink);
}

.updates-list article {
  display: grid;
  grid-template-columns: 54px 120px minmax(240px, 0.8fr) minmax(300px, 1.2fr);
  gap: 24px;
  align-items: center;
  padding: 25px 0;
  border-bottom: 1px solid var(--line);
}

.update-no,
.update-type {
  font-family: "Fira Code", monospace;
  font-size: 10px;
}

.update-no { color: var(--red-dark); }
.update-type { color: var(--teal); font-weight: 700; }
.updates-list h3 { margin: 0; font-size: 18px; }
.updates-list p { margin: 0; color: var(--muted); font-size: 13px; line-height: 1.7; }

.contact-section {
  padding: 120px max(48px, calc((100vw - 1480px) / 2));
  color: white;
  background: var(--red-dark);
}

.contact-inner {
  max-width: 1100px;
}

.contact-section h2 {
  max-width: 820px;
  margin: 26px 0;
  font-size: 58px;
  line-height: 1.15;
}

.contact-lead {
  max-width: 680px;
  margin: 0;
  color: rgba(255, 255, 255, 0.82);
  font-size: 18px;
  line-height: 1.8;
}

.contact-grid {
  display: grid;
  grid-template-columns: 1.5fr 0.6fr;
  gap: 64px;
  margin-top: 64px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.34);
}

.contact-grid span {
  color: rgba(255, 255, 255, 0.62);
  font-size: 11px;
  font-weight: 700;
}

.contact-grid p {
  margin: 8px 0 0;
  font-size: 15px;
  line-height: 1.7;
}

.contact-note {
  margin: 34px 0 0;
  color: rgba(255, 255, 255, 0.58);
  font-size: 11px;
}

.site-footer {
  min-height: 170px;
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 48px;
  align-items: center;
  padding: 44px max(48px, calc((100vw - 1480px) / 2));
  color: #d5dddd;
  background: #0c1213;
}

.site-footer > div:first-child {
  display: flex;
  align-items: center;
  gap: 12px;
}

.site-footer img {
  width: 42px;
  height: 42px;
  object-fit: contain;
  filter: grayscale(1) brightness(2.2);
}

.site-footer strong { font-size: 15px; }

.footer-meta {
  display: grid;
  gap: 7px;
  color: #889697;
  font-size: 11px;
}

.site-footer > p {
  margin: 0;
  color: #687677;
  font-size: 10px;
}

[data-reveal] {
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 700ms ease, transform 700ms cubic-bezier(0.2, 0.72, 0.18, 1);
}

[data-reveal].is-visible {
  opacity: 1;
  transform: translateY(0);
}

@keyframes hero-breathe {
  from { filter: saturate(0.9) contrast(0.98); }
  to { filter: saturate(1.04) contrast(1.02); }
}

@keyframes wave-pulse {
  0% { transform: scaleY(0.72); opacity: 0.52; }
  100% { transform: scaleY(1.18); opacity: 1; }
}

@keyframes scan {
  0%, 14% { transform: translateX(-100%); }
  62%, 100% { transform: translateX(100%); }
}

@keyframes quake-pulse {
  0% { box-shadow: 0 0 0 0 rgba(224, 84, 69, 0.5); }
  70%, 100% { box-shadow: 0 0 0 15px rgba(224, 84, 69, 0); }
}

@media (max-width: 1180px) {
  .desktop-nav { display: none; }
  .header-inner { width: calc(100% - 36px); }
  .menu-button {
    width: 42px;
    height: 42px;
    display: grid;
    place-content: center;
    gap: 6px;
    padding: 0;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.66);
    cursor: pointer;
  }
  .menu-button span { width: 18px; height: 1px; background: var(--ink); transition: transform 180ms ease; }
  .site-header.open .menu-button span:first-child { transform: translateY(3.5px) rotate(45deg); }
  .site-header.open .menu-button span:last-child { transform: translateY(-3.5px) rotate(-45deg); }
  .mobile-nav {
    position: absolute;
    inset: 78px 0 auto;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0;
    padding: 14px 24px 20px;
    background: rgba(247, 248, 246, 0.98);
    border-bottom: 1px solid var(--line);
    box-shadow: 0 18px 34px rgba(17, 23, 25, 0.1);
    opacity: 0;
    visibility: hidden;
    transform: translateY(-8px);
    transition: opacity 180ms ease, transform 180ms ease, visibility 180ms ease;
  }
  .site-header.open .mobile-nav { opacity: 1; visibility: visible; transform: translateY(0); }
  .mobile-nav button { padding: 13px 12px; text-align: left; }
  .hero h1 { font-size: 62px; }
  .research-title { grid-template-columns: 1fr; gap: 28px; }
  .research-content { grid-template-columns: 0.72fr 1.28fr; gap: 44px; }
  .research-row { grid-template-columns: 38px 1fr; }
  .research-row p { grid-column: 2; }
  .platform-heading > div:last-child,
  .team-heading > div:last-child { grid-template-columns: 1fr; gap: 24px; }
  .platform-feature,
  .platform-feature.terra-feature { gap: 42px; }
  .translation-section { grid-template-columns: 0.95fr 1.05fr; }
  .team-list { grid-template-columns: repeat(2, 1fr); gap: 42px 18px; }
}

@media (max-width: 820px) {
  .site-header { height: 68px; }
  .header-inner { width: calc(100% - 28px); }
  .brand { min-width: 0; }
  .brand img { width: 36px; height: 36px; }
  .brand-copy strong { font-size: 14px; }
  .brand-copy span { display: none; }
  .workbench-link { display: none; }
  .locale-switch { width: 70px; }
  .mobile-nav { inset-block-start: 68px; grid-template-columns: 1fr 1fr; }
  .hero { height: calc(100svh - 104px); min-height: 630px; margin-top: 68px; }
  .hero-content { width: calc(100% - 40px); padding: 52px 0 100px; justify-content: flex-end; }
  .hero-copy { width: 100%; }
  .hero h1 { font-size: 48px; }
  .hero-text { max-width: 560px; font-size: 15px; line-height: 1.7; }
  .hero-overlay { background: linear-gradient(0deg, rgba(244, 246, 244, 0.98) 0%, rgba(244, 246, 244, 0.87) 45%, rgba(244, 246, 244, 0.18) 80%, rgba(244, 246, 244, 0.05) 100%); }
  .hero-grid { display: none; }
  .hero-coordinates { bottom: 18px; color: #50595a; }
  .hero-coordinates span:last-child { display: none; }
  .hero-wave { right: -12%; bottom: 128px; width: 58vw; opacity: 0.34; }
  .signal-track { width: calc(100% - 28px); justify-content: flex-start; overflow: hidden; }
  .signal-track span:nth-of-type(n+3), .signal-track i:nth-of-type(n+2) { display: none; }
  .section { padding: 88px 24px; }
  .section-grid { grid-template-columns: 1fr; gap: 22px; }
  .intro-main h2,
  .research-title h2,
  .platform-heading h2,
  .team-heading h2 { font-size: 40px; }
  .intro-lead { font-size: 20px; }
  .identity-list { grid-column: 1; margin-top: 36px; }
  .research-heading,
  .research-content { width: calc(100% - 48px); }
  .research-visual { height: 66vw; min-height: 360px; margin-top: 52px; }
  .research-content { grid-template-columns: 1fr; padding-top: 56px; }
  .field-visual { position: relative; top: auto; height: 460px; }
  .research-row { grid-template-columns: 38px 1fr; }
  .platform-feature,
  .platform-feature.terra-feature { grid-template-columns: 1fr; gap: 42px; margin-top: 68px; }
  .platform-feature.terra-feature { padding-top: 68px; }
  .terra-feature .terra-preview { order: 2; }
  .catalog-preview, .terra-preview { height: 430px; }
  .translation-section { grid-template-columns: 1fr; min-height: auto; }
  .translation-copy { padding: 88px 24px; }
  .translation-copy h2 { margin-bottom: 42px; font-size: 40px; }
  .translation-visual { min-height: 520px; }
  .updates-list article { grid-template-columns: 42px 90px 1fr; }
  .updates-list p { grid-column: 3; }
  .contact-section { padding: 92px 24px; }
  .contact-section h2 { font-size: 46px; }
  .site-footer { grid-template-columns: 1fr 1fr; padding: 40px 24px; }
  .site-footer > p { grid-column: 1 / -1; }
}

@media (max-width: 560px) {
  .mobile-nav { grid-template-columns: 1fr; max-height: calc(100svh - 68px); overflow-y: auto; }
  .hero { min-height: 660px; }
  .hero-media img { object-position: center; }
  .hero h1 { font-size: 40px; line-height: 1.08; }
  .eyebrow { margin-bottom: 18px; font-size: 11px; }
  .hero-actions { align-items: stretch; }
  .hero-actions .button { flex: 1 1 100%; }
  .signal-strip { height: 44px; }
  .section { padding: 72px 18px; }
  .intro-main h2,
  .research-title h2,
  .platform-heading h2,
  .team-heading h2 { font-size: 34px; }
  .identity-row { grid-template-columns: 1fr; gap: 8px; }
  .research-heading,
  .research-content { width: calc(100% - 36px); }
  .research-visual { min-height: 300px; }
  .field-visual { height: 390px; }
  .research-row { gap: 14px; }
  .research-row h3 { font-size: 19px; }
  .platform-copy h3 { font-size: 34px; }
  .catalog-preview, .terra-preview { height: 340px; }
  .terra-preview { grid-template-columns: 54px 1fr; }
  .terra-rail { gap: 22px; }
  .terra-screen { padding: 18px; }
  .terra-greeting { margin-top: 32px; }
  .terra-greeting p { font-size: 18px; }
  .terra-input { inset: auto 18px 18px; min-height: 62px; font-size: 11px; }
  .translation-copy { padding: 72px 18px; }
  .translation-copy h2 { font-size: 34px; }
  .translation-visual { min-height: 380px; }
  .team-list { grid-template-columns: 1fr 1fr; gap: 32px 12px; }
  .person h3 { font-size: 18px; }
  .updates-list article { grid-template-columns: 34px 1fr; gap: 12px; }
  .update-type { grid-column: 2; }
  .updates-list h3, .updates-list p { grid-column: 2; }
  .contact-section { padding: 72px 18px; }
  .contact-section h2 { font-size: 38px; }
  .contact-grid { grid-template-columns: 1fr; gap: 28px; margin-top: 44px; }
  .site-footer { grid-template-columns: 1fr; gap: 26px; padding: 36px 18px; }
  .site-footer > p { grid-column: 1; }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    animation-duration: 1ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 1ms !important;
  }
  [data-reveal] { opacity: 1; transform: none; }
}
</style>
