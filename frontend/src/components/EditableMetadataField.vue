<script setup lang="ts">
defineProps<{ modelValue: string; placeholder: string; disabled: boolean }>()
defineEmits<{ 'update:modelValue': [value: string]; blur: []; enter: [] }>()
</script>

<template>
  <v-text-field
    :model-value="modelValue"
    density="compact"
    variant="plain"
    hide-details
    :placeholder="placeholder"
    class="metadata-field"
    :disabled="disabled"
    @update:model-value="(v) => $emit('update:modelValue', v)"
    @blur="$emit('blur')"
    @keyup.enter="($event.target as HTMLInputElement)?.blur()"
  />
</template>

<style scoped>
.metadata-field {
  min-width: 120px;
  max-width: 220px;
}

.metadata-field :deep(.v-field__input) {
  padding-top: 0;
  padding-bottom: 0;
  min-height: 28px;
}
</style>
