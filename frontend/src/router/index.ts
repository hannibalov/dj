import { createRouter, createWebHistory } from 'vue-router'

import DashboardPage from '@/pages/DashboardPage.vue'
import LibraryPage from '@/pages/LibraryPage.vue'
import SettingsPage from '@/pages/SettingsPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'dashboard', component: DashboardPage },
    { path: '/library', name: 'library', component: LibraryPage },
    { path: '/settings', name: 'settings', component: SettingsPage },
  ],
})

export default router
