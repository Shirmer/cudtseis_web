# 地球组件（planet）

首页右侧的地球，以及 `/earth` 全屏页共用的同一套 Three.js 渲染。进入视口才跑、离开就暂停。

```
planet-config.ts      所有可调参数（贴图、朝向、自转、缩放、打光、图层开关）
planet-scene.ts       渲染与图层注册
layers/               图层系统
  types.ts            PlanetLayer / LayerContext 接口
  layer-manager.ts    图层的开关、透明度、逐帧更新、销毁
  cloud-layer.ts      云层
  quake-layer.ts      地震点位（点状数据图层的参考实现）
  quake-data.ts       地震演示数据
  weather-layer.ts    天气：气旋/风暴（面状效果图层的参考实现）
  weather-data.ts     气旋演示数据
  current-layer.ts    洋流：路径线 + 流动粒子（路径数据图层的参考实现）
  current-data.ts     洋流路径演示数据
  geo-layer.ts        地质：断层线 + 火山点（线段 + 标注点图层的参考实现）
  geo-data.ts         断层带 / 板块边界 / 活火山演示数据
  paths.ts            经纬度路径插值、线段构建等公用工具
  sphere.ts           经纬度 -> 球面坐标等工具
../components/PlanetHero.vue   挂载、海报兜底、缩放控件、图层开关（全屏页）
../views/EarthView.vue         /earth 全屏页：只有地球 + 返回按钮，业务 UI 叠加在这里
```

## 两个入口

| 场景 | 说明 |
| --- | --- |
| 首页首屏 | `PlanetHero`（默认 `variant="hero"`），构图偏右给文案让位，右下角有「全屏地球」按钮 |
| `/earth` | `EarthView`，`variant="full"`，地球居中铺满视口；`Esc` 或左上角「返回首页」退出；带 `/en/earth` 英文路由 |

首页按钮只负责 `emit('expand')`，跳转在 `HomeView.goEarth()` 里；想换成直接 `<RouterLink>` 或加导航项，改那一处即可。

## 图层系统

图层都实现 `PlanetLayer`（`id / name / object / setVisible / setOpacity / update / dispose`），
由 `LayerManager` 统一注册，`planet-scene.ts` 的 `buildLayers()` 按配置创建。
`/earth` 左侧的开关会自动出现，不用改 UI。

已经有的图层：

| 图层 | 说明 | 参数 |
| --- | --- | --- |
| 云层 `clouds` | 复用星球几何体贴一层云，随地球转动并独立漂移，按太阳方向分昼夜 | `layers.clouds.*` |
| 地震 `quakes` | 经纬度点位，震级决定大小，带扩散环动画，支持按年份回放；时间轴向前推进时大地震泛起冲击波纹 | `layers.quakes.*`（波纹见 `layers.quakes.ripple`） |
| 天气 `weather` | 气旋：贴着地表的球冠 + shader 画旋转对数螺旋，自带台风眼 | `layers.weather.*`，数据在 `layers/weather-data.ts` |
| 洋流 `currents` | 经纬度路径插值成球面曲线，暗线打底 + 亮点沿线流动 | `layers.currents.*`，数据在 `layers/current-data.ts` |
| 地质 `geo` | 断层带 / 板块边界画线段，火山用三角形点位 | `layers.geo.*`，数据在 `layers/geo-data.ts` |

### 加一个新图层

1. 新建 `layers/xxx-layer.ts`，实现 `PlanetLayer`；用 `context.pivot` 当父节点就能跟着地球转，
   用 `latLonToVector(context.planetGeometry, lat, lon, context.radius)` 把经纬度换算成球面坐标。
2. 在 `planet-config.ts` 的 `layers` 里加一段配置。
3. 在 `planet-scene.ts` 的 `buildLayers()` 里 `manager.add(new XxxLayer(context, ...), {...})`。

渲染循环、开关、销毁都会自动接上；`update(dt, elapsed)` 里做动画，
`context.now()` 可以拿到当前时间做按时间演算的效果。

三种现成的参考实现，按数据形态挑最接近的抄：

| 数据形态 | 抄哪个 |
| --- | --- |
| 离散点位（地震、钻孔、采样点） | `quake-layer.ts` |
| 面状/区域效果（气旋、温度场、干旱区） | `weather-layer.ts` |
| 路径/流线（洋流、剖面路线） | `current-layer.ts` |
| 线段 + 标注点（断层线、地质界线、钻孔） | `geo-layer.ts` |

