import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import EarthView from '../views/EarthView.vue'
import LegalView from '../views/LegalView.vue'
import ContactView from '../views/ContactView.vue'
import NotFoundView from '../views/NotFoundView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to) {
    if (to.hash) {
      return { el: to.hash, behavior: 'smooth', top: 90 }
    }
    return { top: 0 }
  },
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/en', name: 'home-en', component: HomeView },
    { path: '/earth', name: 'earth', component: EarthView },
    { path: '/en/earth', name: 'earth-en', component: EarthView },
    { path: '/privacy', name: 'privacy', component: LegalView, meta: { doc: 'privacy' } },
    { path: '/en/privacy', name: 'privacy-en', component: LegalView, meta: { doc: 'privacy' } },
    { path: '/terms', name: 'terms', component: LegalView, meta: { doc: 'terms' } },
    { path: '/en/terms', name: 'terms-en', component: LegalView, meta: { doc: 'terms' } },
    { path: '/contact', name: 'contact', component: ContactView },
    { path: '/en/contact', name: 'contact-en', component: ContactView },
    // 未知地址给真正的 404，而不是静默跳回首页（便于排查断链，也不会误导搜索引擎）
    { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView }
  ]
})

export default router
