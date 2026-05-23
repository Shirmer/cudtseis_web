<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const handleWorkbenchClick = () => {
  router.push('/terra') 
}

// 模拟数据：统计
const stats = [
  { value: '5K+', label: '地震事件样本' },
  { value: '10TB', label: '波形数据积累' },
  { value: '99%', label: '模型准确率' }
]

// 模拟数据：新闻
const newsItems = [
  { 
    id: 1, 
    time: '10:42 AM', 
    tag: 'M 4.5', 
    tagClass: 'tag-warning', 
    title: '四川盆地及邻区发生中等强度震颤',
    summary: '监测网络在宜宾附近记录到地震活动。初步数据分析显示震源深度较浅，暂无次生灾害报告。',
    location: '四川·宜宾',
    depth: 12
  },
  { 
    id: 2, 
    time: '09:15 AM', 
    tag: 'SYSTEM', 
    tagClass: 'tag-info',
    title: '台网数据同步完成',
    summary: '所有野外监测台站均已上线，正以低于 50ms 的延迟传输实时波形数据。',
    location: '服务器节点 A',
    depth: null
  },
  { 
    id: 3, 
    time: '昨天', 
    tag: 'M 3.2', 
    tagClass: 'tag-normal',
    title: '监测到微弱余震活动',
    summary: '该地震事件符合区域断裂带应力释放的常规模式，属于正常地质活动。',
    location: '四川·泸定',
    depth: 8
  }
]

</script>

