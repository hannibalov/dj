<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <span>Same song groups</span>
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
        No same-song groups yet. Tracks with matching metadata but different audio
        fingerprints appear here after tagging or a metadata edit.
      </p>
      <v-expansion-panels
        v-else
        variant="accordion"
      >
        <v-expansion-panel
          v-for="group in groups"
          :key="group.group_key"
          :title="groupTitle(group)"
        >
          <v-expansion-panel-text>
            <p class="text-caption text-medium-emphasis mb-3">
              Matched by {{ group.match_type === 'musicbrainz' ? 'MusicBrainz recording' : 'artist, title, and mix' }}.
              Compare quality and choose which copy to keep — nothing is deleted automatically.
            </p>
            <v-table density="compact">
              <thead>
                <tr>
                  <th>File</th>
                  <th>Format</th>
                  <th>LUFS</th>
                  <th>Energy</th>
                  <th>BPM / Key</th>
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
                  :class="{ 'bg-surface-variant': member.track_id === group.suggested_keep_track_id }"
                >
                  <td>
                    {{ basename(member.source_path) }}
                    <v-chip
                      v-if="member.track_id === group.suggested_keep_track_id"
                      size="x-small"
                      color="success"
                      class="ml-1"
                    >
                      Suggested
                    </v-chip>
                  </td>
                  <td>{{ formatLabel(member) }}</td>
                  <td>{{ lufsLabel(member) }}</td>
                  <td>{{ member.energy ?? '—' }}</td>
                  <td>{{ bpmKeyLabel(member) }}</td>
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
            will be kept. Other copies in this group can be moved to archive — files are never auto-deleted.
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

import { fetchSongDuplicateGroups, resolveSongDuplicateGroup } from '@/services/duplicateService'
import type { SongDuplicateGroup, SongDuplicateGroupMember } from '@/types/songDuplicate'
import { basename, trackStatusColor, trackStatusLabel } from '@/utils/labels'

import { usePipelineStore } from '@/stores/pipelineStore'
import { useSnackbarStore } from '@/stores/snackbarStore'

const pipeline = usePipelineStore()
const snackbar = useSnackbarStore()
const groups = ref<SongDuplicateGroup[]>([])
const loading = ref(false)
const resolving = ref(false)
const dialogOpen = ref(false)
const archiveOthers = ref(true)
const pendingGroup = ref<SongDuplicateGroup | null>(null)
const pendingMember = ref<SongDuplicateGroupMember | null>(null)

const pendingBasename = computed(() =>
  pendingMember.value ? basename(pendingMember.value.source_path) : '',
)

function formatLabel(member: SongDuplicateGroupMember): string {
  const ext = member.format_extension?.replace('.', '').toUpperCase() ?? '—'
  if (member.bitrate_kbps != null) {
    return `${ext} ${member.bitrate_kbps}k`
  }
  return ext
}

function lufsLabel(member: SongDuplicateGroupMember): string {
  if (member.integrated_lufs == null) {
    return '—'
  }
  return `${member.integrated_lufs.toFixed(1)} LUFS`
}

function bpmKeyLabel(member: SongDuplicateGroupMember): string {
  const bpm = member.bpm != null ? member.bpm.toFixed(1) : null
  const key = member.camelot
  if (bpm && key) {
    return `${bpm} · ${key}`
  }
  return bpm ?? key ?? '—'
}

function groupTitle(group: SongDuplicateGroup): string {
  return `${group.members.length} copies · ${group.label}`
}

function openKeepDialog(group: SongDuplicateGroup, member: SongDuplicateGroupMember): void {
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
    const result = await resolveSongDuplicateGroup({
      group_key: group.group_key,
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
    snackbar.show(e instanceof Error ? e.message : 'Failed to resolve same-song group', {
      color: 'error',
    })
  } finally {
    resolving.value = false
  }
}

async function load(): Promise<void> {
  loading.value = true
  try {
    groups.value = await fetchSongDuplicateGroups()
  } catch (e) {
    snackbar.show(e instanceof Error ? e.message : 'Failed to load same-song groups', {
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
