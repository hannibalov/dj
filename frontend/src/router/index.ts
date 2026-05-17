import { createRouter, createWebHistory } from 'vue-router'

import DashboardPage from '@/pages/DashboardPage.vue'
import SettingsPage from '@/pages/SettingsPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'dashboard', component: DashboardPage },
    { path: '/settings', name: 'settings', component: SettingsPage },
  ],
})

export default router
