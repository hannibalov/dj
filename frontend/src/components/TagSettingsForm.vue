<template>
  <v-form @submit.prevent="submit">
    <v-row>
      <v-col cols="12" md="6">
        <v-text-field
          v-model.number="form.tag_confidence_threshold"
          label="Auto-tag confidence threshold"
          type="number"
          min="0"
          max="1"
          step="0.05"
          density="compact"
          hint="Matches below this score go to review/"
          persistent-hint
        />
      </v-col>
      <v-col cols="12">
        <v-text-field
          v-model="form.naming_template"
          label="Library naming template"
          density="compact"
          hint="Placeholders: {title}, {artist}, {mix}, {ext}"
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
      Save tagging settings
    </v-btn>
  </v-form>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'

const props = defineProps<{
  tagConfidenceThreshold: number
  namingTemplate: string
  loading: boolean
}>()

const emit = defineEmits<{
  submit: [payload: { tag_confidence_threshold: number; naming_template: string }]
}>()

const form = reactive({
  tag_confidence_threshold: props.tagConfidenceThreshold,
  naming_template: props.namingTemplate,
})

watch(
  () => props.tagConfidenceThreshold,
  (threshold) => {
    form.tag_confidence_threshold = threshold
  },
)

watch(
  () => props.namingTemplate,
  (template) => {
    form.naming_template = template
  },
)

function submit(): void {
  emit('submit', {
    tag_confidence_threshold: form.tag_confidence_threshold,
    naming_template: form.naming_template,
  })
}
</script>
