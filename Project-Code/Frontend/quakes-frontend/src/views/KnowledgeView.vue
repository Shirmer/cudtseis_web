<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiUrl } from '../config/api'

type KnowledgeInit = {
  status: string
  backend: string
  collection: string
  vectorSize: number
  documents: number
  units: number
  indexVersion: string
  message: string
  warning?: string
  generatedAt: string
}

type DocumentIngest = {
  documentId: string
  paperId: string
  title: string
  status: string
  parser: string
  pages: number
  units: number
  fileSha256: string
  vectorStore: Record<string, unknown>
  embeddingBackend: string
  message: string
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
  citation: Record<string, unknown>
  metadata: Record<string, unknown>
}

type KnowledgeSearch = {
  query: string
  topK: number
  backend: string
  collection: string
  warning?: string
  embeddingBackend: string
  diagnostics: Record<string, unknown>
  results: KnowledgeHit[]
  storeStats: {
    documents: number
    units: number
  }
}

type GeoRagAnswer = {
  question: string
  answer: string
  retrievalMode: string
  mode: string
  evidencePack: {
    confidence?: string
    evidence?: Array<{
      id: string
      title: string
      text: string
      page?: number | null
      score?: number
    }>
    limitations?: string[]
  }
  retrievedContexts: Array<{
    id: string
    title: string
    content: string
    score: number
    metadata?: Record<string, unknown>
  }>
  suggestedQuestions: string[]
  diagnostics: Record<string, unknown>
}

const router = useRouter()

const initLoading = ref(false)
const ingestLoading = ref(false)
const searchLoading = ref(false)
const answerLoading = ref(false)
const error = ref('')

const initState = ref<KnowledgeInit | null>(null)
const ingestResult = ref<DocumentIngest | null>(null)
const searchResult = ref<KnowledgeSearch | null>(null)
const answerResult = ref<GeoRagAnswer | null>(null)

const ingestForm = ref({
  filePath: '',
  title: '',
  authors: '',
  year: new Date().getFullYear(),
  doi: '',
  sourceUrl: '',
  force: true
})

const searchForm = ref({
  query: 'active fault rupture tectonic setting',
  topK: 6,
  paperId: '',
  topics: ''
})

const questionForm = ref({
  question: '这些文献中关于断层破裂、构造背景和地震危险性的证据是什么？',
  paperId: '',
  topK: 6
})

const allowedDocumentPattern = /\.(pdf|txt|md)$/i

const storeStats = computed(() => {
  if (searchResult.value?.storeStats) return searchResult.value.storeStats
  if (initState.value) return { documents: initState.value.documents, units: initState.value.units }
  return { documents: 0, units: 0 }
})

const evidenceItems = computed(() => answerResult.value?.evidencePack?.evidence ?? [])

const searchDiagnostics = computed(() => searchResult.value?.diagnostics ?? {})

const answerDiagnostics = computed(() => {
  const diagnostics = answerResult.value?.diagnostics ?? {}
  const retrieval = diagnostics.retrieval
  return typeof retrieval === 'object' && retrieval !== null ? retrieval as Record<string, unknown> : {}
})

const diagnosticList = computed(() => {
  const diagnostics = answerResult.value ? answerDiagnostics.value : searchDiagnostics.value
  const flags = Array.isArray(diagnostics.qualityFlags) ? diagnostics.qualityFlags : []
  return [
    ['策略', diagnostics.retrievalStrategy],
    ['候选', diagnostics.candidateCount],
    ['Dense', diagnostics.denseCandidateCount],
    ['Keyword', diagnostics.keywordCandidateCount],
    ['集中度', diagnostics.topDocumentShare],
    ['风险', flags.length ? flags.join('; ') : 'none']
  ].filter(([, value]) => value !== undefined && value !== null && value !== '')
})

const setError = (value: unknown, fallback: string) => {
  if (value instanceof Error) {
    if (/load failed|failed to fetch/i.test(value.message)) {
      error.value = '请求后端失败：请确认 python3 dev.py 仍在运行，并使用终端输出的前端地址打开页面。'
      return
    }
    error.value = value.message
  } else {
    error.value = fallback
  }
}

const readError = async (response: Response, fallback: string) => {
  const detail = await response.json().catch(() => null)
  if (detail?.detail) return String(detail.detail)
  return `${fallback} (${response.status})`
}

