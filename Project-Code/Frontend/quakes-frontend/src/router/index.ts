import { createRouter, createWebHistory } from 'vue-router'

// --- 1. 原有的组件 (保持不变) ---
import DashboardView from '../views/DashboardView.vue'
import HomeView from '../views/HomeView.vue'
import HistoryData from '../views/HistoryData.vue'

// --- 2. 新增的 Terra 组件 (Sider 风格) ---
import TerraLayout from '../layouts/TerraLayout.vue'
import TerraChat from '../views/TerraChat.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // =========== 原有路由 (保留) ===========
    {
      path: '/',
      name: 'home',
      component: HomeView,
      props: { initialLocale: 'zh' }
    },
    {
      path: '/en',
      name: 'home-en',
      component: HomeView,
      props: { initialLocale: 'en' }
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardView // 访问 /dashboard 还能看到旧地图
    },
    {
      path: '/history',
      name: 'history',
      component: HistoryData // 访问 /history 还能看到表格
    },

    // =========== 新增路由 (Terra) ===========
    {
      path: '/terra',
      component: TerraLayout, // 加载 Sider 布局框架
      redirect: '/terra/chat',
      children: [
        {
          path: 'chat',
          name: 'terra-chat',
          component: TerraChat // 这里显示对话框
        }
      ]
    }
  ]
})

export default router
