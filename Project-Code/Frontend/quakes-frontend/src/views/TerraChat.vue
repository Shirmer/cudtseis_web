<script setup lang="ts">
import { computed, ref, nextTick, onMounted } from 'vue'
import { NDropdown, NConfigProvider, type GlobalThemeOverrides } from 'naive-ui'
import { useRoute } from 'vue-router'
import { apiUrl } from '../config/api'

type ChatMessage = {
  id: number
  role: 'ai' | 'user'
  content: string
  contexts?: RagContext[]
  evidences?: EvidenceItem[]
  suggestions?: string[]
  retrievalMode?: string
  confidence?: string
  modeLabel?: string
  status?: 'normal' | 'error'
}

type RagContext = {
  id?: string
  title: string
  sourceType: string
  score?: number
  content?: string
  metadata?: Record<string, unknown>
}

type EvidenceItem = {
  id: string
  title: string
  text: string
  score?: number
  page?: number | null
  documentId?: string
  paperId?: string
  citation?: string
  metadata?: Record<string, unknown>
}

type RagResponse = {
  answer: string
  question?: string
  retrievedContexts?: RagContext[]
  suggestedQuestions?: string[]
  retrievalMode?: string
  evidencePack?: {
    confidence?: string
    evidence?: EvidenceItem[]
    limitations?: string[]
  }
  diagnostics?: Record<string, unknown>
}

type DocumentUpload = {
  filePath: string
  fileName: string
  storageUri: string
  fileSha256: string
  sizeBytes: number
  message: string
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

type ChatMode = {
  key: string
  label: string
  topK: number
  placeholder: string
  prefix?: string
}

const route = useRoute()
const chatHistory = ref<ChatMessage[]>([
  {
    id: 1,
    role: 'ai',
    content: '你好，我是 Terra 文献 RAG。你可以直接问地质、地震、构造和文献证据相关的问题。',
    modeLabel: 'Geo RAG'
  }
])

const userInput = ref('')
const isSending = ref(false)
const isUploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const currentModel = ref('geo-rag')

const chatModes: ChatMode[] = [
  {
    key: 'geo-rag',
    label: 'Geo RAG',
    topK: 8,
    placeholder: '问文献证据、地震构造、断层破裂、危险性分析等问题'
  },
  {
    key: 'evidence',
    label: '文献证据问答',
    topK: 10,
    placeholder: '输入需要用文献证据回答的问题'
  },
  {
    key: 'analysis',
    label: '地震科研分析',
    topK: 12,
    placeholder: '输入地震现象、区域、断层或构造背景，要求系统给出谨慎分析',
    prefix: '请用地震学和地质学科研分析口径回答，并严格区分文献证据、推断和不确定性。'
  }
]

const modelOptions = chatModes.map((mode) => ({ label: mode.label, key: mode.key }))
const currentMode = computed(() => chatModes.find((mode) => mode.key === currentModel.value) ?? chatModes[0])
const isBusy = computed(() => isSending.value || isUploading.value)
const allowedDocumentPattern = /\.(pdf|txt|md)$/i

const dropdownTheme: GlobalThemeOverrides = {
  Dropdown: {
    color: '#ffffff',             
    textColor: '#333333',         
    borderRadius: '12px',         
    boxShadow: '0 4px 16px rgba(0,0,0,0.1)', // 稍微明显的阴影
    padding: '6px',
    optionHeightMedium: '36px',
    optionColorHover: '#f3f4f6',  
    optionTextColorHover: '#000', 
    fontSizeMedium: '14px',
    border: '1px solid #e5e7eb' // 加个边框
  }
}

const selectMode = (key: string | number) => {
  const value = String(key)
  if (chatModes.some((mode) => mode.key === value)) {
    currentModel.value = value
  }
}

const buildQuestion = (question: string): string => {
  const prefix = currentMode.value.prefix
  return prefix ? `${prefix}\n\n用户问题：${question}` : question
}

const formatRagReply = (payload: RagResponse): string => {
  return payload.answer || '后端没有返回回答内容。'
}

const readError = async (response: Response) => {
  const payload = await response.json().catch(() => null)
  const detail = payload?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  return `HTTP ${response.status}`
}

const titleFromFileName = (name: string) => name.replace(/\.(pdf|txt|md)$/i, '')

const scoreText = (score?: number) => {
  if (typeof score !== 'number') return ''
  return score.toFixed(score >= 1 ? 2 : 3)
}

const evidencePageLabel = (evidence: EvidenceItem) => {
  return evidence.page ? `p.${evidence.page}` : '页码未知'
}

const openEvidenceSource = (evidence: EvidenceItem) => {
  if (!evidence.documentId) return
  const pageAnchor = evidence.page ? `#page=${evidence.page}` : ''
  window.open(apiUrl(`/documents/${encodeURIComponent(evidence.documentId)}/file`) + pageAnchor, '_blank', 'noopener,noreferrer')
}

const triggerFilePicker = () => {
  if (isBusy.value) return
  fileInput.value?.click()
}

const uploadSelectedFile = async (file: File): Promise<DocumentUpload> => {
  const response = await fetch(apiUrl(`/documents/upload?filename=${encodeURIComponent(file.name)}`), {
    method: 'POST',
    headers: { 'Content-Type': file.type || 'application/octet-stream' },
    body: file
  })
  if (!response.ok) throw new Error(await readError(response))
  return await response.json() as DocumentUpload
}

const ingestUploadedDocument = async (upload: DocumentUpload, file: File): Promise<DocumentIngest> => {
  const response = await fetch(apiUrl('/documents/ingest'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filePath: upload.filePath,
      title: titleFromFileName(file.name),
      force: true
    })
  })
  if (!response.ok) throw new Error(await readError(response))
  return await response.json() as DocumentIngest
}

