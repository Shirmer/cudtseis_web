import { SITE } from '../config/site'

export interface ReleaseAsset {
  objectKey: string
  versionName: string
  versionCode: string
  changelog: string
  publishedAt: string
  url: string
}

export interface LatestRelease {
  versionName: string
  versionCode: string
  changelog: string
  publishedAt: string
  apks: Record<string, ReleaseAsset>
}

interface ApiEnvelope<T> {
  code: number
  message: string
  data: T | null
}

export async function fetchLatestRelease(): Promise<LatestRelease> {
  const response = await fetch(SITE.releaseApi, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  const body = (await response.json()) as ApiEnvelope<LatestRelease>
  if (body.code !== 200 || !body.data) throw new Error(body.message || 'release unavailable')
  return body.data
}

export function pickApk(release: LatestRelease): ReleaseAsset | undefined {
  const preferred = ['arm64', 'arm32', 'x86_64']
  for (const key of preferred) {
    const asset = release.apks?.[key]
    if (asset?.url) return asset
  }
  return Object.values(release.apks ?? {})[0]
}
