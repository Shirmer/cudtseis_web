import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import LegalView from '../views/LegalView.vue'
import ContactView from '../views/ContactView.vue'

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
    { path: '/privacy', name: 'privacy', component: LegalView, meta: { doc: 'privacy' } },
    { path: '/en/privacy', name: 'privacy-en', component: LegalView, meta: { doc: 'privacy' } },
    { path: '/terms', name: 'terms', component: LegalView, meta: { doc: 'terms' } },
    { path: '/en/terms', name: 'terms-en', component: LegalView, meta: { doc: 'terms' } },
    { path: '/contact', name: 'contact', component: ContactView },
    { path: '/en/contact', name: 'contact-en', component: ContactView },
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})

export default router
