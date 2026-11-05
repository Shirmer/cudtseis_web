import { readFile, writeFile } from 'node:fs/promises'
const entry = new URL('../dist/index.html', import.meta.url)
const company = await readFile(entry, 'utf8')
const product = company
  .replace(/<title>[^<]*<\/title>/, '<title>GeoCamera 地质相机 | 深视地球</title>')
  .replace(/(name="description"\s+content=")[^"]*/,
    '$1GeoCamera 地质相机，为地质调查、工程勘察与野外教学提供影像定位、路线管理、云端同步与报告导出。')
  .replace('property="og:site_name" content="深视地球"', 'property="og:site_name" content="GeoCamera"')
  .replace('type="image/png" href="/brand/deepseek-earth-logo.png"', 'type="image/png" href="/brand/geocamera-favicon.png"')
  .replace('rel="apple-touch-icon" href="/brand/deepseek-earth-logo.png"', 'rel="apple-touch-icon" href="/brand/geocamera-touch-icon.png"')
if (product === company || !product.includes('<title>GeoCamera')) throw new Error('Product entry not generated')
await writeFile(new URL('../dist/geocamera.html', import.meta.url), product)
console.log('Generated dedicated GeoCamera HTML metadata')
