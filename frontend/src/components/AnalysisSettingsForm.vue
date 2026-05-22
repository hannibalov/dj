<template>
  <v-form @submit.prevent="submit">
    <v-row>
      <v-col cols="12" md="6">
        <v-select
          v-model="form.key_notation"
          label="Key notation"
          :items="notationItems"
          density="compact"
          hint="How keys appear in the tracks table"
          persistent-hint
        />
      </v-col>
    </v-row>
    <v-btn
      type="submit"
      color="primary"
      class="mt-4"
      :loading="loading"
    >
      Save analysis display settings
    </v-btn>
  </v-form>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'

import type { KeyNotation } from '@/types/settings'

const notationItems = [
  { title: 'Camelot (8A, 4B, …)', value: 'camelot' as const },
  { title: 'Traditional (A minor, C major, …)', value: 'traditional' as const },
]

const props = defineProps<{
  keyNotation: KeyNotation
  loading: boolean
}>()

const emit = defineEmits<{
  submit: [payload: { key_notation: KeyNotation }]
}>()

const form = reactive({
  key_notation: props.keyNotation,
})

watch(
  () => props.keyNotation,
  (notation) => {
    form.key_notation = notation
  },
)

function submit(): void {
  emit('submit', { key_notation: form.key_notation })
}
</script>
