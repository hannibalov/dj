<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <span>Duplicate groups</span>
      <v-spacer />
      <v-btn
        size="small"
        variant="text"
        :loading="loading"
        @click="load()"
      >
        Refresh
      </v-btn>
    </v-card-title>
    <v-card-text>
      <v-skeleton-loader
        v-if="loading && groups.length === 0"
        type="list-item@3"
      />
      <p
        v-else-if="groups.length === 0"
        class="text-medium-emphasis text-body-2"
      >
        No duplicate groups yet. Identical fingerprints are grouped after analysis.
      </p>
      <v-expansion-panels
        v-else
        variant="accordion"
      >
        <v-expansion-panel
          v-for="group in groups"
          :key="group.id"
          :title="groupTitle(group)"
        >
          <v-expansion-panel-text>
            <v-table density="compact">
              <thead>
                <tr>
                  <th>File</th>
                  <th>Format</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="member in group.members"
                  :key="member.track_id"
                >
                  <td>{{ basename(member.source_path) }}</td>
                  <td>{{ formatLabel(member) }}</td>
                  <td>
                    <v-chip
                      size="x-small"
                      :color="trackStatusColor(member.status)"
                    >
                      {{ trackStatusLabel(member.status) }}
                    </v-chip>
                  </td>
                </tr>
              </tbody>
            </v-table>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchDuplicateGroups } from '@/services/duplicateService'
import type { DuplicateGroup, DuplicateGroupMember } from '@/types/duplicate'
import { trackStatusColor, trackStatusLabel } from '@/utils/labels'

import { useSnackbarStore } from '@/stores/snackbarStore'

const snackbar = useSnackbarStore()
const groups = ref<DuplicateGroup[]>([])
const loading = ref(false)

function basename(path: string): string {
  const parts = path.split(/[/\\]/)
  return parts[parts.length - 1] ?? path
}

function formatLabel(member: DuplicateGroupMember): string {
  const ext = member.format_extension?.replace('.', '').toUpperCase() ?? '—'
  if (member.bitrate_kbps != null) {
    return `${ext} ${member.bitrate_kbps}k`
  }
  return ext
}

function groupTitle(group: DuplicateGroup): string {
  const short = group.fingerprint_hash.slice(0, 12)
  return `${group.members.length} tracks · ${short}…`
}

async function load(): Promise<void> {
  loading.value = true
  try {
    groups.value = await fetchDuplicateGroups()
  } catch (e) {
    snackbar.show(e instanceof Error ? e.message : 'Failed to load duplicates', {
      color: 'error',
    })
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})

defineExpose({ load })
</script>
