<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchJobs, fetchRunStatus, runJobAsync, type Job } from '../api'

const jobs = ref<Job[]>([])
const timeoutSeconds = ref<number>(3600)
const loading = ref<boolean>(false)
const message = ref<string>('')
const liveLog = ref<string>('')
const homeJobs = computed(() => jobs.value.filter((job) => job.category !== 'grants' && job.category !== 'sustainability'))

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function loadJobs(): Promise<void> {
  loading.value = true
  try {
    const payload = await fetchJobs()
    jobs.value = payload.jobs
    timeoutSeconds.value = payload.timeout_default || 3600
    message.value = 'Scraper listesi hazir.'
  } catch (_error) {
    message.value = 'Scraper listesi alinamadi.'
  } finally {
    loading.value = false
  }
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

      message.value = status.success ? `${job.name} basariyla tamamlandi.` : `${job.name} hata verdi.`
      break
    }
  } catch (_error) {
    message.value = `${job.name} calistirilamadi.`
    liveLog.value = ''
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadJobs()
})
</script>

<template>
  <section class="panel reveal">
    <div class="panel-body">
      <span class="kicker">Core Scrapers</span>
      <h2>Merkezi Is Akisi Kontrolu</h2>
      <p class="lede">Tum ana scraperlari tek panelden tetikle. Timeout suresini ayarla ve ciktilari sirayla takip et.</p>

      <div class="control-row">
        <label class="field-label" for="home-timeout">Timeout (sn)</label>
        <input id="home-timeout" v-model.number="timeoutSeconds" class="text-input" type="number" min="30" step="30" />
        <button class="btn" :disabled="loading" @click="loadJobs">Listeyi Yenile</button>
      </div>

      <p class="status-line" :class="{ pending: loading }">{{ message }}</p>
      <p v-if="loading && liveLog" class="hint">Canli log: {{ liveLog }}</p>

      <div class="job-grid">
        <article
          v-for="(job, index) in homeJobs"
          :key="job.id"
          class="job-card"
          :style="{ animationDelay: `${index * 70}ms` }"
        >
          <h3>{{ job.name }}</h3>
          <p>{{ job.description }}</p>
          <span class="job-meta">Kategori: {{ job.category }}</span>
          <button class="btn mint" :disabled="loading" @click="handleRun(job)">Calistir</button>
        </article>
      </div>
    </div>
  </section>
</template>
