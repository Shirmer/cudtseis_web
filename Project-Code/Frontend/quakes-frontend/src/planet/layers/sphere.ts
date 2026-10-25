import * as THREE from 'three'

/**
 * 经纬度 -> 星球本地坐标。
 *
 * 星球贴图是等距柱状（equirectangular），UV 与经纬度的对应是：
 *   u = (lon + 180) / 360      v = (90 - lat) / 180
 * 这里不按公式硬算，而是从几何体的 UV 里找最近顶点，保证和模型自身的
 * UV 约定完全一致（换模型也不用改）。
 */
export function latLonToVector(
  geometry: THREE.BufferGeometry,
  latitude: number,
  longitude: number,
  radius = 1
): THREE.Vector3 {
  const uv = geometry.getAttribute('uv')
  const position = geometry.getAttribute('position')
  const u = (longitude + 180) / 360
  const v = (90 - latitude) / 180
  let best = 0
  let bestDistance = Infinity
  for (let i = 0; i < uv.count; i += 1) {
    let du = uv.getX(i) - u
    // 经度在贴图接缝处会从 1 跳回 0，取环形最近距离
    du -= Math.round(du)
    const dv = uv.getY(i) - v
    const distance = du * du + dv * dv
    if (distance < bestDistance) {
      bestDistance = distance
      best = i
    }
  }
  return new THREE.Vector3().fromBufferAttribute(position, best).normalize().multiplyScalar(radius)
}

/** 生成一张柔和的圆点贴图，给点图层当 sprite 用（避免额外请求图片）。 */
export function createRadialTexture(size = 128): THREE.Texture {
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const context = canvas.getContext('2d')!
  const gradient = context.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
  gradient.addColorStop(0, 'rgba(255,255,255,1)')
  gradient.addColorStop(0.35, 'rgba(255,255,255,0.85)')
  gradient.addColorStop(1, 'rgba(255,255,255,0)')
  context.fillStyle = gradient
  context.fillRect(0, 0, size, size)
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  return texture
}
