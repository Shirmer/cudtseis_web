<script setup lang="ts">
import { ref, onMounted, onUnmounted, h } from 'vue'
import type { DataTableColumn } from 'naive-ui'
import {
  NButton, NCard, NSelect, NStatistic, NDataTable, NTag,
  NInput, NTabPane, NTabs, NSpin, NEmpty, NAlert,
  NProgress, NModal, NUpload, NSpace,
  NDivider, NInputGroup, NPopconfirm
} from 'naive-ui'
import * as rag from '../api/rag'

const loading = ref(false)
const kbList = ref<rag.KnowledgeBase[]>([])
const currentKb = ref('default')
const healthOk = ref(false)

const stats = ref<rag.KBStats | null>(null)

const documents = ref<rag.Document[]>([])
const docLoading = ref(false)

const tasks = ref<rag.Task[]>([])
const taskPollTimer = ref<ReturnType<typeof setInterval> | null>(null)

const chatMessages = ref<{ role: string; content: string }[]>([])
const chatInput = ref('')
const chatMode = ref('hybrid')
const chatLoading = ref(false)

const showUploadModal = ref(false)
const uploadFiles = ref<File[]>([])

const showBatchUploadModal = ref(false)

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
  const running = documents.value.filter(d =>
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
    console.log('文档已删除')
    await loadDocuments()
    await loadStats()
  } catch (e: any) {
    console.error('删除失败:', e)
  }
}

