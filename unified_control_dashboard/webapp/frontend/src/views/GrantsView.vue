<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchJobs, fetchRunStatus, runJobAsync, type Job } from '../api'

const jobs = ref<Job[]>([])
const timeoutSeconds = ref<number>(3600)
const loading = ref<boolean>(false)
const message = ref<string>('Hibe scraperlarini buradan yonetebilirsin.')
const liveLog = ref<string>('')

const grantJobs = computed(() => jobs.value.filter((job) => job.category === 'grants'))

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

      message.value = status.success ? `${job.name} tamamlandi.` : `${job.name} hata verdi.`
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

      <p class="status-line" :class="{ pending: loading }">{{ message }}</p>
      <p v-if="loading && liveLog" class="hint">Canli log: {{ liveLog }}</p>

      <div class="job-grid">
        <article
          v-for="(job, index) in grantJobs"
          :key="job.id"
          class="job-card"
          :style="{ animationDelay: `${index * 70}ms` }"
        >
          <h3>{{ job.name }}</h3>
          <p>{{ job.description }}</p>
          <button class="btn mint" :disabled="loading" @click="handleRun(job)">Calistir</button>
        </article>
      </div>
    </div>
  </section>
</template>
