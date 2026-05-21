<template>
  <v-form @submit.prevent="submit">
    <v-row>
      <v-col cols="12" md="6">
        <v-text-field
          v-model.number="form.review_lufs_threshold"
          label="Review LUFS threshold"
          type="number"
          step="0.5"
          density="compact"
          hint="Integrated LUFS below this → review/ (default -18)"
          persistent-hint
        />
      </v-col>
      <v-col cols="12" md="6">
        <v-text-field
          v-model.number="form.review_true_peak_db"
          label="Review true peak (dBTP)"
          type="number"
          step="0.1"
          density="compact"
          hint="True peak above this → review/ (default 3.0; MP3 inter-sample peaks are normal below ~3)"
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
      Save loudness gates
    </v-btn>
  </v-form>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'

const props = defineProps<{
  reviewLufsThreshold: number
  reviewTruePeakDb: number
  loading: boolean
}>()

const emit = defineEmits<{
  submit: [payload: { review_lufs_threshold: number; review_true_peak_db: number }]
}>()

const form = reactive({
  review_lufs_threshold: props.reviewLufsThreshold,
  review_true_peak_db: props.reviewTruePeakDb,
})

watch(
  () => props.reviewLufsThreshold,
  (value) => {
    form.review_lufs_threshold = value
  },
)

watch(
  () => props.reviewTruePeakDb,
  (value) => {
    form.review_true_peak_db = value
  },
)

function submit(): void {
  emit('submit', {
    review_lufs_threshold: form.review_lufs_threshold,
    review_true_peak_db: form.review_true_peak_db,
  })
}
</script>
