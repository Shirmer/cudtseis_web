<script setup lang="ts">
import { computed, h, onMounted, onUnmounted, ref } from 'vue'
import type { DataTableColumn } from 'naive-ui'
import {
  NAlert,
  NButton,
  NCard,
  NDataTable,
  NEmpty,
  NInput,
  NInputGroup,
  NModal,
  NPopconfirm,
  NProgress,
  NSelect,
  NSpace,
  NSpin,
  NStatistic,
  NTabPane,
  NTabs,
  NTag,
  NUpload,
} from 'naive-ui'
import * as rag from '../api/rag'

const loading = ref(false)
const kbList = ref<rag.KnowledgeBase[]>([])
const currentKb = ref('default')
const healthOk = ref(false)

const stats = ref<rag.KBStats | null>(null)

const documents = ref<rag.Document[]>([])
const docLoading = ref(false)

const taskPollTimer = ref<ReturnType<typeof setInterval> | null>(null)

const chatMessages = ref<{ role: string; content: string }[]>([])
const chatInput = ref('')
const chatMode = ref('hybrid')
const chatLoading = ref(false)

const showUploadModal = ref(false)
const uploadFiles = ref<File[]>([])

const showBatchUploadModal = ref(false)

const currentKbName = computed(() => {
  return kbList.value.find((kb) => kb.kb_id === currentKb.value)?.name || currentKb.value
})

const visibleTasks = computed(() => {
  return documents.value.filter((doc) => doc.status !== 'indexed' && doc.status !== 'failed')
})

const tableLocale = {
  emptyText: '暂无文档',
}

const indexedRate = computed(() => {
  if (!stats.value || stats.value.total_documents === 0) return 0
  return Math.round((stats.value.indexed / stats.value.total_documents) * 100)
})

async function init() {
  loading.value = true
  try {
    await checkHealth()
    await loadKBs()
    await loadStats()
    await loadDocuments()
  } finally {
    loading.value = false
  }
  startTaskPoll()
}

async function checkHealth() {
  try {
    const res = await fetch('/rag-api/health')
    const data = await res.json()
    healthOk.value = data.status === 'ok'
  } catch {
    healthOk.value = false
  }
}

async function loadKBs() {
  try {
    const data = await rag.listKnowledgeBases()
    kbList.value = data.items
  } catch (e: any) {
    console.error('加载知识库列表失败:', e)
  }
}

async function loadStats() {
  try {
    stats.value = await rag.getKBStats(currentKb.value)
  } catch {
    stats.value = null
  }
}

async function loadDocuments() {
  docLoading.value = true
  try {
    const data = await rag.listDocuments(currentKb.value)
    documents.value = data.items
  } catch (e: any) {
    console.error('加载文档列表失败:', e)
  } finally {
    docLoading.value = false
  }
}

function startTaskPoll() {
  stopTaskPoll()
  taskPollTimer.value = setInterval(loadTasks, 5000)
}

function stopTaskPoll() {
  if (taskPollTimer.value) {
    clearInterval(taskPollTimer.value)
    taskPollTimer.value = null
  }
}

async function loadTasks() {
  const running = documents.value.filter((d) =>
    ['queued', 'processing', 'cloud_running', 'cloud_waiting_parse', 'inserting', 'running'].includes(d.status)
  )
  if (running.length === 0) return
  try {
    const data = await rag.listDocuments(currentKb.value)
    documents.value = data.items
  } catch {}
}

async function switchKb(kbId: string) {
  currentKb.value = kbId
  chatMessages.value = []
  await loadStats()
  await loadDocuments()
}

async function handleDeleteDocument(docId: string) {
  try {
    await rag.deleteDocument(docId)
    await loadDocuments()
    await loadStats()
  } catch (e: any) {
    console.error('删除失败:', e)
  }
}

async function handleIngestDocument(docId: string) {
  try {
    await rag.ingestDocument(docId)
    await loadDocuments()
  } catch (e: any) {
    console.error('创建任务失败:', e)
  }
}

