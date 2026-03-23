<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  fetchAllJobData,
  fetchJobData,
  fetchJobs,
  getDownloadUrl,
  type DataResponse,
  type DataTableResponse,
  type Job,
} from '../api'

const jobs = ref<Job[]>([])
const selectedJobId = ref<string>('')
const tableData = ref<DataResponse | null>(null)
const allTables = ref<DataTableResponse[]>([])
const selectedTableIndex = ref<number>(0)
const loading = ref<boolean>(false)
const message = ref<string>('Scrap secip veriyi getir.')

const dataJobs = computed(() => jobs.value.filter((job) => job.category !== 'grants' && job.category !== 'sustainability'))
const selectedJob = computed(() => dataJobs.value.find((job) => job.id === selectedJobId.value) || null)
const isMultiSourceJob = computed(() => selectedJobId.value === 'rankings_shanghai_urap')
const activeMultiTable = computed(() => allTables.value[selectedTableIndex.value] || null)

async function loadJobs(): Promise<void> {
  const payload = await fetchJobs()
  jobs.value = payload.jobs
  if (!selectedJobId.value && dataJobs.value.length > 0) {
    selectedJobId.value = dataJobs.value[0].id
  }
  if (selectedJobId.value && !dataJobs.value.some((job) => job.id === selectedJobId.value)) {
    selectedJobId.value = dataJobs.value.length > 0 ? dataJobs.value[0].id : ''
  }
}

async function loadData(): Promise<void> {
  if (!selectedJobId.value) {
    message.value = 'Once bir scrap sec.'
    return
  }

  loading.value = true
  message.value = 'Veri yukleniyor...'
  try {
    if (isMultiSourceJob.value) {
      const payload = await fetchAllJobData(selectedJobId.value)
      allTables.value = payload.tables
      const firstNonEmpty = payload.tables.findIndex((table) => table.row_count > 0)
      selectedTableIndex.value = firstNonEmpty >= 0 ? firstNonEmpty : 0
      tableData.value = null
      message.value = `${payload.table_count} ayri tablo yuklendi.`
    } else {
      tableData.value = await fetchJobData(selectedJobId.value)
      allTables.value = []
      selectedTableIndex.value = 0
      message.value = `${tableData.value.row_count} satir yuklendi.`
    }
  } catch (_error) {
    tableData.value = null
    allTables.value = []
    selectedTableIndex.value = 0
    message.value = 'Veri alinamadi. Once scraperi calistirman gerekebilir.'
  } finally {
    loading.value = false
  }
}

function tableTitle(table: DataTableResponse, index: number): string {
  const source = table.source_file.split('/').pop() || table.source_file
  if (source.includes('Shanghai_ARWU')) {
    return `Shanghai (${index + 1})`
  }
  if (source.includes('URAP_Turkey')) {
    return `URAP (${index + 1})`
  }
  return source
}

function downloadExcel(): void {
  if (!selectedJobId.value) {
    return
  }
  window.location.href = getDownloadUrl(selectedJobId.value)
}

onMounted(async () => {
  try {
    await loadJobs()
  } catch (_error) {
    message.value = 'Scrap listesi alinamadi.'
  }
})
</script>

<template>
  <section class="panel reveal">
    <div class="panel-body">
      <span class="kicker">Data Viewer</span>
      <h2>Ham Cikti Kesiti</h2>
      <p class="lede">Her scraper icin tum satirlari getir, tabloda incele ve dogrudan Excel olarak disa aktar.</p>

      <div class="tab-row">
      <button
        v-for="job in dataJobs"
        :key="job.id"
        class="tab-chip"
        :class="{ active: selectedJobId === job.id }"
        @click="selectedJobId = job.id"
      >
        {{ job.name }}
      </button>
      </div>

      <div class="control-row">
        <button class="btn" :disabled="loading" @click="loadData">Veriyi Getir</button>
        <button class="btn mint" :disabled="loading || !selectedJobId" @click="downloadExcel">Excel Indir</button>
      </div>

      <p class="status-line" :class="{ pending: loading }">{{ message }}</p>

      <p v-if="isMultiSourceJob && activeMultiTable" class="meta-line">
        Kaynak: {{ activeMultiTable.source_file }} | Toplam satir: {{ activeMultiTable.row_count }}
      </p>
      <p v-else-if="tableData" class="meta-line">Kaynak: {{ tableData.source_file }} | Toplam satir: {{ tableData.row_count }}</p>

      <div v-if="isMultiSourceJob && allTables.length > 1" class="tab-row">
        <button
          v-for="(table, index) in allTables"
          :key="`${table.source_file}-${index}`"
          class="tab-chip"
          :class="{ active: selectedTableIndex === index }"
          @click="selectedTableIndex = index"
        >
          {{ tableTitle(table, index) }}
        </button>
      </div>

      <div v-if="isMultiSourceJob && activeMultiTable" class="table-shell">
        <table>
          <thead>
            <tr>
              <th v-for="col in activeMultiTable.columns" :key="col">{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in activeMultiTable.rows" :key="rowIndex">
              <td v-for="(cell, cellIndex) in row" :key="`${rowIndex}-${cellIndex}`">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="tableData" class="table-shell">
        <table>
          <thead>
            <tr>
              <th v-for="col in tableData.columns" :key="col">{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in tableData.rows" :key="rowIndex">
              <td v-for="(cell, cellIndex) in row" :key="`${rowIndex}-${cellIndex}`">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p v-else class="hint">
        {{ selectedJob ? `${selectedJob.name} icin veri yuklemek icin "Veriyi Getir" butonuna bas.` : 'Scrap secimi bekleniyor.' }}
      </p>
    </div>
  </section>
</template>
