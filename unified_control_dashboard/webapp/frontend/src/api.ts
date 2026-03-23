import axios from 'axios'

export interface Job {
  id: string
  name: string
  category: string
  description: string
  command: string[]
  expected_outputs: string[]
  dependencies: string[]
}

export interface JobsResponse {
  jobs: Job[]
  timeout_default: number
}

export interface DataResponse {
  job_id: string
  job_name: string
  source_file: string
  source_name: string
  columns: string[]
  rows: string[][]
  row_count: number
}

export interface DataTableResponse {
  source_file: string
  source_name: string
  columns: string[]
  rows: string[][]
  row_count: number
}

export interface MultiDataResponse {
  job_id: string
  job_name: string
  table_count: number
  tables: DataTableResponse[]
}

export interface RunStartResponse {
  run_id: string
  job_id: string
  job_name: string
  status: string
}

export interface RunStatusResponse {
  run_id: string
  job_id: string
  job_name: string
  status: 'running' | 'completed' | 'failed'
  success: boolean | null
  exit_code: number | null
  started_at: string
  finished_at: string | null
  duration_seconds: number
  log_lines: string[]
  last_log_line: string
  updated_at: string
  error: string | null
  result: { success: boolean; job_name: string } | null
}

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

export async function fetchJobs(): Promise<JobsResponse> {
  const response = await api.get('/jobs')
  return response.data as JobsResponse
}

export async function runJob(jobId: string, timeoutSeconds: number): Promise<{ success: boolean; job_name: string }> {
  const response = await api.post(`/run/${jobId}?timeout_seconds=${timeoutSeconds}`)
  return response.data as { success: boolean; job_name: string }
}

export async function runJobAsync(jobId: string, timeoutSeconds: number): Promise<RunStartResponse> {
  const response = await api.post(`/run-async/${jobId}?timeout_seconds=${timeoutSeconds}`)
  return response.data as RunStartResponse
}

export async function fetchRunStatus(runId: string): Promise<RunStatusResponse> {
  const response = await api.get(`/run-status/${runId}`)
  return response.data as RunStatusResponse
}

export async function fetchJobData(jobId: string): Promise<DataResponse> {
  const response = await api.get(`/data/${jobId}`)
  return response.data as DataResponse
}

export async function fetchAllJobData(jobId: string): Promise<MultiDataResponse> {
  const response = await api.get(`/data/${jobId}/all`)
  return response.data as MultiDataResponse
}

export function getDownloadUrl(jobId: string): string {
  return `/api/data/${jobId}/download.xlsx`
}