天气图层的球冠做法值得记一下：`SphereGeometry` 开一个小的 `thetaLength` 就是贴合的球冠，
再用 `setFromUnitVectors(+Y, 目标方向)` 转到经纬度位置，比贴一张 billboard 更贴合球面。

### 悬停拾取（信息卡）

图层只要实现两个可选方法，鼠标悬停和 `setHighlight` 就会自动生效：

```ts
getPickables(): Pickable[]                       // { id, label, detail, position }，position 用图层本地坐标
setHighlight(id: string | null)                  // 高亮某个元素
```

场景侧做的是屏幕空间投影 + 最近点匹配（`PICK_RADIUS = 16px`），并对球体背面做点乘剔除，
比 `Raycaster` 便宜很多；结果通过 `onHover(info | null)` 抛给 Vue，`PlanetHero` 里渲染成跟随光标的信息卡。
`picking` 只在对 `/earth` 时开启，首页保持干净。

现在四类元素都能悬停：地震点、火山、气旋、洋流路径、断层带（断层/洋流按沿线取样成若干可拾取点，
所以鼠标放到线附近就能看到名称）。

新图层想支持悬停，照着 `quake-layer.ts` 的 `aHighlight` 属性 + `getPickables()` 抄即可。
注意 `getPickables()` 每 80ms 会被调用一次，**结果要缓存**（各图层都在构造/`setData` 时算好），
否则每帧都会重新分配上百个对象。

### 时间轴

图层实现两个可选方法就能接上底部时间轴：

```ts
setTime(value: number): void            // 时间轴位置（地震这里是年份）
getTimeRange(): { min: number; max: number }
```

地震层的做法是给每个点存一个 `aYear` 属性、材质里放一个 `uYear` uniform，
顶点着色器把 `aYear > uYear` 的点移出裁剪空间，再用 `appear` 做个弹出动画——
**不重建几何、不重新上传缓冲**，所以拖动时间轴是实时的。

`/earth` 底部的播放条只在「地震图层可见」时出现：拖动即时过滤，点播放从最早年份走到最新，
播完自动停；关掉图层再打开会回到「全部可见」。

### 时间轴

滑块上方那条按年份的分布条来自 `quake-layer.getHistogram()`：每年一根，柱高按该年事件数归一化
（空年份留一条 1px 的底），颜色用图层色。数据换源后分布条会跟着变，不用重绘场景。

### 导出图片

「保存」把当前画面导出为 PNG（同一帧内 `render()` + `toDataURL()`，不含 DOM 控件），
再叠一行角标：左下是 `深视地球 · GeoCamera`，右下是当前视角 `104.1°E 30.9°N 125% 2024`
（经度 / 纬度 / 缩放 / 时间轴年份，年份只有打开地震层时才有）。
这一层是画在离屏 canvas 上的，如果渲染失败会回退成无水印的原图。

### 分享链接

「分享」按钮把当前状态写进 URL 并复制到剪贴板：

```
/earth?lon=104.1&lat=30.9&zoom=1.50&layers=clouds,quakes&year=2010
```

| 参数 | 含义 |
| --- | --- |
| `lon` / `lat` | 正对镜头的经纬度 |
| `zoom` | 缩放倍数 |
| `layers` | 可见图层 id，逗号分隔 |
| `year` | 时间轴年份 |

打开链接会自动还原。注意 `lon/lat` 是在星球贴图加载时按**当时的相机位置**求朝向的，
所以带 `zoom` 的链接也能准确对准（相机拉近后"正对镜头"的点本来就会偏一点）。

### 巡游模式

`/earth` 右下角「巡游」按钮：强制自转（`spin.tourBoost` 倍速）并把时间轴循环播放，
适合展会大屏无人值守。点地球、拖拽或手动播放都会立刻退出巡游，点控件不会。

### 图例与导出

`getCount?()` 返回的数据条数会显示在 `/earth` 左侧图层开关上（如「地震 20」）。
右下角的「保存」按钮调用 `scene.capture()` 导出当前画面：

```ts
capture(): string | null   // 同一帧内 render 后 toDataURL，导出的是纯 3D 画面，不含 DOM 控件
```

### 接真实数据

地震层已经接到外置目录 `public/data/earthquakes.json`，换数据不用改代码：

```json
{
  "source": "…",
  "updated": "2026-10-18",
  "events": [
    { "lat": 31.0, "lon": 103.4, "magnitude": 7.9, "place": "中国 四川 汶川", "time": "2008-05-12" }
  ]
}
```

