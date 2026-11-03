import type { LayerInfo, PlanetLayer } from './types'

interface Entry {
  layer: PlanetLayer
  visible: boolean
  opacity: number
}

/** 图层注册表：统一负责开关、透明度、逐帧更新和销毁。 */
export class LayerManager {
  private readonly entries = new Map<string, Entry>()

  add(layer: PlanetLayer, options: { visible?: boolean; opacity?: number } = {}) {
    const visible = options.visible ?? true
    const opacity = options.opacity ?? 1
    layer.setVisible(visible)
    layer.setOpacity(opacity)
    this.entries.set(layer.id, { layer, visible, opacity })
    return layer
  }

  get(id: string) {
    return this.entries.get(id)?.layer
  }

  has(id: string) {
    return this.entries.has(id)
  }

  setVisible(id: string, visible: boolean) {
    const entry = this.entries.get(id)
    if (!entry) return
    entry.visible = visible
    entry.layer.setVisible(visible)
  }

  setOpacity(id: string, opacity: number) {
    const entry = this.entries.get(id)
    if (!entry) return
    entry.opacity = opacity
    entry.layer.setOpacity(opacity)
  }

  list(): LayerInfo[] {
    return [...this.entries.values()].map(({ layer, visible, opacity }) => ({
      id: layer.id,
      name: layer.name,
      nameEn: layer.nameEn,
      visible,
      opacity,
      count: layer.getCount?.(),
      meta: layer.getMeta?.()
    }))
  }

  update(dt: number, elapsed: number) {
    for (const entry of this.entries.values()) {
      if (!entry.visible) continue
      entry.layer.update(dt, elapsed)
    }
  }

  dispose() {
    for (const entry of this.entries.values()) entry.layer.dispose()
    this.entries.clear()
  }
}
