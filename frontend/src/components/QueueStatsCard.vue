<template>
  <v-card>
    <v-card-title>Queue</v-card-title>
    <v-card-text>
      <v-skeleton-loader
        v-if="loading"
        type="list-item@4"
      />
      <v-list
        v-else
        density="compact"
      >
        <v-list-item
          title="Pending"
          :subtitle="String(pending)"
        />
        <v-list-item
          title="Running"
          :subtitle="String(running)"
        />
        <v-list-item
          title="Completed"
          :subtitle="String(completed)"
        />
        <v-list-item
          title="Failed"
          :subtitle="String(failed)"
        />
      </v-list>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
defineProps<{
  pending: number
  running: number
  completed: number
  failed: number
  loading: boolean
}>()
</script>
