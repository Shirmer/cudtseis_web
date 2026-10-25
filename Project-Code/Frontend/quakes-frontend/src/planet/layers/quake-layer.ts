import * as THREE from 'three'
import { latLonToVector } from './sphere'
import type { LayerContext, LayerMeta, Pickable, PlanetLayer, YearBucket } from './types'

export interface QuakeEvent {
  lat: number
  lon: number
  /** 震级 */
  magnitude: number
  place: string
  time: string
}

export interface QuakeRippleOptions {
  enabled: boolean
  /** 触发波纹的最小震级 */
  minMagnitude: number
  /** 一次波纹的持续秒数 */
  life: number
  /** 最大半径（星球本地单位） */
  maxRadius: number
  color: [number, number, number]
  /** 同时存在的波纹上限 */
  max: number
}

export interface QuakeLayerOptions {
  color: [number, number, number]
  /** 点的基础世界尺寸 */
  size: number
  /** 每级震级增加的尺寸 */
  magnitudeScale: number
  altitude: number
  opacity: number
  ripple?: QuakeRippleOptions
}

interface Ripple {
  mesh: THREE.Mesh
  material: THREE.MeshBasicMaterial
  age: number
  active: boolean
}

const vertexShader = /* glsl */ `
  uniform float uTime;
  uniform float uViewportHeight;
  uniform float uSize;
  uniform float uMagnitudeScale;
  uniform float uYear;
  attribute float aMagnitude;
  attribute float aPhase;
  attribute float aHighlight;
  attribute float aYear;
  varying float vMagnitude;
  varying float vPhase;
  varying float vHighlight;
  varying float vAppear;

  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mv;

    // 时间轴之后才发生的事件：直接移出裁剪空间
    if (aYear > uYear + 0.001) {
      gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
      gl_PointSize = 0.0;
      vMagnitude = 0.0;
      vPhase = 0.0;
      vHighlight = 0.0;
      vAppear = 0.0;
      return;
    }

    // 刚出现的事件做一点「弹出」动画
    float appear = clamp((uYear - aYear) * 3.0 + 0.35, 0.0, 1.0);
    float worldSize = (uSize + (aMagnitude - 5.0) * uMagnitudeScale) * (1.0 + aHighlight * 0.28) * appear;
    float pulse = 1.0 + 0.12 * sin(uTime * 1.8 + aPhase * 6.2831);
    float pixels = worldSize * pulse * uViewportHeight * projectionMatrix[1][1] * 0.5 / max(-mv.z, 0.001);
    gl_PointSize = clamp(pixels, 2.0, 220.0);

    vMagnitude = aMagnitude;
    vPhase = aPhase;
    vHighlight = aHighlight;
    vAppear = appear;
  }
`

const fragmentShader = /* glsl */ `
  uniform float uTime;
  uniform float uOpacity;
  uniform vec3 uColor;
  varying float vMagnitude;
  varying float vPhase;
  varying float vHighlight;
  varying float vAppear;

  void main() {
    vec2 p = (gl_PointCoord - 0.5) * 2.0;
    float r = length(p);
    if (r > 1.0) discard;

    // 实心核
    float core = smoothstep(1.0, 0.0, r / 0.22);
    // 向外扩散的冲击环
    float t = fract(uTime * 0.35 + vPhase);
    float ringRadius = 0.18 + t * 0.82;
    float ring = smoothstep(0.10, 0.0, abs(r - ringRadius)) * (1.0 - t);

    float alpha = clamp(core + ring * 0.6 + vHighlight * 0.08, 0.0, 1.0) * vAppear;
    if (alpha <= 0.01) discard;
    vec3 color = mix(uColor, vec3(1.0), vHighlight * 0.3);
    gl_FragColor = vec4(color, alpha * uOpacity);
  }
`

/**
 * 地震点位图层（演示数据）。
 * 用 Points + 自定义 shader 做「实心核 + 扩散环」，震级决定点的大小。
 * 接真实数据时只要换 events 来源，渲染部分不用动。
 */
export class QuakeLayer implements PlanetLayer {
  readonly id = 'quakes'
  readonly name = '地震'
  readonly nameEn = 'Earthquakes'
  readonly object: THREE.Points