const handleDocumentSelected = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  if (!allowedDocumentPattern.test(file.name)) {
    chatHistory.value.push({
      id: Date.now(),
      role: 'ai',
      content: '只支持上传 PDF、TXT 或 Markdown 文献。',
      modeLabel: currentMode.value.label,
      status: 'error'
    })
    nextTick(scrollToBottom)
    return
  }

  chatHistory.value.push({
    id: Date.now(),
    role: 'user',
    content: `上传文献：${file.name}`,
    modeLabel: currentMode.value.label
  })
  isUploading.value = true
  nextTick(scrollToBottom)

  try {
    const upload = await uploadSelectedFile(file)
    const ingest = await ingestUploadedDocument(upload, file)
    const lines = [
      `文献已入库：${ingest.title || file.name}`,
      `状态：${ingest.status}；解析器：${ingest.parser}`,
      `页数：${ingest.pages}；知识单元：${ingest.units}；图表/公式单元：${ingest.multimodalUnits ?? 0}`,
      `Embedding：${ingest.embeddingBackend || '未返回'}`,
      ingest.storageUri ? `存储：${ingest.storageUri}` : ''
    ].filter(Boolean)
    chatHistory.value.push({
      id: Date.now() + 1,
      role: 'ai',
      content: lines.join('\n'),
      modeLabel: '文献入库',
      suggestions: [
        `总结 ${ingest.title || titleFromFileName(file.name)} 的主要地质证据`,
        '这篇文献可以支撑哪些断层或构造背景判断？',
        '列出当前文献证据的不确定性'
      ],
      status: 'normal'
    })
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'Unknown error'
    chatHistory.value.push({
      id: Date.now() + 1,
      role: 'ai',
      content: `文献上传或入库失败：${detail}\n请确认后端服务、embedding 服务和向量库正常运行。`,
      modeLabel: '文献入库',
      status: 'error'
    })
  } finally {
    isUploading.value = false
    nextTick(scrollToBottom)
  }
}

