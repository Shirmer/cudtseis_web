<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <div class="app-wrapper">
    
    <!-- === 左侧 Sider 风格侧边栏 (白色复刻版) === -->
    <aside class="sider-sidebar">
      
      <!-- 1. 顶部品牌区 -->
      <div class="nav-brand">
        <div class="brand-left">
          <!-- 这里放Logo，如果没有图就显示文字 -->
          <span class="brand-logo-icon">🧠</span>
          <span class="brand-text">Terra</span>
        </div>
        <button class="close-btn" title="隐藏侧边栏">
           <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
      </div>

      <!-- 2. 核心入口 (高亮：聊天) -->
      <div class="nav-item active-chat" @click="router.push('/')">
        <span class="icon">💬</span> 
        <span class="text">聊天</span>
      </div>

      <!-- 3. 滚动功能列表 -->
      <div class="scroll-menu">
        <div class="nav-item">
          <span class="icon">📝</span> <span class="text">REC笔记</span>
        </div>
        <div class="nav-item">
          <span class="icon">🪐</span> <span class="text">Agent</span>
        </div>
        <div class="nav-item">
          <span class="icon">✒️</span> <span class="text">写作</span>
        </div>
        <div class="nav-item">
          <span class="icon">🌐</span> <span class="text">翻译</span>
        </div>
        <div class="nav-item">
          <span class="icon">👁️</span> <span class="text">OCR</span>
        </div>
        <div class="nav-item">
          <span class="icon">🛡️</span> <span class="text">语法</span>
        </div>
        <div class="nav-item">
          <span class="icon">❓</span> <span class="text">提问</span>
        </div>
        <div class="nav-item">
          <span class="icon">🔍</span> <span class="text">搜索</span>
        </div>
        <div class="nav-item">
          <span class="icon">🧰</span> <span class="text">工具</span>
        </div>

        <!-- 分割线 -->
        <div class="divider"></div>

        <!-- 下半部分功能列表 (带箭头) -->
        <div class="nav-item">
          <span class="icon">🎨</span> <span class="text">绘画大师</span>
          <span class="arrow">→</span>
        </div>
        <div class="nav-item">
          <span class="icon">📄</span> <span class="text">ChatPDF</span>
          <span class="arrow">→</span>
        </div>
        <div class="nav-item">
          <span class="icon">📚</span> <span class="text">Wisebase</span>
          <span class="arrow">→</span>
        </div>
      </div>

      <!-- 4. 底部 Footer (用户头像 + 设置 + 折叠) -->
      <div class="nav-footer">
        <div class="footer-left">
          <!-- 空白头像占位符 -->
          <div class="avatar-placeholder">
             <span class="user-icon">👤</span>
          </div>
          
          <!-- 图标按钮组 -->
          <button class="icon-btn" title="多窗口">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          </button>
          <button class="icon-btn" title="设置">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
          </button>
        </div>

        <div class="footer-right">
          <button class="collapse-circle-btn" title="收起">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          </button>
        </div>
      </div>

    </aside>

    <!-- === 右侧内容容器 === -->
    <main class="content-area">
      <router-view></router-view>
    </main>
    
  </div>
</template>

<style scoped>
/* 全局容器 */
.app-wrapper {
  display: flex;
  width: 100vw;
  height: 100vh;
  background-color: #ffffff;
  overflow: hidden;
}

/* 侧边栏容器 (浅灰色背景) */
.sider-sidebar {
  width: 240px;
  background-color: #f7f7f8; /* 浅灰 */
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  color: #4b5563;
  flex-shrink: 0;
  user-select: none;
}

/* 1. 顶部品牌区 */
.nav-brand {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; padding: 0 4px;
}
.brand-left { display: flex; align-items: center; gap: 8px; }
.brand-logo-icon { font-size: 24px; }
.brand-text { font-size: 20px; font-weight: 700; color: #1f2329; }
.close-btn { 
  background: none; border: none; color: #9ca3af; cursor: pointer; padding: 4px; 
  display: flex; align-items: center; justify-content: center;
}
.close-btn:hover { color: #374151; background-color: #e5e7eb; border-radius: 4px; }

/* 2. 聊天高亮入口 (仿 Sider 胶囊风格) */
.active-chat {
  background-color: #eef2ff; /* 极淡的蓝紫色背景 */
  color: #4f46e5;          /* 深蓝紫色文字 */
  padding: 12px;
  border-radius: 12px;
  font-size: 15px; font-weight: 600;
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.active-chat:hover { background-color: #e0e7ff; }
.active-chat .icon { font-size: 18px; }

/* 3. 滚动菜单区 */
.scroll-menu {
  flex: 1;
  overflow-y: auto;
  display: flex; flex-direction: column; gap: 4px;
  /* 隐藏滚动条 */
  scrollbar-width: none; 
}
.scroll-menu::-webkit-scrollbar { display: none; }

/* 通用菜单项 */
.nav-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 14px;
  color: #646a73; /* 深灰 */
  cursor: pointer;
  transition: background-color 0.15s;
}
/* 排除 active-chat 的 hover */
.nav-item:not(.active-chat):hover { background-color: #e5e7eb; color: #1f2329; }

.nav-item .icon { font-size: 18px; width: 22px; text-align: center; color: #8f959e; }
.nav-item:hover .icon { color: #1f2329; }

.arrow { margin-left: auto; font-size: 14px; color: #9ca3af; opacity: 0; transition: opacity 0.2s; }
.nav-item:hover .arrow { opacity: 1; }

/* 分割线 */
.divider {
  height: 1px;
  background-color: #e5e7eb;
  margin: 12px 8px;
}

/* 5. 底部 Footer */
.nav-footer {
  margin-top: auto;
  padding-top: 16px;
  display: flex; justify-content: space-between; align-items: center;
}

.footer-left { display: flex; align-items: center; gap: 12px; }

/* 空白头像占位符 */
.avatar-placeholder {
  width: 32px; height: 32px;
  background-color: #e0e2e5; /* 稍微深一点的灰，显示出圆形 */
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
}
.user-icon { font-size: 18px; color: #fff; opacity: 0.8; }

/* 底部图标按钮 */
.icon-btn {
  background: none; border: none; color: #9ca3af; cursor: pointer; padding: 4px;
  display: flex; align-items: center; justify-content: center;
}
.icon-btn:hover { color: #374151; }

.footer-right { display: flex; align-items: center; }

/* 圆形折叠按钮 */
.collapse-circle-btn {
  width: 32px; height: 32px;
  border-radius: 50%;
  background-color: #e5e7eb; /* 浅灰底 */
  color: #646a73;
  border: none;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}
.collapse-circle-btn:hover { background-color: #d1d5db; color: #000; }

/* 右侧内容区 */
.content-area {
  flex: 1;
  background-color: #ffffff;
  overflow: hidden;
  position: relative;
}
</style>