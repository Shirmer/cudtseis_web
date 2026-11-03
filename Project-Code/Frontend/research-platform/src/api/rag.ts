const RAG_API_BASE = '/rag-api/api/v1'
const RAG_ADMIN_BASE = '/rag-api/api/v1/admin'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`)
  }
  return res.json()
}

export interface KnowledgeBase {
  kb_id: string
  name: string
  description: string
}

export async function listKnowledgeBases(): Promise<{ items: KnowledgeBase[] }> {
  return request(`${RAG_API_BASE}/knowledge-bases`)
}

export async function getKnowledgeBase(kbId: string): Promise<{ kb_id: string; status: string }> {
  return request(`${RAG_API_BASE}/knowledge-bases/${kbId}`)
}

export interface Document {
  document_id: string
  kb_id: string
  filename: string
  file_path: string
  status: string
  created_at: string
}

export async function listDocuments(kbId: string): Promise<{ kb_id: string; items: Document[] }> {
  return request(`${RAG_API_BASE}/knowledge-bases/${kbId}/documents`)
}

export async function uploadDocument(kbId: string, file: File): Promise<Document> {
  const form = new FormData()
  form.append('file', file)
  return request(`${RAG_API_BASE}/knowledge-bases/${kbId}/documents`, {
    method: 'POST',
    body: form,
  })
}

export async function deleteDocument(documentId: string): Promise<{ status: string }> {
  return request(`${RAG_API_BASE}/documents/${documentId}`, { method: 'DELETE' })
}

export async function getDocumentDetail(documentId: string): Promise<Document> {
  return request(`${RAG_API_BASE}/documents/${documentId}`)
}

export interface BatchCloudIngestItem {
  document_id: string
  task_id: string
  file_path: string
  filename: string
}

export async function batchCloudIngest(
  kbId: string,
  files: File[],
  options?: { model_version?: string; enable_formula?: boolean; enable_table?: boolean; is_ocr?: boolean; language?: string }
): Promise<{ kb_id: string; status: string; items: BatchCloudIngestItem[] }> {
  const form = new FormData()
  for (const f of files) form.append('files', f)
  if (options?.model_version) form.append('model_version', options.model_version)
  if (options?.enable_formula !== undefined) form.append('enable_formula', String(options.enable_formula))
  if (options?.enable_table !== undefined) form.append('enable_table', String(options.enable_table))
  if (options?.is_ocr !== undefined) form.append('is_ocr', String(options.is_ocr))
  if (options?.language) form.append('language', options.language)
  return request(`${RAG_API_BASE}/knowledge-bases/${kbId}/documents/batch-cloud-ingest`, {
    method: 'POST',
    body: form,
  })
}

export async function ingestDocument(documentId: string): Promise<{ task_id: string; document_id: string; status: string }> {
  return request(`${RAG_API_BASE}/documents/${documentId}/ingest`, { method: 'POST' })
}

export interface Task {
  task_id: string
  document_id: string
  kb_id: string
  status: string
  message: string
  created_at: string
  updated_at: string
}

export async function getTask(taskId: string): Promise<Task> {
  return request(`${RAG_API_BASE}/tasks/${taskId}`)
}

export interface ChatRequest {
  question: string
  mode?: string
  vlm_enhanced?: boolean
  enable_rerank?: boolean
}

export interface ChatResponse {
  kb_id: string
  question: string
  answer: string
  mode: string
  vlm_enhanced: boolean
  enable_rerank: boolean
}

export async function chat(
  kbId: string,
  req: ChatRequest
): Promise<ChatResponse> {
  return request(`${RAG_API_BASE}/knowledge-bases/${kbId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
}

export interface ServerFile {
  filename: string
  file_path: string
  size_bytes: number
  sha256: string | null
  is_duplicate: boolean
  reason: string | null
}

export async function listServerFiles(
  dir: string,
  kbId: string = 'default'
): Promise<{ items: ServerFile[] }> {
  return request(`${RAG_ADMIN_BASE}/server-files?dir=${encodeURIComponent(dir)}&kb_id=${kbId}`)
}

export interface KBStats {
  kb_id: string
  total_documents: number
  indexed: number
  failed: number
  waiting_parser: number
  processing: number
  uploaded: number
  total_entities: number
  total_relations: number
}

export async function getKBStats(kbId: string): Promise<KBStats> {
  return request(`${RAG_API_BASE}/knowledge-bases/${kbId}/stats`)
}