const initKnowledge = async () => {
  initLoading.value = true
  error.value = ''
  try {
    const response = await fetch(apiUrl('/knowledge/init'), { method: 'POST' })
    if (!response.ok) throw new Error(await readError(response, '初始化失败'))
    initState.value = await response.json() as KnowledgeInit
  } catch (err) {
    setError(err, '初始化失败')
  } finally {
    initLoading.value = false
  }
}

const ingestDocument = async () => {
  const filePath = ingestForm.value.filePath.trim()
  if (!filePath) {
    error.value = '请填写后端可访问的文献文件路径'
    return
  }
  if (!allowedDocumentPattern.test(filePath)) {
    error.value = '这里需要填写具体文献文件，例如 Project-Code/backend/.data/geo_rag_documents/2604.27126v1.pdf；不能只填文件夹。'
    return
  }
  ingestLoading.value = true
  error.value = ''
  try {
    const payload = {
      filePath,
      title: ingestForm.value.title.trim() || undefined,
      authors: ingestForm.value.authors
        .split(/[;,，；]/)
        .map((item) => item.trim())
        .filter(Boolean),
      year: ingestForm.value.year || undefined,
      doi: ingestForm.value.doi.trim() || undefined,
      sourceUrl: ingestForm.value.sourceUrl.trim() || undefined,
      force: ingestForm.value.force
    }
    const response = await fetch(apiUrl('/documents/ingest'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!response.ok) throw new Error(await readError(response, '导入失败'))
    ingestResult.value = await response.json() as DocumentIngest
    await initKnowledge()
  } catch (err) {
    setError(err, '导入失败')
  } finally {
    ingestLoading.value = false
  }
}

const searchKnowledge = async () => {
  if (!searchForm.value.query.trim()) {
    error.value = '请填写检索问题'
    return
  }
  searchLoading.value = true
  error.value = ''
  try {
    const payload = {
      query: searchForm.value.query.trim(),
      topK: Number(searchForm.value.topK) || 6,
      paperId: searchForm.value.paperId.trim() || undefined,
      topics: searchForm.value.topics
        .split(/[;,，；]/)
        .map((item) => item.trim())
        .filter(Boolean)
    }
    const response = await fetch(apiUrl('/knowledge/search'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!response.ok) throw new Error(await readError(response, '检索失败'))
    searchResult.value = await response.json() as KnowledgeSearch
  } catch (err) {
    setError(err, '检索失败')
  } finally {
    searchLoading.value = false
  }
}

const askKnowledge = async () => {
  if (!questionForm.value.question.trim()) {
    error.value = '请填写问答问题'
    return
  }
  answerLoading.value = true
  error.value = ''
  try {
    const response = await fetch(apiUrl('/rag/papers/query'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: questionForm.value.question.trim(),
        paperId: questionForm.value.paperId.trim() || undefined,
        topK: Number(questionForm.value.topK) || 6
      })
    })
    if (!response.ok) throw new Error(await readError(response, '问答失败'))
    answerResult.value = await response.json() as GeoRagAnswer
  } catch (err) {
    setError(err, '问答失败')
  } finally {
    answerLoading.value = false
  }
}

const fillFromIngest = () => {
  if (!ingestResult.value) return
  searchForm.value.paperId = ingestResult.value.paperId
  questionForm.value.paperId = ingestResult.value.paperId
}

onMounted(() => {
  void initKnowledge()
})
</script>

