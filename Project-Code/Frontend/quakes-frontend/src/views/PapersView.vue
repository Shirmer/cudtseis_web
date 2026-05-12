<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiUrl } from '../config/api'

type KnowledgeInit = {
  backend: string
  documents: number
  units: number
  indexVersion: string
  warning?: string
}

type KnowledgeHit = {
  unitId: string
  documentId: string
  paperId: string
  title: string
  contentType: string
  text: string
  page?: number | null
  score: number
  metadata: Record<string, unknown>
}

type KnowledgeContextItem = {
  unitId: string
  documentId: string
  paperId: string
  title: string
  contentType: string
  text: string
  page?: number | null
  unitIndex: number
  position: 'before' | 'current' | 'after' | 'nearby'
  metadata: Record<string, unknown>
}

type KnowledgeContext = {
  unitId: string
  documentId: string
  paperId: string
  title: string
  page?: number | null
  fileName: string
  sourceAvailable: boolean
  items: KnowledgeContextItem[]
}

type KnowledgeSearch = {
  query: string
  results: KnowledgeHit[]
  diagnostics: Record<string, unknown>
  storeStats: {
    documents: number
    units: number
  }
}

const router = useRouter()

const query = ref('')
const topK = ref(10)
const paperId = ref('')
const loading = ref(false)
const initLoading = ref(false)
const error = ref('')
const initState = ref<KnowledgeInit | null>(null)
const response = ref<KnowledgeSearch | null>(null)
const contextByUnit = ref<Record<string, KnowledgeContext>>({})
const contextLoading = ref<Record<string, boolean>>({})
const contextError = ref<Record<string, string>>({})

const exampleQueries = [
  'active fault rupture tectonic setting',
  '地震危险性 断层 构造背景',
  'supershear rupture near-field ground motion',
  '地震震源机制 与 活动断层'
]

const results = computed(() => response.value?.results ?? [])
const stats = computed(() => {
  if (response.value?.storeStats) return response.value.storeStats
  if (initState.value) return { documents: initState.value.documents, units: initState.value.units }
  return { documents: 0, units: 0 }
})

const qualityFlags = computed(() => {
  const flags = response.value?.diagnostics?.qualityFlags
  return Array.isArray(flags) && flags.length ? flags.join('；') : '暂无明显风险'
})

const initKnowledge = async () => {
  initLoading.value = true
  try {
    const res = await fetch(apiUrl('/knowledge/init'), { method: 'POST' })
    if (res.ok) initState.value = await res.json() as KnowledgeInit
  } finally {
    initLoading.value = false
  }
}

const searchPapers = async () => {
  if (!query.value.trim()) {
    error.value = '请输入要检索的问题、关键词或地震源信息'
    return
  }

  loading.value = true
  error.value = ''
  try {
    const res = await fetch(apiUrl('/knowledge/search'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query.value.trim(),
        topK: Number(topK.value) || 10,
        paperId: paperId.value.trim() || undefined
      })
    })
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}))
      throw new Error(detail.detail || `检索失败 (${res.status})`)
    }
    response.value = await res.json() as KnowledgeSearch
  } catch (err) {
    error.value = err instanceof Error ? err.message : '论文检索暂时不可用'
  } finally {
    loading.value = false
  }
}

const closeContext = (unitId: string) => {
  const next = { ...contextByUnit.value }
  delete next[unitId]
  contextByUnit.value = next
}

const toggleContext = async (hit: KnowledgeHit) => {
  if (contextByUnit.value[hit.unitId]) {
    closeContext(hit.unitId)
    return
  }

  contextLoading.value = { ...contextLoading.value, [hit.unitId]: true }
  contextError.value = { ...contextError.value, [hit.unitId]: '' }
  try {
    const res = await fetch(apiUrl(`/knowledge/units/${encodeURIComponent(hit.unitId)}/context?window=1`))
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}))
      throw new Error(detail.detail || `上下文加载失败 (${res.status})`)
    }
    const payload = await res.json() as KnowledgeContext
    contextByUnit.value = { ...contextByUnit.value, [hit.unitId]: payload }
  } catch (err) {
    contextError.value = {
      ...contextError.value,
      [hit.unitId]: err instanceof Error ? err.message : '上下文暂时不可用'
    }
  } finally {
    contextLoading.value = { ...contextLoading.value, [hit.unitId]: false }
  }
}

