import * as THREE from 'three'
import { sampleSphericalPath } from './paths'
import type { LayerContext, Pickable, PlanetLayer } from './types'

export interface CurrentPath {
  name: string
  /** 路标点 [纬度, 经度] */
  points: [number, number][]
}

export interface CurrentLayerOptions {
  altitude: number
  opacity: number
  color: [number, number, number]
  /** 流速：越大流动越快 */
  speed: number
  /** 每条路径上的流动段数 */
  dash: number
  /** 粒子大小（世界单位） */
  size: number
}

const vertexShader = /* glsl */ `
  uniform float uViewportHeight;
  uniform float uSize;
  attribute float aFlow;
  attribute float aSeed;
  varying float vFlow;
  varying float vSeed;

  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mv;
    gl_PointSize = clamp(uSize * uViewportHeight * projectionMatrix[1][1] * 0.5 / max(-mv.z, 0.001), 1.5, 32.0);
    vFlow = aFlow;
    vSeed = aSeed;
  }
`

const fragmentShader = /* glsl */ `
  uniform float uTime;
  uniform float uSpeed;
  uniform float uDash;
  uniform float uOpacity;
  uniform vec3 uColor;
  varying float vFlow;
  varying float vSeed;

  void main() {
    vec2 p = (gl_PointCoord - 0.5) * 2.0;
    float r = length(p);
    if (r > 1.0) discard;

    // 沿路径循环流动的亮段
    float phase = fract(vFlow * uDash - uTime * uSpeed + vSeed * 0.05);
    float pulse = smoothstep(0.0, 0.12, phase) * (1.0 - smoothstep(0.44, 0.6, phase));

    // 路径两端淡出，避免突然截断
    float edge = smoothstep(0.0, 0.05, vFlow) * (1.0 - smoothstep(0.95, 1.0, vFlow));

    float dot_ = smoothstep(1.0, 0.2, r);
    float alpha = dot_ * pulse * edge * uOpacity;
    if (alpha <= 0.01) discard;
    gl_FragColor = vec4(uColor, alpha);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`

/**
 * 洋流图层：暗色路径线打底 + 亮点沿路径流动。
 * 路径按经纬度路标插值到球面，跨 180° 经线会自动走短弧。
 */
export class CurrentLayer implements PlanetLayer {
  readonly id = 'currents'
  readonly name = '洋流'
  readonly nameEn = 'Ocean currents'
  readonly object: THREE.Group

  private readonly material: THREE.ShaderMaterial
  private readonly lineMaterial: THREE.LineBasicMaterial
  private readonly paths: CurrentPath[]
  private readonly pickables: Pickable[] = []
  private readonly viewport = new THREE.Vector2()
  private readonly context: LayerContext
  private readonly pointGeometry: THREE.BufferGeometry
  private readonly lineGeometry: THREE.BufferGeometry
  private visible = false

  constructor(context: LayerContext, paths: CurrentPath[], options: CurrentLayerOptions) {
    this.context = context
    this.paths = paths
    this.object = new THREE.Group()
    this.object.visible = false

    const positions: number[] = []
    const flows: number[] = []
    const seeds: number[] = []
    const linePositions: number[] = []
    const radius = context.radius * options.altitude

    paths.forEach((path, pathIndex) => {
      const samples = sampleSphericalPath(context.planetGeometry, path.points, radius)

      // 沿线取样，鼠标放到洋流附近就能看到名称
      const pickStep = Math.max(1, Math.floor(samples.length / 12))
      for (let i = 0; i < samples.length; i += pickStep) {
        this.pickables.push({
          id: `current-${pathIndex}-${i}`,
          label: path.name,
          detail: '洋流路径',
          position: samples[i]
        })
      }

      let total = 0
      const distances = [0]
      for (let i = 1; i < samples.length; i += 1) {
        total += samples[i].distanceTo(samples[i - 1])
        distances.push(total)
      }
      samples.forEach((point, index) => {
        positions.push(point.x, point.y, point.z)
        flows.push(total > 0 ? distances[index] / total : 0)
        seeds.push((pathIndex * 0.37) % 1)
        if (index > 0) {
          linePositions.push(...samples[index - 1].toArray(), ...point.toArray())
        }
      })
    })

    this.pointGeometry = new THREE.BufferGeometry()
    this.pointGeometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    this.pointGeometry.setAttribute('aFlow', new THREE.Float32BufferAttribute(flows, 1))
    this.pointGeometry.setAttribute('aSeed', new THREE.Float32BufferAttribute(seeds, 1))
    this.pointGeometry.computeBoundingSphere()

    this.material = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uViewportHeight: { value: 900 },
        uSize: { value: options.size },
        uSpeed: { value: options.speed },
        uDash: { value: options.dash },
        uOpacity: { value: options.opacity },
        uColor: { value: new THREE.Color().fromArray(options.color).convertSRGBToLinear() }
      },
      vertexShader,
      fragmentShader,
      transparent: true,
      depthWrite: false,
      depthTest: true,
      blending: THREE.AdditiveBlending
    })

    this.lineGeometry = new THREE.BufferGeometry()
    this.lineGeometry.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3))
    this.lineMaterial = new THREE.LineBasicMaterial({
      color: new THREE.Color().fromArray(options.color).convertSRGBToLinear(),
      transparent: true,
      opacity: 0.22,
      depthWrite: false
    })

    const lines = new THREE.LineSegments(this.lineGeometry, this.lineMaterial)
    lines.renderOrder = 1
    const points = new THREE.Points(this.pointGeometry, this.material)
    points.renderOrder = 2
    this.object.add(lines, points)
    context.pivot.add(this.object)
  }

  get data(): readonly CurrentPath[] {
    return this.paths
  }

  getCount() {
    return this.paths.length
  }

  getPickables(): Pickable[] {
    return this.pickables
  }

  setVisible(visible: boolean) {
    this.visible = visible
    this.object.visible = visible
  }

  setOpacity(opacity: number) {
    const clamped = THREE.MathUtils.clamp(opacity, 0, 1)
    this.material.uniforms.uOpacity.value = clamped
    this.lineMaterial.opacity = 0.22 * clamped
  }

  update(_dt: number, elapsed: number) {
    if (!this.visible) return
    this.material.uniforms.uTime.value = elapsed
    this.context.renderer.getDrawingBufferSize(this.viewport)
    this.material.uniforms.uViewportHeight.value = this.viewport.y
  }

  dispose() {
    this.object.removeFromParent()
    this.pointGeometry.dispose()
    this.lineGeometry.dispose()
    this.material.dispose()
    this.lineMaterial.dispose()
  }
}
