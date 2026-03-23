<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchJobData, fetchJobs, fetchRunStatus, getDownloadUrl, runJobAsync, type DataResponse, type Job } from '../api'

const jobs = ref<Job[]>([])
const timeoutSeconds = ref<number>(3600)
const loading = ref<boolean>(false)
const message = ref<string>('ITU surdurulebilirlik scraperini buradan yonetebilirsin.')
const resultData = ref<DataResponse | null>(null)
const liveLog = ref<string>('')

const ituJobs = computed(() => jobs.value.filter((job) => job.id === 'sustainability_itu_news' || job.category === 'sustainability'))
const ituJob = computed(() => ituJobs.value.length > 0 ? ituJobs.value[0] : null)

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function loadJobs(): Promise<void> {
  const payload = await fetchJobs()
  jobs.value = payload.jobs
  timeoutSeconds.value = payload.timeout_default || 3600
}

async function handleRun(job: Job): Promise<void> {
  loading.value = true
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

      message.value = status.success ? `${job.name} tamamlandi. Sonuclari guncelleyebilirsin.` : `${job.name} hata verdi.`
      break
    }
  } catch (_error) {
    message.value = `${job.name} calistirilamadi.`
    liveLog.value = ''
  } finally {
    loading.value = false
  }
}

async function loadResults(): Promise<void> {
  if (!ituJob.value) {
    message.value = 'ITU scraper kaydi bulunamadi.'
    return
  }

  loading.value = true
  message.value = 'ITU sonuclari yukleniyor...'
  try {
    resultData.value = await fetchJobData(ituJob.value.id)
    message.value = `${resultData.value.row_count} satir yuklendi.`
  } catch (_error) {
    resultData.value = null
    message.value = 'Sonuc verisi alinamadi. Once scraperi calistir.'
  } finally {
    loading.value = false
  }
}

function downloadExcel(): void {
  if (!ituJob.value) {
    return
  }
  window.location.href = getDownloadUrl(ituJob.value.id)
}

onMounted(async () => {
  try {
    await loadJobs()
  } catch (_error) {
    message.value = 'ITU scraper listesi alinamadi.'
  }
})
</script>

<template>
  <section class="panel reveal">
    <div class="panel-body">
      <span class="kicker">Sustainability Feed</span>
      <h2>ITU Haber Takip Katmani</h2>
      <p class="lede">ITU surdurulebilirlik haberlerini tek bir akis halinde topla, kontrol et ve disa aktar.</p>

      <div class="control-row">
        <label class="field-label" for="itu-timeout">Timeout (sn)</label>
        <input id="itu-timeout" v-model.number="timeoutSeconds" class="text-input" type="number" min="30" step="30" />
        <button class="btn ghost" :disabled="loading || !ituJob" @click="loadResults">Sonuclari Getir</button>
        <button class="btn mint" :disabled="loading || !ituJob" @click="downloadExcel">Excel Indir</button>
      </div>

      <p class="status-line" :class="{ pending: loading }">{{ message }}</p>
      <p v-if="loading && liveLog" class="hint">Canli log: {{ liveLog }}</p>

      <div class="job-grid">
        <article
          v-for="(job, index) in ituJobs"
          :key="job.id"
          class="job-card"
          :style="{ animationDelay: `${index * 70}ms` }"
        >
          <h3>{{ job.name }}</h3>
          <p>{{ job.description }}</p>
          <button class="btn" :disabled="loading" @click="handleRun(job)">Calistir</button>
        </article>
      </div>

      <p v-if="resultData" class="meta-line">Kaynak: {{ resultData.source_file }} | Toplam satir: {{ resultData.row_count }}</p>

      <div v-if="resultData" class="table-shell">
        <table>
          <thead>
            <tr>
              <th v-for="col in resultData.columns" :key="col">{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in resultData.rows" :key="rowIndex">
              <td v-for="(cell, cellIndex) in row" :key="`${rowIndex}-${cellIndex}`">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