const openOriginal = (hit: KnowledgeHit) => {
  const baseUrl = apiUrl(`/documents/${encodeURIComponent(hit.documentId)}/file`)
  const pageAnchor = hit.page ? `#page=${hit.page}` : ''
  window.open(`${baseUrl}${pageAnchor}`, '_blank', 'noopener,noreferrer')
}

const positionLabel = (position: KnowledgeContextItem['position']) => {
  if (position === 'current') return '当前命中'
  if (position === 'before') return '前文'
  if (position === 'after') return '后文'
  return '相关片段'
}

const runExample = (value: string) => {
  query.value = value
  void searchPapers()
}

const askWithCurrentQuery = () => {
  if (!query.value.trim()) return
  router.push({
    path: '/terra/chat',
    query: { q: query.value.trim() }
  })
}

onMounted(() => {
  void initKnowledge()
})
</script>

<template>
  <main class="papers-page">
    <header class="topbar">
      <button class="ghost-button" @click="router.push('/')">返回首页</button>
      <strong>论文检索</strong>
      <button class="ghost-button" @click="router.push('/knowledge')">导入文献</button>
    </header>

    <section class="hero">
      <div>
        <span class="kicker">Literature Search</span>
        <h1>检索论文与证据</h1>
        <p>输入科研问题、关键词，或从地震目录复制震级、深度、位置等信息，系统会在已入库文献中寻找相关证据。</p>
      </div>
      <div class="metrics">
        <div><strong>{{ stats.documents }}</strong><span>文献</span></div>
        <div><strong>{{ stats.units }}</strong><span>知识单元</span></div>
        <div><strong>{{ initState?.backend ?? '-' }}</strong><span>检索后端</span></div>
      </div>
    </section>

    <section v-if="error" class="notice error">{{ error }}</section>
    <section v-if="initState?.warning" class="notice warning">{{ initState.warning }}</section>

    <section class="search-panel">
      <label>
        <span>检索问题</span>
        <textarea
          v-model="query"
          rows="4"
          placeholder="例如：活动断层破裂与地震危险性的证据是什么？"
          @keydown.meta.enter.prevent="searchPapers"
          @keydown.ctrl.enter.prevent="searchPapers"
        ></textarea>
      </label>

      <div class="search-options">
        <label>
          <span>结果数量</span>
          <input v-model.number="topK" type="number" min="1" max="30" />
        </label>
        <label>
          <span>限定论文 ID</span>
          <input v-model="paperId" placeholder="可选" />
        </label>
      </div>

      <div class="actions">
        <button class="primary-button" :disabled="loading" @click="searchPapers">
          {{ loading ? '检索中' : '检索论文' }}
        </button>
        <button class="ghost-button" :disabled="!query.trim()" @click="askWithCurrentQuery">去工作台问答</button>
        <button class="ghost-button" :disabled="initLoading" @click="initKnowledge">
          {{ initLoading ? '刷新中' : '刷新库状态' }}
        </button>
      </div>
    </section>

    <section class="example-strip">
      <span>常用问题</span>
      <button v-for="item in exampleQueries" :key="item" @click="runExample(item)">{{ item }}</button>
    </section>

    <section v-if="response" class="diagnostic-strip">
      <span>命中 {{ response.results.length }}</span>
      <span>候选 {{ response.diagnostics.candidateCount ?? '-' }}</span>
      <span>策略 {{ response.diagnostics.retrievalStrategy ?? 'hybrid' }}</span>
      <span>{{ qualityFlags }}</span>
    </section>

    <section class="results">
      <div class="result-head">
        <h2>检索结果</h2>
        <span>{{ response ? `${response.results.length} 条` : '等待检索' }}</span>
      </div>

      <div v-if="loading" class="state-card">正在检索文献...</div>
      <div v-else-if="response && !results.length" class="state-card">没有找到匹配结果，可以换一个问题或先导入更多文献。</div>
      <div v-else-if="!response" class="state-card">输入问题后开始检索。</div>

      <article v-for="(hit, index) in results" v-else :key="hit.unitId" class="result-card">
        <div class="result-index">{{ index + 1 }}</div>
        <div class="card-head">
          <h3>{{ hit.title || hit.paperId }}</h3>
          <span>{{ hit.score.toFixed(3) }}</span>
        </div>
        <p>{{ hit.text }}</p>
        <footer>
          <span>{{ hit.contentType }}</span>
          <span v-if="hit.page">p.{{ hit.page }}</span>
          <span>{{ hit.paperId }}</span>
        </footer>
        <div class="card-actions">
          <button class="inline-button" :disabled="contextLoading[hit.unitId]" @click="toggleContext(hit)">
            <span v-if="contextLoading[hit.unitId]">加载中</span>
            <span v-else>{{ contextByUnit[hit.unitId] ? '收起上下文' : '查看上下文' }}</span>
          </button>
          <button class="inline-button" @click="openOriginal(hit)">
            打开原文{{ hit.page ? ` p.${hit.page}` : '' }}
          </button>
        </div>

        <div v-if="contextError[hit.unitId]" class="context-error">{{ contextError[hit.unitId] }}</div>
        <div v-if="contextByUnit[hit.unitId]" class="context-panel">
          <div
            v-for="item in contextByUnit[hit.unitId].items"
            :key="item.unitId"
            class="context-row"
            :class="{ current: item.position === 'current' }"
          >
            <div class="context-meta">
              <strong>{{ positionLabel(item.position) }}</strong>
              <span>{{ item.contentType }}</span>
              <span v-if="item.page">p.{{ item.page }}</span>
            </div>
            <p>{{ item.text }}</p>
          </div>
        </div>
      </article>
    </section>
  </main>