const handleSend = async () => {
  if (!userInput.value.trim() || isBusy.value) return
  const question = userInput.value.trim()
  const mode = currentMode.value
  chatHistory.value.push({ id: Date.now(), role: 'user', content: question, modeLabel: mode.label })
  userInput.value = ''
  nextTick(scrollToBottom)
  isSending.value = true

  try {
    const response = await fetch(apiUrl('/rag/papers/query'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: buildQuestion(question),
        topK: mode.topK
      })
    })

    if (!response.ok) {
      throw new Error(await readError(response))
    }

    const payload: RagResponse = await response.json()
    const evidences = payload.evidencePack?.evidence?.slice(0, 5) ?? []
    chatHistory.value.push({
      id: Date.now() + 1,
      role: 'ai',
      content: formatRagReply(payload),
      contexts: payload.retrievedContexts?.slice(0, 4) ?? [],
      evidences,
      suggestions: payload.suggestedQuestions?.slice(0, 3) ?? [],
      retrievalMode: payload.retrievalMode,
      confidence: payload.evidencePack?.confidence,
      modeLabel: mode.label,
      status: 'normal'
    })
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'Unknown error'
    chatHistory.value.push({
      id: Date.now() + 1,
      role: 'ai',
      content: `RAG 调用失败：${detail}\n请确认后端服务、文献检索链路和 /api/rag/papers/query 接口已正常启动。`,
      modeLabel: mode.label,
      status: 'error'
    })
  } finally {
    isSending.value = false
    nextTick(scrollToBottom)
  }
}

const resetChat = () => {
  chatHistory.value = [
    {
      id: 1,
      role: 'ai',
      content: '你好，我是 Terra 文献 RAG。你可以直接问地质、地震、构造和文献证据相关的问题。',
      modeLabel: currentMode.value.label
    }
  ]
}

