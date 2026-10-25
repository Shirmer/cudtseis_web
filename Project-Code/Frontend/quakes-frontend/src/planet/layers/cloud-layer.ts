import * as THREE from 'three'
import type { LayerContext, PlanetLayer } from './types'

export interface CloudLayerOptions {
  texture: string
  /** 距地表的高度倍数，1.0015 即贴着地表上方一点点 */
  altitude: number
  opacity: number
  /** 相对地球的漂移速度（弧度/秒），正数向东 */
  drift: number
  /** 云密度阈值，越大云越少 */
  threshold: number
  /** 边缘过渡宽度，越大边缘越柔 */
  softness: number
  tint: [number, number, number]
}

const vertexShader = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vWorldNormal;
  void main() {
    vUv = uv;
    vec4 world = modelMatrix * vec4(position, 1.0);
    vWorldNormal = normalize(mat3(modelMatrix) * normal);
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`

const fragmentShader = /* glsl */ `
  uniform sampler2D cloudMap;
  uniform float opacity;
  uniform float threshold;
  uniform float softness;
  uniform vec3 sunDirection;
  uniform vec3 tint;
  varying vec2 vUv;
  varying vec3 vWorldNormal;

  void main() {
    // 贴图是灰度云图：亮度就是云量
    float density = texture2D(cloudMap, vUv).r;
    float alpha = smoothstep(threshold, threshold + softness, density);
    if (alpha <= 0.004) discard;

    vec3 n = normalize(vWorldNormal);
    float daylight = clamp(dot(n, sunDirection), 0.0, 1.0);
    // 夜面只留一点点城市光反射，避免整块死黑
    float shade = mix(0.05, 1.0, pow(daylight, 0.7));
    gl_FragColor = vec4(tint * shade, alpha * opacity);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`

/**
 * 云层：复用星球几何体（UV 与地表贴图完全对齐），缩放一点点贴在地表上方。
 * 独立于地球自转缓慢漂移，看起来像真实的云系移动。
 */
export class CloudLayer implements PlanetLayer {
  readonly id = 'clouds'
  readonly name = '云层'
  readonly nameEn = 'Clouds'
  readonly object: THREE.Mesh

  private readonly material: THREE.ShaderMaterial
  private texture: THREE.Texture | null = null
  private drift = 0
  private disposed = false
  private visible: boolean
  private opacity: number

  constructor(private readonly context: LayerContext, private readonly options: CloudLayerOptions) {
    const geometry = context.planetGeometry.clone()
    geometry.scale(options.altitude, options.altitude, options.altitude)

    this.material = new THREE.ShaderMaterial({
      uniforms: {
        cloudMap: { value: null },
        opacity: { value: options.opacity },
        threshold: { value: options.threshold },
        softness: { value: options.softness },
        sunDirection: { value: context.sunDirection.clone() },
        tint: { value: new THREE.Color().fromArray(options.tint) }
      },
      vertexShader,
      fragmentShader,
      transparent: true,
      depthWrite: false,
      side: THREE.FrontSide
    })

    this.visible = true
    this.opacity = options.opacity
    this.object = new THREE.Mesh(geometry, this.material)
    this.object.renderOrder = 1
    context.pivot.add(this.object)

    new THREE.TextureLoader().load(
      context.assetUrl(options.texture),
      (texture) => {
        if (this.disposed) {
          texture.dispose()
          return
        }
        // 和地表贴图一样，glTF 的 UV 不允许再翻转
        texture.flipY = false
        texture.wrapS = THREE.RepeatWrapping
        texture.colorSpace = THREE.NoColorSpace
        texture.anisotropy = Math.min(context.renderer.capabilities.getMaxAnisotropy(), 8)
        texture.needsUpdate = true
        this.material.uniforms.cloudMap.value = texture
        this.texture = texture
      },
      undefined,
      () => undefined
    )
  }

  setVisible(visible: boolean) {
    this.visible = visible
    this.object.visible = visible
  }

  setOpacity(opacity: number) {
    this.opacity = THREE.MathUtils.clamp(opacity, 0, 1)
    this.material.uniforms.opacity.value = this.opacity
  }

  update(dt: number) {
    if (!this.visible) return
    this.drift += dt * this.options.drift
    // 云层在星球本地空间里绕轴多转一点，形成漂移
    this.object.rotation.y = this.drift
  }

  dispose() {
    this.disposed = true
    this.object.removeFromParent()
    this.object.geometry.dispose()
    this.material.dispose()
    this.texture?.dispose()
  }
}
