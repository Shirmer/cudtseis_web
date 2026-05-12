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

      <article v-for="hit in results" v-else :key="hit.unitId" class="result-card">
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
  background: #f7f9fc;
  color: #172033;
  font-family: "Helvetica Neue", "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 40px;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid #e2e8f0;
  backdrop-filter: blur(12px);
}

.hero,
.search-panel,
.example-strip,
.diagnostic-strip,
.results,
.notice {
  width: min(1180px, 90vw);
  margin: 20px auto 0;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 28px;
  align-items: end;
  padding: 30px 0 8px;
}

.kicker {
  display: block;
  margin-bottom: 10px;
  color: #52627a;
  font-size: 13px;
}

h1,
h2,
h3 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  font-size: 42px;
  line-height: 1.18;
}

.hero p {
  max-width: 720px;
  margin: 14px 0 0;
  color: #52627a;
  line-height: 1.8;
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
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.metrics div {
  padding: 14px;
}

.metrics strong {
  display: block;
  font-size: 22px;
  overflow-wrap: anywhere;
}

.metrics span {
  display: block;
  margin-top: 5px;
  color: #64748b;
  font-size: 12px;
}

.notice {
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 13px;
}

.notice.error {
  color: #a8071a;
  background: #fff1f0;
  border: 1px solid #ffccc7;
}

.notice.warning {
  color: #7a4f00;
  background: #fffbe6;
  border: 1px solid #ffe58f;
}

.search-panel {
  padding: 20px;
}

label {
  display: grid;
  gap: 7px;
}

label span {
  color: #475569;
  font-size: 13px;
}

textarea,
input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 11px 12px;
  font: inherit;
  color: #172033;
  background: #ffffff;
}

textarea {
  resize: vertical;
  min-height: 110px;
}

textarea:focus,
input:focus {
  outline: none;
  border-color: #2f5da8;
  box-shadow: 0 0 0 3px rgba(47, 93, 168, 0.12);
}

.search-options {
  display: grid;
  grid-template-columns: 160px minmax(0, 1fr);
  gap: 12px;
  margin-top: 14px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

button {
  min-height: 38px;
  border-radius: 8px;
  padding: 0 14px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.primary-button {
  border: 1px solid #2f5da8;
  background: #2f5da8;
  color: #ffffff;
}

.ghost-button {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
}

.inline-button {
  min-height: 32px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #1f4f99;
  font-size: 13px;
}

.example-strip,
.diagnostic-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.example-strip span,
.diagnostic-strip span {
  color: #64748b;
  font-size: 12px;
}

.example-strip button,
.diagnostic-strip span {
  min-height: 30px;
  border: 1px solid #dbe4ee;
  border-radius: 999px;
  background: #ffffff;
  padding: 5px 10px;
}

.diagnostic-strip {
  padding: 12px;
}

.diagnostic-strip span {
  color: #334155;
}

.results {
  padding: 20px;
  margin-bottom: 50px;
}

.result-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.result-head span {
  color: #64748b;
  font-size: 13px;
}

.state-card {
  padding: 26px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  color: #64748b;
  text-align: center;
}

.result-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
  padding: 16px;
}

.result-card + .result-card {
  margin-top: 12px;
}

.result-card:hover {
  border-color: #2f5da8;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.07);
}

.card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.card-head h3 {
  font-size: 18px;
}

.card-head span {
  color: #1f4f99;
  font-size: 12px;
}

.result-card p {
  margin: 10px 0;
  color: #334155;
  line-height: 1.75;
}

.result-card footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.context-error {
  margin-top: 10px;
  color: #b42318;
  font-size: 13px;
}

.context-panel {
  margin-top: 12px;
  padding: 12px 0 0 14px;
  border-top: 1px solid #e2e8f0;
  border-left: 3px solid #9db7df;
}

.context-row {
  padding: 0 0 14px;
}

.context-row + .context-row {
  margin-top: 14px;
  border-top: 1px dashed #dbe4ee;
  padding-top: 14px;
}

.context-row.current {
  border-left: 3px solid #2f5da8;
  padding-left: 12px;
}

.context-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  color: #64748b;
  font-size: 12px;
}

.context-meta strong {
  color: #1f4f99;
}

.context-row p {
  margin: 8px 0 0;
  color: #334155;
}

@media (max-width: 900px) {
  .hero,
  .search-options {
    grid-template-columns: 1fr;
  }

  .metrics {
    grid-template-columns: 1fr;
  }
}
</style>
