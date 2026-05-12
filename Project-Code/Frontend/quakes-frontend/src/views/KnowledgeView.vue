<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiUrl } from '../config/api'

type KnowledgeInit = {
  backend: string
  documents: number
  units: number
  indexVersion: string
  storageBackend?: string
  warning?: string
}

type DocumentIngest = {
  documentId: string
  paperId: string
  title: string
  status: string
  parser: string
  pages: number
  units: number
  multimodalUnits?: number
  storageUri?: string
  embeddingBackend: string
  message: string
}

type DocumentUpload = {
  filePath: string
  fileName: string
  storageUri: string
  fileSha256: string
  sizeBytes: number
  message: string
}

type DocumentBatchIngest = {
  total: number
  succeeded: number
  skipped: number
  failed: number
  items: Array<{
    filePath: string
    status: string
    title: string
    pages: number
    units: number
    multimodalUnits?: number
    storageUri?: string
    error: string
  }>
}

const router = useRouter()

const initState = ref<KnowledgeInit | null>(null)
const initLoading = ref(false)
const ingestLoading = ref(false)
const batchLoading = ref(false)
const error = ref('')
const mode = ref<'single' | 'batch'>('single')
const sourceMode = ref<'upload' | 'path'>('upload')
const ingestResult = ref<DocumentIngest | null>(null)
const batchResult = ref<DocumentBatchIngest | null>(null)
const selectedFile = ref<File | null>(null)

const singleForm = ref({
  filePath: '',
  title: '',
  authors: '',
  year: new Date().getFullYear(),
  doi: '',
  sourceUrl: '',
  force: true
})

const batchForm = ref({
  directoryPath: 'Project-Code/backend/.data/geo_rag_documents',
  recursive: false,
  force: true,
  limit: 50
})

const stats = computed(() => ({
  documents: initState.value?.documents ?? 0,
  units: initState.value?.units ?? 0,
  backend: initState.value?.backend ?? '-',
  storageBackend: initState.value?.storageBackend ?? '-'
}))

const batchItems = computed(() => (batchResult.value?.items ?? []).slice(0, 10))
const allowedDocumentPattern = /\.(pdf|txt|md)$/i
const selectedFileLabel = computed(() => selectedFile.value?.name ?? '选择 PDF/TXT/MD 文件')

const readError = async (response: Response, fallback: string) => {
  const detail = await response.json().catch(() => null)
  if (detail?.detail) return String(detail.detail)
  return `${fallback} (${response.status})`
}

const setError = (value: unknown, fallback: string) => {
  if (value instanceof Error) {
    if (/load failed|failed to fetch/i.test(value.message)) {
      error.value = '请求后端失败：请确认 python3 dev.py 正在运行。'
      return
    }
    error.value = value.message
  } else {
    error.value = fallback
  }
}

const initKnowledge = async () => {
  initLoading.value = true
  error.value = ''
  try {
    const response = await fetch(apiUrl('/knowledge/init'), { method: 'POST' })
    if (!response.ok) throw new Error(await readError(response, '刷新状态失败'))
    initState.value = await response.json() as KnowledgeInit
  } catch (err) {
    setError(err, '刷新状态失败')
  } finally {
    initLoading.value = false
  }
}

const onFileSelected = (event: Event) => {
  const target = event.target as HTMLInputElement
  selectedFile.value = target.files?.[0] ?? null
}

const uploadSelectedFile = async (file: File): Promise<DocumentUpload> => {
  const response = await fetch(apiUrl(`/documents/upload?filename=${encodeURIComponent(file.name)}`), {
    method: 'POST',
    headers: { 'Content-Type': file.type || 'application/octet-stream' },
    body: file
  })
  if (!response.ok) throw new Error(await readError(response, '上传失败'))
  return await response.json() as DocumentUpload
}