- 路径在 `layers.quakes.dataUrl` 配置，留空则只用内置示例
- 兼容 `{ events: [...] }` 和直接给数组两种写法
- 单条解析失败会跳过；整份失败/为空则回退到 `layers/quake-data.ts` 的示例数据
- 加载成功后热替换：图例数量、时间轴范围、悬停信息卡一起更新，不重建场景

图层数据都在 `*-data.ts` 里，和渲染完全分离。运行期换数据用 `setData()`（地震层已经实现）：

```ts
const quakes = scene.getLayer('quakes') as QuakeLayer | undefined
const events = await fetch('/api/earthquakes?days=30').then(r => r.json())
quakes?.setData(events)   // 只重建几何属性，材质和 shader 不动
```

新图层想支持热更新，照着 `quake-layer.ts` 的 `buildGeometry()` / `setData()` 拆一下即可。

> 注意：自定义 shader 里用配置色时记得 `convertSRGBToLinear()`，
> 否则颜色会被当成线性值再转一次 sRGB，整体发白（三角点、粒子都踩过这个坑）。

## 改美术时最常动的几项

| 想改什么 | 改哪里 | 说明 |
| --- | --- | --- |
| 换地球贴图 | `assets.dayMap` / `dayMapHigh` / `nightMap` | 2:1 等距柱状图，放 `public/media/planet/`，路径不带前导斜杠 |
| 换兜底海报 | `assets.poster`（首页）/ `assets.posterFull`（全屏页） | 加载完成前和降级时显示 |
| 打开时正对哪块大陆 | `initial.longitude` / `initial.latitude` | 默认 103.9 / 30.6（成都），东经北纬为正 |
| 地球在画面里的位置、大小 | `layout.hero.*`（首页）/ `layout.full.*`（全屏页） | 各按容器宽高比三档切换，x 右为正、y 上为正 |
| 自转快慢、停下多久恢复 | `spin.speed` / `spin.resumeDelay` | speed 是弧度/秒，0.045 ≈ 两分半一圈 |
| 拖拽手感 | `drag.*` | 灵敏度、上下翻转限位、惯性衰减 |
| 点击聚焦 | `focus.ease` / `focus.hold` | 转动快慢、聚焦后暂停自转的秒数 |
| 巡游模式 | `spin.tourBoost` | 巡游时的自转倍数 |
| 缩放范围 | `zoom.min` / `zoom.max` / `zoom.step` | 1 = 初始大小 |
| 太阳方向（决定晨昏线位置） | `sunDirection` + `lights[0].position` | 两者要大致同向，否则夜景和打光会打架 |
| 亮度和氛围 | `lights[].intensity` / `ambient.intensity` / `material.nightIntensity` | 夜面城市灯光强度在 `nightIntensity` |
| 晨昏线暖光 | `material.twilightIntensity` | 日出/日落那条暖色散射带，0 关闭 |
| 海面高光 | `material.oceanRoughness` / `oceanSpecular` / `oceanThreshold` | 用白天贴图的「蓝色占比」判断海洋，海洋更光滑；`oceanSpecular` 控高光强度 |
| 大气光晕 | `atmosphere.layers` | power 越大边缘越窄，emission 控制亮度；`blending: 'additive'` 的层只提亮不压暗星空 |
| 云量 / 云层浓度 | `layers.clouds.threshold` / `opacity` | threshold 调大云变少，opacity 控制通透度 |
| 云的移动速度 | `layers.clouds.drift` | 弧度/秒，与地球自转叠加 |
| 地震点大小 / 颜色 | `layers.quakes.size` / `magnitudeScale` / `color` | 点位尺寸随视角缩放 |
| 地震波纹 | `layers.quakes.ripple.*` | `minMagnitude` 控制触发门槛，`life`/`maxRadius` 控制扩散节奏 |
| 气旋数量 / 大小 / 颜色 | `layers.weather.*`、`weather-data.ts` | `altitude` 要高于云层，否则会被云盖住 |
| 洋流流速 / 粒子大小 | `layers.currents.speed` / `size` / `dash` | `dash` 是每条路径上的流动段数 |

改完刷新页面即可，Vite 会热更新。

## 往 `/earth` 上加业务 UI

`EarthView.vue` 里留了叠加层位置，直接加元素并把 `z-index` 设到 3 以上即可（`.earth-page::after` 的渐变层是 2，控件是 3/4）：

```vue
<!-- 后续业务 UI（点位、图例、数据图层、侧栏等）叠加在这一层，z-index 高于 3 即可 -->
```

地球区域的 DOM 层级：画布 `z-index: auto` → 渐变遮罩 `::after: 2` → 缩放控件 `3` → 顶栏/返回 `4`。
如果要做点击地球取经纬度之类的交互，在 `planet-scene.ts` 的 pointer 事件里把屏幕坐标转成球面经纬度，再通过 `options` 回调抛给 Vue 即可。

