<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import PageShell from '../components/PageShell.vue'
import DownloadButton from '../components/DownloadButton.vue'
import { SITE, localeFromPath } from '../config/site'
import { usePageMeta } from '../composables/usePageMeta'

const route = useRoute()
const locale = computed(() => localeFromPath(route.path))

const copy = computed(() => locale.value === 'zh'
  ? {
      label: 'CONTACT',
      title: '联系我们',
      subtitle: '欢迎围绕产品、合作与技术支持与我们联系，我们会在收到消息后尽快回复。',
      direct: '联系方式',
      emailNote: '产品咨询、合作洽谈与技术支持统一通过以下邮箱受理。',
      directions: '合作方向',
      items: [
        { title: '产品试用与演示', text: '申请试用账号，了解 GeoCamera 在真实野外场景中的工作方式。' },
        { title: '行业项目合作', text: '面向地质调查、工程勘察单位的项目合作与团队部署。' },
        { title: '高校与科研合作', text: '面向高校与科研院所的教学、实习与科研数据场景合作。' },
        { title: '定制开发与数据服务', text: '围绕野外数据采集与管理的定制开发、数据整理与分析服务。' }
      ],
      company: '公司信息',
      companyName: '公司名称',
      address: '地址',
      email: '邮箱',
      site: '官网',
      siteValue: '域名备案办理中，暂通过当前地址访问',
      downloadTitle: '下载 GeoCamera',
      downloadText: '安卓版可直接下载安装。'
    }
  : {
      label: 'CONTACT',
      title: 'Contact Us',
      subtitle: 'Reach out for product questions, partnerships and technical support — we will get back to you as soon as possible.',
      direct: 'Contact details',
      emailNote: 'Product inquiries, partnerships and technical support are handled through the email below.',
      directions: 'How we can work together',
      items: [
        { title: 'Trials & demos', text: 'Request a trial account and see how GeoCamera works in real field scenarios.' },
        { title: 'Industry projects', text: 'Project cooperation and team deployment for geological survey and engineering units.' },
        { title: 'Academic cooperation', text: 'Collaboration with universities and institutes on teaching, field practice and research data.' },
        { title: 'Custom development & data services', text: 'Customized field data collection and management, data organization and analysis.' }
      ],
      company: 'Company information',
      companyName: 'Company',
      address: 'Address',
      email: 'Email',
      site: 'Website',
      siteValue: 'Domain filing in progress — temporarily available at the current address',
      downloadTitle: 'Get GeoCamera',
      downloadText: 'The Android version is available for direct download.'
    })

usePageMeta(
  () => locale.value,
  () => (locale.value === 'zh' ? `联系我们 | ${SITE.brandZh}` : `Contact | ${SITE.brandEn}`)
)
</script>

<template>
  <PageShell
    :locale="locale"
    :label="copy.label"
    :title="copy.title"
    :subtitle="copy.subtitle"
  >
    <div class="contact-layout">
      <div class="contact-main">
        <section class="contact-block">
          <h2>{{ copy.direct }}</h2>
          <p>{{ copy.emailNote }}</p>
          <a class="email-card" :href="`mailto:${SITE.contact.email}`">
            <span class="email-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="5" width="18" height="14" rx="2" />
                <path d="m3 7 9 6 9-6" />
              </svg>
            </span>
            <span class="email-copy">
              <strong>{{ SITE.contact.email }}</strong>
              <small>{{ locale === 'zh' ? '点击发送邮件' : 'Click to send an email' }}</small>
            </span>
          </a>
        </section>

        <section class="contact-block">
          <h2>{{ copy.directions }}</h2>
          <div class="direction-grid">
            <article v-for="item in copy.items" :key="item.title">
              <h3>{{ item.title }}</h3>
              <p>{{ item.text }}</p>
            </article>
          </div>
        </section>
      </div>

      <aside class="contact-side">
        <section class="company-card">
          <h2>{{ copy.company }}</h2>
          <dl>
            <div>
              <dt>{{ copy.companyName }}</dt>
              <dd>{{ locale === 'zh' ? SITE.companyZh : SITE.companyEn }}</dd>
            </div>
            <div>
              <dt>{{ copy.address }}</dt>
              <dd>{{ locale === 'zh' ? SITE.contact.addressZh : SITE.contact.addressEn }}</dd>
            </div>
            <div>
              <dt>{{ copy.email }}</dt>
              <dd><a :href="`mailto:${SITE.contact.email}`">{{ SITE.contact.email }}</a></dd>
            </div>
            <div>
              <dt>{{ copy.site }}</dt>
              <dd>{{ copy.siteValue }}</dd>
            </div>
          </dl>
        </section>

        <section class="download-card">
          <h2>{{ copy.downloadTitle }}</h2>
          <p>{{ copy.downloadText }}</p>
          <DownloadButton :locale="locale" variant="primary" />
        </section>
      </aside>
    </div>
  </PageShell>