<template>
  <main class="knowledge-page">
    <header class="topbar">
      <button class="ghost-button" @click="router.push('/')">返回首页</button>
      <strong>CDUT SEISLAB · GEO KNOWLEDGE</strong>
      <button class="ghost-button" @click="router.push('/papers')">论文库</button>
    </header>

    <section class="summary-band">
      <div>
        <span class="eyebrow">MVP Knowledge Base</span>
        <h1>地质文献知识库</h1>
      </div>
      <div class="metric-row">
        <div>
          <strong>{{ initState?.backend ?? '-' }}</strong>
          <span>向量后端</span>
        </div>
        <div>
          <strong>{{ storeStats.documents }}</strong>
          <span>文献</span>
        </div>
        <div>
          <strong>{{ storeStats.units }}</strong>
          <span>知识单元</span>
        </div>
        <div>
          <strong>{{ initState?.indexVersion ?? '-' }}</strong>
          <span>索引版本</span>
        </div>
      </div>
    </section>

    <section v-if="error" class="notice error">{{ error }}</section>
    <section v-if="initState?.warning" class="notice warning">{{ initState.warning }}</section>

    <section class="workspace-grid">
      <section class="panel ingest-panel">
        <div class="panel-heading">
          <div>
            <span>01</span>
            <h2>文献入库</h2>
          </div>
          <button class="secondary-button" :disabled="initLoading" @click="initKnowledge">
            {{ initLoading ? '初始化中' : '初始化' }}
          </button>
        </div>

        <label>
          <span>文件路径</span>
          <input v-model="ingestForm.filePath" placeholder="Project-Code/backend/.data/geo_rag_documents/example.pdf" />
          <small>填写具体 PDF/TXT/MD 文件路径，不是文件夹路径。</small>
        </label>

        <div class="form-grid">
          <label>
            <span>标题</span>
            <input v-model="ingestForm.title" placeholder="论文标题" />
          </label>
          <label>
            <span>作者</span>
            <input v-model="ingestForm.authors" placeholder="Author A; Author B" />
          </label>
          <label>
            <span>年份</span>
            <input v-model.number="ingestForm.year" type="number" min="1500" max="2200" />
          </label>
          <label>
            <span>DOI</span>
            <input v-model="ingestForm.doi" placeholder="10.xxxx/example" />
          </label>
        </div>

        <label>
          <span>来源</span>
          <input v-model="ingestForm.sourceUrl" placeholder="https://..." />
        </label>

        <label class="checkbox-line">
          <input v-model="ingestForm.force" type="checkbox" />
          <span>重建已有文档</span>
        </label>

        <button class="primary-button" :disabled="ingestLoading" @click="ingestDocument">
          {{ ingestLoading ? '导入中' : '导入并索引' }}
        </button>

        <div v-if="ingestResult" class="result-strip">
          <div><strong>{{ ingestResult.status }}</strong><span>{{ ingestResult.parser }}</span></div>
          <div><strong>{{ ingestResult.pages }}</strong><span>页</span></div>
          <div><strong>{{ ingestResult.units }}</strong><span>单元</span></div>
          <button class="tiny-button" @click="fillFromIngest">使用该论文</button>
        </div>
      </section>

      <section class="panel">
        <div class="panel-heading">
          <div>
            <span>02</span>
            <h2>知识检索</h2>
          </div>
        </div>

        <label>
          <span>检索问题</span>
          <textarea v-model="searchForm.query" rows="4"></textarea>
        </label>

        <div class="form-grid compact">
          <label>
            <span>Top K</span>
            <input v-model.number="searchForm.topK" type="number" min="1" max="30" />
          </label>
          <label>
            <span>Paper ID</span>
            <input v-model="searchForm.paperId" placeholder="可选" />
          </label>
          <label>
            <span>Topics</span>
            <input v-model="searchForm.topics" placeholder="fault; rupture" />
          </label>
        </div>

        <button class="primary-button" :disabled="searchLoading" @click="searchKnowledge">
          {{ searchLoading ? '检索中' : '检索知识单元' }}
        </button>

        <div v-if="searchResult" class="diagnostics">
          <span>{{ searchResult.backend }}</span>
          <span>{{ searchResult.embeddingBackend }}</span>
          <span>{{ searchResult.results.length }} hits</span>
        </div>

        <div v-if="searchResult" class="quality-card">
          <strong>检索质量诊断</strong>
          <dl>
            <template v-for="([label, value], index) in diagnosticList" :key="`${label}-${index}`">
              <dt>{{ label }}</dt>
              <dd>{{ value }}</dd>
            </template>
          </dl>
        </div>
      </section>
    </section>

    <section class="qa-layout">
      <section class="panel qa-panel">
        <div class="panel-heading">
          <div>
            <span>03</span>
            <h2>文献问答</h2>
          </div>
        </div>

        <label>
          <span>问题</span>
          <textarea v-model="questionForm.question" rows="4"></textarea>
        </label>

        <div class="form-grid compact">
          <label>
            <span>Paper ID</span>
            <input v-model="questionForm.paperId" placeholder="可选" />
          </label>
          <label>
            <span>Top K</span>
            <input v-model.number="questionForm.topK" type="number" min="1" max="20" />
          </label>
        </div>

        <button class="primary-button" :disabled="answerLoading" @click="askKnowledge">
          {{ answerLoading ? '生成中' : '生成证据回答' }}
        </button>
      </section>

      <section class="answer-surface">
        <div v-if="answerResult" class="answer-block">
          <div class="answer-meta">
            <span>{{ answerResult.retrievalMode }}</span>
            <span>{{ answerResult.evidencePack?.confidence ?? 'unknown' }}</span>
          </div>
          <p>{{ answerResult.answer }}</p>
          <div class="quality-card compact-card">
            <strong>回答证据诊断</strong>
            <dl>
              <template v-for="([label, value], index) in diagnosticList" :key="`${label}-${index}`">
                <dt>{{ label }}</dt>
                <dd>{{ value }}</dd>
              </template>
            </dl>
          </div>
        </div>
        <div v-else class="empty-state">等待文献问答结果</div>
      </section>
    </section>

    <section class="results-grid">
      <section class="results-column">
        <h2>检索结果</h2>
        <article v-for="hit in searchResult?.results ?? []" :key="hit.unitId" class="hit-item">
          <div class="hit-head">
            <strong>{{ hit.title || hit.paperId }}</strong>
            <span>{{ hit.score.toFixed(3) }}</span>
          </div>
          <p>{{ hit.text }}</p>
          <footer>
            <span>{{ hit.contentType }}</span>
            <span v-if="hit.page">p.{{ hit.page }}</span>
            <span>{{ hit.paperId }}</span>
          </footer>
        </article>
        <div v-if="searchResult && searchResult.results.length === 0" class="empty-list">未检索到知识单元</div>
      </section>

      <section class="results-column">
        <h2>证据包</h2>
        <article v-for="item in evidenceItems" :key="item.id" class="hit-item evidence">
          <div class="hit-head">
            <strong>{{ item.id }} · {{ item.title }}</strong>
            <span v-if="typeof item.score === 'number'">{{ item.score.toFixed(3) }}</span>
          </div>
          <p>{{ item.text }}</p>
          <footer>
            <span v-if="item.page">p.{{ item.page }}</span>
          </footer>
        </article>
        <div v-if="answerResult && evidenceItems.length === 0" class="empty-list">暂无证据</div>
      </section>
    </section>
  </main>
