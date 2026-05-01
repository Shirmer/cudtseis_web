<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiUrl } from '../config/api'

type PaperItem = {
  id: string
  title: string
  authorsText: string
  journal: string
  year: number
  topics: string[]
  evidenceType: string
  abstractPreview: string
  retrievalScore: number
  retrievalBreakdown: Record<string, number>
  metadataDecision: { quality: string; reasons: string[] }
  validation: { passed: boolean }
}

type PaperResponse = {
  total: number
  items: PaperItem[]
  topicCounts: Record<string, number>
  queryPlan: {
    rewritten: string[]
    candidateCount: number
    recalledCount: number
    rerank: string
  }
}

type StorageStatus = {
  papers: number
  chunks: number
  relations: number
  sizeBytes: number
  status: string
}

const router = useRouter()
const query = ref('')
const selectedTopic = ref('')
const loading = ref(false)
const error = ref('')
const response = ref<PaperResponse | null>(null)
const storage = ref<StorageStatus | null>(null)
const showImport = ref(false)
const importLoading = ref(false)
const importError = ref('')
const importForm = ref({
  title: '',
  authors: '',
  journal: '',
  year: new Date().getFullYear(),
  doi: '',
  url: '',
  topics: '',
  evidenceType: 'Manual',
  abstractPreview: '',
  claim: '',
  evidence: '',
  reasoning: ''
})

const papers = computed(() => response.value?.items ?? [])
const topicEntries = computed(() => Object.entries(response.value?.topicCounts ?? {}))
const queryPlan = computed(() => response.value?.queryPlan)
const presetQuestions = [
  '震源机制怎么解释',
  '四川盆地构造背景',
  '余震序列风险判断',
  '地震预警方法比较',
  '强震动与灾害影响'
]

const loadPapers = async () => {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams()
    if (query.value.trim()) params.set('q', query.value.trim())
    if (selectedTopic.value) params.set('topic', selectedTopic.value)
    params.set('limit', '30')
    const res = await fetch(apiUrl(`/papers?${params.toString()}`))
    if (!res.ok) throw new Error(`Paper API failed with ${res.status}`)
    response.value = (await res.json()) as PaperResponse
  } catch (err) {
    error.value = err instanceof Error ? err.message : '论文数据库暂时不可用'
  } finally {
    loading.value = false
  }
}

const loadStorage = async () => {
  const res = await fetch(apiUrl('/papers/storage'))
  if (res.ok) storage.value = (await res.json()) as StorageStatus
}

const selectTopic = (topic: string) => {
  selectedTopic.value = selectedTopic.value === topic ? '' : topic
  loadPapers()
}

const runPresetQuery = (value: string) => {
  query.value = value
  loadPapers()
}

const openPaper = (paperId: string) => {
  router.push(`/papers/${encodeURIComponent(paperId)}`)
}

const submitPaper = async () => {
  importLoading.value = true
  importError.value = ''
  try {
    const payload = {
      ...importForm.value,
      authors: importForm.value.authors.split(/[;,，；]/).map((item) => item.trim()).filter(Boolean),
      topics: importForm.value.topics.split(/[;,，；]/).map((item) => item.trim()).filter(Boolean)
    }
    const res = await fetch(apiUrl('/papers'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}))
      throw new Error(detail.detail || `Paper import failed with ${res.status}`)
    }
    const created = await res.json()
    showImport.value = false
    resetImportForm()
    await loadStorage()
    await loadPapers()
    openPaper(created.id)
  } catch (err) {
    importError.value = err instanceof Error ? err.message : '入库失败'
  } finally {
    importLoading.value = false
  }
}

const resetImportForm = () => {
  importForm.value = {
    title: '',
    authors: '',
    journal: '',
    year: new Date().getFullYear(),
    doi: '',
    url: '',
    topics: '',
    evidenceType: 'Manual',
    abstractPreview: '',
    claim: '',
    evidence: '',
    reasoning: ''
  }
}