  private readonly material: THREE.ShaderMaterial
  private events: QuakeEvent[]
  private points: THREE.Vector3[] = []
  private highlight = -1
  private pickables: Pickable[] = []
  private readonly options: QuakeLayerOptions
  private readonly ripples: Ripple[] = []
  private currentYear: number | null = null
  private meta: LayerMeta | undefined
  private histogram: YearBucket[] = []
  private visible = true
  private disposed = false

  private readonly context: LayerContext
  private readonly viewport = new THREE.Vector2()

  constructor(context: LayerContext, events: QuakeEvent[], options: QuakeLayerOptions) {
    this.context = context
    this.options = options
    this.events = events
    const geometry = this.buildGeometry(events)

    this.material = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uViewportHeight: { value: 1080 },
        uOpacity: { value: options.opacity },
        uColor: { value: new THREE.Color().fromArray(options.color).convertSRGBToLinear() },
        uSize: { value: options.size },
        uMagnitudeScale: { value: options.magnitudeScale },
        uYear: { value: Number.MAX_SAFE_INTEGER }
      },
      vertexShader,
      fragmentShader,
      transparent: true,
      depthWrite: false,
      depthTest: true,
      // 用普通混合而不是加色：白天那一面也能看清，不会被地表亮部吃掉
      blending: THREE.NormalBlending
    })

    this.object = new THREE.Points(geometry, this.material)

    const rippleOptions = options.ripple
    if (rippleOptions?.enabled) {
      const rippleGeometry = new THREE.RingGeometry(0.72, 1, 64)
      const rippleColor = new THREE.Color().fromArray(rippleOptions.color).convertSRGBToLinear()
      for (let i = 0; i < rippleOptions.max; i += 1) {
        const material = new THREE.MeshBasicMaterial({
          color: rippleColor,
          transparent: true,
          opacity: 0,
          depthWrite: false,
          side: THREE.DoubleSide,
          blending: THREE.AdditiveBlending
        })
        const mesh = new THREE.Mesh(rippleGeometry, material)
        mesh.visible = false
        mesh.renderOrder = 2
        this.object.add(mesh)
        this.ripples.push({ mesh, material, age: 0, active: false })
      }
    }
    this.object.renderOrder = 3
    context.pivot.add(this.object)
  }

  /** 当前数据点，后续可以换成接口返回 */
  get data(): readonly QuakeEvent[] {
    return this.events
  }

  /**
   * 运行期换数据：接真实接口 / 时间轴回放时调用，
   * 只重建几何属性，材质和 shader 不用动。
   */
  setData(events: QuakeEvent[]) {
    this.events = events
    const geometry = this.buildGeometry(events)
    this.object.geometry.dispose()
    this.object.geometry = geometry
  }

  private buildGeometry(events: QuakeEvent[]) {
    const count = Math.max(events.length, 1)
    const positions = new Float32Array(count * 3)
    const magnitudes = new Float32Array(count)
    const phases = new Float32Array(count)
    const highlights = new Float32Array(count)
    const years = new Float32Array(count)
    this.points = []

    events.forEach((event, index) => {
      const point = latLonToVector(
        this.context.planetGeometry,
        event.lat,
        event.lon,
        this.context.radius * this.options.altitude
      )
      positions.set([point.x, point.y, point.z], index * 3)
      magnitudes[index] = event.magnitude
      phases[index] = (index * 0.618) % 1
      highlights[index] = index === this.highlight ? 1 : 0
      years[index] = Number(event.time.slice(0, 4)) || 0
      this.points.push(point)
    })

    this.buildHistogram()

    this.pickables = events.map((event, index) => ({
      id: `quake-${index}`,
      label: event.place,
      detail: `M${event.magnitude} · ${event.time}`,
      position: this.points[index] ?? new THREE.Vector3()
    }))

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute('aMagnitude', new THREE.BufferAttribute(magnitudes, 1))
    geometry.setAttribute('aPhase', new THREE.BufferAttribute(phases, 1))
    geometry.setAttribute('aHighlight', new THREE.BufferAttribute(highlights, 1))
    geometry.setAttribute('aYear', new THREE.BufferAttribute(years, 1))
    geometry.computeBoundingSphere()
    return geometry
  }

  getPickables(): Pickable[] {
    return this.pickables
  }

  private buildHistogram() {
    const buckets = new Map<number, YearBucket>()
    for (const event of this.events) {
      const year = Number(event.time.slice(0, 4))
      if (!Number.isFinite(year) || year <= 0) continue
      const bucket = buckets.get(year)
      if (bucket) {
        bucket.count += 1
        bucket.peak = Math.max(bucket.peak, event.magnitude)
      } else {
        buckets.set(year, { year, count: 1, peak: event.magnitude })
      }
    }
    this.histogram = [...buckets.values()].sort((a, b) => a.year - b.year)
  }

  getHistogram(): YearBucket[] {
    return this.histogram
  }

  setMeta(meta: LayerMeta) {
    this.meta = meta
  }

  getMeta(): LayerMeta | undefined {
    return this.meta
  }

  setHighlight(id: string | null) {
    const next = id ? Number(id.split('-')[1]) : -1
    if (next === this.highlight) return
    this.highlight = Number.isFinite(next) ? next : -1
    const attribute = this.object.geometry.getAttribute('aHighlight') as THREE.BufferAttribute | undefined
    if (!attribute) return
    for (let i = 0; i < attribute.count; i += 1) attribute.setX(i, i === this.highlight ? 1 : 0)
    attribute.needsUpdate = true
  }

  getCount() {
    return this.events.length
  }

  setTime(year: number) {
    const previous = this.currentYear
    this.material.uniforms.uYear.value = year
    this.currentYear = year
    // 第一次设置（打开图层）不触发；只有时间轴向前推进才冒波纹
    if (previous !== null && year > previous) this.spawnRipples(previous, year)
  }

  private spawnRipples(from: number, to: number) {
    const options = this.options.ripple
    if (!options?.enabled) return
    let spawned = 0
    this.events.forEach((event, index) => {
      if (spawned >= options.max) return
      const year = Number(event.time.slice(0, 4)) || 0
      if (year <= from || year > to || event.magnitude < options.minMagnitude) return
      const point = this.points[index]
      if (!point) return
      // 每次冒两圈，第二圈晚 0.35 秒，看起来像冲击波扩散
      for (const delay of [0, -0.35]) {
        const ripple = this.ripples.find((item) => !item.active)
        if (!ripple) break
        ripple.active = true
        ripple.age = delay
        ripple.mesh.visible = true
        ripple.mesh.position.copy(point).multiplyScalar(1.006)
        const normal = point.clone().normalize()
        ripple.mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal)
        ripple.mesh.scale.setScalar(0.05)
        ripple.material.opacity = 0
      }
      spawned += 1
    })
  }

  getTimeRange() {
    const years = this.events.map((event) => Number(event.time.slice(0, 4)) || 0).filter((year) => year > 0)
    if (!years.length) return { min: 2000, max: new Date().getFullYear() }
    return { min: Math.min(...years), max: Math.max(...years) }
  }

  setVisible(visible: boolean) {
    this.visible = visible
    this.object.visible = visible
  }

  setOpacity(opacity: number) {
    this.material.uniforms.uOpacity.value = THREE.MathUtils.clamp(opacity, 0, 1)
  }

  update(dt: number, elapsed: number) {
    if (!this.visible) return
    this.material.uniforms.uTime.value = elapsed

    const options = this.options.ripple
    if (options?.enabled) {
      for (const ripple of this.ripples) {
        if (!ripple.active) continue
        if (ripple.age < 0) {
          ripple.age += dt
          continue
        }
        ripple.age += dt
        const t = ripple.age / options.life
        if (t >= 1) {
          ripple.active = false
          ripple.mesh.visible = false
          ripple.material.opacity = 0
          continue
        }
        const eased = 1 - Math.pow(1 - t, 2.2)
        ripple.mesh.scale.setScalar(0.05 + eased * options.maxRadius)
        ripple.material.opacity = (1 - t) * 0.85
      }
    }
    // gl_PointSize 是设备像素，viewport 变化（窗口缩放 / 像素比自适应）要跟着更新
    this.context.renderer.getDrawingBufferSize(this.viewport)
    this.material.uniforms.uViewportHeight.value = this.viewport.y
  }

  dispose() {
    this.disposed = true
    const rippleGeometry = this.ripples[0]?.mesh.geometry
    this.ripples.forEach((ripple) => ripple.material.dispose())
    rippleGeometry?.dispose()
    this.object.removeFromParent()
    this.object.geometry.dispose()
    this.material.dispose()
  }
}