async function handleIngestDocument(docId: string) {
  try {
    const result = await rag.ingestDocument(docId)
    console.log('已创建入库任务:', result.task_id.slice(0, 8))
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
      console.log(`上传成功: ${file.name}`)
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
    const result = await rag.batchCloudIngest(currentKb.value, uploadFiles.value, {
      model_version: 'vlm',
      enable_formula: true,
      enable_table: true,
      language: 'ch',
    })
    console.log(`已提交 ${result.items.length} 个文件到 MinerU 云解析`)
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
    chatMessages.value.push({ role: 'assistant', content: '❌ 查询失败: ' + e.message })
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
  return h(NTag, { type: m.type, size: 'small' }, { default: () => m.text })
}

const docColumns: DataTableColumn<rag.Document>[] = [
  { title: '文件名', key: 'filename', ellipsis: { tooltip: true }, width: 300 },
  { title: '状态', key: 'status', render: (row) => statusTag(row.status), width: 100 },
  { title: '上传时间', key: 'created_at', width: 180 },
  {
    title: '操作', width: 180,
    render(row) {
      const btns: any[] = []
      if (row.status === 'uploaded' || row.status === 'waiting_parser' || row.status === 'failed') {
        btns.push(h(NButton, {
          size: 'tiny', type: 'primary', ghost: true,
          onClick: () => handleIngestDocument(row.document_id),
        }, { default: () => '入库' }))
      }
      btns.push(h(NPopconfirm, {
        onPositiveClick: () => handleDeleteDocument(row.document_id),
      }, {
        default: () => '确定删除？',
        trigger: () => h(NButton, {
          size: 'tiny', type: 'error', ghost: true,
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
  <div class="rag-dashboard">
    <header class="rag-header">
      <div class="header-left">
        <h1>RAG 知识库</h1>
        <n-tag v-if="healthOk" type="success" size="small">服务正常</n-tag>
        <n-tag v-else type="error" size="small">服务异常</n-tag>
      </div>
      <div class="header-right">
        <n-select
          v-model:value="currentKb"
          :options="kbList.map(k => ({ label: k.name, value: k.kb_id }))"
          style="width: 220px"
          @update:value="switchKb"
        />
        <n-button @click="init" :loading="loading" quaternary circle>
          ↻
        </n-button>
      </div>
    </header>

    <n-spin :show="loading">
      <div class="stats-row" v-if="stats">
        <n-card size="small" class="stat-card">
          <n-statistic title="文档总数" :value="stats.total_documents" />
        </n-card>
        <n-card size="small" class="stat-card">
          <n-statistic title="已入库" :value="stats.indexed" />
        </n-card>
        <n-card size="small" class="stat-card">
          <n-statistic title="等待解析" :value="stats.waiting_parser" />
        </n-card>
        <n-card size="small" class="stat-card">
          <n-statistic title="失败" :value="stats.failed" />
        </n-card>
      </div>

      <n-divider />

      <n-tabs type="line" animated>
        <n-tab-pane name="documents" tab="文档管理">
          <div class="toolbar">
            <n-button type="primary" @click="showUploadModal = true">
              上传 PDF
            </n-button>
            <n-button @click="showBatchUploadModal = true">
              批量上传并云解析
            </n-button>
            <n-button @click="loadDocuments" :loading="docLoading" quaternary>
              刷新
            </n-button>
          </div>
          <n-data-table
            :columns="docColumns"
            :data="documents"
            :loading="docLoading"
            :bordered="false"
            :single-line="false"
            size="small"
          />
          <n-empty v-if="!docLoading && documents.length === 0" description="暂无文档" style="margin-top: 40px" />
        </n-tab-pane>

        <n-tab-pane name="chat" tab="知识问答">
          <div class="chat-mode-bar">
            <n-select
              v-model:value="chatMode"
              :options="[
                { label: '混合 (mix)', value: 'mix' },
                { label: '本地 (local)', value: 'local' },
                { label: '全局 (global)', value: 'global' },
                { label: '混合 (hybrid)', value: 'hybrid' },
                { label: '朴素 (naive)', value: 'naive' },
              ]"
              style="width: 180px"
            />
          </div>
          <div class="chat-box">
            <div class="chat-messages" ref="chatRef">
              <div v-for="(msg, i) in chatMessages" :key="i" :class="['msg', msg.role]">
                <div class="msg-label">{{ msg.role === 'user' ? '你' : 'RAG' }}</div>
                <div class="msg-content">{{ msg.content }}</div>
              </div>
              <n-empty v-if="chatMessages.length === 0" description="输入问题开始知识问答" style="margin-top: 60px" />
              <div v-if="chatLoading" class="msg assistant">
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
                <n-button type="primary" :loading="chatLoading" @click="handleChat" :disabled="!chatInput.trim()">
                  发送
                </n-button>
              </n-input-group>
            </div>
          </div>
        </n-tab-pane>

        <n-tab-pane name="tasks" tab="任务状态">
          <n-alert type="info" :bordered="false" style="margin-bottom: 16px">
            正在运行的任务每 5 秒自动刷新
          </n-alert>
          <div v-for="doc in documents.filter(d => d.status !== 'indexed' && d.status !== 'failed')" :key="doc.document_id" class="task-item">
            <div class="task-header">
              <span class="task-filename">{{ doc.filename }}</span>
              <n-tag :type="statusMap[doc.status]?.type || 'default'" size="small">
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
          <n-empty v-if="documents.filter(d => d.status !== 'indexed').length === 0" description="没有运行中的任务" style="margin-top: 40px" />
        </n-tab-pane>
      </n-tabs>
    </n-spin>

    <n-modal v-model:show="showUploadModal" title="上传 PDF" preset="card" style="width: 500px">
      <n-upload
        :multiple="true"
        accept=".pdf"
        :default-upload="false"
        @change="({ fileList }) => uploadFiles = fileList.map(f => f.file!) as File[]"
      >
        <n-button>选择 PDF 文件</n-button>
      </n-upload>
      <div style="margin-top: 16px; text-align: right">
        <n-button @click="showUploadModal = false" style="margin-right: 8px">取消</n-button>
        <n-button type="primary" @click="handleUpload" :disabled="uploadFiles.length === 0">上传</n-button>
      </div>
    </n-modal>

    <n-modal v-model:show="showBatchUploadModal" title="批量上传 + MinerU 云解析" preset="card" style="width: 500px">
      <p>一次最多 50 个文件，上传后自动提交到 MinerU 云解析并入库。</p>
      <n-upload
        :multiple="true"
        accept=".pdf"
        :default-upload="false"
        @change="({ fileList }) => uploadFiles = fileList.map(f => f.file!) as File[]"
      >
        <n-button>选择 PDF 文件</n-button>
      </n-upload>
      <div style="margin-top: 16px; text-align: right">
        <n-button @click="showBatchUploadModal = false" style="margin-right: 8px">取消</n-button>
        <n-button type="primary" @click="handleBatchUpload" :disabled="uploadFiles.length === 0">提交云解析</n-button>
      </div>
    </n-modal>
  </div>
</template>

<style scoped>
.rag-dashboard {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}
.rag-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-left h1 {
  margin: 0;
  font-size: 24px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.stat-card {
  text-align: center;
}
.toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.chat-box {
  display: flex;
  flex-direction: column;
  height: 500px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
}
.chat-mode-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.msg {
  margin-bottom: 16px;
}
.msg-label {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 4px;
}
.msg-content {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.user .msg-content {
  background: #2563eb;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.assistant .msg-content {
  background: #f3f4f6;
  border-bottom-left-radius: 4px;
}
.typing {
  color: #9ca3af;
}
.chat-input-area {
  padding: 12px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}
.task-item {
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
}
.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.task-filename {
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 500px;
}
</style>