const formatBytes = (value: number) => {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

onMounted(async () => {
  await Promise.all([loadPapers(), loadStorage()])
})
</script>

<template>
  <main class="papers-page">
    <header class="topbar">
      <button class="ghost-button" @click="router.push('/')">返回首页</button>
      <strong>CDUT SEISLAB · PAPER DATABASE</strong>
      <button class="ghost-button" @click="showImport = !showImport">论文入库</button>
    </header>

    <section class="hero">
      <div>
        <span class="kicker">Evidence-first RAG</span>
        <h1>论文检索</h1>
        <p>先检索和筛选文献，点击结果进入更完整的地震专业解读、证据链、校验和语义切块页面。</p>
      </div>
      <div v-if="storage" class="metrics">
        <div><strong>{{ storage.papers }}</strong><span>论文</span></div>
        <div><strong>{{ storage.chunks }}</strong><span>语义块</span></div>
        <div><strong>{{ storage.relations }}</strong><span>图谱关系</span></div>
        <div><strong>{{ formatBytes(storage.sizeBytes) }}</strong><span>本地库</span></div>
      </div>
    </section>

    <section class="search-panel">
      <input
        v-model="query"
        type="search"
        placeholder="检索论文、方法、区域或证据，例如：四川盆地、余震序列、断层机制"
        @keyup.enter="loadPapers"
      />
      <button class="primary-button" :disabled="loading" @click="loadPapers">
        {{ loading ? '检索中' : '检索' }}
      </button>
    </section>

    <section class="preset-strip">
      <span>问题导向入口</span>
      <button v-for="item in presetQuestions" :key="item" class="preset-chip" @click="runPresetQuery(item)">
        {{ item }}
      </button>
    </section>

    <section v-if="queryPlan" class="query-strip">
      <span>候选 {{ queryPlan.candidateCount }}</span>
      <span>召回 {{ queryPlan.recalledCount }}</span>
      <span>{{ queryPlan.rerank }}</span>
      <span v-for="rewrite in queryPlan.rewritten" :key="rewrite">{{ rewrite }}</span>
    </section>

    <section v-if="showImport" class="import-panel">
      <h2>论文入库</h2>
      <div class="import-grid">
        <input v-model="importForm.title" placeholder="论文标题" />
        <input v-model="importForm.authors" placeholder="作者，用逗号或分号分隔" />
        <input v-model="importForm.journal" placeholder="期刊 / 会议 / 来源" />
        <input v-model.number="importForm.year" type="number" placeholder="年份" />
        <input v-model="importForm.doi" placeholder="DOI" />
        <input v-model="importForm.url" placeholder="URL / PDF / HTML 来源" />
        <input v-model="importForm.topics" placeholder="主题，用逗号或分号分隔" />
        <input v-model="importForm.evidenceType" placeholder="证据类型" />
      </div>
      <textarea v-model="importForm.abstractPreview" placeholder="正文/摘要提取结果"></textarea>
      <div class="import-grid cer-inputs">
        <textarea v-model="importForm.claim" placeholder="Claim"></textarea>
        <textarea v-model="importForm.evidence" placeholder="Evidence"></textarea>
        <textarea v-model="importForm.reasoning" placeholder="Reasoning"></textarea>
      </div>
      <p v-if="importError" class="import-error">{{ importError }}</p>
      <div class="import-actions">
        <button class="ghost-button" @click="resetImportForm">清空</button>
        <button class="primary-button" :disabled="importLoading" @click="submitPaper">
          {{ importLoading ? '入库中' : '写入本地库' }}
        </button>
      </div>
    </section>

    <section class="content">
      <aside class="filters">
        <h2>主题</h2>
        <button
          v-for="[topic, count] in topicEntries"
          :key="topic"
          :class="{ active: selectedTopic === topic }"
          @click="selectTopic(topic)"
        >
          <span>{{ topic }}</span>
          <strong>{{ count }}</strong>
        </button>
      </aside>

      <section class="results">
        <div class="result-head">
          <h2>检索结果</h2>
          <span>{{ response?.total ?? 0 }} 篇</span>
        </div>
        <div v-if="error" class="state-card">{{ error }}</div>
        <div v-else-if="loading" class="state-card">正在加载论文数据库...</div>
        <div v-else-if="!papers.length" class="state-card">没有找到匹配论文。</div>

        <article v-for="paper in papers" v-else :key="paper.id" class="paper-card" @click="openPaper(paper.id)">
          <div class="paper-meta">
            <span>{{ paper.journal }}</span>
            <span>{{ paper.year }}</span>
            <span>{{ paper.evidenceType }}</span>
            <span :class="{ pass: paper.validation.passed }">{{ paper.validation.passed ? '校验通过' : '需复核' }}</span>
          </div>
          <h3>{{ paper.title }}</h3>
          <p class="authors">{{ paper.authorsText }}</p>
          <p>{{ paper.abstractPreview }}</p>
          <p class="paper-note">{{ paper.metadataDecision.reasons.join(' / ') }}</p>
          <div class="score-row">
            <span>Score {{ paper.retrievalScore.toFixed(2) }}</span>
            <span>V {{ paper.retrievalBreakdown.vector.toFixed(2) }}</span>
            <span>K {{ paper.retrievalBreakdown.keyword.toFixed(2) }}</span>
            <span>S {{ paper.retrievalBreakdown.structured.toFixed(2) }}</span>
            <span>G {{ paper.retrievalBreakdown.graph.toFixed(2) }}</span>
            <span>R {{ paper.retrievalBreakdown.rerank.toFixed(2) }}</span>
          </div>
          <div class="topic-list">
            <span v-for="topic in paper.topics" :key="topic">{{ topic }}</span>
          </div>
        </article>
      </section>
    </section>
  </main>
</template>

<style scoped>
.papers-page {
  min-height: 100vh;
  background: #f8fafc;
  color: #111827;
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
  background: rgba(255, 255, 255, 0.94);
  border-bottom: 1px solid #e5e7eb;
  backdrop-filter: blur(12px);
}

.ghost-button,
.primary-button {
  border: 1px solid #111827;
  border-radius: 6px;
  padding: 9px 14px;
  font-weight: 800;
  cursor: pointer;
}

.ghost-button {
  background: #fff;
  color: #111827;
}

.primary-button {
  background: #111827;
  color: #fff;
}

.hero,
.search-panel,
.preset-strip,
.query-strip,
.import-panel,
.content {
  width: min(1240px, 88vw);
  margin: 24px auto 0;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 32px;
  align-items: end;
  padding: 42px 0 14px;
}

.kicker {
  display: inline-block;
  margin-bottom: 10px;
  color: #dc2626;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 1.6px;
  text-transform: uppercase;
}

.hero h1 {
  margin: 0 0 14px;
  font-size: 48px;
}

.hero p {
  max-width: 720px;
  margin: 0;
  color: #4b5563;
  font-size: 16px;
  line-height: 1.8;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.metrics div,
.search-panel,
.query-strip,
.import-panel,
.filters,
.results {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.metrics div {
  padding: 14px;
}

.metrics strong {
  display: block;
  font-size: 24px;
}

.metrics span,
.authors,
.paper-meta {
  color: #6b7280;
  font-size: 13px;
}

.search-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  padding: 16px;
}

.search-panel input,
.import-grid input,
.import-panel textarea {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 12px 14px;
  font: inherit;
}

.query-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 14px;
}

.query-strip span,
.score-row span,
.topic-list span,
.preset-chip {
  padding: 5px 9px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 800;
}

.preset-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.preset-strip span {
  color: #6b7280;
  font-size: 12px;
  font-weight: 800;
}

.preset-chip {
  border: 1px solid #bfdbfe;
  cursor: pointer;
}

.import-panel {
  padding: 20px;
}

.import-panel h2 {
  margin: 0 0 14px;
  font-size: 20px;
}

.import-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.import-panel > textarea,
.cer-inputs {
  margin-top: 12px;
}

.import-panel textarea {
  min-height: 86px;
  resize: vertical;
}

.cer-inputs {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.import-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}

.import-error {
  color: #b91c1c;
  font-size: 13px;
}

.content {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
  padding-bottom: 60px;
}

.filters,
.results {
  padding: 20px;
}

.filters h2,
.result-head h2 {
  margin: 0;
  font-size: 20px;
}

.filters button {
  display: flex;
  justify-content: space-between;
  width: 100%;
  margin-top: 10px;
  padding: 11px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}

.filters button.active {
  border-color: #dc2626;
  background: #fff7ed;
}

.result-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 14px;
}

.paper-card {
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
}

.paper-card + .paper-card {
  margin-top: 12px;
}

.paper-card:hover {
  border-color: #dc2626;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}

.paper-meta,
.score-row,
.topic-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.paper-meta {
  margin-bottom: 10px;
  font-weight: 800;
}

.paper-meta .pass {
  color: #166534;
}

.paper-card h3 {
  margin: 0 0 8px;
  font-size: 20px;
}

.paper-card p {
  margin: 0 0 12px;
  color: #4b5563;
  font-size: 14px;
  line-height: 1.7;
}

.paper-note {
  color: #64748b !important;
  font-size: 12px !important;
}

.topic-list span {
  background: #f3f4f6;
  color: #111827;
}

.state-card {
  padding: 24px;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
  color: #6b7280;
  text-align: center;
}

@media (max-width: 900px) {
  .hero,
  .content,
  .search-panel,
  .preset-strip,
  .import-grid,
  .cer-inputs {
    grid-template-columns: 1fr;
  }
}
</style>
