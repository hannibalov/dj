<template>
  <v-form @submit.prevent="submit">
    <v-row>
      <v-col cols="12" md="4">
        <v-text-field
          v-model.number="form.review_min_mp3_bitrate_kbps"
          label="Min MP3 bitrate (kbps)"
          type="number"
          step="32"
          min="0"
          density="compact"
          hint="MP3 below this → review/ (default 320, 0 = off)"
          persistent-hint
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          v-model.number="form.review_min_lossless_bit_depth"
          label="Min lossless bit depth"
          type="number"
          step="1"
          min="0"
          density="compact"
          hint="WAV/FLAC/AIFF below this → review/ (default 16, 0 = off)"
          persistent-hint
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          v-model.number="form.review_min_lossless_sample_rate_hz"
          label="Min lossless sample rate (Hz)"
          type="number"
          step="1000"
          min="0"
          density="compact"
          hint="Below this → review/ (default 44100, 0 = off)"
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
      Save quality gates
    </v-btn>
  </v-form>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'

const props = defineProps<{
  reviewMinMp3BitrateKbps: number
  reviewMinLosslessBitDepth: number
  reviewMinLosslessSampleRateHz: number
  loading: boolean
}>()

const emit = defineEmits<{
  submit: [
    payload: {
      review_min_mp3_bitrate_kbps: number
      review_min_lossless_bit_depth: number
      review_min_lossless_sample_rate_hz: number
    },
  ]
}>()

const form = reactive({
  review_min_mp3_bitrate_kbps: props.reviewMinMp3BitrateKbps,
  review_min_lossless_bit_depth: props.reviewMinLosslessBitDepth,
  review_min_lossless_sample_rate_hz: props.reviewMinLosslessSampleRateHz,
})

watch(
  () => props.reviewMinMp3BitrateKbps,
  (value) => {
    form.review_min_mp3_bitrate_kbps = value
  },
)

watch(
  () => props.reviewMinLosslessBitDepth,
  (value) => {
    form.review_min_lossless_bit_depth = value
  },
)

watch(
  () => props.reviewMinLosslessSampleRateHz,
  (value) => {
    form.review_min_lossless_sample_rate_hz = value
  },
)

function submit(): void {
  emit('submit', {
    review_min_mp3_bitrate_kbps: form.review_min_mp3_bitrate_kbps,
    review_min_lossless_bit_depth: form.review_min_lossless_bit_depth,
    review_min_lossless_sample_rate_hz: form.review_min_lossless_sample_rate_hz,
  })
}
</script>
