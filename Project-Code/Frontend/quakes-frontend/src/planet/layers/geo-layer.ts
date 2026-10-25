import * as THREE from 'three'
import { latLonToVector } from './sphere'
import { sampleSphericalPath, toLineSegments } from './paths'
import type { GeoLine, GeoSite } from './geo-data'
import type { LayerContext, Pickable, PlanetLayer } from './types'

export interface GeoLayerOptions {
  altitude: number
  opacity: number
  lineColor: [number, number, number]
  siteColor: [number, number, number]
  /** 线条透明度（相对整体 opacity） */
  lineOpacity: number
  /** 火山三角形的大小（世界单位） */
  siteSize: number
}

const siteVertexShader = /* glsl */ `
  uniform float uViewportHeight;
  uniform float uSize;
  attribute float aHighlight;
  varying float vHighlight;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mv;
    float scale = 1.0 + aHighlight * 0.32;
    gl_PointSize = clamp(uSize * scale * uViewportHeight * projectionMatrix[1][1] * 0.5 / max(-mv.z, 0.001), 3.0, 56.0);
    vHighlight = aHighlight;
  }
`

const siteFragmentShader = /* glsl */ `
  uniform vec3 uColor;
  uniform float uOpacity;
  varying float vHighlight;
  void main() {
    vec2 p = gl_PointCoord - 0.5;
    float r = length(p);

    // 三角形：顶点朝上，底边在下方
    float y = p.y;
    float halfWidth = (0.45 - y) * 0.58;
    bool inside = y > -0.36 && y < 0.45 && abs(p.x) <= halfWidth;
    float triangle = inside ? 1.0 - smoothstep(-0.02, 0.0, abs(p.x) - halfWidth) : 0.0;

    // 背后一点柔光，让 6px 的小三角也能被看见
    float halo = (1.0 - smoothstep(0.1, 0.5, r)) * 0.16;
    float alpha = clamp(triangle + halo * (1.0 - triangle), 0.0, 1.0) * uOpacity * (1.0 + vHighlight * 0.12);
    if (alpha <= 0.01) discard;
    gl_FragColor = vec4(mix(uColor, vec3(1.0), vHighlight * 0.4), alpha);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`

/**
 * 地质图层：断层带 / 板块边界用线段，火山用三角形点位。
 * 线段和点位都贴在球面上，随地球一起转。
 */
export class GeoLayer implements PlanetLayer {
  readonly id = 'geo'
  readonly name = '地质'
  readonly nameEn = 'Geology'
  readonly object: THREE.Group

  private readonly lineGeometry: THREE.BufferGeometry
  private readonly siteGeometry: THREE.BufferGeometry
  private readonly lineMaterial: THREE.LineBasicMaterial
  private readonly siteMaterial: THREE.ShaderMaterial
  private readonly viewport = new THREE.Vector2()
  private readonly context: LayerContext
  private readonly options: GeoLayerOptions
  private readonly lines: GeoLine[]
  private readonly sites: GeoSite[]
  private sitePoints: THREE.Vector3[] = []
  private pickables: Pickable[] = []
  private highlight = -1
  private visible = false

