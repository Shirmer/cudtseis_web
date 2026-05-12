<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { NDropdown, NConfigProvider, type GlobalThemeOverrides } from 'naive-ui'
import { useRoute } from 'vue-router'
import { apiUrl } from '../config/api'

type ChatMessage = {
  id: number
  role: 'ai' | 'user'
  content: string
  contexts?: RagContext[]
  suggestions?: string[]
}

type RagContext = {
  title: string
  sourceType: string
  score?: number
}

type RagResponse = {
  answer: string
  question?: string
  retrievedContexts?: RagContext[]
  suggestedQuestions?: string[]
  retrievalMode?: string
  evidencePack?: {
    confidence?: string
  }
}

// --- 逻辑部分 (保持不变) ---
const route = useRoute()
const chatHistory = ref<ChatMessage[]>([
  { id: 1, role: 'ai', content: '你好，我是 Terra 文献 RAG。你可以直接问地质、地震、构造和文献证据相关的问题。' }
])

const userInput = ref('')
const isSending = ref(false)
const currentModel = ref('Geo RAG')

const modelOptions = [
  { label: 'Geo RAG', key: 'Geo RAG' },
  { label: '文献证据问答', key: '文献证据问答' },
  { label: '地震科研分析', key: '地震科研分析' }
]

// --- 样式定制：纯白 Dropdown ---
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

const formatRagReply = (payload: RagResponse): string => {
  const meta = [
    payload.retrievalMode ? `检索模式：${payload.retrievalMode}` : '',
    payload.evidencePack?.confidence ? `可信度：${payload.evidencePack.confidence}` : ''
  ].filter(Boolean).join('；')

  return [
    payload.answer,
    meta
  ]
    .filter(Boolean)
    .join('\n\n')
}