</template>

<style scoped>
.contact-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(280px, 1fr);
  gap: 40px;
  align-items: start;
}

.contact-block {
  padding: 40px 44px;
  border: 1px solid rgba(16, 24, 29, 0.1);
  border-radius: 20px;
  background: #fff;
}

.contact-block + .contact-block {
  margin-top: 28px;
}

.contact-block h2 {
  margin: 0 0 12px;
  font-size: 22px;
}

.contact-block > p {
  margin: 0 0 24px;
  color: #667072;
  font-size: 15px;
  line-height: 1.85;
}

.email-card {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 22px 24px;
  border: 1px solid rgba(217, 122, 28, 0.35);
  border-radius: 16px;
  background: rgba(217, 122, 28, 0.08);
  text-decoration: none;
  transition: transform 200ms ease, background 200ms ease, box-shadow 200ms ease;
}

.email-card:hover {
  transform: translateY(-3px);
  background: rgba(217, 122, 28, 0.14);
  box-shadow: 0 18px 40px rgba(16, 24, 29, 0.1);
}

.email-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  color: #fff;
  background: #d97a1c;
}

.email-icon svg {
  width: 24px;
  height: 24px;
}

.email-copy {
  display: grid;
  gap: 3px;
}

.email-copy strong {
  color: #10181d;
  font-size: 18px;
}

.email-copy small {
  color: #667072;
  font-size: 13px;
}

.direction-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.direction-grid article {
  padding: 20px 20px 22px;
  border: 1px solid rgba(16, 24, 29, 0.1);
  border-radius: 14px;
  background: #faf9f5;
}

.direction-grid h3 {
  margin: 0 0 8px;
  font-size: 16px;
}

.direction-grid p {
  margin: 0;
  color: #667072;
  font-size: 14px;
  line-height: 1.75;
}

.contact-side {
  display: grid;
  gap: 24px;
}

.company-card {
  padding: 32px 30px;
  border: 1px solid rgba(16, 24, 29, 0.1);
  border-radius: 20px;
  background: #fff;
}

.company-card h2,
.download-card h2 {
  margin: 0 0 18px;
  font-size: 19px;
}

.company-card dl {
  margin: 0;
  display: grid;
  gap: 16px;
}

.company-card dl div {
  display: grid;
  gap: 4px;
}

.company-card dt {
  color: #667072;
  font-size: 12px;
  letter-spacing: 0.12em;
}

.company-card dd {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
}

.company-card a {
  color: #a85a0e;
  font-weight: 600;
  text-decoration: none;
}

.company-card a:hover {
  text-decoration: underline;
}

.download-card {
  padding: 32px 30px;
  border-radius: 20px;
  color: #fff;
  background: #10181d;
}

.download-card p {
  margin: 0 0 22px;
  color: rgba(255, 255, 255, 0.66);
  font-size: 14px;
  line-height: 1.75;
}

@media (max-width: 1024px) {
  .contact-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .contact-block {
    padding: 28px 22px;
  }

  .direction-grid {
    grid-template-columns: 1fr;
  }
}
</style>