<template>
  <div class="journal-page">
    
    <!-- 1. 导航 -->
    <nav class="navbar">
      <div class="brand-group">
        <img src="/cdut_seislab_dino.svg" alt="CDUT SEISLAB Dinosaur Logo" class="nav-logo" />
        <div class="brand-text">CDUT SEISLAB</div>
      </div>
      
      <div class="nav-links">
        <a href="#research">科学研究</a>
        <a href="#faculty">研究团队</a>
        <a href="#tools">智能工具</a>

        <button class="nav-link-button" @click="router.push('/dashboard')">地震目录</button>
        <button class="nav-link-button" @click="router.push('/history')">历史数据</button>
        <button class="nav-link-button" @click="router.push('/rag')">RAG 工作台</button>

        <a href="#news">最新动态</a>
      </div>

      <!-- ★ 恢复右侧按钮，但绑定了新的空函数 handleWorkbenchClick -->
      <button class="btn-enter" @click="handleWorkbenchClick">进入工作台</button>
      
    </nav>

    <!-- 2. Hero 区域 -->
    <section class="hero-section">
      <div class="bg-text">SEISMOLOGY</div>
      
      <div class="hero-content">
        <div class="text-group">
          <h1 class="main-title">
            解码<br>
            深地构造
          </h1>
          <p class="sub-text">
            成都理工大学地震实验室：<br>
            地球物理学与人工智能的深度融合前沿。
          </p>
          <a href="#more" class="link-arrow">探索研究方法论 →</a>
        </div>

        <div class="visual-group">
          <div class="simple-image-card">
            <img src="/snow_moutain.png" alt="Deep Earth Structure" />
          </div>
        </div>
      </div>
    </section>

    <!-- 3. Parallax Window -->
    <section class="parallax-window">
      <div class="parallax-content">
        <div class="window-header">ABOUT US</div>
        <div class="window-body">
          <div class="desc-text">
            我们正在定义<br>地震研究的未来。<br>
            <span class="highlight">以前所未有的清晰度<br>重构地球内部结构。</span>
          </div>
          <div class="glass-card">
            <div class="stat-item" v-for="(item, index) in stats" :key="index">
              <div class="stat-num">{{ item.value }}</div>
              <div class="stat-label">{{ item.label }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 4. Faculty -->
    <section class="faculty-section" id="faculty">
      <div class="section-header">
        <h2>研究团队</h2>
        <p>汇聚地球物理与人工智能领域的顶尖学者</p>
      </div>
      <div class="team-grid">
        <div class="member-card">
          <div class="avatar"><img src="/lct.png" alt="梁春涛" style="object-fit: cover; object-position: top;" /></div>
          <h3>梁春涛</h3><span class="role">实验室主任</span><span class="field">固体地球物理学</span>
        </div>
        <div class="member-card">
          <div class="avatar"><img src="/fxl.png" alt="范兴利" style="object-fit: cover; object-position: top;" /></div>
          <h3>范兴利</h3><span class="role">教授</span><span class="field">固体地球物理学</span>
        </div>
        <div class="member-card">
          <div class="avatar"><img src="/ly.png" alt="林弈" style="object-fit: cover; object-position: top;" /></div>
          <h3>林弈</h3><span class="role">副教授</span><span class="field">固体地球物理学</span>
        </div>
        <div class="member-card">
          <div class="avatar"><img src="/lxy.png" alt="刘兴业" style="object-fit: cover; object-position: top;" /></div>
          <h3>刘兴业</h3><span class="role">教授</span><span class="field">固体地球物理学</span>
        </div>
      </div>
    </section>

    <!-- 5. Toolbox -->
    <section class="tools-section" id="tools">
      <div class="tool-header">INTELLIGENT TOOLBOX</div>
      <div class="tool-grid">
        <div class="tool-card large" @click="router.push('/dashboard')">
          <h3>地震事件目录可视化</h3>
          <p>基于 WebGL 的实时地震数据监测与可视化平台。</p>
        </div>

        <div class="tool-card" @click="router.push('/history')">
          <h3>历史地震数据检索</h3>
          <p>按时间、震级和区域快速筛选事件记录，支持表格化浏览。</p>
        </div>

        <div class="tool-card rag-card" @click="router.push('/rag')">
          <h3>RAG 知识工作台</h3>
          <p>进入完整文献问答、PDF 入库、批量任务和文档列表管理界面。</p>
        </div>
      </div>
    </section>

    <!-- 6. News -->
    <section class="news-section" id="news">
      <div class="news-container">
        <h2 class="section-divider-title">最新事件 / 预警信息</h2>
        <div class="news-grid">
          <div v-for="item in newsItems" :key="item.id" class="news-card-item">
            <div class="news-header-row">
              <span class="news-time">{{ item.time }}</span>
              <span class="news-tag" :class="item.tagClass">{{ item.tag }}</span>
            </div>
            <h3 class="news-title">{{ item.title }}</h3>
            <p class="news-summary">{{ item.summary }}</p>
            <div class="news-meta-footer">
              <span>📍 {{ item.location }}</span>
              <span v-if="item.depth" style="margin-left:15px">深度: {{ item.depth }}km</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 7. Contact Us -->
    <section class="contact-section">
      <div class="contact-container">
        <div class="contact-header">
          <h2>联系我们</h2>
          <p>Contact Us</p>
        </div>
        <div class="contact-content">
          <div class="contact-item">
            <div class="contact-text">
              <h4>地址 / Address</h4>
              <p>四川省成都市成华区二仙桥东三路1号<br>成都理工大学地球物理学院</p>
            </div>
          </div>
          <div class="contact-item">
            <div class="contact-text">
              <h4>邮箱 / Email</h4>
              <p>seislab@cdut.edu.cn<br>cooperation@cdut.edu.cn</p>
            </div>
          </div>
          <div class="contact-item">
            <div class="contact-text">
              <h4>电话 / Phone</h4>
              <p>+86 028-12345678</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 8. Footer -->
    <footer class="simple-footer">
      <div class="copyright">© 2025 成都理工大学地震实验室 | CDUT SEISLAB</div>
    </footer>
  </div>
</template>

<style scoped>
/* --- 全局基础 --- */
.journal-page { 
  font-family: "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif; 
  color: #111; 
  background: #fff; 
  overflow-x: hidden; 
}
.main-title, .brand-text, .window-body, .section-header h2, .contact-header h2 { 
  font-family: "Times New Roman", "Songti SC", "SimSun", serif; 
}

/* --- 1. 导航 (样式微调) --- */
.navbar { display: flex; justify-content: space-between; align-items: center; padding: 20px 40px; position: sticky; top: 0; z-index: 100; background: rgba(255,255,255,0.9); backdrop-filter: blur(10px); border-bottom: 1px solid #eee; }
.brand-group { display: flex; align-items: center; gap: 12px; }
.nav-logo { height: 40px; width: auto; }
.brand-text { font-size: 20px; font-weight: 800; letter-spacing: 1px; color: #000; font-family: "Helvetica Neue", sans-serif; }

/* 导航链接容器 */
.nav-links { 
  display: flex; 
  align-items: center; 
}

/* 常规链接样式 */
.nav-links a,
.nav-link-button { 
  margin: 0 15px; 
  text-decoration: none; 
  color: #666; 
  font-size: 15px; 
  font-weight: 500; 
  transition: color 0.2s;
  border: 0;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
}
.nav-links a:hover,
.nav-link-button:hover { color: #dc2626; }

/* 右侧按钮：保持黑色药丸形状，但目前功能为空 */
.btn-enter { background: #000; color: #fff; border: none; padding: 8px 24px; border-radius: 20px; font-weight: bold; cursor: pointer; transition: transform 0.2s; font-size: 14px; }
.btn-enter:hover { transform: scale(1.05); }

/* --- 2. Hero Section --- */
.hero-section { position: relative; min-height: 85vh; display: flex; align-items: center; justify-content: center; padding: 0 5%; overflow: hidden; }
.bg-text { position: absolute; top: 12%; left: 50%; transform: translateX(-50%); font-size: 15vw; font-weight: 900; color: #f3f4f6; opacity: 0.6; z-index: 0; pointer-events: none; font-family: sans-serif; }
.hero-content { display: flex; justify-content: space-between; align-items: center; width: 100%; max-width: 1200px; z-index: 1; position: relative; }
.text-group { flex: 1; padding-right: 40px; z-index: 10; }
.main-title { font-size: 5rem; line-height: 1.2; margin-bottom: 25px; color: #111; letter-spacing: -1px; font-weight: bold; }
.sub-text { font-size: 1.2rem; color: #555; margin-bottom: 30px; max-width: 450px; line-height: 1.6; }
.link-arrow { color: #dc2626; text-decoration: none; font-weight: bold; border-bottom: 2px solid #dc2626; padding-bottom: 2px; }

/* --- 右侧视觉 --- */
.visual-group { width: 600px; height: 450px; position: relative; }
.simple-image-card {
  width: 100%; height: 100%;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(0,0,0,0.15);
  background: #f3f3f3;
}
.simple-image-card img {
  width: 100%; height: 100%;
  object-fit: cover;
  transition: transform 0.6s ease;
}
.simple-image-card:hover img {
  transform: scale(1.03);
}

/* --- 3. Parallax Window --- */
.parallax-window { position: relative; height: 600px; width: 100%; background-image: url('/snow_moutain.png'); background-attachment: fixed; background-position: center; background-size: cover; display: flex; align-items: center; justify-content: center; }
.parallax-window::before { content: ""; position: absolute; inset: 0; background: rgba(17, 24, 39, 0.7); z-index: 0; }
.parallax-content { position: relative; z-index: 1; width: 100%; max-width: 1000px; color: #fff; display: flex; flex-direction: column; }
.window-header { font-size: 12px; letter-spacing: 3px; font-weight: bold; color: #dc2626; margin-bottom: 20px; font-family: sans-serif; }
.window-body { display: flex; justify-content: space-between; align-items: flex-end; }
.desc-text { font-size: 2.2rem; line-height: 1.5; max-width: 60%; font-weight: bold; }
.desc-text .highlight { color: #d1d5db; font-size: 1.4rem; display: block; margin-top: 15px; font-weight: normal; opacity: 0.9; }
.glass-card { background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 16px; padding: 30px; display: flex; gap: 40px; transform: translateY(40px); box-shadow: 0 20px 40px rgba(0,0,0,0.3); }
.stat-item { text-align: center; }
.stat-num { font-size: 2rem; font-weight: 800; color: #fff; font-family: sans-serif; }
.stat-label { font-size: 0.9rem; color: #9ca3af; margin-top: 5px; }

/* Faculty */
.faculty-section { background: #f9fafb; padding: 100px 5% 60px; text-align: center; }
.section-header h2 { font-size: 2.2rem; margin-bottom: 10px; font-weight: bold; }
.section-header p { color: #666; margin-bottom: 50px; font-size: 1.1rem; }
.team-grid { display: flex; justify-content: center; gap: 60px; flex-wrap: wrap; max-width: 1000px; margin: 0 auto; }
.member-card { display: flex; flex-direction: column; align-items: center; }

/* ★ 头像修复 */
.avatar { 
  width: 120px; height: 120px; 
  border-radius: 50%; 
  border: 4px solid #fff; 
  overflow: hidden; 
  box-shadow: 0 4px 10px rgba(0,0,0,0.1); 
  margin-bottom: 15px; 
  transition: transform 0.3s; 
}
.member-card:hover .avatar { transform: scale(1.05); }
.avatar img { 
  width: 100%; height: 100%; 
  object-fit: cover; 
  object-position: center; 
}
.member-card h3 { font-size: 1.2rem; margin: 5px 0; font-weight: bold; }
.member-card .role { color: #dc2626; font-size: 0.9rem; font-weight: bold; margin-bottom: 2px; }
.member-card .field { color: #888; font-size: 0.85rem; }

/* Tools */
.tools-section { padding: 60px 5%; max-width: 1200px; margin: 0 auto; }
.tool-header { font-weight: bold; font-size: 0.9rem; margin-bottom: 20px; letter-spacing: 1px; color: #999; }
.tool-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; }
.tool-card { padding: 30px; border-radius: 12px; border: 1px solid #eee; background: #fff; transition: all 0.3s; cursor: pointer; position: relative; overflow: hidden; }
.tool-card:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.05); border-color: #dc2626; }
.tool-card h3 { font-size: 1.5rem; margin-bottom: 10px; font-weight: bold; }
.tool-card p { color: #666; line-height: 1.6; }
.tool-card.large { background: #f3f4f6; }
.tool-card.rag-card { border-color: rgba(220, 38, 38, 0.28); background: #fffafa; }

/* Section Title Style */
.section-divider-title { 
  font-size: 14px; font-weight: 800; letter-spacing: 2px; color: #000; 
  margin-bottom: 40px; border-bottom: 2px solid #000; padding-bottom: 10px; 
  display: inline-block; font-family: sans-serif;
}

/* News */
.news-section { padding: 60px 5%; background-color: #fff; border-top: 1px solid #eee; }
.news-container { max-width: 1200px; margin: 0 auto; }
.news-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 40px; }
.news-card-item { border-left: 1px solid #eee; padding-left: 20px; transition: border-color 0.3s; }
.news-card-item:hover { border-left-color: #dc2626; }
.news-header-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; font-family: 'Courier New', monospace; font-size: 11px; }
.news-tag { padding: 2px 6px; border-radius: 2px; color: #fff; font-weight: bold; }
.tag-warning { background-color: #f59e0b; }
.tag-info { background-color: #3b82f6; }
.tag-normal { background-color: #10b981; }
.news-title { font-size: 18px; line-height: 1.4; font-weight: 700; margin-bottom: 10px; color: #111; }
.news-summary { font-size: 14px; color: #666; line-height: 1.6; margin-bottom: 15px; text-align: justify; }
.news-meta-footer { font-size: 12px; color: #999; font-weight: 600; display: flex; align-items: center; }

/* Contact Section (Modified) */
.contact-section { 
  background-color: #111; 
  color: #fff; 
  padding: 40px 5%; 
}
.contact-container { max-width: 1000px; margin: 0 auto; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 40px; }
.contact-header { flex: 1; min-width: 250px; }
.contact-header h2 { font-size: 2.5rem; margin-bottom: 10px; color: #fff; }
.contact-header p { font-size: 1.2rem; color: #666; font-family: sans-serif; letter-spacing: 1px; }

.contact-content { 
  flex: 2; 
  display: grid; 
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
  gap: 30px; 
}
.contact-item { 
  display: flex; 
  gap: 12px; 
  align-items: flex-start; 
}
.contact-item h4 { 
  font-size: 13px; 
  color: #999; 
  margin: 0 0 5px 0; 
  text-transform: uppercase; 
  letter-spacing: 1px; 
  line-height: 1.4;
}
.contact-item p { 
  font-size: 14px; 
  line-height: 1.6; 
  color: #ddd; 
  margin: 0;
}

/* Footer */
.simple-footer { padding: 20px; background-color: #000; color: #444; text-align: center; font-size: 12px; border-top: 1px solid #222; }

/* Mobile */
@media (max-width: 768px) {
  .hero-content { flex-direction: column; text-align: center; }
  .text-group { padding-right: 0; margin-bottom: 40px; }
  .visual-group { width: 100%; max-width: 400px; height: 300px; }
  .bg-text { font-size: 20vw; top: 5%; }
  .window-body { flex-direction: column; align-items: center; text-align: center; }
  .glass-card { width: 100%; transform: translateY(0); flex-direction: column; gap: 20px; }
  .tool-grid { grid-template-columns: 1fr; }
  .nav-links { display: none; }
  .main-title { font-size: 3rem; }
  .contact-container { flex-direction: column; }
}
</style>
