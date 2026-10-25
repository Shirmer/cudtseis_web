<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import PageShell from '../components/PageShell.vue'
import { SITE, localeFromPath } from '../config/site'
import { privacy, terms, type LegalDoc } from '../content/legal'
import { usePageMeta } from '../composables/usePageMeta'

const route = useRoute()
const locale = computed(() => localeFromPath(route.path))
const doc = computed<LegalDoc>(() => (route.meta.doc === 'terms' ? terms[locale.value] : privacy[locale.value]))
const updated = computed(() => (locale.value === 'zh'
  ? '更新日期：2026 年 10 月 13 日'
  : 'Last updated: October 13, 2026'))

usePageMeta(() => locale.value, () => ({
  title: `${doc.value.title} | ${locale.value === 'zh' ? SITE.brandZh : SITE.brandEn}`,
  description: (doc.value.intro[0] ?? '').split(/(?<=[。.])/)[0].slice(0, 140)
}))
</script>

<template>
  <PageShell
    :locale="locale"
    :label="doc.label"
    :title="doc.title"
    :meta="updated"
  >
    <div class="legal-layout">
      <aside class="legal-toc" :aria-label="locale === 'zh' ? '目录' : 'Contents'">
        <p>{{ locale === 'zh' ? '目录' : 'Contents' }}</p>
        <a v-for="(section, index) in doc.sections" :key="section.title" :href="`#section-${index}`">
          {{ section.title }}
        </a>
        <a href="#contact">{{ doc.contact.title }}</a>
      </aside>

      <article class="legal-doc">
        <p v-for="paragraph in doc.intro" :key="paragraph" class="legal-intro">{{ paragraph }}</p>

        <section v-for="(section, index) in doc.sections" :id="`section-${index}`" :key="section.title" class="legal-section">
          <h2>{{ section.title }}</h2>
          <p v-for="paragraph in section.paragraphs ?? []" :key="paragraph">{{ paragraph }}</p>
          <ul v-if="section.list">
            <li v-for="entry in section.list" :key="entry">{{ entry }}</li>
          </ul>
          <div v-if="section.items" class="legal-items">
            <div v-for="item in section.items" :key="item.title" class="legal-item">
              <strong>{{ item.title }}</strong>
              <p>{{ item.text }}</p>
            </div>
          </div>
        </section>

        <section id="contact" class="legal-section legal-contact">
          <h2>{{ doc.contact.title }}</h2>
          <p v-for="paragraph in doc.contact.paragraphs" :key="paragraph">{{ paragraph }}</p>
          <dl>
            <div v-for="row in doc.contact.rows" :key="row.label">
              <dt>{{ row.label }}</dt>
              <dd>
                <a v-if="row.value.includes('@')" :href="`mailto:${row.value}`">{{ row.value }}</a>
                <template v-else>{{ row.value }}</template>
              </dd>
            </div>
          </dl>
        </section>
      </article>
    </div>
  </PageShell>
</template>

<style scoped>
.legal-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 48px;
  align-items: start;
}

.legal-toc {
  position: sticky;
  top: 110px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 22px 20px;
  border: 1px solid rgba(16, 24, 29, 0.12);
  border-radius: 16px;
  background: #fff;
}

.legal-toc p {
  margin: 0 0 10px;
  color: #a85a0e;
  font-size: 12px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.legal-toc a {
  padding: 6px 8px;
  border-radius: 8px;
  color: #667072;
  font-size: 13px;
  line-height: 1.5;
  text-decoration: none;
  transition: background 160ms ease, color 160ms ease;
}

.legal-toc a:hover {
  color: #10181d;
  background: rgba(217, 122, 28, 0.1);
}

.legal-doc {
  padding: 48px 52px;
  border: 1px solid rgba(16, 24, 29, 0.1);
  border-radius: 20px;
  background: #fff;
}

.legal-intro {
  margin: 0 0 18px;
  color: #3a4448;
  font-size: 15px;
  line-height: 1.95;
}

.legal-section {
  margin-top: 44px;
  scroll-margin-top: 104px;
}

.legal-section h2 {
  margin: 0 0 18px;
  padding-top: 26px;
  border-top: 1px solid rgba(16, 24, 29, 0.1);
  font-size: 19px;
  line-height: 1.4;
}

.legal-section p {
  margin: 0 0 14px;
  color: #3a4448;
  font-size: 15px;
  line-height: 1.95;
}

.legal-section ul {
  margin: 0 0 14px;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
}

.legal-section li {
  position: relative;
  padding-left: 22px;
  color: #3a4448;
  font-size: 15px;
  line-height: 1.85;
}

.legal-section li::before {
  content: "";
  position: absolute;
  top: 0.72em;
  left: 2px;
  width: 10px;
  height: 2px;
  background: #d97a1c;
}

.legal-items {
  display: grid;
  gap: 14px;
}

.legal-item {
  padding: 16px 18px;
  border: 1px solid rgba(16, 24, 29, 0.1);
  border-radius: 12px;
  background: #faf9f5;
}

.legal-item strong {
  display: block;
  margin-bottom: 6px;
  font-size: 15px;
}

.legal-item p {
  margin: 0;
  font-size: 14px;
}

.legal-contact dl {
  margin: 20px 0 0;
  display: grid;
  gap: 10px;
}

.legal-contact dl div {
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 12px;
  align-items: baseline;
}

.legal-contact dt {
  color: #667072;
  font-size: 14px;
}

.legal-contact dd {
  margin: 0;
  font-size: 15px;
}

.legal-contact a {
  color: #a85a0e;
  font-weight: 600;
  text-decoration: none;
}

.legal-contact a:hover {
  text-decoration: underline;
}

@media (max-width: 1024px) {
  .legal-layout {
    grid-template-columns: 1fr;
    gap: 24px;
  }

  .legal-toc {
    position: static;
  }
}

@media (max-width: 720px) {
  .legal-doc {
    padding: 28px 20px;
  }

  .legal-contact dl div {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}
</style>