const chatContainer = ref<HTMLElement | null>(null)
const scrollToBottom = () => {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

onMounted(() => {
  const initialQuestion = String(route.query.q ?? '').trim()
  if (initialQuestion) userInput.value = initialQuestion
})
</script>

<template>
  <div class="chat-layout">
    
    <!-- 1. 聊天区域 (白底) -->
    <main class="chat-main" ref="chatContainer">
      <div class="content-width-limiter">
        <div v-for="msg in chatHistory" :key="msg.id" class="msg-row" :class="[msg.role, msg.status]">
          <div v-if="msg.role === 'ai'" class="avatar ai">T</div>
          <div class="message-stack">
            <div v-if="msg.role === 'ai'" class="message-meta">
              <span>{{ msg.modeLabel ?? 'Geo RAG' }}</span>
              <span v-if="msg.retrievalMode">{{ msg.retrievalMode }}</span>
              <span v-if="msg.confidence">可信度 {{ msg.confidence }}</span>
            </div>
            <div class="bubble">{{ msg.content }}</div>
            <div v-if="msg.evidences?.length" class="evidence-list">
              <article v-for="evidence in msg.evidences" :key="`${msg.id}-${evidence.id}`" class="evidence-card">
                <div class="evidence-head">
                  <strong>{{ evidence.id }} · {{ evidence.title || evidence.paperId || 'Untitled' }}</strong>
                  <span>{{ evidencePageLabel(evidence) }}<template v-if="scoreText(evidence.score)"> · {{ scoreText(evidence.score) }}</template></span>
                </div>
                <p>{{ evidence.text }}</p>
                <small v-if="evidence.citation">{{ evidence.citation }}</small>
                <button
                  v-if="evidence.documentId"
                  type="button"
                  class="source-link"
                  @click="openEvidenceSource(evidence)"
                >
                  打开原文
                </button>
              </article>
            </div>
            <div v-if="msg.contexts?.length" class="citation-list">
              <article v-for="context in msg.contexts" :key="`${msg.id}-${context.title}`" class="citation-card">
                <strong>{{ context.title }}</strong>
                <span>{{ context.sourceType }}<template v-if="typeof context.score === 'number'"> · {{ context.score.toFixed(2) }}</template></span>
                <p v-if="context.content">{{ context.content }}</p>
              </article>
            </div>
            <div v-if="msg.suggestions?.length" class="suggestion-list">
              <button
                v-for="suggestion in msg.suggestions"
                :key="`${msg.id}-${suggestion}`"
                type="button"
                class="suggestion-chip"
                @click="userInput = suggestion"
              >
                {{ suggestion }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- 2. 底部控制区 (白底) -->
    <footer class="footer-section">
      <div class="content-width-limiter">
        
        <!-- === 悬浮 Header (样式微调为白色风格) === -->
        <div class="floating-header">
          <div class="header-left">
          <n-config-provider :theme-overrides="dropdownTheme">
            <n-dropdown 
              trigger="click" 
              placement="top-start" 
              :options="modelOptions" 
              @select="selectMode"
            >
              <button class="model-pill">
                <span class="star-icon">R</span>
                <span class="model-name">{{ currentMode.label }}</span>
                <span class="chevron-down">⌄</span>
              </button>
            </n-dropdown>
          </n-config-provider>
          </div>

          <div class="header-tools">
            <button class="icon-btn" title="History">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><path d="M14 2v6h6"></path><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
            </button>
            <button class="new-chat-btn" @click="resetChat" title="新建 RAG 问答">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            </button>
          </div>
        </div>
        
        <!-- 输入框区域 (白底阴影) -->
        <div class="input-box">
          <textarea 
            v-model="userInput"
            @keydown.enter.exact.prevent="handleSend"
            :placeholder="currentMode.placeholder"
            class="chat-textarea"
          ></textarea>

          <div class="input-actions">
            <div class="left-actions">
              <span class="mode-chip">证据优先</span>
              <span class="mode-chip">TopK {{ currentMode.topK }}</span>
              <span v-if="isUploading" class="mode-chip active">文献入库中</span>
            </div>

            <div class="right-actions">
               <input
                 ref="fileInput"
                 type="file"
                 class="hidden-file-input"
                 accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
                 @change="handleDocumentSelected"
               />
               <button
                 class="icon-btn-small attachment-btn"
                 :disabled="isBusy"
                 :title="isUploading ? '文献入库中' : '上传 PDF/TXT/MD 并入库'"
                 @click="triggerFilePicker"
               >
                 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
               </button>
               <button class="send-btn" @click="handleSend" :disabled="!userInput.trim() || isBusy">
                 <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
               </button>
            </div>
          </div>
        </div>

      </div>
    </footer>

  </div>
</template>

<style scoped>
.chat-layout {
  --ink: #10201d;
  --muted: #6a7974;
  --panel: rgba(255, 255, 251, 0.9);
  --line: rgba(40, 67, 61, 0.14);
  --mineral: #1d8f82;
  --copper: #b86535;
  --lichen: #d8e8cd;
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  overflow: hidden;
  position: relative;
  color: var(--ink);
  background:
    linear-gradient(118deg, rgba(18, 55, 50, 0.1), transparent 34%),
    repeating-linear-gradient(165deg, rgba(16, 32, 29, 0.045) 0 1px, transparent 1px 28px),
    linear-gradient(180deg, #f4f1e8 0%, #eef4ee 52%, #f9faf6 100%);
  font-family: Lato, "PingFang SC", "Microsoft YaHei", sans-serif;
}

.chat-layout::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(29, 143, 130, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(184, 101, 53, 0.045) 1px, transparent 1px);
  background-size: 52px 52px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.65), transparent 78%);
}

.content-width-limiter {
  width: min(100%, 920px);
  margin: 0 auto;
  padding: 0 22px;
  box-sizing: border-box;
  position: relative;
  z-index: 1;
}

.chat-main {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 32px 0 24px;
  display: flex;
  flex-direction: column;
}