## 调试参数

```
/?lon=116&lat=39     指定初始朝向（北京），方便对贴图方向
/?spin=0             冻结自转，方便截图和校色
/?perf              左下角显示帧率与当前渲染分辨率
/?debug             把场景句柄挂到 window.__planet，可在控制台调图层、换数据
/earth?spin=0        全屏页同样支持这些参数
```

## 实现要点

- **朝向**：`faceQuaternion()` 从模型 UV 里找离目标经纬度最近的顶点，再把它转到镜头方向。换任意球体模型都不用重调角度。
- **夜面灯光**：`onBeforeCompile` 注入一段 shader，用太阳方向算 `daylight`，只在背光面叠加夜景贴图。白天那一面不会出现城市灯光。
- **晨昏线**：夜面灯光那段 shader 里顺带算了一条 `sunDot` 落在 ±0.2 附近的暖色带，
  模拟日出/日落的散射，让明暗交界不是一刀切。
- **海面高光**：同一段 `onBeforeCompile` 里再改一次 `roughnessFactor`——按贴图的蓝色占比把海洋的粗糙度从 0.92 降到 0.42，
  阳光只在洋面上留下镜面反光，陆地保持哑光。深蓝海洋在线性空间里也很暗，所以用「蓝占比」而不是「蓝-红差值」。
- **模型并行加载**：`PlanetHero` 在 `await import('planet-scene')` 之前就发起 glb 的 fetch，把 Promise 通过
  `options.modelBuffer` 传给场景，场景用 `GLTFLoader.parse()` 解析。限速 400KB/s 实测：glb 的请求开始时间
  从"分块下载完之后"提前到"和分块同一时刻"，提前约 1 秒。
- **贴图预加载**：白天/夜景贴图在 `await import()` 之前用 `<link rel="preload" as="image">` 起头，
  场景模块里再请求时直接命中缓存（实测 0ms）。限速 500KB/s 下"导航 → 就绪"从 4032ms 降到 3780ms。
- **贴图分级**：首屏 2K，空闲 1.2 秒后换 4K（触屏设备跳过：多下 480KB、多占 33MB 显存，
  而手机屏幕像素远小于 4K）；换图在 shader 里用 `detailMap` + `detailMix` 做 450ms **交叉淡入**，
  淡完再把 `material.map` 换成 4K 并释放旧图，避免瞬切闪一下。
- **入场**：星球真正显示时镜头从 8% 远处缓入，1.4 秒归位（在加载期间不会空放）。
- **性能**：动态分辨率（帧率不够就降 dpr，有余量再升回去）、离开视口暂停、`prefers-reduced-motion` / 省流量 / 无 WebGL 直接回退静态海报。
- **交互**：拖拽旋转（带惯性，向下拖动画面跟着往下走）、右下角按钮缩放、双击或「复位」回到初始视角、`⌘/Ctrl + 滚轮` 缩放（普通滚轮留给页面滚动，可在 `zoom.wheelRequiresModifier` 里改）。
- **键盘**：`←/→/↑/↓` 旋转、`+/-` 缩放、`R` 复位、`空格` 播放/暂停时间轴（只在 `/earth` 生效，输入框内不拦截）。
- **巡游的影院状态**：巡游开启时图例与工具条压到 34% 透明度，让地球成为主体；鼠标移上去或
  键盘焦点进入会恢复。注意点击后要主动 `blur()`，否则 `:focus-within` 会把压暗顶回去。
- **首次引导**：第一次进入 `/earth` 会显示一张提示卡（拖拽/点击/巡游），点「开始探索」或 9 秒后消失，
  用 `localStorage['geocamera:earth-guide-v1']` 记住；任何操作也会提前关掉它。
- **点击聚焦**：点中一个点位后，解析出把该点转到镜头正前方的 yaw/pitch，再指数缓动过去；聚焦期间冻结自转，结束后额外停 `focus.hold` 秒。求解时会把自转角并进 yaw，所以镜头不会突跳。
- **悬停**：屏幕空间投影 + 16px 最近点匹配（比 Raycaster 便宜），带背面剔除，结果通过 `onHover` 交给 Vue 渲染信息卡。

## 贴图来源

NASA Blue Marble（公共领域）：2004 年 7 月合成图，`world.topo.bathy.200407`；
夜景为 NASA Black Marble 2012。已转成 WebP，2K 约 170KB、4K 约 470KB。
