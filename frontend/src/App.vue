<template>
  <v-app>
    <v-app-bar
      color="surface"
      elevation="1"
      title="DJ Library Pipeline"
    />
    <v-navigation-drawer
      permanent
      width="220"
    >
      <v-list
        nav
        density="compact"
      >
        <v-list-item
          v-for="item in navItems"
          :key="item.to"
          :title="item.title"
          :prepend-icon="item.icon"
          :to="item.to"
          link
        />
      </v-list>
    </v-navigation-drawer>
    <AppSnackbar />
    <v-main class="app-main">
      <v-container
        fluid
        class="app-container"
      >
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import AppSnackbar from '@/components/AppSnackbar.vue'

const navItems = [
  { title: 'Dashboard', icon: 'mdi-view-dashboard', to: '/' },
  { title: 'Library', icon: 'mdi-music-box-multiple', to: '/library' },
  { title: 'Settings', icon: 'mdi-cog', to: '/settings' },
]
</script>
