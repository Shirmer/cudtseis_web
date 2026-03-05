import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

// 建议移到这里：先把样式加载好，再渲染页面
import 'leaflet/dist/leaflet.css' 

// 引入 Naive UI 通用字体 
import 'vfonts/Lato.css' 
// 引入等宽字体 
import 'vfonts/FiraCode.css' 

const app = createApp(App)

app.use(router)

app.mount('#app')