<script setup lang="ts">
import { h, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NDropdown } from 'naive-ui'
import type { DropdownOption } from 'naive-ui'

const router = useRouter()

// --- 1. 下拉菜单配置 ---
const dbOptions: DropdownOption[] = [
  {
    label: '地震目录', 
    key: 'catalog'
  },
  {
    label: '论文',
    key: 'papers'
  },
  {
    label: '文献知识库',
    key: 'knowledge'
  }
]

// --- 2. 数据库下拉菜单逻辑 ---
// 点击"地震目录" -> 进入原来的 Dashboard 功能
const handleDbSelect = (key: string | number) => {
  if (key === 'catalog') {
    router.push('/dashboard') 
  } else if (key === 'papers') {
    router.push('/papers')
  } else if (key === 'knowledge') {
    router.push('/knowledge')
  }
}

// --- 3. 右侧按钮逻辑 (目前为空) ---
const handleWorkbenchClick = () => {
  // console.log('工作台按钮被点击 - 功能暂未开放')
  // 将来可以在这里写： router.push('/login') 或 弹出登录框
  // alert('功能开发中...')
  router.push('/terra') 
}

// 模拟数据：统计
const stats = [
  { value: '5K+', label: '文献解析量' },
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

// 论文数据库架构
const paperPipeline = [
  {
    id: 'source',
    title: '文献来源',
    desc: '汇聚 DOI、期刊页、arXiv、机构库与团队本地论文记录。'
  },
  {
    id: 'acquire',
    title: 'PDF / HTML 采集层',
    desc: '采集全文、摘要、元数据与可访问链接，保留来源追踪。'
  },
  {
    id: 'parse',
    title: '文档解析层',
    desc: '借鉴 RAG-Anything，拆解正文、表格、图表说明与公式。'
  },
  {
    id: 'chunk',
    title: '语义清洗与切块层',
    desc: '按章节、图表、方法、结论和专业术语进行语义切块。'
  },
  {
    id: 'store',
    title: '知识存储层',
    desc: '向量库 + 元数据库 + 轻量知识图谱共同承载证据。'
  },
  {
    id: 'retrieve',
    title: '混合检索层',
    desc: '融合向量、关键词、结构化字段和图谱关系检索。'
  },
  {
    id: 'generate',
    title: '生成层',
    desc: '借鉴 ResearchClaw 输出 Claim / Evidence / Reasoning / Citation。'
  },
  {
    id: 'output',
    title: '地震专业解读输出',
    desc: '面向构造、震源机制、危险性和监测场景给出可引用解释。'
  }
]

const retrievalModes = [
  '向量检索',
  '关键词检索',
  '结构化字段检索',
  '图谱关系检索'
]

const parserSlots = [
  '正文提取',
  '表格解析',
  '图片/图表说明',
  '公式识别'
]

// 模拟数据：论文数据库条目
const papers = [
  {
    id: 1,
    title: "Deep Learning for Real-time Earthquake Early Warning",
    authors: "Chuntao Liang, et al.",
    journal: "Nature Communications",
    year: "2024",
    type: "Claim-ready",
    evidence: "用于支撑实时预警模型与震相识别方法的证据链生成。",
    link: "#"
  },
  {
    id: 2,
    title: "Seismic Phase Picking using Transformer Networks",
    authors: "Xingli Fan, Yi Lin",
    journal: "GRL (Geophysical Research Letters)",
    year: "2023",
    type: "Method",
    evidence: "可解析为方法、实验数据、性能指标与引用证据。",
    link: "#"
  },
  {
    id: 3,
    title: "High-resolution Tomography of the Sichuan Basin",
    authors: "Yi Lin, Chuntao Liang",
    journal: "JGR: Solid Earth",
    year: "2023",
    type: "Region",
    evidence: "可关联四川盆地、速度结构、断裂构造等图谱节点。",
    link: "#"
  },
  {
    id: 4,
    title: "Automated Fault Detection with 3D CNNs",
    authors: "Xingye Liu, et al.",
    journal: "Computers & Geosciences",
    year: "2022",
    type: "Graph",
    evidence: "可抽取断层识别、模型结构、训练数据和图表证据。",
    link: "#"
  }
]
</script>

<template>
  <div class="journal-page">
    
    <!-- 1. 导航 -->
    <nav class="navbar">
      <div class="brand-group">
        <img src="/cdut_logo.png" alt="CDUT Logo" class="nav-logo" />
        <div class="brand-text">CDUT SEISLAB</div>
      </div>
      
      <div class="nav-links">
        <a href="#research">科学研究</a>
        <a href="#faculty">研究团队</a>
        <a href="#tools">智能工具</a>

        <!-- 数据库下拉菜单 -->
        <n-dropdown 
          trigger="hover" 
          :options="dbOptions" 
          @select="handleDbSelect"
        >
          <span class="nav-dropdown-trigger">
            数据库 <span class="arrow-icon">▾</span>
          </span>
        </n-dropdown>

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
        <!-- 这里的卡片依旧保持原逻辑，点击进入 Dashboard -->
        <div class="tool-card large" @click="router.push('/dashboard')">
          <h3>地震事件目录可视化</h3>
          <p>基于 WebGL 的实时地震数据监测与可视化平台。</p>
        </div>
        <div class="tool-card small" @click="router.push('/papers')">
          <h3>Paper Agent</h3>
          <p>与 5000+ 篇学术文献进行 AI 对话。</p>
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

    <!-- 7. Papers -->
    <section class="papers-section" id="papers">
      <div class="news-container">
        <h2 class="section-divider-title">论文数据库 / PAPER KNOWLEDGE BASE</h2>
        <div class="paper-module-hero">
          <div class="paper-module-copy">
            <span class="module-kicker">RAG-Anything Inspired Pipeline</span>
            <h3>从论文全文到可引用的地震专业证据链</h3>
            <p>
              论文模块不只展示 PDF 列表，而是把文献采集、文档解析、语义切块、知识存储、
              混合检索和 ResearchClaw 式生成组织成一条可追踪链路。
            </p>
          </div>
          <div class="parser-box">
            <span v-for="slot in parserSlots" :key="slot">{{ slot }}</span>
          </div>
        </div>

        <div class="pipeline-grid">
          <article v-for="(step, index) in paperPipeline" :key="step.id" class="pipeline-card">
            <div class="pipeline-index">{{ String(index + 1).padStart(2, '0') }}</div>
            <h3>{{ step.title }}</h3>
            <p>{{ step.desc }}</p>
          </article>
        </div>

        <div class="retrieval-band">
          <div>
            <span class="module-kicker">Hybrid Retrieval</span>
            <h3>向量库 + 元数据库 + 轻量知识图谱</h3>
          </div>
          <div class="retrieval-tags">
            <span v-for="mode in retrievalModes" :key="mode">{{ mode }}</span>
          </div>
        </div>

        <div class="cer-preview">
          <div class="cer-column">
            <span>Claim</span>
            <p>该论文是否支持某一区域构造或震源机制判断。</p>
          </div>
          <div class="cer-column">
            <span>Evidence</span>
            <p>直接引用正文、表格、图件说明或公式对应证据。</p>
          </div>
          <div class="cer-column">
            <span>Reasoning</span>
            <p>解释证据如何连接到地震学问题。</p>
          </div>
          <div class="cer-column">
            <span>Citation</span>
            <p>保留 DOI、年份、期刊和可访问来源。</p>
          </div>
        </div>

        <div class="paper-list">
          <div v-for="paper in papers" :key="paper.id" class="paper-card">
            <div class="paper-info">
              <div class="paper-meta">
                <span class="paper-journal">{{ paper.journal }}</span>
                <span class="paper-year">{{ paper.year }}</span>
                <span class="paper-type">{{ paper.type }}</span>
              </div>
              <h3 class="paper-title">{{ paper.title }}</h3>
              <p class="paper-authors">{{ paper.authors }}</p>
              <p class="paper-evidence">{{ paper.evidence }}</p>
            </div>
            <button class="btn-pdf" @click="router.push('/papers')">入库</button>
          </div>
        </div>
      </div>
    </section>

    <!-- 8. Contact Us -->
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

    <!-- 9. Footer -->
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
.nav-links a { 
  margin: 0 15px; 
  text-decoration: none; 
  color: #666; 
  font-size: 15px; 
  font-weight: 500; 
  transition: color 0.2s;
}
.nav-links a:hover { color: #dc2626; }

/* 数据库下拉触发器样式 */
.nav-dropdown-trigger {
  margin: 0 15px;
  color: #666;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: color 0.2s;
}
.nav-dropdown-trigger:hover {
  color: #dc2626; /* CDUT主题红 */
}
.arrow-icon {
  font-size: 12px;
  margin-left: 4px;
}

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
.tool-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
.tool-card { padding: 30px; border-radius: 12px; border: 1px solid #eee; background: #fff; transition: all 0.3s; cursor: pointer; position: relative; overflow: hidden; }
.tool-card:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.05); border-color: #dc2626; }
.tool-card h3 { font-size: 1.5rem; margin-bottom: 10px; font-weight: bold; }
.tool-card p { color: #666; line-height: 1.6; }
.tool-card.large { background: #f3f4f6; }

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

/* Papers Section */
.papers-section { padding: 70px 5% 90px; background-color: #fff; border-top: 1px solid #eee; }
.paper-module-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.8fr);
  gap: 28px;
  align-items: stretch;
  margin-bottom: 28px;
}
.paper-module-copy {
  padding: 30px;
  border-radius: 8px;
  background: #111827;
  color: #fff;
}
.module-kicker {
  display: inline-block;
  margin-bottom: 12px;
  color: #dc2626;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 1.5px;
  text-transform: uppercase;
}
.paper-module-copy h3,
.retrieval-band h3 {
  margin: 0 0 14px;
  font-size: 28px;
  line-height: 1.25;
}
.paper-module-copy p {
  max-width: 720px;
  margin: 0;
  color: #d1d5db;
  font-size: 15px;
  line-height: 1.8;
}
.parser-box {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 22px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
}
.parser-box span {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 72px;
  padding: 12px;
  border-radius: 6px;
  background: #fff;
  color: #111827;
  font-size: 14px;
  font-weight: 700;
  text-align: center;
  border: 1px solid #eee;
}
.pipeline-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 28px;
}
.pipeline-card {
  min-height: 170px;
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}
.pipeline-index {
  color: #dc2626;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 1px;
  margin-bottom: 14px;
}
.pipeline-card h3 {
  margin: 0 0 10px;
  font-size: 16px;
  line-height: 1.4;
}
.pipeline-card p {
  margin: 0;
  color: #666;
  font-size: 13px;
  line-height: 1.65;
}
.retrieval-band {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: center;
  padding: 24px 28px;
  margin-bottom: 22px;
  border-radius: 8px;
  background: #f3f4f6;
}
.retrieval-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}
.retrieval-tags span {
  padding: 8px 12px;
  border-radius: 999px;
  background: #fff;
  color: #111827;
  font-size: 13px;
  font-weight: 700;
  border: 1px solid #e5e7eb;
}
.cer-preview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 28px;
}
.cer-column {
  padding: 18px;
  border-left: 3px solid #dc2626;
  background: #fff7ed;
}
.cer-column span {
  display: block;
  margin-bottom: 8px;
  color: #9a3412;
  font-size: 13px;
  font-weight: 900;
}
.cer-column p {
  margin: 0;
  color: #555;
  font-size: 13px;
  line-height: 1.65;
}
.paper-list { display: flex; flex-direction: column; gap: 16px; }
.paper-card { 
  display: flex; justify-content: space-between; align-items: center; 
  padding: 25px; border: 1px solid #eee; border-radius: 8px; 
  transition: all 0.3s; background: #fafafa;
}
.paper-card:hover { border-color: #dc2626; background: #fff; box-shadow: 0 5px 15px rgba(0,0,0,0.05); }
.paper-info { flex: 1; padding-right: 20px; }
.paper-meta { font-size: 12px; font-weight: 700; color: #dc2626; margin-bottom: 8px; font-family: sans-serif; }
.paper-journal { margin-right: 10px; text-transform: uppercase; }
.paper-year { color: #999; }
.paper-type { margin-left: 10px; color: #111; background: #e5e7eb; padding: 2px 8px; border-radius: 999px; }
.paper-title { font-size: 18px; font-weight: bold; margin-bottom: 8px; color: #111; }
.paper-authors { font-size: 14px; color: #666; font-style: italic; }
.paper-evidence { margin: 8px 0 0; color: #555; font-size: 13px; line-height: 1.6; }
.btn-pdf { 
  display: inline-block; padding: 8px 16px; border: 1px solid #111; 
  color: #111; text-decoration: none; font-size: 12px; font-weight: bold; 
  border-radius: 4px; transition: all 0.2s; white-space: nowrap;
}
.btn-pdf:hover { background: #111; color: #fff; }

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
  .paper-module-hero,
  .pipeline-grid,
  .cer-preview {
    grid-template-columns: 1fr;
  }
  .retrieval-band {
    align-items: flex-start;
    flex-direction: column;
  }
  .retrieval-tags {
    justify-content: flex-start;
  }
  .paper-card { flex-direction: column; align-items: flex-start; gap: 15px; }
  .btn-pdf { width: 100%; text-align: center; }
}
</style>
