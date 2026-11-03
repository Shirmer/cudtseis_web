import type { QuakeEvent } from './quake-layer'

export interface QuakeFeed {
  source?: string
  updated?: string
  events: QuakeEvent[]
}

function normalize(item: unknown): QuakeEvent | null {
  if (!item || typeof item !== 'object') return null
  const record = item as Record<string, unknown>
  const lat = Number(record.lat)
  const lon = Number(record.lon)
  const magnitude = Number(record.magnitude)
  const time = typeof record.time === 'string' ? record.time : ''
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || !Number.isFinite(magnitude) || !time) return null
  return {
    lat,
    lon,
    magnitude,
    time,
    place: typeof record.place === 'string' && record.place ? record.place : `${lat.toFixed(1)}°, ${lon.toFixed(1)}°`
  }
}

/**
 * 读取外置地震目录（public/data/earthquakes.json）。
 * 兼容两种写法：直接给数组，或 `{ events: [...] }`。
 * 单条解析失败会被跳过，不会因为一条脏数据整层挂掉。
 */
export async function loadQuakeFeed(url: string): Promise<QuakeFeed> {
  const response = await fetch(url, { cache: 'no-cache' })
  if (!response.ok) throw new Error(`quake feed HTTP ${response.status}`)
  const json: unknown = await response.json()
  const raw = Array.isArray(json) ? json : (json as { events?: unknown } | null)?.events
  if (!Array.isArray(raw)) throw new Error('quake feed: missing events[]')
  const events = raw.map(normalize).filter((event): event is QuakeEvent => event !== null)
  if (!events.length) throw new Error('quake feed: no valid events')
  const meta = Array.isArray(json) ? {} : (json as Record<string, unknown>)
  return {
    events,
    source: typeof meta.source === 'string' ? meta.source : undefined,
    updated: typeof meta.updated === 'string' ? meta.updated : undefined
  }
}