</template>

<style scoped>
.knowledge-page {
  min-height: 100vh;
  background: #f5f6f8;
  color: #20242c;
}

.topbar {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  background: #ffffff;
  border-bottom: 1px solid #e6e8ec;
}

.topbar strong {
  font-size: 14px;
  letter-spacing: 0;
}

.summary-band {
  display: flex;
  justify-content: space-between;
  gap: 32px;
  align-items: end;
  padding: 32px;
  background: #ffffff;
  border-bottom: 1px solid #e6e8ec;
}

.eyebrow {
  display: block;
  color: #667085;
  font-size: 13px;
  margin-bottom: 8px;
}

h1,
h2 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  font-size: 30px;
  line-height: 1.2;
}

h2 {
  font-size: 16px;
}

.metric-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(112px, 1fr));
  gap: 12px;
  min-width: 520px;
}

.metric-row div,
.result-strip div {
  background: #f5f6f8;
  border: 1px solid #e6e8ec;
  border-radius: 8px;
  padding: 12px;
}

.metric-row strong,
.result-strip strong {
  display: block;
  font-size: 18px;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.metric-row span,
.result-strip span {
  display: block;
  color: #667085;
  font-size: 12px;
  margin-top: 6px;
}

.notice {
  margin: 16px 32px 0;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 13px;
}

.notice.error {
  background: #fff1f0;
  border: 1px solid #ffccc7;
  color: #a8071a;
}

.notice.warning {
  background: #fffbe6;
  border: 1px solid #ffe58f;
  color: #7a4f00;
}

.workspace-grid,
.qa-layout,
.results-grid {
  display: grid;
  gap: 16px;
  padding: 16px 32px 0;
}

.workspace-grid {
  grid-template-columns: minmax(360px, 1.1fr) minmax(360px, 1fr);
}

.qa-layout {
  grid-template-columns: minmax(360px, 0.9fr) minmax(420px, 1.2fr);
}

.results-grid {
  grid-template-columns: 1fr 1fr;
  padding-bottom: 32px;
}

.panel,
.answer-surface,
.results-column {
  background: #ffffff;
  border: 1px solid #e6e8ec;
  border-radius: 8px;
  padding: 20px;
}

.panel-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 18px;
}