.chat-main::-webkit-scrollbar { width: 10px; }
.chat-main::-webkit-scrollbar-track { background: transparent; }
.chat-main::-webkit-scrollbar-thumb {
  background: rgba(35, 82, 74, 0.18);
  border: 3px solid transparent;
  border-radius: 999px;
  background-clip: content-box;
}

.msg-row {
  display: flex;
  gap: 14px;
  width: 100%;
  margin-bottom: 26px;
}

.msg-row.user {
  justify-content: flex-end;
}

.avatar {
  width: 38px;
  height: 38px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
  box-shadow: 0 12px 28px rgba(13, 35, 31, 0.1);
}

.avatar.ai {
  background: linear-gradient(145deg, #163a35, #267c70);
  border: 1px solid rgba(255, 255, 255, 0.62);
  color: #fff;
}

.message-stack {
  display: flex;
  flex-direction: column;
  gap: 11px;
  max-width: min(92%, 760px);
}

.message-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  color: var(--muted);
  font-size: 12px;
}

.message-meta span {
  border: 1px solid rgba(43, 78, 70, 0.14);
  border-radius: 999px;
  padding: 4px 9px;
  background: rgba(255, 255, 251, 0.72);
  backdrop-filter: blur(10px);
}

.bubble {
  max-width: 100%;
  white-space: pre-wrap;
  padding: 14px 16px;
  border-radius: 18px;
  color: #18322e;
  font-size: 15px;
  line-height: 1.78;
  background: rgba(255, 255, 251, 0.8);
  border: 1px solid rgba(38, 76, 68, 0.12);
  box-shadow: 0 16px 38px rgba(24, 44, 41, 0.07);
}

.msg-row.user .message-stack {
  align-items: flex-end;
}

.msg-row.user .bubble {
  background: linear-gradient(135deg, #183934, #1f7d71);
  color: #f8fff9;
  border-color: rgba(255, 255, 255, 0.2);
  border-bottom-right-radius: 7px;
  max-width: min(100%, 640px);
}

.msg-row.ai .bubble {
  border-bottom-left-radius: 7px;
}

.msg-row.error .bubble {
  color: #7c1f1a;
  background: #fff4ee;
  border-color: rgba(196, 81, 55, 0.32);
}

.citation-list,
.suggestion-list,
.evidence-list {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}

.evidence-list {
  flex-direction: column;
}

.evidence-card,
.citation-card {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(38, 76, 68, 0.14);
  background:
    linear-gradient(90deg, rgba(29, 143, 130, 0.07), transparent 36%),
    rgba(255, 255, 251, 0.88);
  box-shadow: 0 14px 32px rgba(23, 42, 39, 0.07);
}

.evidence-card {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-radius: 14px;
}

.evidence-card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, var(--mineral), var(--copper));
}

.evidence-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.evidence-head strong {
  color: #132722;
  font-size: 13px;
  line-height: 1.45;
}

.evidence-head span,
.evidence-card small {
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
}

.evidence-card p,
.citation-card p {
  margin: 0;
  color: #33443f;
  font-size: 13px;
  line-height: 1.65;
}

.source-link {
  justify-self: start;
  min-height: 30px;
  border: 1px solid rgba(29, 143, 130, 0.28);
  border-radius: 999px;
  background: rgba(255, 255, 251, 0.82);
  color: #146b62;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.source-link:hover,
.suggestion-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(22, 58, 53, 0.12);
}

.citation-card {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 11px 13px;
  border-radius: 14px;
}

.citation-card strong {
  font-size: 13px;
  color: #132722;
}

.citation-card span {
  font-size: 12px;
  color: var(--muted);
}

.suggestion-chip {
  border: 1px solid rgba(38, 76, 68, 0.15);
  background: rgba(255, 255, 251, 0.78);
  color: #24423d;
  border-radius: 999px;
  padding: 7px 13px;
  font-size: 12px;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.footer-section {
  flex-shrink: 0;
  padding: 0 0 24px;
  background: linear-gradient(180deg, transparent, rgba(244, 241, 232, 0.9) 24%);
  position: relative;
  z-index: 2;
}

.floating-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 0 2px;
}

