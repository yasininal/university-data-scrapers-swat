<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  fetchJobData,
  fetchJobs,
  fetchRunStatus,
  getDownloadUrl,
  runJobAsync,
  type DataResponse,
  type Job,
} from '../api'

const jobs = ref<Job[]>([])
const timeoutSeconds = ref<number>(3600)
const loadingRun = ref<boolean>(false)
const loadingData = ref<boolean>(false)
const message = ref<string>('Hibe scraperlarini buradan yonetebilirsin.')
const dataMessage = ref<string>('Bir hibe kaynagi secip veriyi goster.')
const liveLog = ref<string>('')
const selectedDataJobId = ref<string>('')
const tableData = ref<DataResponse | null>(null)
const globalFilter = ref<string>('')
const columnFilterKey = ref<string>('')
const columnFilterValue = ref<string>('')

// --- Yeni filtre alanları ---
const deadlineSort = ref<string>('asc')   // 'asc' | 'desc' | ''
const budgetMin = ref<string>('')
const budgetMax = ref<string>('')

const grantJobs = computed(() => jobs.value.filter((job) => job.category === 'grants'))
const selectedDataJob = computed(() => grantJobs.value.find((job) => job.id === selectedDataJobId.value) || null)

// EU Funding artık ertelendi değil — postponedJobIds tamamen boş
const postponedJobIds = new Set<string>([])

const filterableColumns = computed(() => tableData.value?.columns || [])

const filteredRows = computed(() => {
  if (!tableData.value) {
    return [] as string[][]
  }

  const query = globalFilter.value.trim().toLowerCase()
  const colKey = columnFilterKey.value
  const colQuery = columnFilterValue.value.trim().toLowerCase()
  const colIndex = colKey ? tableData.value.columns.findIndex((col) => col === colKey) : -1

  // deadline ve budget_amount sütun indekslerini bul
  const deadlineIndex = tableData.value.columns.findIndex(
    (col) => col.toLowerCase() === 'deadline'
  )
  const budgetIndex = tableData.value.columns.findIndex(
    (col) => col.toLowerCase() === 'budget_amount'
  )

  const budgetMinVal = budgetMin.value !== '' ? parseFloat(budgetMin.value) : null
  const budgetMaxVal = budgetMax.value !== '' ? parseFloat(budgetMax.value) : null

  let rows = tableData.value.rows.filter((row) => {
    const globalOk = !query || row.some((cell) => String(cell).toLowerCase().includes(query))
    if (!globalOk) return false

    if (colQuery && colIndex >= 0) {
      if (!String(row[colIndex] || '').toLowerCase().includes(colQuery)) return false
    }

    if ((budgetMinVal !== null || budgetMaxVal !== null) && budgetIndex >= 0) {
      const rawBudget = row[budgetIndex]
      const budget = rawBudget !== null && rawBudget !== '' ? parseFloat(String(rawBudget)) : null
      if (budget === null || isNaN(budget)) {
        if (budgetMinVal !== null || budgetMaxVal !== null) return false
      } else {
        if (budgetMinVal !== null && budget < budgetMinVal) return false
        if (budgetMaxVal !== null && budget > budgetMaxVal) return false
      }
    }

    return true
  })

  // Deadline sıralaması
  if (deadlineSort.value && deadlineIndex >= 0) {
    rows = [...rows].sort((a, b) => {
      const dA = a[deadlineIndex]
      const dB = b[deadlineIndex]
      if (!dA && !dB) return 0
      if (!dA) return 1
      if (!dB) return -1
      const tA = new Date(String(dA)).getTime()
      const tB = new Date(String(dB)).getTime()
      if (isNaN(tA) && isNaN(tB)) return 0
      if (isNaN(tA)) return 1
      if (isNaN(tB)) return -1
      return deadlineSort.value === 'asc' ? tA - tB : tB - tA
    })
  }

  return rows
})

