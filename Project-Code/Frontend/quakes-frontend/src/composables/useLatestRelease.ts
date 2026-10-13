import { ref } from 'vue'
import { fetchLatestRelease, pickApk, type LatestRelease, type ReleaseAsset } from '../services/release'

const release = ref<LatestRelease | null>(null)
const loading = ref(false)
const failed = ref(false)
let inflight: Promise<void> | null = null

async function load(): Promise<void> {
  if (inflight) return inflight
  loading.value = true
  failed.value = false
  inflight = (async () => {
    try {
      release.value = await fetchLatestRelease()
    } catch {
      failed.value = true
      release.value = null
    } finally {
      loading.value = false
      inflight = null
    }
  })()
  return inflight
}

export function useLatestRelease() {
  if (!inflight && !release.value && !failed.value) void load()
  return {
    release,
    loading,
    failed,
    reload: load
  }
}

export function useApkDownload() {
  async function download(): Promise<ReleaseAsset | undefined> {
    let current = release.value
    if (!current) {
      await load()
      current = release.value
    }
    const asset = current ? pickApk(current) : undefined
    if (asset?.url) window.location.assign(asset.url)
    return asset
  }
  return { download }
}