async function handleUpload() {
  if (uploadFiles.value.length === 0) return
  showUploadModal.value = false
  for (const file of uploadFiles.value) {
    try {
      await rag.uploadDocument(currentKb.value, file)
    } catch (e: any) {
      console.error(`上传失败 ${file.name}:`, e)
    }
  }
  uploadFiles.value = []
  await loadDocuments()
  await loadStats()
}

async function handleBatchUpload() {
  if (uploadFiles.value.length === 0) return
  showBatchUploadModal.value = false
  try {
    await rag.batchCloudIngest(currentKb.value, uploadFiles.value, {
      model_version: 'vlm',
      enable_formula: true,
      enable_table: true,
      language: 'ch',
    })
    uploadFiles.value = []
    await loadDocuments()
  } catch (e: any) {
    console.error('批量上传失败:', e)
  }
}

async function handleChat() {
  const q = chatInput.value.trim()
  if (!q || chatLoading.value) return
  chatInput.value = ''
  chatMessages.value.push({ role: 'user', content: q })
  chatLoading.value = true
  try {
    const res = await rag.chat(currentKb.value, {
      question: q,
      mode: chatMode.value,
      vlm_enhanced: true,
      enable_rerank: false,
    })
    chatMessages.value.push({ role: 'assistant', content: res.answer })
  } catch (e: any) {
    chatMessages.value.push({ role: 'assistant', content: '查询失败: ' + e.message })
  } finally {
    chatLoading.value = false
  }
}

const statusMap: Record<string, { type: 'success' | 'warning' | 'error' | 'info' | 'default'; text: string }> = {
  indexed: { type: 'success', text: '已入库' },
  uploaded: { type: 'info', text: '已上传' },
  waiting_parser: { type: 'warning', text: '等待解析' },
  failed: { type: 'error', text: '失败' },
  processing: { type: 'warning', text: '处理中' },
  inserting: { type: 'warning', text: '入库中' },
  cloud_parsing: { type: 'warning', text: '云端解析' },
  cloud_running: { type: 'warning', text: '云解析中' },
  cloud_waiting_parse: { type: 'warning', text: '排队中' },
  queued: { type: 'default', text: '排队' },
}

function statusTag(s: string) {
  const m = statusMap[s] || { type: 'default' as const, text: s }
  return h(NTag, { type: m.type, size: 'small', round: true }, { default: () => m.text })
}

const docColumns: DataTableColumn<rag.Document>[] = [
  { title: '文件名', key: 'filename', ellipsis: { tooltip: true }, minWidth: 280 },
  { title: '状态', key: 'status', render: (row) => statusTag(row.status), width: 110 },
  { title: '上传时间', key: 'created_at', width: 190 },
  {
    title: '操作',
    key: 'actions',
    width: 190,
    render(row) {
      const btns: any[] = []
      if (row.status === 'uploaded' || row.status === 'waiting_parser' || row.status === 'failed') {
        btns.push(h(NButton, {
          size: 'tiny',
          type: 'primary',
          ghost: true,
          onClick: () => handleIngestDocument(row.document_id),
        }, { default: () => '入库' }))
      }
      btns.push(h(NPopconfirm, {
        onPositiveClick: () => handleDeleteDocument(row.document_id),
      }, {
        default: () => '确定删除？',
        trigger: () => h(NButton, {
          size: 'tiny',
          type: 'error',
          ghost: true,
        }, { default: () => '删除' }),
      }))
      return h(NSpace, { justify: 'center' }, { default: () => btns })
    },
  },
]

onMounted(() => {
  init()
})

onUnmounted(() => {
  stopTaskPoll()
})
</script>