.header-left,
.header-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.model-pill,
.icon-btn,
.new-chat-btn,
.icon-btn-small,
.send-btn {
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.model-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 251, 0.84);
  border: 1px solid rgba(38, 76, 68, 0.16);
  color: #203b36;
  padding: 8px 13px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(22, 44, 40, 0.08);
  backdrop-filter: blur(14px);
}

.model-pill:hover {
  transform: translateY(-1px);
  border-color: rgba(29, 143, 130, 0.38);
}

.star-icon {
  color: var(--copper);
  font-weight: 900;
}

.chevron-down {
  color: #7c8c86;
  font-size: 12px;
  margin-left: 2px;
}

.new-chat-btn,
.send-btn:not(:disabled) {
  background: linear-gradient(135deg, #18433d, #1e8d80);
  color: #fff;
  box-shadow: 0 12px 24px rgba(23, 95, 86, 0.24);
}

.new-chat-btn {
  width: 36px;
  height: 36px;
  border-radius: 13px;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.new-chat-btn:hover,
.send-btn:not(:disabled):hover,
.icon-btn:hover,
.icon-btn-small:hover {
  transform: translateY(-1px);
}

.icon-btn,
.icon-btn-small {
  background: rgba(255, 255, 251, 0.54);
  border: 1px solid rgba(38, 76, 68, 0.12);
  color: #687873;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 13px;
}

.icon-btn:hover,
.icon-btn-small:hover {
  color: #183934;
  border-color: rgba(29, 143, 130, 0.26);
}

.input-box {
  background:
    linear-gradient(135deg, rgba(255, 255, 251, 0.94), rgba(241, 247, 239, 0.92)),
    var(--panel);
  border: 1px solid rgba(38, 76, 68, 0.18);
  border-radius: 20px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  box-shadow:
    0 24px 60px rgba(18, 36, 32, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.74);
  backdrop-filter: blur(18px);
}

.input-box:focus-within {
  border-color: rgba(29, 143, 130, 0.52);
  box-shadow:
    0 28px 70px rgba(18, 36, 32, 0.18),
    0 0 0 4px rgba(29, 143, 130, 0.1);
}

.chat-textarea {
  width: 100%;
  height: 58px;
  resize: none;
  border: none;
  outline: none;
  background: transparent;
  color: #10201d;
  font-family: inherit;
  font-size: 15px;
  line-height: 1.55;
}

.chat-textarea::placeholder {
  color: #7b8a84;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  margin-top: 10px;
}

.left-actions,
.right-actions {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
}

.mode-chip {
  background: rgba(216, 232, 205, 0.62);
  border: 1px solid rgba(38, 76, 68, 0.12);
  color: #4b5f58;
  font-size: 12px;
  font-weight: 800;
  padding: 5px 10px;
  border-radius: 999px;
  display: flex;
  align-items: center;
}

.mode-chip.active {
  color: #125f56;
  background: rgba(29, 143, 130, 0.12);
  border-color: rgba(29, 143, 130, 0.28);
}

.hidden-file-input {
  display: none;
}

.icon-btn-small {
  width: 34px;
  height: 34px;
  border-radius: 12px;
}

.icon-btn-small:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.send-btn {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 13px;
  background: rgba(32, 59, 54, 0.08);
  color: #9aa6a1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: not-allowed;
}

.send-btn:not(:disabled) {
  cursor: pointer;
}

@media (max-width: 720px) {
  .content-width-limiter {
    padding: 0 14px;
  }

  .chat-main {
    padding-top: 22px;
  }

  .floating-header,
  .input-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .header-tools,
  .right-actions {
    justify-content: flex-end;
  }

  .message-stack {
    max-width: calc(100% - 48px);
  }

  .msg-row.user .message-stack {
    max-width: 92%;
  }
}
</style>
