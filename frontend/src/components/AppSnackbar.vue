<template>
  <v-snackbar
    :key="snackbar.message"
    v-model="snackbar.visible"
    :color="snackbar.color"
    :timeout="snackbar.timeout"
    location="bottom end"
    multi-line
  >
    {{ snackbar.message }}
    <template #actions>
      <v-btn
        variant="text"
        icon="mdi-close"
        :aria-label="'Dismiss'"
        @click="snackbar.close()"
      />
    </template>
  </v-snackbar>
</template>

<script setup lang="ts">
import { useSnackbarStore } from '@/stores/snackbarStore'

const snackbar = useSnackbarStore()
</script>
