export type Values = Record<string, string | number | boolean>
export interface Parameter {
  key: string
  label: string
  type: 'text' | 'number' | 'boolean' | 'enum' | 'file' | 'directory'
  description?: string
  required?: boolean
  secret?: boolean
  default?: string | number | boolean
  minimum?: number
  maximum?: number
  options?: string[]
}
export interface Flow {
  id: string
  name: string
  description: string
  version: string
  author: string
  dry_run: 'simulation' | 'preview' | 'unsupported'
  parameters: Parameter[]
  capabilities: string[]
}
export interface Run {
  id: string
  flow_id: string
  name: string
  version: string
  dry_run: boolean
  status: string
  progress: number
  started_at: string
  finished_at: string | null
  summary: string
  error: string
  config: Values
  files: string[]
  logs: { at: string; level: string; message: string }[]
}
let token = ''
export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'X-AWM-Token': token }
  if (body !== undefined && !(body instanceof FormData))
    headers['Content-Type'] = 'application/json'
  const response = await fetch(`/api${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
  })
  const result = await response.json()
  if (!response.ok) throw new Error(result.error || '请求失败')
  return result as T
}
export async function bootstrap() {
  const info = await api<{ token: string; version: string; data_dir: string }>('/bootstrap')
  token = info.token
  return info
}
export const fileUrl = (id: string, file: string) =>
  `/api/runs/${id}/files/${file.split('/').map(encodeURIComponent).join('/')}`