.panel-heading span {
  display: block;
  color: #667085;
  font-size: 12px;
  margin-bottom: 4px;
}

label {
  display: grid;
  gap: 7px;
  margin-bottom: 14px;
}

label span {
  color: #4b5563;
  font-size: 13px;
}

label small {
  color: #667085;
  font-size: 12px;
}

input,
textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  padding: 10px 12px;
  font: inherit;
  font-size: 14px;
  background: #ffffff;
  color: #20242c;
}

textarea {
  resize: vertical;
  min-height: 92px;
}

input:focus,
textarea:focus {
  outline: none;
  border-color: #3366cc;
  box-shadow: 0 0 0 3px rgba(51, 102, 204, 0.12);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-grid.compact {
  grid-template-columns: 120px 1fr 1fr;
}

.checkbox-line {
  display: inline-flex;
  grid-template-columns: none;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.checkbox-line input {
  width: 16px;
  height: 16px;
}

button {
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font: inherit;
  font-weight: 600;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.primary-button,
.secondary-button,
.ghost-button,
.tiny-button {
  min-height: 38px;
  padding: 0 14px;
}

.primary-button {
  background: #254f9f;
  color: #ffffff;
}

.primary-button:hover:not(:disabled) {
  background: #1f4286;
}

.secondary-button {
  background: #eef2ff;
  color: #254f9f;
}

.ghost-button,
.tiny-button {
  background: #ffffff;
  color: #344054;
  border: 1px solid #d0d5dd;
}

.tiny-button {
  min-height: 34px;
  align-self: end;
}

.result-strip {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(3, minmax(80px, 1fr)) auto;
  gap: 10px;
}

.diagnostics,
.answer-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.diagnostics span,
.answer-meta span {
  background: #f2f4f7;
  color: #344054;
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 12px;
}

.quality-card {
  margin-top: 14px;
  border: 1px solid #e6e8ec;
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
}

.quality-card strong {
  display: block;
  font-size: 13px;
  margin-bottom: 10px;
}

.quality-card dl {
  display: grid;
  grid-template-columns: 86px 1fr;
  gap: 7px 10px;
  margin: 0;
  font-size: 12px;
}

.quality-card dt {
  color: #667085;
}

.quality-card dd {
  margin: 0;
  color: #20242c;
  overflow-wrap: anywhere;
}

.compact-card {
  max-width: 720px;
}

.answer-surface {
  min-height: 260px;
}

.answer-block p {
  white-space: pre-wrap;
  line-height: 1.75;
  margin: 16px 0 0;
}

.empty-state,
.empty-list {
  color: #667085;
  background: #f8fafc;
  border: 1px dashed #d0d5dd;
  border-radius: 8px;
  padding: 24px;
  text-align: center;
}

.results-column h2 {
  margin-bottom: 14px;
}

.hit-item {
  border: 1px solid #e6e8ec;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 12px;
  background: #ffffff;
}

.hit-item.evidence {
  background: #fcfcfd;
}

.hit-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: start;
}

.hit-head strong {
  font-size: 14px;
  line-height: 1.35;
}

.hit-head span {
  color: #254f9f;
  font-size: 12px;
  font-weight: 700;
}

.hit-item p {
  color: #344054;
  font-size: 13px;
  line-height: 1.65;
  margin: 10px 0;
}

.hit-item footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #667085;
  font-size: 12px;
}

@media (max-width: 980px) {
  .summary-band,
  .topbar {
    padding-left: 18px;
    padding-right: 18px;
  }

  .summary-band {
    display: block;
  }

  .metric-row {
    min-width: 0;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-top: 20px;
  }

  .workspace-grid,
  .qa-layout,
  .results-grid {
    grid-template-columns: 1fr;
    padding-left: 18px;
    padding-right: 18px;
  }

  .form-grid,
  .form-grid.compact,
  .result-strip {
    grid-template-columns: 1fr;
  }
}
</style>
