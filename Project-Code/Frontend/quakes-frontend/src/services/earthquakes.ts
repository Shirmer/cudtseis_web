import { apiPath } from '../config/api'

export type EarthquakeEvent = {
  id: string
  time: string
  updated?: string
  mag: number
  place: string
  depth_km: number | null
  lon: number
  lat: number
  magType?: string | null
  nst?: number | null
  gap?: number | null
  dmin?: number | null
  rms?: number | null
  net?: string | null
  type?: string | null
  horizontalError?: number | null
  depthError?: number | null
  magError?: number | null
  magNst?: number | null
  status?: string | null
  locationSource?: string | null
  magSource?: string | null
  url?: string | null
}

export type CatalogQuery = {
  hours?: number
  start?: string
  end?: string
  minMag: number
  maxMag?: number | null
  minDepth?: number | null
  maxDepth?: number | null
  minLon?: number | null
  maxLon?: number | null
  minLat?: number | null
  maxLat?: number | null
  bbox?: string | null
  limit?: number
}

export type CatalogSource = 'backend' | 'usgs'

export type CatalogResult = {
  events: EarthquakeEvent[]
  source: CatalogSource
  fetchedAt: string
}

const USGS_QUERY_URL = 'https://earthquake.usgs.gov/fdsnws/event/1/query'

function finiteNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function textValue(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim() : null
}

function normalizePlaceName(value: unknown) {
  const place = textValue(value) ?? 'Unknown region'
  if (/^Taiwan region$/i.test(place)) return 'Taiwan region, China'
  if (/^Taiwan$/i.test(place)) return 'Taiwan, China'
  return place.replace(/,\s*Taiwan\b(?!\s*,?\s*China)/gi, ', Taiwan, China')
}

export function localizedPlaceName(place: string, locale: 'zh' | 'en') {
  if (locale === 'en') return place
  return place
    .replace(/Taiwan region, China/gi, '中国台湾地区')
    .replace(/Taiwan, China/gi, '中国台湾地区')
}

export function normalizeEvent(raw: Record<string, unknown>): EarthquakeEvent | null {
  const id = textValue(raw.id)
  const time = textValue(raw.time)
  const mag = finiteNumber(raw.mag)
  const lon = finiteNumber(raw.lon)
  const lat = finiteNumber(raw.lat)

  if (!id || !time || mag === null || lon === null || lat === null) return null

  return {
    id,
    time,
    updated: textValue(raw.updated) ?? undefined,
    mag,
    place: normalizePlaceName(raw.place),
    depth_km: finiteNumber(raw.depth_km),
    lon,
    lat,
    magType: textValue(raw.magType ?? raw.mag_type),
    nst: finiteNumber(raw.nst),
    gap: finiteNumber(raw.gap),
    dmin: finiteNumber(raw.dmin),
    rms: finiteNumber(raw.rms),
    net: textValue(raw.net),
    type: textValue(raw.type),
    horizontalError: finiteNumber(raw.horizontalError),
    depthError: finiteNumber(raw.depthError),
    magError: finiteNumber(raw.magError),
    magNst: finiteNumber(raw.magNst),
    status: textValue(raw.status),
    locationSource: textValue(raw.locationSource),
    magSource: textValue(raw.magSource),
    url: textValue(raw.url),
  }
}

function normalizeBackendPayload(payload: unknown): EarthquakeEvent[] {
  if (!Array.isArray(payload)) throw new Error('Invalid catalog response')
  return payload
    .map((item) => normalizeEvent((item ?? {}) as Record<string, unknown>))
    .filter((item): item is EarthquakeEvent => item !== null)
}

function backendParams(query: CatalogQuery) {
  const params = new URLSearchParams()
  if (query.start) params.set('start', query.start)
  if (query.end) params.set('end', query.end)
  if (!query.start && !query.end) params.set('hours', String(query.hours ?? 24))
  params.set('minMag', String(query.minMag))
  params.set('limit', String(query.limit ?? 5000))
  if (query.maxMag !== null && query.maxMag !== undefined) params.set('maxMag', String(query.maxMag))
  if (query.minDepth !== null && query.minDepth !== undefined) params.set('minDepth', String(query.minDepth))
  if (query.maxDepth !== null && query.maxDepth !== undefined) params.set('maxDepth', String(query.maxDepth))
  if (query.bbox) params.set('bbox', query.bbox)
  if (!query.bbox && query.minLon !== null && query.minLon !== undefined) params.set('minLon', String(query.minLon))
  if (!query.bbox && query.maxLon !== null && query.maxLon !== undefined) params.set('maxLon', String(query.maxLon))
  if (!query.bbox && query.minLat !== null && query.minLat !== undefined) params.set('minLat', String(query.minLat))
  if (!query.bbox && query.maxLat !== null && query.maxLat !== undefined) params.set('maxLat', String(query.maxLat))
  return params
}

