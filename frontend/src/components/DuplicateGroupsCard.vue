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
                  <th>Artist / title</th>
                  <th>Format</th>
                  <th>LUFS</th>
                  <th>Status</th>
                  <th class="text-end">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="member in group.members"
                  :key="member.track_id"
                >
                  <td>{{ basename(member.source_path) }}</td>
                  <td>{{ metadataLabel(member) }}</td>
                  <td>{{ formatLabel(member) }}</td>
                  <td>{{ lufsLabel(member) }}</td>
                  <td>
                    <v-chip
                      size="x-small"
                      :color="trackStatusColor(member.status)"
                    >
                      {{ trackStatusLabel(member.status) }}
                    </v-chip>
                  </td>
                  <td class="text-end">
                    <v-btn
                      size="small"
                      color="primary"
                      variant="tonal"
                      :disabled="resolving"
                      @click="openKeepDialog(group, member)"
                    >
                      Keep
                    </v-btn>
                  </td>
                </tr>
              </tbody>
            </v-table>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>

    <v-dialog
      v-model="dialogOpen"
      max-width="440"
    >
      <v-card>
        <v-card-title>Keep this copy?</v-card-title>
        <v-card-text>
          <p class="text-body-2 mb-3">
            <strong>{{ pendingBasename }}</strong>
            will be promoted through tagging and routing.
          </p>
          <v-checkbox
            v-model="archiveOthers"
            label="Archive all other copies in this group"
            hide-details
            density="compact"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            :disabled="resolving"
            @click="dialogOpen = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            :loading="resolving"
            @click="confirmKeep"
          >
            Confirm
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchDuplicateGroups, resolveDuplicateGroup } from '@/services/duplicateService'
import type { DuplicateGroup, DuplicateGroupMember } from '@/types/duplicate'
import { basename, trackStatusColor, trackStatusLabel } from '@/utils/labels'

import { usePipelineStore } from '@/stores/pipelineStore'
import { useSnackbarStore } from '@/stores/snackbarStore'

const pipeline = usePipelineStore()
const snackbar = useSnackbarStore()
const groups = ref<DuplicateGroup[]>([])
const loading = ref(false)
const resolving = ref(false)
const dialogOpen = ref(false)
const archiveOthers = ref(true)
const pendingGroup = ref<DuplicateGroup | null>(null)
const pendingMember = ref<DuplicateGroupMember | null>(null)

const pendingBasename = computed(() =>
  pendingMember.value ? basename(pendingMember.value.source_path) : '',
)

function formatLabel(member: DuplicateGroupMember): string {
  const ext = member.format_extension?.replace('.', '').toUpperCase() ?? '—'
  if (member.bitrate_kbps != null) {
    return `${ext} ${member.bitrate_kbps}k`
  }
  return ext
}

function metadataLabel(member: DuplicateGroupMember): string {
  if (member.artist && member.title) {
    return `${member.artist} — ${member.title}`
  }
  return member.title ?? member.artist ?? '—'
}

function lufsLabel(member: DuplicateGroupMember): string {
  if (member.integrated_lufs == null) {
    return '—'
  }
  return `${member.integrated_lufs.toFixed(1)} LUFS`
}

function groupTitle(group: DuplicateGroup): string {
  const short = group.fingerprint_hash.slice(0, 12)
  return `${group.members.length} tracks · ${short}…`
}

function openKeepDialog(group: DuplicateGroup, member: DuplicateGroupMember): void {
  pendingGroup.value = group
  pendingMember.value = member
  archiveOthers.value = true
  dialogOpen.value = true
}

async function confirmKeep(): Promise<void> {
  const group = pendingGroup.value
  const member = pendingMember.value
  if (!group || !member) {
    return
  }

  const archiveTrackIds = archiveOthers.value
    ? group.members
        .filter((m) => m.track_id !== member.track_id)
        .map((m) => m.track_id)
    : []

  resolving.value = true
  try {
    const result = await resolveDuplicateGroup({
      group_id: group.id,
      keep_track_id: member.track_id,
      archive_track_ids: archiveTrackIds,
    })
    dialogOpen.value = false
    const archived = result.archived_track_ids.length
    snackbar.show(
      archived > 0
        ? `Kept ${basename(member.source_path)}; archived ${archived} other(s)`
        : `Kept ${basename(member.source_path)}`,
      { color: 'success' },
    )
    await load()
    await pipeline.load()
  } catch (e) {
    snackbar.show(e instanceof Error ? e.message : 'Failed to resolve duplicate', {
      color: 'error',
    })
  } finally {
    resolving.value = false
  }
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