<template>
  <main class="rag-dashboard">
    <section class="rag-hero">
      <div class="brand-lockup">
        <img src="/cdut_logo.png" alt="CDUT Logo" />
        <div>
          <span>CDUT SEISLAB</span>
          <strong>RAG 工作台</strong>
        </div>
      </div>

      <div class="hero-copy">
        <span class="eyebrow">KNOWLEDGE RETRIEVAL</span>
        <h1>地震知识问答与文档入库</h1>
        <p>面向团队内部的文档解析、知识检索和证据问答工作流。</p>
      </div>

      <div class="hero-controls">
        <n-tag :type="healthOk ? 'success' : 'error'" size="small" round>
          {{ healthOk ? 'RAG 服务正常' : 'RAG 服务异常' }}
        </n-tag>
        <n-select
          v-model:value="currentKb"
          :options="kbList.map(k => ({ label: k.name, value: k.kb_id }))"
          class="kb-select"
          @update:value="switchKb"
        />
        <n-button tertiary circle :loading="loading" @click="init" title="刷新">↻</n-button>
      </div>
    </section>

    <n-spin :show="loading">
      <section class="overview-row" v-if="stats">
        <n-card class="metric-card" size="small" :bordered="false">
          <n-statistic title="当前知识库" :value="currentKbName" />
        </n-card>
        <n-card class="metric-card" size="small" :bordered="false">
          <n-statistic title="文档总数" :value="stats.total_documents" />
        </n-card>
        <n-card class="metric-card" size="small" :bordered="false">
          <n-statistic title="已入库" :value="stats.indexed" />
        </n-card>
        <n-card class="metric-card accent" size="small" :bordered="false">
          <n-statistic title="入库完成率" :value="indexedRate" suffix="%" />
        </n-card>
      </section>

      <section class="workspace-shell">
        <n-tabs type="segment" animated>
          <n-tab-pane name="documents" tab="文档管理">
            <div class="section-toolbar">
              <div>
                <span class="section-kicker">DOCUMENTS</span>
                <h2>文档入库</h2>
              </div>
              <div class="toolbar-actions">
                <n-button type="primary" @click="showUploadModal = true">上传 PDF</n-button>
                <n-button secondary @click="showBatchUploadModal = true">批量云解析</n-button>
                <n-button tertiary :loading="docLoading" @click="loadDocuments">刷新</n-button>
              </div>
            </div>

            <n-data-table
              :columns="docColumns"
              :data="documents"
              :loading="docLoading"
              :bordered="false"
              :single-line="false"
              :locale="tableLocale"
              size="small"
              class="document-table"
            />
          </n-tab-pane>

          <n-tab-pane name="chat" tab="知识问答">
            <div class="section-toolbar">
              <div>
                <span class="section-kicker">ASK</span>
                <h2>证据问答</h2>
              </div>
              <n-select
                v-model:value="chatMode"
                :options="[
                  { label: '混合 mix', value: 'mix' },
                  { label: '本地 local', value: 'local' },
                  { label: '全局 global', value: 'global' },
                  { label: '混合 hybrid', value: 'hybrid' },
                  { label: '朴素 naive', value: 'naive' },
                ]"
                class="mode-select"
              />
            </div>

            <div class="chat-panel">
              <div class="chat-messages">
                <div v-for="(msg, i) in chatMessages" :key="i" :class="['message-row', msg.role]">
                  <div class="msg-label">{{ msg.role === 'user' ? '你' : 'RAG' }}</div>
                  <div class="msg-content">{{ msg.content }}</div>
                </div>
                <n-empty
                  v-if="chatMessages.length === 0"
                  description="输入问题开始知识问答"
                  class="empty-state"
                />
                <div v-if="chatLoading" class="message-row assistant">
                  <div class="msg-label">RAG</div>
                  <div class="msg-content typing">思考中...</div>
                </div>
              </div>
              <div class="chat-input-area">
                <n-input-group>
                  <n-input
                    v-model:value="chatInput"
                    placeholder="输入问题..."
                    :disabled="chatLoading"
                    @keyup.enter="handleChat"
                  />
                  <n-button type="primary" :loading="chatLoading" :disabled="!chatInput.trim()" @click="handleChat">
                    发送
                  </n-button>
                </n-input-group>
              </div>
            </div>
          </n-tab-pane>

          <n-tab-pane name="tasks" tab="任务状态">
            <n-alert type="info" :bordered="false" class="task-alert">
              正在运行的任务每 5 秒自动刷新。
            </n-alert>
            <div class="task-list">
              <div v-for="doc in visibleTasks" :key="doc.document_id" class="task-item">
                <div class="task-header">
                  <span class="task-filename">{{ doc.filename }}</span>
                  <n-tag :type="statusMap[doc.status]?.type || 'default'" size="small" round>
                    {{ statusMap[doc.status]?.text || doc.status }}
                  </n-tag>
                </div>
                <n-progress
                  v-if="doc.status === 'processing' || doc.status === 'cloud_running'"
                  type="line"
                  :percentage="50"
                  :indicator-placement="'inside'"
                  status="info"
                  :height="8"
                />
                <n-progress
                  v-else-if="doc.status === 'queued' || doc.status === 'cloud_waiting_parse'"
                  type="line"
                  :percentage="25"
                  :indicator-placement="'inside'"
                  status="warning"
                  :height="8"
                />
                <n-progress
                  v-else-if="doc.status === 'indexed'"
                  type="line"
                  :percentage="100"
                  :indicator-placement="'inside'"
                  status="success"
                  :height="8"
                />
              </div>
            </div>
            <n-empty v-if="visibleTasks.length === 0" description="没有运行中的任务" class="empty-state" />
          </n-tab-pane>
        </n-tabs>
      </section>
    </n-spin>

    <n-modal v-model:show="showUploadModal" title="上传 PDF" preset="card" class="upload-modal">
      <n-upload
        :multiple="true"
        accept=".pdf"
        :default-upload="false"
        @change="({ fileList }) => uploadFiles = fileList.map(f => f.file!) as File[]"
      >
        <n-button>选择 PDF 文件</n-button>
      </n-upload>
      <div class="modal-actions">
        <n-button @click="showUploadModal = false">取消</n-button>
        <n-button type="primary" :disabled="uploadFiles.length === 0" @click="handleUpload">上传</n-button>
      </div>
    </n-modal>

    <n-modal v-model:show="showBatchUploadModal" title="批量上传 + MinerU 云解析" preset="card" class="upload-modal">
      <p class="modal-note">一次最多 50 个文件，上传后自动提交到 MinerU 云解析并入库。</p>
      <n-upload
        :multiple="true"
        accept=".pdf"
        :default-upload="false"
        @change="({ fileList }) => uploadFiles = fileList.map(f => f.file!) as File[]"
      >
        <n-button>选择 PDF 文件</n-button>
      </n-upload>
      <div class="modal-actions">
        <n-button @click="showBatchUploadModal = false">取消</n-button>
        <n-button type="primary" :disabled="uploadFiles.length === 0" @click="handleBatchUpload">提交云解析</n-button>
      </div>
    </n-modal>
  </main>