  constructor(context: LayerContext, lines: GeoLine[], sites: GeoSite[], options: GeoLayerOptions) {
    this.context = context
    this.options = options
    this.lines = lines
    this.sites = sites
    this.object = new THREE.Group()
    this.object.visible = false

    // --- 断层线 ---
    const linePositions: number[] = []
    const lineColors: number[] = []
    const radius = context.radius * options.altitude
    const base = new THREE.Color().fromArray(options.lineColor).convertSRGBToLinear()
    for (const line of lines) {
      const samples = sampleSphericalPath(context.planetGeometry, line.points, radius)
      const start = linePositions.length
      toLineSegments(samples, linePositions)
      // 板块边界比断层暗一点，视觉上分出主次
      const tint = line.kind === 'boundary' ? base.clone().multiplyScalar(0.65) : base.clone()
      for (let i = start; i < linePositions.length; i += 3) lineColors.push(tint.r, tint.g, tint.b)
    }

    this.lineGeometry = new THREE.BufferGeometry()
    this.lineGeometry.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3))
    this.lineGeometry.setAttribute('color', new THREE.Float32BufferAttribute(lineColors, 3))
    this.lineGeometry.computeBoundingSphere()

    this.lineMaterial = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: options.lineOpacity,
      depthWrite: false
    })

    // --- 火山点 ---
    const sitePositions: number[] = []
    const siteHighlights: number[] = []
    this.sitePoints = []
    for (const site of sites) {
      const point = latLonToVector(context.planetGeometry, site.lat, site.lon, radius)
      sitePositions.push(point.x, point.y, point.z)
      siteHighlights.push(0)
      this.sitePoints.push(point)
    }
    this.siteGeometry = new THREE.BufferGeometry()
    this.siteGeometry.setAttribute('position', new THREE.Float32BufferAttribute(sitePositions, 3))
    this.siteGeometry.setAttribute('aHighlight', new THREE.Float32BufferAttribute(siteHighlights, 1))
    this.siteGeometry.computeBoundingSphere()

    this.siteMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uViewportHeight: { value: 900 },
        uSize: { value: options.siteSize },
        uColor: { value: new THREE.Color().fromArray(options.siteColor).convertSRGBToLinear() },
        uOpacity: { value: options.opacity }
      },
      vertexShader: siteVertexShader,
      fragmentShader: siteFragmentShader,
      transparent: true,
      depthWrite: false,
      depthTest: true
    })

    // 断层沿线取样成可拾取点，鼠标放到线附近就能看到名称
    const linePickables: Pickable[] = []
    for (const line of lines) {
      const samples = sampleSphericalPath(context.planetGeometry, line.points, radius)
      const step = Math.max(1, Math.floor(samples.length / 12))
      for (let i = 0; i < samples.length; i += step) {
        linePickables.push({
          id: `fault-${line.name}-${i}`,
          label: line.name,
          detail: line.kind === 'boundary' ? '板块边界' : line.kind === 'belt' ? '构造带' : '断层',
          position: samples[i]
        })
      }
    }

    this.pickables = [
      ...this.sites.map((site, index) => ({
        id: `volcano-${index}`,
        label: site.name,
        detail: site.kind === 'volcano' ? '活火山' : '地质点',
        position: this.sitePoints[index] ?? new THREE.Vector3()
      })),
      ...linePickables
    ]

    const lineMesh = new THREE.LineSegments(this.lineGeometry, this.lineMaterial)
    lineMesh.renderOrder = 2
    const siteMesh = new THREE.Points(this.siteGeometry, this.siteMaterial)
    siteMesh.renderOrder = 3
    this.object.add(lineMesh, siteMesh)
    context.pivot.add(this.object)
  }

  get data(): { lines: readonly GeoLine[]; sites: readonly GeoSite[] } {
    return { lines: this.lines, sites: this.sites }
  }

  getCount() {
    return this.sites.length + this.lines.length
  }

  getPickables(): Pickable[] {
    return this.pickables
  }

  setHighlight(id: string | null) {
    const next = id ? Number(id.split('-')[1]) : -1
    if (next === this.highlight) return
    this.highlight = Number.isFinite(next) ? next : -1
    const attribute = this.siteGeometry.getAttribute('aHighlight') as THREE.BufferAttribute | undefined
    if (!attribute) return
    for (let i = 0; i < attribute.count; i += 1) attribute.setX(i, i === this.highlight ? 1 : 0)
    attribute.needsUpdate = true
  }

  setVisible(visible: boolean) {
    this.visible = visible
    this.object.visible = visible
  }

  setOpacity(opacity: number) {
    const clamped = THREE.MathUtils.clamp(opacity, 0, 1)
    this.lineMaterial.opacity = this.options.lineOpacity * clamped
    this.siteMaterial.uniforms.uOpacity.value = clamped
  }

  update(_dt: number) {
    if (!this.visible) return
    this.context.renderer.getDrawingBufferSize(this.viewport)
    this.siteMaterial.uniforms.uViewportHeight.value = this.viewport.y
  }

  dispose() {
    this.object.removeFromParent()
    this.lineGeometry.dispose()
    this.siteGeometry.dispose()
    this.lineMaterial.dispose()
    this.siteMaterial.dispose()
  }
}