</template>

<style scoped>
.papers-page {
  min-height: 100vh;
  color: #11231f;
  background:
    linear-gradient(125deg, rgba(29, 143, 130, 0.12), transparent 34%),
    repeating-linear-gradient(168deg, rgba(21, 42, 38, 0.05) 0 1px, transparent 1px 34px),
    linear-gradient(180deg, #f3efe4 0%, #eef6f0 48%, #fbfbf4 100%);
  font-family: Lato, "PingFang SC", "Microsoft YaHei", sans-serif;
  overflow-x: hidden;
}

.papers-page::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(29, 143, 130, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(184, 101, 53, 0.04) 1px, transparent 1px);
  background-size: 58px 58px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.62), transparent 82%);
}

.topbar,
.hero,
.search-panel,
.example-strip,
.diagnostic-strip,
.results,
.notice {
  position: relative;
  z-index: 1;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding: 14px max(22px, 5vw);
  background: rgba(245, 242, 231, 0.82);
  border-bottom: 1px solid rgba(38, 76, 68, 0.13);
  backdrop-filter: blur(18px);
}

.topbar strong {
  font-size: 14px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #25423c;
}

.hero,
.search-panel,
.example-strip,
.diagnostic-strip,
.results,
.notice {
  width: min(1180px, 91vw);
  margin: 22px auto 0;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(310px, 380px);
  gap: 30px;
  align-items: end;
  padding: 24px 0 6px;
}

