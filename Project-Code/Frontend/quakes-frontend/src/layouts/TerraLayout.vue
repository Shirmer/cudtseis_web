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
          <span class="brand-logo-icon">T</span>
          <span class="brand-text">Terra</span>
        </div>
        <button class="close-btn" title="隐藏侧边栏">
           <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
      </div>

      <!-- 2. 核心入口 (高亮：聊天) -->
      <div class="nav-item active-chat" @click="router.push('/terra/chat')">
        <span class="icon">💬</span> 
        <span class="text">证据问答</span>
      </div>

      <div class="scroll-menu">
        <span class="nav-section">地震数据</span>
        <div class="nav-item" @click="router.push('/dashboard')">
          <span class="icon">◉</span> <span class="text">实时仪表盘</span>
        </div>
        <div class="nav-item" @click="router.push('/history')">
          <span class="icon">≋</span> <span class="text">历史数据</span>
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
.app-wrapper {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #101b18;
}

.sider-sidebar {
  width: 252px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 18px 14px;
  color: #dfe8df;
  user-select: none;
  background:
    linear-gradient(180deg, rgba(29, 143, 130, 0.16), transparent 34%),
    repeating-linear-gradient(150deg, rgba(255, 255, 255, 0.045) 0 1px, transparent 1px 30px),
    #13231f;
  border-right: 1px solid rgba(235, 232, 214, 0.16);
  box-shadow: inset -1px 0 0 rgba(0, 0, 0, 0.22);
}

.nav-brand {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
  padding: 0 3px;
}

.brand-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-logo-icon {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #e5c46b, #1d8f82);
  color: #10201d;
  font-size: 18px;
  font-weight: 900;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.28);
}

.brand-text {
  font-size: 21px;
  font-weight: 900;
  color: #f5f3e8;
  letter-spacing: 0.02em;
}

.close-btn,
.icon-btn,
.collapse-circle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(235, 232, 214, 0.12);
  background: rgba(255, 255, 255, 0.045);
  color: #b9c6bf;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, color 0.18s ease, border-color 0.18s ease;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: 11px;
}

.close-btn:hover,
.icon-btn:hover,
.collapse-circle-btn:hover {
  transform: translateY(-1px);
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(229, 196, 107, 0.28);
}

.active-chat {
  position: relative;
  background:
    linear-gradient(135deg, rgba(229, 196, 107, 0.22), rgba(29, 143, 130, 0.22)),
    rgba(255, 255, 255, 0.06);
  color: #fff7dc;
  border: 1px solid rgba(229, 196, 107, 0.26);
  padding: 13px 12px;
  border-radius: 15px;
  font-size: 15px;
  font-weight: 900;
  margin-bottom: 10px;
  box-shadow: 0 16px 34px rgba(0, 0, 0, 0.23);
}

.active-chat::before {
  content: "";
  position: absolute;
  left: -14px;
  top: 12px;
  bottom: 12px;
  width: 3px;
  border-radius: 999px;
  background: #e5c46b;
}

.scroll-menu {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 5px;
  scrollbar-width: none;
}

.scroll-menu::-webkit-scrollbar {
  display: none;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 42px;
  padding: 0 12px;
  border-radius: 13px;
  font-size: 14px;
  color: #aebdb6;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, color 0.18s ease;
}

.nav-section {
  display: block;
  padding: 13px 12px 6px;
  color: rgba(245, 243, 232, 0.48);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.12em;
}

.nav-item:not(.active-chat):hover {
  transform: translateX(3px);
  background: rgba(255, 255, 255, 0.075);
  color: #f5f3e8;
}

.nav-item .icon {
  width: 24px;
  text-align: center;
  color: #e5c46b;
  font-size: 17px;
  font-weight: 900;
}

.nav-item .text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arrow {
  margin-left: auto;
  font-size: 14px;
  color: #8fa39a;
  opacity: 0;
  transition: opacity 0.18s ease;
}

.nav-item:hover .arrow {
  opacity: 1;
}

.divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(235, 232, 214, 0.18), transparent);
  margin: 12px 8px;
}

.nav-footer {
  margin-top: auto;
  padding-top: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid rgba(235, 232, 214, 0.1);
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar-placeholder {
  width: 34px;
  height: 34px;
  border-radius: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(235, 232, 214, 0.12);
}

.user-icon {
  font-size: 17px;
  color: #f5f3e8;
  opacity: 0.9;
}

.icon-btn {
  width: 34px;
  height: 34px;
  border-radius: 12px;
}

.footer-right {
  display: flex;
  align-items: center;
}

.collapse-circle-btn {
  width: 34px;
  height: 34px;
  border-radius: 50%;
}

.content-area {
  flex: 1;
  overflow: hidden;
  position: relative;
  background: #f4f1e8;
}

@media (max-width: 760px) {
  .sider-sidebar {
    width: 76px;
    padding: 14px 10px;
  }

  .brand-text,
  .nav-item .text,
  .nav-section,
  .arrow,
  .close-btn,
  .nav-footer {
    display: none;
  }

  .nav-item {
    justify-content: center;
    padding: 0;
  }

  .active-chat::before {
    left: -10px;
  }
}
</style>
