import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

export interface PlanetSceneOptions {
  onReady?: () => void
  onError?: () => void
}

export interface PlanetSceneHandle {
  setOffset(x: number, y: number, scale?: number): void
  setPaused(paused: boolean): void
  dispose(): void
}

const PLANET_POSITION = new THREE.Vector3(-0.55, 0.35, 0)
const PLANET_QUATERNION = new THREE.Quaternion(0.413011163, 0.581873119, -0.061157357, 0.697929323)

const CAMERA = {
  position: new THREE.Vector3(0.03301453835, 0.69856543589, 33.25363458814),
  target: new THREE.Vector3(-0.1, 0.1, 0),
  fov: 31.41727565803149,
  near: 0.1,
  far: 150,
  referenceAspect: 4 / 3
}

const ATMOSPHERE = {
  center: PLANET_POSITION,
  lightDirection: new THREE.Vector3(0.85052991, 0.45067921, 0.27108523).normalize(),
  lightAmbient: 0.1,
  layers: [
    { radius: 5.064, power: 8, opacity: 0.7, colorLinear: [0.16, 0.48, 1.0], emission: 5.0 },
    { radius: 5.102, power: 12, opacity: 0.25, colorLinear: [0.18, 0.22, 1.0], emission: 0.8 }
  ]
}

const ASSET_BASE = `${import.meta.env.BASE_URL}media/planet/`

function cinematicFov(baseFov: number, referenceAspect: number, aspect: number) {
  return THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(baseFov) / 2) * Math.max(1, referenceAspect / aspect)))
}