function isPostponed(job: Job): boolean {
  return postponedJobIds.has(job.id)
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function loadJobs(): Promise<void> {
  const payload = await fetchJobs()
  jobs.value = payload.jobs
  timeoutSeconds.value = payload.timeout_default || 3600
  if (!selectedDataJobId.value && grantJobs.value.length > 0) {
    selectedDataJobId.value = grantJobs.value[0].id
  }
  if (selectedDataJobId.value && !grantJobs.value.some((job) => job.id === selectedDataJobId.value)) {
    selectedDataJobId.value = grantJobs.value.length > 0 ? grantJobs.value[0].id : ''
  }
}

async function handleRun(job: Job): Promise<void> {
  if (isPostponed(job)) {
    message.value = `${job.name} su an ertelendi.`
    return
  }
  loadingRun.value = true
  message.value = `${job.name} calisiyor...`
  liveLog.value = ''
  try {
    const start = await runJobAsync(job.id, timeoutSeconds.value)
    while (true) {
      const status = await fetchRunStatus(start.run_id)
      liveLog.value = status.last_log_line || ''
      if (status.status === 'running') {
        message.value = `${job.name} calisiyor... (${Math.round(status.duration_seconds)} sn)`
        await sleep(1500)
        continue
      }
      message.value = status.success ? `${job.name} tamamlandi.` : `${job.name} hata verdi.`
      break
    }
  } catch (_error) {
    message.value = `${job.name} calistirilamadi.`
    liveLog.value = ''
  } finally {
    loadingRun.value = false
  }
}

async function loadData(jobId?: string): Promise<void> {
  if (jobId) {
    selectedDataJobId.value = jobId
  }
  if (!selectedDataJobId.value) {
    dataMessage.value = 'Once bir hibe kaynagi sec.'
    return
  }

  const selected = grantJobs.value.find((job) => job.id === selectedDataJobId.value)
  if (selected && isPostponed(selected)) {
    dataMessage.value = `${selected.name} su an ertelendi.`
    tableData.value = null
    return
  }

  loadingData.value = true
  dataMessage.value = 'Hibe verisi yukleniyor...'
  try {
    tableData.value = await fetchJobData(selectedDataJobId.value)
    if (!columnFilterKey.value && tableData.value.columns.length > 0) {
      columnFilterKey.value = tableData.value.columns[0]
    }
    dataMessage.value = `${tableData.value.row_count} satir yuklendi.`
  } catch (_error) {
    tableData.value = null
    dataMessage.value = 'Hibe verisi alinamadi. Once scraperi calistirman gerekebilir.'
  } finally {
    loadingData.value = false
  }
}

function downloadExcel(): void {
  if (!selectedDataJobId.value) {
    return
  }
  window.location.href = getDownloadUrl(selectedDataJobId.value)
}

function clearFilters(): void {
  globalFilter.value = ''
  columnFilterKey.value = ''
  columnFilterValue.value = ''
  budgetMin.value = ''
  budgetMax.value = ''
  deadlineSort.value = 'asc'
}

onMounted(async () => {
  try {
    await loadJobs()
  } catch (_error) {
    message.value = 'Hibe scraper listesi alinamadi.'
  }
})
</script>

<template>
  <section class="panel reveal">
    <div class="panel-body">
      <span class="kicker">Funding Track</span>
      <h2>Hibe Kaynaklari Operasyonu</h2>
      <p class="lede">Hibe odakli scraperlari yonet, tek tek tetikle ve tamamlanma durumunu anlik takip et.</p>

      <div class="control-row">
        <label class="field-label" for="grant-timeout">Timeout (sn)</label>
        <input id="grant-timeout" v-model.number="timeoutSeconds" class="text-input" type="number" min="30" step="30" />
      </div>

      <p class="status-line" :class="{ pending: loadingRun }">{{ message }}</p>
      <p v-if="loadingRun && liveLog" class="hint">Canli log: {{ liveLog }}</p>

      <div class="job-grid">
        <article
          v-for="(job, index) in grantJobs"
          :key="job.id"
          class="job-card"
          :style="{ animationDelay: `${index * 70}ms` }"
        >
          <h3>{{ job.name }}</h3>
          <p>{{ job.description }}</p>
          <span v-if="isPostponed(job)" class="job-meta">Durum: Ertelendi</span>
          <div class="control-row">
            <button class="btn mint" :disabled="loadingRun || isPostponed(job)" @click="handleRun(job)">Calistir</button>
            <button class="btn" :disabled="loadingData || isPostponed(job)" @click="loadData(job.id)">Veriyi Goster</button>
          </div>
        </article>
      </div>

      <div class="control-row">
        <label class="field-label" for="grant-data-job">Veri kaynagi</label>
        <select id="grant-data-job" v-model="selectedDataJobId" class="text-input">
          <option
            v-for="job in grantJobs"
            :key="`data-${job.id}`"
            :value="job.id"
            :disabled="isPostponed(job)"
          >
            {{ job.name }}{{ isPostponed(job) ? ' (Ertelendi)' : '' }}
          </option>
        </select>
        <button class="btn" :disabled="loadingData || !selectedDataJobId" @click="loadData()">Veriyi Getir</button>
        <button class="btn mint" :disabled="loadingData || !selectedDataJobId" @click="downloadExcel">Excel Indir</button>
      </div>

      <p class="status-line" :class="{ pending: loadingData }">{{ dataMessage }}</p>
      <p v-if="tableData" class="meta-line">Kaynak: {{ tableData.source_file }} | Gorunen satir: {{ filteredRows.length }} / {{ tableData.row_count }}</p>

      <div v-if="tableData" class="filter-panel">
        <!-- Satır 1: Metin filtreleri -->
        <div class="control-row">
          <label class="field-label" for="grant-filter-global">Genel arama</label>
          <input id="grant-filter-global" v-model="globalFilter" class="text-input" type="text" placeholder="Tum kolonlarda ara" />

          <label class="field-label" for="grant-filter-col">Kolon</label>
          <select id="grant-filter-col" v-model="columnFilterKey" class="text-input">
            <option value="">Seciniz</option>
            <option v-for="col in filterableColumns" :key="`filter-col-${col}`" :value="col">{{ col }}</option>
          </select>

          <input
            v-model="columnFilterValue"
            class="text-input"
            type="text"
            :placeholder="columnFilterKey ? `${columnFilterKey} icinde ara` : 'Kolon secip ara'"
          />
        </div>

        <!-- Satır 2: Deadline sıralaması + Bütçe aralığı -->
        <div class="control-row">
          <label class="field-label" for="deadline-sort">Deadline sirasi</label>
          <select id="deadline-sort" v-model="deadlineSort" class="text-input" style="max-width:200px">
            <option value="asc">Yakin → Uzak (varsayilan)</option>
            <option value="desc">Uzak → Yakin</option>
            <option value="">Siralama yok</option>
          </select>

          <label class="field-label" for="budget-min">Butce min</label>
          <input
            id="budget-min"
            v-model="budgetMin"
            class="text-input"
            type="number"
            min="0"
            step="1000"
            placeholder="0"
            style="max-width:120px"
          />

          <label class="field-label" for="budget-max">Butce max</label>
          <input
            id="budget-max"
            v-model="budgetMax"
            class="text-input"
            type="number"
            min="0"
            step="1000"
            placeholder="Sinirsiz"
            style="max-width:120px"
          />

          <button class="btn" @click="clearFilters" style="margin-left:8px">Filtreleri Temizle</button>
        </div>
      </div>

      <div v-if="tableData" class="table-shell">
        <table>
          <thead>
            <tr>
              <th v-for="col in tableData.columns" :key="col">{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in filteredRows" :key="rowIndex">
              <td v-for="(cell, cellIndex) in row" :key="`${rowIndex}-${cellIndex}`">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p v-else class="hint">
        {{ selectedDataJob ? `${selectedDataJob.name} icin veriyi yuklemek icin "Veriyi Getir"e bas.` : 'Hibe verisi icin once kaynak sec.' }}
      </p>
    </div>
  </section>
</template>