async function fetchBackendCatalog(query: CatalogQuery, signal: AbortSignal) {
  const response = await fetch(apiPath(`/api/events?${backendParams(query).toString()}`), {
    signal,
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) throw new Error(`Catalog API returned ${response.status}`)
  return normalizeBackendPayload(await response.json())
}

function usgsParams(query: CatalogQuery) {
  const now = new Date()
  const end = query.end ? new Date(query.end) : now
  const start = query.start
    ? new Date(query.start)
    : new Date(end.getTime() - (query.hours ?? 24) * 60 * 60 * 1000)

  const params = new URLSearchParams({
    format: 'geojson',
    starttime: start.toISOString(),
    endtime: end.toISOString(),
    minmagnitude: String(query.minMag),
    orderby: 'time',
    limit: String(Math.min(query.limit ?? 5000, 20000)),
  })

  if (query.maxMag !== null && query.maxMag !== undefined) params.set('maxmagnitude', String(query.maxMag))
  if (query.minDepth !== null && query.minDepth !== undefined) params.set('mindepth', String(query.minDepth))
  if (query.maxDepth !== null && query.maxDepth !== undefined) params.set('maxdepth', String(query.maxDepth))

  if (query.bbox) {
    const [west, south, east, north] = query.bbox.split(',')
    params.set('minlongitude', west)
    params.set('minlatitude', south)
    params.set('maxlongitude', east)
    params.set('maxlatitude', north)
  } else {
    if (query.minLon !== null && query.minLon !== undefined) params.set('minlongitude', String(query.minLon))
    if (query.maxLon !== null && query.maxLon !== undefined) params.set('maxlongitude', String(query.maxLon))
    if (query.minLat !== null && query.minLat !== undefined) params.set('minlatitude', String(query.minLat))
    if (query.maxLat !== null && query.maxLat !== undefined) params.set('maxlatitude', String(query.maxLat))
  }

  return params
}

function normalizeUsgsPayload(payload: unknown): EarthquakeEvent[] {
  const features = (payload as { features?: unknown[] } | null)?.features
  if (!Array.isArray(features)) throw new Error('Invalid USGS response')

  return features.flatMap((feature) => {
    const item = feature as {
      id?: unknown
      properties?: Record<string, unknown>
      geometry?: { coordinates?: unknown[] }
    }
    const properties = item.properties ?? {}
    const coordinates = item.geometry?.coordinates ?? []
    const timeMs = finiteNumber(properties.time)
    const updatedMs = finiteNumber(properties.updated)

    const normalized = normalizeEvent({
      id: item.id,
      time: timeMs === null ? null : new Date(timeMs).toISOString(),
      updated: updatedMs === null ? null : new Date(updatedMs).toISOString(),
      mag: properties.mag,
      place: properties.place,
      depth_km: coordinates[2],
      lon: coordinates[0],
      lat: coordinates[1],
      magType: properties.magType,
      nst: properties.nst,
      gap: properties.gap,
      dmin: properties.dmin,
      rms: properties.rms,
      net: properties.net,
      type: properties.type,
      horizontalError: properties.horizontalError,
      depthError: properties.depthError,
      magError: properties.magError,
      magNst: properties.magNst,
      status: properties.status,
      locationSource: properties.locationSource,
      magSource: properties.magSource,
      url: properties.url,
    })

    return normalized ? [normalized] : []
  })
}

async function fetchUsgsCatalog(query: CatalogQuery, signal: AbortSignal) {
  const response = await fetch(`${USGS_QUERY_URL}?${usgsParams(query).toString()}`, {
    signal,
    headers: { Accept: 'application/geo+json, application/json' },
  })
  if (!response.ok) throw new Error(`USGS returned ${response.status}`)
  return normalizeUsgsPayload(await response.json())
}

export async function fetchCatalog(query: CatalogQuery, signal: AbortSignal): Promise<CatalogResult> {
  try {
    const events = await fetchBackendCatalog(query, signal)
    return { events, source: 'backend', fetchedAt: new Date().toISOString() }
  } catch (backendError) {
    if (signal.aborted) throw backendError
  }

  try {
    const events = await fetchUsgsCatalog(query, signal)
    return { events, source: 'usgs', fetchedAt: new Date().toISOString() }
  } catch (fallbackError) {
    if (signal.aborted) throw fallbackError
    throw new Error('Catalog API and USGS fallback are unavailable')
  }
}

export function catalogCsv(events: EarthquakeEvent[]) {
  const columns: Array<[keyof EarthquakeEvent, string]> = [
    ['id', 'Event ID'],
    ['time', 'Time (UTC)'],
    ['updated', 'Updated (UTC)'],
    ['mag', 'Magnitude'],
    ['magType', 'Magnitude type'],
    ['place', 'Place'],
    ['depth_km', 'Depth (km)'],
    ['lon', 'Longitude'],
    ['lat', 'Latitude'],
    ['net', 'Network'],
    ['type', 'Event type'],
    ['status', 'Status'],
    ['gap', 'Azimuthal gap'],
    ['rms', 'RMS'],
  ]

  const escapeCell = (value: unknown) => {
    if (value === null || value === undefined) return ''
    const text = String(value)
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
  }

  const rows = events.map((event) => columns.map(([key]) => escapeCell(event[key])).join(','))
  return `\uFEFF${columns.map(([, label]) => label).join(',')}\n${rows.join('\n')}`
}