</template>

<style scoped>
.rag-dashboard {
  min-height: 100vh;
  padding: 28px;
  color: #111;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.74), #f7f7f5 360px),
    url('/snow_moutain.png') center top / cover no-repeat;
  box-sizing: border-box;
}

.rag-hero {
  min-height: 260px;
  display: grid;
  grid-template-columns: minmax(180px, 0.75fr) minmax(280px, 1.4fr) minmax(260px, 0.9fr);
  align-items: end;
  gap: 24px;
  max-width: 1280px;
  margin: 0 auto 22px;
  padding: 24px 0 30px;
  border-bottom: 1px solid rgba(17, 17, 17, 0.12);
}

.brand-lockup {
  display: flex;
  align-items: center;
  gap: 14px;
  align-self: start;
}

.brand-lockup img {
  width: 44px;
  height: 44px;
  object-fit: contain;
}

.brand-lockup span,
.section-kicker {
  display: block;
  color: #dc2626;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 1.6px;
}

.brand-lockup strong {
  display: block;
  margin-top: 3px;
  color: #111;
  font-size: 18px;
}

.hero-copy {
  max-width: 620px;
}

.eyebrow {
  display: inline-block;
  margin-bottom: 12px;
  color: #dc2626;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 2px;
}

.hero-copy h1 {
  margin: 0;
  color: #111;
  font-family: "Times New Roman", "Songti SC", "SimSun", serif;
  font-size: clamp(36px, 5vw, 64px);
  line-height: 1.06;
}