const handleSend = async () => {
  if (!userInput.value.trim() || isSending.value) return
  chatHistory.value.push({ id: Date.now(), role: 'user', content: userInput.value })
  const question = userInput.value.trim()
  userInput.value = ''
  nextTick(scrollToBottom)
  isSending.value = true

  try {
    const response = await fetch(apiUrl('/rag/papers/query'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        topK: 8
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const payload: RagResponse = await response.json()
    chatHistory.value.push({
      id: Date.now() + 1,
      role: 'ai',
      content: formatRagReply(payload),
      contexts: payload.retrievedContexts?.slice(0, 3) ?? [],
      suggestions: payload.suggestedQuestions?.slice(0, 3) ?? []
    })
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'Unknown error'
    chatHistory.value.push({
      id: Date.now() + 1,
      role: 'ai',
      content: `RAG 调用失败：${detail}\n请确认后端服务和文献检索链路已正常启动。`
    })
  } finally {
    isSending.value = false
    nextTick(scrollToBottom)
  }
}

const resetChat = () => {
  chatHistory.value = [{ id: 1, role: 'ai', content: '你好，我是 Terra 文献 RAG。你可以直接问地质、地震、构造和文献证据相关的问题。' }]
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
        <div v-for="msg in chatHistory" :key="msg.id" class="msg-row" :class="msg.role">
          <div v-if="msg.role === 'ai'" class="avatar ai">✨</div>
          <div class="message-stack">
            <div class="bubble">{{ msg.content }}</div>
            <div v-if="msg.contexts?.length" class="citation-list">
              <article v-for="context in msg.contexts" :key="`${msg.id}-${context.title}`" class="citation-card">
                <strong>{{ context.title }}</strong>
                <span>{{ context.sourceType }}<template v-if="typeof context.score === 'number'"> · {{ context.score.toFixed(2) }}</template></span>
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
              @select="(key) => currentModel = key"
            >
              <button class="model-pill">
                <span class="star-icon">✨</span>
                <span class="model-name">{{ currentModel }}</span>
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
            @keydown.enter.prevent="handleSend"
            placeholder="问文献证据、地震构造、断层破裂、危险性分析等问题"
            class="chat-textarea"
          ></textarea>

          <div class="input-actions">
            <div class="left-actions">
              <button class="pill-btn">
                <span class="icon">○</span> 思考
              </button>
              <button class="pill-btn">
                <span class="icon">📦</span> 工具
              </button>
            </div>

            <div class="right-actions">
               <button class="icon-btn-small attachment-btn">
                 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
               </button>
               <button class="send-btn" @click="handleSend" :disabled="!userInput.trim()">
                 <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
               </button>
            </div>
          </div>
        </div>

        <div class="footer-text">Powered by CDUT Seislab</div>
      </div>
    </footer>

  </div>
</template>

<style scoped>
/* 1. 基础布局：改为白底 */
.chat-layout {
  display: flex; flex-direction: column; height: 100%; width: 100%;
  background-color: #ffffff; /* 纯白背景 */
  color: #1f2329; /* 深黑字 */
  overflow: hidden;
}

/* 2. 核心限制器 */
.content-width-limiter {
  width: 100%; max-width: 800px; margin: 0 auto; padding: 0 16px; box-sizing: border-box;
}

/* 3. 聊天内容区 */
.chat-main {
  flex: 1; 
  overflow-y: auto; 
  overflow-x: hidden; 
  padding: 20px 0;
  display: flex; flex-direction: column;
}
.chat-main::-webkit-scrollbar { width: 6px; }
.chat-main::-webkit-scrollbar-thumb { background-color: #e5e7eb; border-radius: 3px; }

.msg-row { display: flex; gap: 16px; width: 100%; margin-bottom: 24px; }
.msg-row.user { justify-content: flex-end; }
.avatar { 
  width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  margin-top: 4px;
}
.avatar.ai { background-color: #ffffff; border: 1px solid #e5e7eb; }
.bubble { padding: 8px 0; font-size: 15px; line-height: 1.6; color: #1f2329; max-width: 90%; }
.bubble { white-space: pre-wrap; }
.message-stack { display: flex; flex-direction: column; gap: 10px; max-width: 90%; }

/* 用户气泡：浅灰/浅蓝背景 */
.msg-row.user .bubble { 
  background-color: #f3f4f6; /* 浅灰 */
  padding: 10px 16px; border-radius: 12px; color: #1f2329; 
}

.citation-list,
.suggestion-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.citation-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
}

.citation-card strong {
  font-size: 13px;
  color: #111827;
}

.citation-card span {
  font-size: 12px;
  color: #6b7280;
}

.suggestion-chip {
  border: 1px solid #dbe4ee;
  background: #ffffff;
  color: #374151;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
}

.suggestion-chip:hover {
  background: #f3f4f6;
}

/* 4. 底部固定区域 */
.footer-section {
  flex-shrink: 0; padding-bottom: 24px; background-color: #ffffff;
}

/* 模型选择栏 */
.floating-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px;
  padding: 0 4px; 
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

/* 模型胶囊按钮 (浅色版) */
.model-pill {
  display: flex; align-items: center; gap: 8px;
  background-color: #ffffff; 
  border: 1px solid #e5e7eb; /* 浅色边框 */
  color: #374151; /* 深色文字 */
  padding: 6px 12px; border-radius: 20px; font-size: 14px; font-weight: 500;
  cursor: pointer; transition: all 0.2s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.model-pill:hover { background-color: #f9fafb; border-color: #d1d5db; }
.star-icon { background: linear-gradient(135deg, #3b82f6, #a855f7); -webkit-background-clip: text; color: transparent; font-weight: bold; }
.chevron-down { color: #9ca3af; font-size: 12px; margin-left: 4px; }

/* 右侧工具 */
.header-tools { display: flex; align-items: center; gap: 12px; }
.new-chat-btn {
  width: 32px; height: 32px; background-color: #6366f1; border-radius: 10px; border: none;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.new-chat-btn:hover { background-color: #4f46e5; }
.icon-btn { background: none; border: none; color: #9ca3af; cursor: pointer; display: flex; }
.icon-btn:hover { color: #374151; }

/* 输入框本体 (白底 + 边框 + 阴影) */
.input-box {
  background-color: #ffffff; 
  border: 1px solid #e5e7eb; 
  border-radius: 16px;
  padding: 12px 16px; display: flex; flex-direction: column;
  transition: border 0.2s; 
  box-shadow: 0 4px 12px rgba(0,0,0,0.08); /* 柔和阴影 */
}
.input-box:focus-within { border-color: #6366f1; /* 聚焦变紫/蓝 */ }

.chat-textarea {
  background: transparent; border: none; outline: none;
  color: #1f2329; /* 深色输入文字 */
  font-size: 15px; width: 100%; height: 48px; resize: none; font-family: inherit;
}
.chat-textarea::placeholder { color: #9ca3af; }

.input-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }

.left-actions { display: flex; gap: 8px; }
.pill-btn {
  background-color: #f3f4f6; /* 浅灰按钮 */
  border: none; color: #6b7280;
  font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 20px;
  display: flex; align-items: center; gap: 6px; cursor: pointer; transition: all 0.2s;
}
.pill-btn:hover { background-color: #e5e7eb; color: #374151; }

.right-actions { display: flex; align-items: center; gap: 12px; }
.icon-btn-small { background: none; border: none; color: #9ca3af; cursor: pointer; display: flex; }
.icon-btn-small:hover { color: #374151; }

/* 发送按钮 */
.send-btn {
  width: 32px; height: 32px; background-color: #f3f4f6; color: #d1d5db; /* 默认浅灰 */
  border: none; border-radius: 8px; display: flex; align-items: center; justify-content: center;
  cursor: not-allowed; transition: all 0.2s;
}
.send-btn:not(:disabled) {
  background-color: #6366f1; color: #fff; cursor: pointer; /* 激活变紫 */
}

.footer-text { text-align: center; color: #9ca3af; font-size: 11px; margin-top: 8px; }

@media (max-width: 720px) {
  .floating-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

}
</style>