const ingestSingle = async () => {
  let filePath = singleForm.value.filePath.trim()
  if (sourceMode.value === 'upload') {
    if (!selectedFile.value) {
      error.value = '请选择要上传到服务器的 PDF/TXT/MD 文件'
      return
    }
    if (!allowedDocumentPattern.test(selectedFile.value.name)) {
      error.value = '只支持 PDF、TXT 或 Markdown 文献。'
      return
    }
  } else {
    if (!filePath) {
      error.value = '请填写服务器上的 PDF/TXT/MD 文件路径'
      return
    }
    if (!allowedDocumentPattern.test(filePath)) {
      error.value = '单篇导入要填写具体文件，不是文件夹；文件夹请用批量导入。'
      return
    }
  }

  ingestLoading.value = true
  error.value = ''
  try {
    if (sourceMode.value === 'upload' && selectedFile.value) {
      const upload = await uploadSelectedFile(selectedFile.value)
      filePath = upload.filePath
      if (!singleForm.value.title.trim()) {
        singleForm.value.title = selectedFile.value.name.replace(/\.(pdf|txt|md)$/i, '')
      }
    }
    const payload = {
      filePath,
      title: singleForm.value.title.trim() || undefined,
      authors: singleForm.value.authors
        .split(/[;,，；]/)
        .map((item) => item.trim())
        .filter(Boolean),
      year: singleForm.value.year || undefined,
      doi: singleForm.value.doi.trim() || undefined,
      sourceUrl: singleForm.value.sourceUrl.trim() || undefined,
      force: singleForm.value.force
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

const ingestBatch = async () => {
  const directoryPath = batchForm.value.directoryPath.trim()
  if (!directoryPath) {
    error.value = '请填写文献文件夹路径'
    return
  }

  batchLoading.value = true
  error.value = ''
  try {
    const response = await fetch(apiUrl('/documents/batch-ingest'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        directoryPath,
        recursive: batchForm.value.recursive,
        force: batchForm.value.force,
        limit: Number(batchForm.value.limit) || 50,
        extensions: ['.pdf', '.txt', '.md']
      })
    })
    if (!response.ok) throw new Error(await readError(response, '批量导入失败'))
    batchResult.value = await response.json() as DocumentBatchIngest
    await initKnowledge()
  } catch (err) {
    setError(err, '批量导入失败')
  } finally {
    batchLoading.value = false
  }
}

onMounted(() => {
  void initKnowledge()
})
</script>

<template>
  <main class="knowledge-page">
    <header class="topbar">
      <button class="ghost-button" @click="router.push('/')">返回首页</button>
      <strong>文献知识库</strong>
      <button class="ghost-button" @click="router.push('/papers')">检索论文</button>
    </header>

    <section class="hero">
      <div>
        <span class="eyebrow">Knowledge Ingest</span>
        <h1>导入文献</h1>
        <p>把本地 PDF、TXT 或 Markdown 文献加入知识库。系统会按“每篇文献独立处理”的规则解析、切块、向量化并写入数据库。</p>
      </div>
      <div class="metrics">
        <div><strong>{{ stats.documents }}</strong><span>文献</span></div>
        <div><strong>{{ stats.units }}</strong><span>知识单元</span></div>
        <div><strong>{{ stats.backend }}</strong><span>向量库</span></div>
        <div><strong>{{ stats.storageBackend }}</strong><span>原文存储</span></div>
      </div>
    </section>

    <section v-if="error" class="notice error">{{ error }}</section>
    <section v-if="initState?.warning" class="notice warning">{{ initState.warning }}</section>

    <section class="workspace">
      <section class="panel">
        <div class="panel-head">
          <div>
            <span>Import</span>
            <h2>选择导入方式</h2>
          </div>
          <button class="ghost-button" :disabled="initLoading" @click="initKnowledge">
            {{ initLoading ? '刷新中' : '刷新状态' }}
          </button>
        </div>

        <div class="mode-switch">
          <button :class="{ active: mode === 'single' }" @click="mode = 'single'">单篇导入</button>
          <button :class="{ active: mode === 'batch' }" @click="mode = 'batch'">批量导入</button>
        </div>

        <template v-if="mode === 'single'">
          <div class="source-switch">
            <button :class="{ active: sourceMode === 'upload' }" @click="sourceMode = 'upload'">上传到服务器</button>
            <button :class="{ active: sourceMode === 'path' }" @click="sourceMode = 'path'">服务器已有文件</button>
          </div>

          <label v-if="sourceMode === 'upload'" class="file-picker">
            <span>文献文件</span>
            <input type="file" accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown" @change="onFileSelected" />
            <strong>{{ selectedFileLabel }}</strong>
            <small>上传后会先保存到后端配置的文献存储目录，再进行解析和索引。</small>
          </label>

          <label v-else>
            <span>服务器文件路径</span>
            <input v-model="singleForm.filePath" placeholder="/opt/cudtseis_web/storage/geo_rag_documents/example.pdf" />
          </label>

          <div class="form-grid">
            <label>
              <span>标题</span>
              <input v-model="singleForm.title" placeholder="可选，不填则自动使用文件名" />
            </label>
            <label>
              <span>作者</span>
              <input v-model="singleForm.authors" placeholder="可选，用分号分隔" />
            </label>
            <label>
              <span>年份</span>
              <input v-model.number="singleForm.year" type="number" min="1500" max="2200" />
            </label>
            <label>
              <span>DOI</span>
              <input v-model="singleForm.doi" placeholder="可选" />
            </label>
          </div>

          <label>
            <span>来源链接</span>
            <input v-model="singleForm.sourceUrl" placeholder="可选" />
          </label>

          <label class="checkbox-line">
            <input v-model="singleForm.force" type="checkbox" />
            <span>如果已存在，重新解析并覆盖旧索引</span>
          </label>

          <button class="primary-button" :disabled="ingestLoading" @click="ingestSingle">
            {{ ingestLoading ? '导入中' : '导入并索引' }}
          </button>
        </template>

        <template v-else>
          <label>
            <span>文件夹路径</span>
            <input v-model="batchForm.directoryPath" placeholder="Project-Code/backend/.data/geo_rag_documents" />
          </label>

          <div class="form-grid">
            <label>
              <span>最多导入</span>
              <input v-model.number="batchForm.limit" type="number" min="1" max="1000" />
            </label>
            <label class="checkbox-line lower">
              <input v-model="batchForm.recursive" type="checkbox" />
              <span>包含子文件夹</span>
            </label>
            <label class="checkbox-line lower">
              <input v-model="batchForm.force" type="checkbox" />
              <span>重新解析已有文献</span>
            </label>
          </div>

          <button class="primary-button" :disabled="batchLoading" @click="ingestBatch">
            {{ batchLoading ? '批量导入中' : '批量导入并索引' }}
          </button>
        </template>
      </section>

      <section class="panel result-panel">
        <div class="panel-head">
          <div>
            <span>Result</span>
            <h2>导入结果</h2>
          </div>
        </div>

        <div v-if="mode === 'single' && ingestResult" class="result-summary">
          <div><strong>{{ ingestResult.status }}</strong><span>{{ ingestResult.parser }}</span></div>
          <div><strong>{{ ingestResult.pages }}</strong><span>页</span></div>
          <div><strong>{{ ingestResult.units }}</strong><span>知识单元</span></div>
          <div><strong>{{ ingestResult.multimodalUnits ?? 0 }}</strong><span>图表/公式单元</span></div>
          <button class="ghost-button" @click="router.push('/papers')">去检索</button>
          <p v-if="ingestResult.storageUri" class="storage-note">{{ ingestResult.storageUri }}</p>
        </div>

        <div v-else-if="mode === 'batch' && batchResult" class="batch-result">
          <div class="result-summary">
            <div><strong>{{ batchResult.succeeded }}</strong><span>成功</span></div>
            <div><strong>{{ batchResult.failed }}</strong><span>失败</span></div>
            <div><strong>{{ batchResult.skipped }}</strong><span>跳过</span></div>
          </div>
          <article v-for="item in batchItems" :key="item.filePath" class="batch-item">
            <strong>{{ item.title || item.filePath }}</strong>
            <span>{{ item.status }} · {{ item.pages }} 页 · {{ item.units }} 单元 · {{ item.multimodalUnits ?? 0 }} 多模态</span>
            <small v-if="item.storageUri" class="storage-note">{{ item.storageUri }}</small>
            <small v-if="item.error" class="batch-error">{{ item.error }}</small>
          </article>
          <button class="ghost-button" @click="router.push('/papers')">去检索</button>
        </div>

        <div v-else class="empty-state">导入完成后会在这里显示结果。</div>
      </section>
    </section>
  </main>
</template>

<style scoped>
.knowledge-page {
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
.workspace,
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

.eyebrow,
.panel-head span {
  display: block;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 13px;
}

h1,
h2 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  font-size: 42px;
  line-height: 1.18;
}

h2 {
  font-size: 18px;
}

.hero p {
  max-width: 760px;
  margin: 14px 0 0;
  color: #52627a;
  line-height: 1.8;
}

.metrics,
.result-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.metrics div,
.result-summary div,
.panel {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.metrics div,
.result-summary div {
  padding: 14px;
}

.metrics strong,
.result-summary strong {
  display: block;
  font-size: 22px;
  overflow-wrap: anywhere;
}

.metrics span,
.result-summary span {
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

.workspace {
  display: grid;
  grid-template-columns: minmax(360px, 0.9fr) minmax(420px, 1fr);
  gap: 16px;
  padding-bottom: 50px;
}

.panel {
  padding: 20px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 18px;
}

.mode-switch,
.source-switch {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.source-switch {
  margin-bottom: 14px;
}

label {
  display: grid;
  gap: 7px;
  margin-bottom: 14px;
}

label span {
  color: #475569;
  font-size: 13px;
}

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

input:focus {
  outline: none;
  border-color: #2f5da8;
  box-shadow: 0 0 0 3px rgba(47, 93, 168, 0.12);
}

.file-picker {
  border: 1px dashed #b7c8df;
  border-radius: 8px;
  padding: 14px;
  background: #fbfdff;
}

.file-picker input {
  padding: 0;
  border: none;
  background: transparent;
}

.file-picker strong {
  color: #172033;
  overflow-wrap: anywhere;
}

.file-picker small,
.storage-note {
  color: #64748b;
  font-size: 12px;
  overflow-wrap: anywhere;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.checkbox-line {
  display: inline-flex;
  grid-template-columns: none;
  align-items: center;
  gap: 8px;
}

.checkbox-line.lower {
  align-self: end;
  min-height: 42px;
}

.checkbox-line input {
  width: 16px;
  height: 16px;
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

.ghost-button,
.mode-switch button,
.source-switch button {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
}

.mode-switch button.active,
.source-switch button.active {
  border-color: #2f5da8;
  background: #eef4ff;
  color: #1f4f99;
}

.result-panel {
  min-height: 360px;
}

.result-summary {
  margin-bottom: 16px;
}

.batch-result {
  display: grid;
  gap: 12px;
}

.batch-item {
  display: grid;
  gap: 6px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.batch-item span,
.batch-item small {
  color: #64748b;
  font-size: 12px;
}

.batch-item .batch-error {
  color: #a8071a;
}

.empty-state {
  min-height: 220px;
  display: grid;
  place-items: center;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  color: #64748b;
}

@media (max-width: 900px) {
  .hero,
  .workspace,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .metrics,
  .result-summary {
    grid-template-columns: 1fr;
  }
}
</style>