.hero-copy p {
  margin: 16px 0 0;
  max-width: 520px;
  color: #4b5563;
  font-size: 16px;
  line-height: 1.7;
}

.hero-controls {
  justify-self: end;
  width: min(100%, 360px);
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 16px;
  border: 1px solid rgba(17, 17, 17, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(12px);
}

.hero-controls .n-tag {
  grid-column: span 2;
  width: fit-content;
}

.kb-select,
.mode-select {
  min-width: 190px;
}

.overview-row {
  max-width: 1280px;
  margin: 0 auto 18px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.metric-card {
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #fff;
}

.metric-card.accent {
  border-color: rgba(220, 38, 38, 0.28);
  background: #fff5f5;
}

.workspace-shell {
  max-width: 1280px;
  margin: 0 auto;
  padding: 22px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 18px 45px rgba(17, 24, 39, 0.08);
}

.section-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin: 20px 0 18px;
}

.section-toolbar h2 {
  margin: 5px 0 0;
  font-size: 24px;
  line-height: 1.2;
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.document-table {
  border-radius: 8px;
  overflow: hidden;
}

.chat-panel {
  min-height: 560px;
  display: flex;
  flex-direction: column;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: #fbfbfa;
}

.chat-messages {
  flex: 1;
  min-height: 460px;
  overflow-y: auto;
  padding: 18px;
}

.message-row {
  max-width: 78%;
  margin-bottom: 16px;
}

.message-row.user {
  margin-left: auto;
}

.msg-label {
  margin-bottom: 5px;
  color: #6b7280;
  font-size: 12px;
  font-weight: 800;
}

.message-row.user .msg-label {
  text-align: right;
}

.msg-content {
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: #111;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
}

.message-row.user .msg-content {
  border-color: #111;
  background: #111;
  color: #fff;
}

.message-row.assistant .msg-content {
  border-left: 3px solid #dc2626;
}

.typing {
  color: #6b7280;
}

.chat-input-area {
  padding: 14px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}

.task-alert {
  margin: 18px 0;
}

.task-list {
  display: grid;
  gap: 10px;
}

.task-item {
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 9px;
}

.task-filename {
  min-width: 0;
  color: #111827;
  font-size: 14px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-state {
  margin: 54px auto;
}

.upload-modal {
  width: min(560px, calc(100vw - 32px));
}

.modal-note {
  margin: 0 0 16px;
  color: #4b5563;
  line-height: 1.7;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

:deep(.n-tabs .n-tabs-rail) {
  border-radius: 8px;
  background: #f3f4f6;
}

:deep(.n-tabs .n-tabs-tab.n-tabs-tab--active) {
  color: #111;
  font-weight: 800;
}

:deep(.n-button--primary-type) {
  --n-color: #111 !important;
  --n-color-hover: #dc2626 !important;
  --n-color-pressed: #991b1b !important;
  --n-border: 1px solid #111 !important;
  --n-border-hover: 1px solid #dc2626 !important;
  --n-border-pressed: 1px solid #991b1b !important;
}

@media (max-width: 980px) {
  .rag-dashboard {
    padding: 18px;
  }

  .rag-hero {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .hero-controls {
    justify-self: stretch;
    width: 100%;
  }

  .overview-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .overview-row {
    grid-template-columns: 1fr;
  }

  .workspace-shell {
    padding: 14px;
  }

  .section-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .toolbar-actions {
    justify-content: flex-start;
  }

  .message-row {
    max-width: 100%;
  }
}
</style>
