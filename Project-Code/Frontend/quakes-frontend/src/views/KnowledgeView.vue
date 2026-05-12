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
  color: #11231f;
  background:
    linear-gradient(125deg, rgba(184, 101, 53, 0.1), transparent 30%),
    repeating-linear-gradient(168deg, rgba(21, 42, 38, 0.05) 0 1px, transparent 1px 34px),
    linear-gradient(180deg, #f3efe4 0%, #eef6f0 48%, #fbfbf4 100%);
  font-family: Lato, "PingFang SC", "Microsoft YaHei", sans-serif;
  overflow-x: hidden;
}

.knowledge-page::before {
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
.workspace,
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
.workspace,
.notice {
  width: min(1180px, 91vw);
  margin: 22px auto 0;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 420px);
  gap: 30px;
  align-items: end;
  padding: 24px 0 6px;
}

.eyebrow,
.panel-head span {
  display: inline-flex;
  margin-bottom: 10px;
  color: #24665d;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.eyebrow {
  padding: 5px 10px;
  border: 1px solid rgba(38, 76, 68, 0.15);
  border-radius: 999px;
  background: rgba(255, 255, 251, 0.58);
}

h1,
h2 {
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
  max-width: 780px;
  margin: 12px 0 0;
  color: #5e7069;
  line-height: 1.72;
  font-size: 15px;
}

.metrics,
.result-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.metrics div,
.result-summary div,
.panel {
  border: 1px solid rgba(38, 76, 68, 0.14);
  background: rgba(255, 255, 251, 0.78);
  box-shadow: 0 18px 46px rgba(24, 44, 41, 0.08);
  backdrop-filter: blur(16px);
}

.metrics div,
.result-summary div {
  min-height: 76px;
  padding: 15px;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.metrics strong,
.result-summary strong {
  display: block;
  color: #15342f;
  font-size: 24px;
  font-weight: 900;
  overflow-wrap: anywhere;
}

.metrics span,
.result-summary span {
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

.workspace {
  display: grid;
  grid-template-columns: minmax(360px, 0.9fr) minmax(420px, 1fr);
  gap: 18px;
  padding-bottom: 56px;
}

.panel {
  position: relative;
  overflow: hidden;
  padding: 22px;
  border-radius: 22px;
}

.panel::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, #1d8f82, #b86535);
  opacity: 0.72;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
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
  gap: 8px;
  margin-bottom: 14px;
}

label span {
  color: #52645e;
  font-size: 13px;
  font-weight: 900;
}

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

input:focus {
  outline: none;
  border-color: rgba(29, 143, 130, 0.55);
  box-shadow: 0 0 0 4px rgba(29, 143, 130, 0.1);
  background: #fffefa;
}

.file-picker {
  border: 1px dashed rgba(38, 76, 68, 0.28);
  border-radius: 18px;
  padding: 16px;
  background:
    linear-gradient(90deg, rgba(29, 143, 130, 0.07), transparent 42%),
    rgba(255, 255, 251, 0.58);
}

.file-picker input {
  padding: 0;
  border: none;
  background: transparent;
}

.file-picker strong {
  color: #142823;
  overflow-wrap: anywhere;
  font-weight: 900;
}

.file-picker small,
.storage-note {
  color: #64756f;
  font-size: 12px;
  line-height: 1.6;
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
  gap: 9px;
  color: #465f57;
  font-weight: 800;
}

.checkbox-line.lower {
  align-self: end;
  min-height: 44px;
}

.checkbox-line input {
  width: 17px;
  height: 17px;
  accent-color: #1d8f82;
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

.ghost-button,
.mode-switch button,
.source-switch button {
  border: 1px solid rgba(38, 76, 68, 0.16);
  background: rgba(255, 255, 251, 0.76);
  color: #24423d;
}

.ghost-button:hover:not(:disabled),
.mode-switch button:hover,
.source-switch button:hover {
  border-color: rgba(29, 143, 130, 0.36);
  box-shadow: 0 10px 22px rgba(22, 58, 53, 0.1);
}

.mode-switch button.active,
.source-switch button.active {
  border-color: rgba(29, 143, 130, 0.55);
  background: rgba(29, 143, 130, 0.12);
  color: #146b62;
  box-shadow: inset 0 0 0 1px rgba(29, 143, 130, 0.08);
}

.result-panel {
  min-height: 370px;
}

.result-summary {
  margin-bottom: 16px;
}

.result-summary .ghost-button {
  align-self: start;
}

.batch-result {
  display: grid;
  gap: 12px;
}

.batch-item {
  display: grid;
  gap: 7px;
  padding: 15px;
  border: 1px solid rgba(38, 76, 68, 0.13);
  border-radius: 16px;
  background:
    linear-gradient(90deg, rgba(29, 143, 130, 0.055), transparent 42%),
    rgba(255, 255, 251, 0.62);
}

.batch-item strong {
  color: #142823;
}

.batch-item span,
.batch-item small {
  color: #64756f;
  font-size: 12px;
}

.batch-item .batch-error {
  color: #8f2b22;
  font-weight: 800;
}

.empty-state {
  min-height: 240px;
  display: grid;
  place-items: center;
  border: 1px dashed rgba(38, 76, 68, 0.25);
  border-radius: 18px;
  color: #64756f;
  background: rgba(255, 255, 251, 0.4);
  text-align: center;
}

@media (max-width: 940px) {
  .hero,
  .workspace,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .metrics,
  .result-summary {
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

  .panel {
    padding: 16px;
  }

  .panel-head {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
