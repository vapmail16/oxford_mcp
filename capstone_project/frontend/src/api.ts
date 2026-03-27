import axios, { isAxiosError } from 'axios'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

export interface ChatResponse {
  response: string
  session_id: string
  sources?: string[]
}

/** Result of a teaching API call — includes HTTP status for classroom demos */
export interface TeachingApiResult {
  method: string
  path: string
  status: number
  body: unknown
}

function wrap(
  method: string,
  path: string,
  status: number,
  body: unknown
): TeachingApiResult {
  return { method, path, status, body }
}

export async function teachingGetPing(): Promise<TeachingApiResult> {
  const path = '/teaching/api-basics/ping'
  const res = await api.get(path)
  return wrap('GET', path, res.status, res.data)
}

export async function teachingPostEcho(message: string): Promise<TeachingApiResult> {
  const path = '/teaching/api-basics/echo'
  const res = await api.post(path, { message })
  return wrap('POST', path, res.status, res.data)
}

export async function teachingPostLlm(message: string): Promise<TeachingApiResult> {
  const path = '/teaching/api-basics/llm'
  const res = await api.post(path, { message })
  return wrap('POST', path, res.status, res.data)
}

export async function teachingPostDbMessage(
  content: string,
  userEmail: string
): Promise<TeachingApiResult> {
  const path = '/teaching/api-basics/messages'
  const res = await api.post(path, { content, user_email: userEmail })
  return wrap('POST', path, res.status, res.data)
}

export async function teachingPostNote(content: string): Promise<TeachingApiResult> {
  const path = '/teaching/api-basics/notes'
  const res = await api.post(path, { content })
  return wrap('POST', path, res.status, res.data)
}

export async function teachingGetNote(noteId: number): Promise<TeachingApiResult> {
  const path = `/teaching/api-basics/notes/${noteId}`
  const res = await api.get(path)
  return wrap('GET', path, res.status, res.data)
}

export async function teachingPutNote(noteId: number, content: string): Promise<TeachingApiResult> {
  const path = `/teaching/api-basics/notes/${noteId}`
  const res = await api.put(path, { content })
  return wrap('PUT', path, res.status, res.data)
}

export async function teachingDeleteNote(noteId: number): Promise<TeachingApiResult> {
  const path = `/teaching/api-basics/notes/${noteId}`
  const res = await api.delete(path)
  return wrap('DELETE', path, res.status, res.data ?? {})
}

export async function postTeachingTrace(
  message: string,
  userEmail: string
): Promise<TeachingApiResult> {
  const path = '/teaching/pipeline/trace'
  const res = await api.post<TeachingTracePayload>(path, { message, user_email: userEmail })
  return wrap('POST', path, res.status, res.data)
}

export function parseAxiosTeachingError(e: unknown): TeachingApiResult | null {
  if (!isAxiosError(e) || !e.response) return null
  let path = e.config?.url ? String(e.config.url) : ''
  if (path.startsWith(API_BASE)) path = path.slice(API_BASE.length)
  if (!path.startsWith('/')) path = `/${path}`
  return {
    method: (e.config?.method ?? '?').toUpperCase(),
    path: path || '?',
    status: e.response.status,
    body: e.response.data,
  }
}

/** Deterministic architecture rows from teaching API (success or 404 detail). */
export interface TeachingFlowStep {
  layer: string
  title: string
  summary: string
  detail: string
}

export function extractFlowStepsFromBody(data: unknown): TeachingFlowStep[] | undefined {
  if (!data || typeof data !== 'object') return undefined
  const o = data as Record<string, unknown>
  if (Array.isArray(o.flow_steps)) return o.flow_steps as TeachingFlowStep[]
  const d = o.detail
  if (d && typeof d === 'object') {
    const inner = d as Record<string, unknown>
    if (Array.isArray(inner.flow_steps)) return inner.flow_steps as TeachingFlowStep[]
  }
  return undefined
}

/** Teaching-only pipeline trace — not production /chat */
export interface TeachingStep {
  key: string
  layer?: string
  label: string
  status: string
  duration_ms: number
  detail: Record<string, unknown>
}

export interface TeachingTracePayload {
  run_id: string
  session_id: string
  assistant_response: string
  steps: TeachingStep[]
}