.kicker {
  display: inline-flex;
  margin-bottom: 12px;
  padding: 5px 10px;
  border: 1px solid rgba(38, 76, 68, 0.15);
  border-radius: 999px;
  color: #24665d;
  background: rgba(255, 255, 251, 0.58);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

h1,
h2,
h3 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  color: #10231f;
  font-size: clamp(30px, 4vw, 46px);
  line-height: 1.08;
  font-weight: 900;
}

h2 {
  color: #142823;
  font-size: 21px;
}

.hero p {
  max-width: 760px;
  margin: 12px 0 0;
  color: #5e7069;
  line-height: 1.72;
  font-size: 15px;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.metrics div,
.search-panel,
.diagnostic-strip,
.results {
  border: 1px solid rgba(38, 76, 68, 0.14);
  background: rgba(255, 255, 251, 0.78);
  box-shadow: 0 18px 46px rgba(24, 44, 41, 0.08);
  backdrop-filter: blur(16px);
}

.metrics div {
  min-height: 76px;
  padding: 15px;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.metrics strong {
  display: block;
  color: #15342f;
  font-size: 24px;
  font-weight: 900;
  overflow-wrap: anywhere;
}

.metrics span {
  display: block;
  color: #6c7c76;
  font-size: 12px;
  font-weight: 800;
}

.notice {
  padding: 13px 15px;
  border-radius: 14px;
  font-size: 13px;
  box-shadow: 0 12px 30px rgba(24, 44, 41, 0.06);
}

.notice.error {
  color: #84251f;
  background: rgba(255, 244, 238, 0.9);
  border: 1px solid rgba(196, 81, 55, 0.28);
}

.notice.warning {
  color: #77500e;
  background: rgba(255, 248, 219, 0.9);
  border: 1px solid rgba(196, 145, 53, 0.3);
}

.search-panel {
  padding: 22px;
  border-radius: 22px;
}

label {
  display: grid;
  gap: 8px;
}

label span {
  color: #52645e;
  font-size: 13px;
  font-weight: 900;
}

textarea,
input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(38, 76, 68, 0.18);
  border-radius: 14px;
  padding: 12px 13px;
  font: inherit;
  color: #11231f;
  background: rgba(255, 255, 251, 0.86);
  transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

textarea {
  resize: vertical;
  min-height: 128px;
  line-height: 1.65;
}

textarea:focus,
input:focus {
  outline: none;
  border-color: rgba(29, 143, 130, 0.55);
  box-shadow: 0 0 0 4px rgba(29, 143, 130, 0.1);
  background: #fffefa;
}

.search-options {
  display: grid;
  grid-template-columns: 168px minmax(0, 1fr);
  gap: 14px;
  margin-top: 15px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}

button {
  min-height: 40px;
  border-radius: 13px;
  padding: 0 15px;
  font: inherit;
  font-weight: 900;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

button:hover:not(:disabled) {
  transform: translateY(-1px);
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.primary-button {
  border: 1px solid #184a43;
  background: linear-gradient(135deg, #183934, #1d8f82);
  color: #ffffff;
  box-shadow: 0 14px 28px rgba(23, 95, 86, 0.22);
}

.ghost-button {
  border: 1px solid rgba(38, 76, 68, 0.16);
  background: rgba(255, 255, 251, 0.76);
  color: #24423d;
}

.ghost-button:hover:not(:disabled),
.inline-button:hover:not(:disabled) {
  border-color: rgba(29, 143, 130, 0.36);
  box-shadow: 0 10px 22px rgba(22, 58, 53, 0.1);
}

.inline-button {
  min-height: 34px;
  border: 1px solid rgba(38, 76, 68, 0.16);
  background: rgba(255, 255, 251, 0.8);
  color: #146b62;
  font-size: 13px;
}

.example-strip,
.diagnostic-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  align-items: center;
}

.example-strip {
  padding: 0;
}

.example-strip span,
.diagnostic-strip span {
  color: #62756f;
  font-size: 12px;
  font-weight: 800;
}

.example-strip button,
.diagnostic-strip span {
  min-height: 31px;
  border: 1px solid rgba(38, 76, 68, 0.14);
  border-radius: 999px;
  background: rgba(255, 255, 251, 0.74);
  padding: 5px 11px;
}

.example-strip button {
  color: #2d4943;
  font-size: 12px;
}

.diagnostic-strip {
  padding: 13px;
  border-radius: 18px;
}

.diagnostic-strip span {
  color: #2d4943;
}

.results {
  padding: 22px;
  margin-bottom: 54px;
  border-radius: 22px;
}

.result-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
}

.result-head span {
  color: #64756f;
  font-size: 13px;
  font-weight: 800;
}

.state-card {
  padding: 30px;
  border: 1px dashed rgba(38, 76, 68, 0.24);
  border-radius: 16px;
  color: #64756f;
  text-align: center;
  background: rgba(255, 255, 251, 0.45);
}

.result-card {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(38, 76, 68, 0.13);
  border-radius: 18px;
  background:
    linear-gradient(90deg, rgba(29, 143, 130, 0.06), transparent 38%),
    rgba(255, 255, 251, 0.82);
  padding: 17px;
  box-shadow: 0 12px 30px rgba(24, 44, 41, 0.055);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.result-card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, #1d8f82, #b86535);
  opacity: 0.75;
}

.result-index {
  position: absolute;
  right: 15px;
  bottom: 14px;
  color: rgba(20, 40, 35, 0.08);
  font-size: 52px;
  line-height: 1;
  font-weight: 900;
  pointer-events: none;
}

.result-card + .result-card {
  margin-top: 13px;
}

.result-card:hover {
  transform: translateY(-2px);
  border-color: rgba(29, 143, 130, 0.34);
  box-shadow: 0 20px 42px rgba(24, 44, 41, 0.11);
}

.card-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding-right: 10px;
}

.card-head h3 {
  color: #142823;
  font-size: 18px;
  line-height: 1.35;
}

.card-head span {
  align-self: flex-start;
  border: 1px solid rgba(29, 143, 130, 0.24);
  border-radius: 999px;
  padding: 4px 8px;
  color: #146b62;
  background: rgba(29, 143, 130, 0.08);
  font-size: 12px;
  font-weight: 900;
}

.result-card p {
  margin: 12px 0;
  color: #354a44;
  line-height: 1.82;
}

.result-card footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #667a72;
  font-size: 12px;
  font-weight: 800;
}

.result-card footer span {
  border: 1px solid rgba(38, 76, 68, 0.12);
  border-radius: 999px;
  padding: 4px 8px;
  background: rgba(255, 255, 251, 0.58);
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  margin-top: 14px;
}

.context-error {
  margin-top: 11px;
  color: #8f2b22;
  font-size: 13px;
  font-weight: 800;
}

.context-panel {
  margin-top: 14px;
  padding: 13px 0 0 16px;
  border-top: 1px solid rgba(38, 76, 68, 0.12);
  border-left: 3px solid rgba(29, 143, 130, 0.45);
}

.context-row {
  padding: 0 0 14px;
}

.context-row + .context-row {
  margin-top: 14px;
  border-top: 1px dashed rgba(38, 76, 68, 0.16);
  padding-top: 14px;
}

.context-row.current {
  border-left: 3px solid #b86535;
  padding-left: 12px;
}

.context-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  color: #667a72;
  font-size: 12px;
}

.context-meta strong {
  color: #146b62;
}

.context-row p {
  margin: 8px 0 0;
  color: #354a44;
}

@media (max-width: 900px) {
  .hero,
  .search-options {
    grid-template-columns: 1fr;
  }

  .metrics {
    grid-template-columns: 1fr;
  }

  .topbar {
    padding-inline: 16px;
  }
}

@media (max-width: 620px) {
  .topbar strong {
    display: none;
  }

  .search-panel,
  .results {
    padding: 16px;
  }

  .card-head {
    flex-direction: column;
  }
}
</style>
