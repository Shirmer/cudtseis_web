import * as THREE from 'three'
import { latLonToVector } from './sphere'
import type { LayerContext, Pickable, PlanetLayer } from './types'

export interface StormCell {
  lat: number
  lon: number
  /** 风暴半径（球面角度，度） */
  size: number
  /** 强度 0-1，影响透明度与对比度 */
  intensity: number
  /** 1 = 逆时针（北半球），-1 = 顺时针（南半球） */
  spin?: number
  name?: string
}

export interface WeatherLayerOptions {
  altitude: number
  opacity: number
  /** 螺旋旋转速度 */
  speed: number
  color: [number, number, number]
}

const vertexShader = /* glsl */ `
  varying vec3 vLocal;
  varying vec3 vWorldNormal;
  void main() {
    vLocal = position;
    vWorldNormal = normalize(mat3(modelMatrix) * normal);
    gl_Position = projectionMatrix * viewMatrix * modelMatrix * vec4(position, 1.0);
  }
`

const fragmentShader = /* glsl */ `
  uniform float uTime;
  uniform float uIntensity;
  uniform float uOpacity;
  uniform float uSpin;
  uniform float uSinRadius;
  uniform float uSpeed;
  uniform float uHighlight;
  uniform vec3 uColor;
  uniform vec3 uSunDirection;
  varying vec3 vLocal;
  varying vec3 vWorldNormal;

  void main() {
    // 把球冠上的点投影到「以风暴中心为原点」的切平面坐标
    vec2 p = normalize(vLocal).xz / uSinRadius;
    float r = length(p);
    if (r > 1.0) discard;

    float angle = atan(p.y, p.x);
    // 对数螺旋：越往外绕得越开；上界收窄让云带更"紧"
    float swirl = sin(angle * 3.0 + log(max(r, 0.06)) * 3.4 - uTime * 1.5 * uSpin * uSpeed);
    float band = smoothstep(-0.15, 0.55, swirl);

    float eye = smoothstep(0.03, 0.12, r);                                  // 台风眼（内部完全透明）
    float eyewall = smoothstep(0.12, 0.16, r) * (1.0 - smoothstep(0.18, 0.3, r)); // 眼墙：一圈更实的亮环
    float rim = 1.0 - smoothstep(0.58, 1.0, r);                             // 边缘淡出
    float daylight = clamp(dot(normalize(vWorldNormal), uSunDirection), 0.0, 1.0);
    float shade = mix(0.5, 1.0, daylight);

    float body = clamp(band * 0.72 + eyewall * 0.95, 0.0, 1.0);
    float alpha = body * eye * rim * uIntensity * uOpacity * shade * (1.0 + uHighlight * 0.3);
    if (alpha <= 0.004) discard;

    // 冷色云带 + 更白的眼墙，避免整块发灰
    vec3 color = mix(uColor, vec3(0.9, 0.95, 1.0), band * 0.35);
    color = mix(color, vec3(1.0), eyewall * 0.45 + uHighlight * 0.35);
    color *= mix(0.62, 1.0, daylight);
    gl_FragColor = vec4(color, alpha * 0.92);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`

/**
 * 天气图层：每个风暴是一块贴着地表的球冠，用 shader 画旋转的对数螺旋云带，
 * 自带台风眼和边缘淡出。数据换成真实气旋中心即可，渲染不用动。
 */
export class WeatherLayer implements PlanetLayer {
  readonly id = 'weather'
  readonly name = '天气'
  readonly nameEn = 'Weather'
  readonly object: THREE.Group

  private readonly materials: THREE.ShaderMaterial[] = []
  private readonly geometries: THREE.BufferGeometry[] = []
  private readonly storms: StormCell[]
  private readonly stormPoints: THREE.Vector3[] = []
  private highlight = -1
  private pickables: Pickable[] = []
  private visible = true
  private elapsed = 0

  constructor(context: LayerContext, storms: StormCell[], options: WeatherLayerOptions) {
    this.storms = storms
    this.object = new THREE.Group()
    this.object.renderOrder = 2
    this.object.visible = false

    const sun = context.sunDirection.clone()
    for (const storm of storms) {
      const angular = THREE.MathUtils.degToRad(storm.size)
      const geometry = new THREE.SphereGeometry(context.radius * options.altitude, 64, 32, 0, Math.PI * 2, 0, angular)
      this.geometries.push(geometry)

      const material = new THREE.ShaderMaterial({
        uniforms: {
          uTime: { value: 0 },
          uIntensity: { value: storm.intensity },
          uOpacity: { value: options.opacity },
          uSpin: { value: storm.spin ?? 1 },
          uSpeed: { value: options.speed },
          uHighlight: { value: 0 },
          uSinRadius: { value: Math.sin(angular) },
          uColor: { value: new THREE.Color().fromArray(options.color).convertSRGBToLinear() },
          uSunDirection: { value: sun }
        },
        vertexShader,
        fragmentShader,
        transparent: true,
        depthWrite: false,
        side: THREE.FrontSide
      })
      this.materials.push(material)

      const mesh = new THREE.Mesh(geometry, material)
      const direction = latLonToVector(context.planetGeometry, storm.lat, storm.lon, 1).normalize()
      mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction)
      this.stormPoints.push(direction.clone().multiplyScalar(context.radius * options.altitude))
      this.object.add(mesh)
    }

    this.pickables = storms.map((storm, index) => ({
      id: `storm-${index}`,
      label: storm.name ?? '热带气旋',
      detail: `${storm.size.toFixed(1)}° · 强度 ${Math.round(storm.intensity * 100)}%`,
      position: this.stormPoints[index] ?? new THREE.Vector3()
    }))

    context.pivot.add(this.object)
  }

  get data(): readonly StormCell[] {
    return this.storms
  }

  getCount() {
    return this.storms.length
  }

  getPickables(): Pickable[] {
    return this.pickables
  }

  setHighlight(id: string | null) {
    const next = id ? Number(id.split('-')[1]) : -1
    if (next === this.highlight) return
    this.highlight = Number.isFinite(next) ? next : -1
    this.materials.forEach((material, index) => {
      material.uniforms.uHighlight.value = index === this.highlight ? 1 : 0
    })
  }

  setVisible(visible: boolean) {
    this.visible = visible
    this.object.visible = visible
  }

  setOpacity(opacity: number) {
    for (const material of this.materials) {
      material.uniforms.uOpacity.value = THREE.MathUtils.clamp(opacity, 0, 1)
    }
  }

  update(dt: number) {
    if (!this.visible) return
    this.elapsed += dt
    for (const material of this.materials) material.uniforms.uTime.value = this.elapsed
  }

  dispose() {
    this.object.removeFromParent()
    this.geometries.forEach((geometry) => geometry.dispose())
    this.materials.forEach((material) => material.dispose())
  }
}