export function createPlanetScene(host: HTMLElement, options: PlanetSceneOptions = {}): PlanetSceneHandle {
  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.AgXToneMapping
  renderer.toneMappingExposure = 2 ** 0.35
  renderer.setClearColor(0x02040a, 1)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75))
  const canvas = renderer.domElement
  canvas.setAttribute('aria-hidden', 'true')
  canvas.style.touchAction = 'pan-y'
  host.appendChild(canvas)

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(CAMERA.fov, 1, CAMERA.near, CAMERA.far)
  camera.position.copy(CAMERA.position)
  camera.lookAt(CAMERA.target)

  // Whole composition can slide horizontally/vertically for hero layouts.
  const composer = new THREE.Group()
  scene.add(composer)

  const planetPivot = new THREE.Group()
  planetPivot.position.copy(PLANET_POSITION)
  composer.add(planetPivot)

  let planetMesh: THREE.Mesh | null = null
  let background: THREE.Texture | null = null
  let disposed = false
  let paused = false
  let running = false
  let frameId = 0
  let ready = false

  const geometryCache: THREE.BufferGeometry[] = []
  const materialCache: THREE.Material[] = []

  function addAtmosphere() {
    const geometry = new THREE.SphereGeometry(1, 96, 48)
    geometryCache.push(geometry)
    for (const layer of ATMOSPHERE.layers) {
      const material = new THREE.ShaderMaterial({
        uniforms: {
          tint: { value: new THREE.Color().fromArray(layer.colorLinear).multiplyScalar(layer.emission) },
          power: { value: layer.power },
          opacity: { value: layer.opacity },
          sunDirection: { value: ATMOSPHERE.lightDirection.clone() },
          ambient: { value: ATMOSPHERE.lightAmbient }
        },
        vertexShader: `varying vec3 worldNormal; varying vec3 worldPosition;
          void main(){ vec4 world = modelMatrix * vec4(position, 1.0); worldPosition = world.xyz;
          worldNormal = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * world; }`,
        fragmentShader: `uniform vec3 tint; uniform float power; uniform float opacity;
          uniform vec3 sunDirection; uniform float ambient; varying vec3 worldNormal; varying vec3 worldPosition;
          void main(){ vec3 n = normalize(worldNormal); vec3 v = normalize(cameraPosition - worldPosition);
            float rim = pow(1.0 - clamp(abs(dot(n, v)), 0.0, 1.0), power);
            float light = max(dot(n, sunDirection), 0.0) + ambient;
            gl_FragColor = vec4(tint, clamp(rim * opacity * light, 0.0, 1.0));
            #include <tonemapping_fragment>
            #include <colorspace_fragment>
          }`,
        transparent: true,
        depthWrite: false,
        side: THREE.FrontSide
      })
      materialCache.push(material)
      const shell = new THREE.Mesh(geometry, material)
      shell.position.copy(ATMOSPHERE.center)
      shell.scale.setScalar(layer.radius)
      composer.add(shell)
    }
  }

  function addLights() {
    const specs = [
      { color: [1, 0.86, 0.74], intensity: 3.5, position: [12, 7, 4] },
      { color: [0.17, 0.35, 1], intensity: 0.12, position: [-8, 4, 7] },
      { color: [1, 0.49, 0.3], intensity: 0.6, position: [6, 7, -4] }
    ]
    for (const spec of specs) {
      const light = new THREE.DirectionalLight(new THREE.Color().fromArray(spec.color), spec.intensity)
      light.position.fromArray(spec.position)
      light.target.position.copy(PLANET_POSITION)
      composer.add(light, light.target)
    }
    composer.add(new THREE.AmbientLight(new THREE.Color().fromArray([0.05, 0.065, 0.13]), 0.13))
  }

  addAtmosphere()
  addLights()

  const loader = new GLTFLoader()
  loader.load(
    `${ASSET_BASE}planet.glb`,
    (gltf) => {
      if (disposed) return
      planetMesh = gltf.scene.getObjectByName('Planet_Core') as THREE.Mesh | null
      if (!planetMesh) {
        options.onError?.()
        return
      }
      planetMesh.position.set(0, 0, 0)
      planetMesh.quaternion.copy(PLANET_QUATERNION)
      const material = planetMesh.material as THREE.MeshStandardMaterial
      if (material) material.roughness = 0.92
      planetPivot.add(planetMesh)
    },
    undefined,
    () => {
      if (!disposed) options.onError?.()
    }
  )

  fetch(`${ASSET_BASE}space-subtle.webp`)
    .then((response) => response.blob())
    .then((blob) => createImageBitmap(blob, { imageOrientation: 'flipY' }))
    .then((bitmap) => {
      if (disposed) {
        bitmap.close()
        return
      }
      background = new THREE.Texture(bitmap)
      background.flipY = false
      background.colorSpace = THREE.SRGBColorSpace
      background.needsUpdate = true
      scene.background = background
    })
    .catch(() => {})

  function resize() {
    const width = Math.max(host.clientWidth, 1)
    const height = Math.max(host.clientHeight, 1)
    camera.aspect = width / height
    camera.fov = cinematicFov(CAMERA.fov, CAMERA.referenceAspect, camera.aspect)
    camera.updateProjectionMatrix()
    renderer.setSize(width, height, false)
  }

  const resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(host)
  resize()

  const clock = new THREE.Clock()
  let spinAngle = 0
  let dragging = false
  let touchCandidate: { id: number; x: number; y: number } | null = null
  let lastX = 0
  let lastY = 0
  let dragYaw = 0
  let dragPitch = 0

  const spinQ = new THREE.Quaternion()
  const dragQ = new THREE.Quaternion()
  const dragEuler = new THREE.Euler()
  const worldUp = new THREE.Vector3(0, 1, 0)

  function onPointerDown(event: PointerEvent) {
    if (event.pointerType === 'mouse') {
      if (event.button !== 0) return
      dragging = true
      lastX = event.clientX
      lastY = event.clientY
      canvas.setPointerCapture(event.pointerId)
      return
    }
    touchCandidate = { id: event.pointerId, x: event.clientX, y: event.clientY }
  }

  function onPointerMove(event: PointerEvent) {
    if (!dragging && touchCandidate && touchCandidate.id === event.pointerId) {
      const dx = event.clientX - touchCandidate.x
      const dy = event.clientY - touchCandidate.y
      if (Math.abs(dx) > 10 && Math.abs(dx) > Math.abs(dy)) {
        dragging = true
        lastX = touchCandidate.x
        lastY = touchCandidate.y
        touchCandidate = null
        canvas.setPointerCapture(event.pointerId)
      }
    }
    if (!dragging) return
    dragYaw += (event.clientX - lastX) * 0.005
    dragPitch += (event.clientY - lastY) * 0.003
    dragPitch = Math.max(-1.2, Math.min(1.2, dragPitch))
    lastX = event.clientX
    lastY = event.clientY
  }

  function onPointerUp(event: PointerEvent) {
    if (touchCandidate && touchCandidate.id === event.pointerId) touchCandidate = null
    if (dragging) {
      dragging = false
      if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId)
    }
  }

  canvas.addEventListener('pointerdown', onPointerDown)
  canvas.addEventListener('pointermove', onPointerMove)
  canvas.addEventListener('pointerup', onPointerUp)
  canvas.addEventListener('pointercancel', onPointerUp)

  function renderFrame() {
    const dt = Math.min(clock.getDelta(), 0.1)
    if (!dragging) spinAngle += dt * 0.05
    spinQ.setFromAxisAngle(worldUp, spinAngle)
    dragEuler.set(dragPitch, dragYaw, 0, 'YXZ')
    dragQ.setFromEuler(dragEuler)
    planetPivot.quaternion.copy(spinQ).multiply(dragQ)
    renderer.render(scene, camera)
    if (!ready && planetMesh) {
      ready = true
      options.onReady?.()
    }
  }

  function loop() {
    if (disposed || paused) {
      running = false
      return
    }
    renderFrame()
    frameId = requestAnimationFrame(loop)
  }

  function start() {
    if (disposed || paused || running) return
    running = true
    clock.getDelta()
    frameId = requestAnimationFrame(loop)
  }

  loop()

  return {
    setOffset(x: number, y: number, scale = 1) {
      composer.position.set(x, y, 0)
      composer.scale.setScalar(scale)
    },
    setPaused(next: boolean) {
      if (paused === next) return
      paused = next
      if (paused) {
        cancelAnimationFrame(frameId)
        running = false
      } else {
        start()
      }
    },
    dispose() {
      if (disposed) return
      disposed = true
      cancelAnimationFrame(frameId)
      resizeObserver.disconnect()
      canvas.removeEventListener('pointerdown', onPointerDown)
      canvas.removeEventListener('pointermove', onPointerMove)
      canvas.removeEventListener('pointerup', onPointerUp)
      canvas.removeEventListener('pointercancel', onPointerUp)
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry?.dispose()
          const materials = Array.isArray(object.material) ? object.material : [object.material]
          materials.forEach((material) => {
            for (const value of Object.values(material as Record<string, unknown>)) {
              if (value instanceof THREE.Texture) (value as THREE.Texture).dispose()
            }
            material.dispose()
          })
        }
      })
      geometryCache.forEach((geometry) => geometry.dispose())
      materialCache.forEach((material) => material.dispose())
      background?.dispose()
      renderer.dispose()
      renderer.forceContextLoss()
      canvas.remove()
    }
  }
}
