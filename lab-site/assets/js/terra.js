/* Terra · local, buildless interaction prototype. No network or scientific computation. */
(() => {
  'use strict';
  const catalogPage = document.body.dataset.page === 'catalog';
  const paths = {
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    chat: '<path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-2 2V11.5a9.5 9.5 0 0 1 19 0Z"/><path d="M7 9h9M7 13h6"/>',
    globe: '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18M5 6.5h14M5 17.5h14"/>',
    wave: '<path d="M2 12h3l2-6 3 13 3-17 3 17 2-7h4"/>',
    spectrum: '<path d="M3 3v18h18M6 16l3-2 3-9 3 11 3-5 3 6"/>',
    pin: '<path d="M19 10c0 5-7 12-7 12S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2.5"/>',
    search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    book: '<path d="M12 5v16M12 5C9 3 5 3 2 4v15c3-1 7-1 10 2 3-3 7-3 10-2V4c-3-1-7-1-10 1Z"/>',
    translate: '<path d="M3 5h12M9 2v3M5 5c0 5 5 9 9 10M13 5c0 5-5 9-10 10M13 21l4-10 4 10M15 17h4"/>',
    note: '<path d="M14 3H4v18h16V11M9 15l1-4L19 2l3 3-9 9-4 1Z"/>',
    file: '<path d="M14 2H4v20h16V8l-6-6Z M14 2v6h6M8 13h8M8 17h6"/>',
    arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    'arrow-left': '<path d="M20 12H4m6-6-6 6 6 6"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 4 2c-1.5 1-1.5 1.5-1.5 2M12 17h.01"/>',
    upload: '<path d="M12 16V3m-5 5 5-5 5 5M3 15v6h18v-6"/>',
    spark: '<path d="m12 2 2.7 7.3L22 12l-7.3 2.7L12 22l-2.7-7.3L2 12l7.3-2.7L12 2Z"/>',
    download: '<path d="M12 3v13m-5-5 5 5 5-5M3 17v4h18v-4"/>'
  };
  const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.file}</svg>`;
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  document.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML = icon(el.dataset.icon); });
  const tools = [
    {id:'overview',name:'工作台概览',en:'WORKSPACE',icon:'grid',group:'开始',desc:'从一个问题出发，找到适合的研究工具。'},
    {id:'assistant',name:'科研问答',en:'RESEARCH ASSISTANT',icon:'chat',group:'开始',desc:'梳理研究问题，组织思路与文献证据。'},
    {id:'catalog',name:'地震目录',en:'EARTHQUAKE CATALOG',icon:'globe',group:'地震数据',desc:'按时间、区域和震级探索地震事件。'},
    {id:'waveform',name:'波形查看',en:'WAVEFORM VIEWER',icon:'wave',group:'地震数据',desc:'浏览多通道波形，标记与比较震相。'},
    {id:'spectrum',name:'频谱分析',en:'SPECTRAL ANALYSIS',icon:'spectrum',group:'地震数据',desc:'设置分析参数，查看频域表达。'},
    {id:'location',name:'震源定位',en:'HYPOCENTER LOCATION',icon:'pin',group:'地震数据',desc:'整理台站与到时，预览定位工作流程。'},
    {id:'papers',name:'文献检索',en:'LITERATURE SEARCH',icon:'search',group:'文献研究',desc:'围绕研究主题查找与整理相关文献。'},
    {id:'reading',name:'论文精读',en:'PAPER READING',icon:'book',group:'文献研究',desc:'按问题、方法、证据与局限拆解论文。'},
    {id:'translate',name:'学术翻译',en:'ACADEMIC TRANSLATION',icon:'translate',group:'文献研究',desc:'保留专业术语，预览双语阅读流程。'},
    {id:'notes',name:'研究笔记',en:'RESEARCH NOTES',icon:'note',group:'科研写作',desc:'随手记录想法，让研究线索有处可循。'},
    {id:'report',name:'报告草拟',en:'REPORT OUTLINE',icon:'file',group:'科研写作',desc:'从研究主题出发，组织报告结构。'}
  ];
  const byId = Object.fromEntries(tools.map(t => [t.id,t]));
  const workspace = document.getElementById('workspace');
  document.querySelector('.skip').addEventListener('click',e=>{e.preventDefault();workspace.focus();workspace.scrollIntoView();});
  const drafts = {};
  const outputs = {};
  const messages = [];
  let current = '';
  let selectedEvent = 0;
  let toastTimer;
  const events = [
    {id:'DEMO-001',place:'示例区域 A',date:'2026-01-15',mag:4.2,depth:12,lon:103.2,lat:31.1,x:150,y:95},
    {id:'DEMO-002',place:'示例区域 B',date:'2026-01-14',mag:3.5,depth:8,lon:104.1,lat:30.3,x:220,y:150},
    {id:'DEMO-003',place:'示例区域 C',date:'2026-01-12',mag:5.1,depth:18,lon:102.6,lat:29.8,x:108,y:200},
    {id:'DEMO-004',place:'示例区域 D',date:'2026-01-10',mag:2.8,depth:6,lon:104.8,lat:31.8,x:290,y:65}
  ];
  let filteredEvents = events;
  function toast(text) { const el=document.getElementById('toast');el.textContent=text;el.classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('visible'),3000); }
  function capture() {
    if (!current) return;
    const form=workspace.querySelector('form[data-tool-form]');
    if (form) drafts[current]=Object.fromEntries([...new FormData(form)].filter(([,v])=>typeof v==='string'));
  }
  function restore() {
    const form=workspace.querySelector('form[data-tool-form]');
    if (!form || !drafts[current]) return;
    Object.entries(drafts[current]).forEach(([key,value])=>{const el=form.elements.namedItem(key);if(el)el.value=value;});
  }
  function field(name,label,type='text',value='',options=[]) {
    const id=`field-${name}`;
    const input=type==='select'?`<select id="${id}" name="${name}">${options.map(v=>`<option${v===value?' selected':''}>${esc(v)}</option>`).join('')}</select>`:type==='textarea'?`<textarea id="${id}" name="${name}" placeholder="${esc(value)}"></textarea>`:`<input id="${id}" name="${name}" type="${type}" value="${esc(value)}" ${type==='number'?'step="any"':''}>`;
    return `<div class="field"><label for="${id}">${label}</label>${input}</div>`;
  }
  const button = (label='查看示例结果') => `<div class="actions"><button class="primary" type="submit">${icon('spark')}${label}</button><button class="secondary" type="reset">重置参数</button><span class="hint">仅展示预设示例</span></div>`;
  function upload(accept) { return `<div class="dropzone">${icon('upload')}<label for="sample-file">选择文件，预览资料准备流程</label><input id="sample-file" type="file" accept="${accept}"><p id="file-caption">文件只在本机选择，不上传、不解析；切换工具后需重新选择。</p></div>`; }
  function heading(t) { return `<div class="page-heading"><div><span class="eyebrow">${t.en}</span><h1>${t.name}</h1><p>${t.desc}</p></div><div class="heading-symbol">${icon(t.icon)}</div></div>`; }
  function guide(steps) { return `<aside class="guide"><div class="guide-icon">${icon('spark')}</div><h3>让研究有条理地推进</h3><ol>${steps.map(s=>`<li>${s}</li>`).join('')}</ol><div class="guide-status"><strong>当前为界面演示</strong>参数可编辑，结果为预设示例。后续可在此接入中心的数据与计算服务。</div></aside>`; }
  function resultBox(content) { return `<section class="panel result" aria-label="示例结果"><div class="panel-header"><h2>结果预览</h2><span class="demo-label">预设示例 · 非计算结果</span></div><div class="result-body">${content}</div></section>`; }
  function shell(form,title,steps) { return `<div class="work-layout"><div><section class="panel"><div class="panel-header"><h2>${title}</h2><span>01 / 准备输入</span></div><div class="panel-body"><form data-tool-form>${form}</form></div></section><div id="output" aria-live="polite">${outputs[current]||'<div class="empty-result">设置输入后，查看这个工具的示例输出。</div>'}</div></div>${guide(steps)}</div>`; }
  function card(t) { return `<a href="#${t.id}" class="tool-card"><div class="tool-card-head"><span class="tool-icon ${t.group==='文献研究'?'amber':t.group==='科研写作'?'blue':''}">${icon(t.icon)}</span><span>${t.en.split(' ')[0]}</span></div><h3>${t.name}</h3><p>${t.desc}</p><span class="card-arrow">↗</span></a>`; }
  function home() {
    return `<div class="page-heading"><div><span class="eyebrow">YOUR RESEARCH, CONNECTED</span><h1>在这里，开始下一次探索。</h1><p>把地震数据、文献与研究思路，连接在同一个工作空间。</p></div><div class="heading-symbol">${icon('globe')}</div></div><section class="hero-banner"><div><span class="eyebrow">TERRA RESEARCH WORKSPACE</span><h2>从观测，到新的认识。</h2><p>查看一段波形，读懂一篇论文，或记录一个尚未成形的想法。<br>选择左侧工具，开始你的研究流程。</p><a class="primary" href="#assistant">开启科研问答 ${icon('arrow')}</a></div><div class="hero-art"><svg viewBox="0 0 320 180" aria-hidden="true"><g opacity=".45"><ellipse cx="170" cy="85" rx="105" ry="65"/><ellipse cx="170" cy="85" rx="70" ry="65"/><ellipse cx="170" cy="85" rx="30" ry="65"/><ellipse cx="170" cy="85" rx="105" ry="24"/><path d="M65 85h210M170 20v130"/></g><path d="M15 90h50l8-13 9 32 10-57 10 77 10-65 10 37 10-15 10 4h163" stroke-width="1.8"/><circle cx="170" cy="85" r="5" fill="#7a9671" stroke="none"/></svg><span>OBSERVE / CONNECT / DISCOVER</span></div></section><div class="section-title"><h2>常用工具</h2><span>为地震科研整理的工具集 · 9 个工具</span></div><div class="tool-grid">${['waveform','spectrum','location','papers','reading','notes'].map(id=>card(byId[id])).join('')}</div><div class="section-title"><h2>更多研究支持</h2><span>从分析思路到成果表达</span></div><div class="tool-grid">${['assistant','translate','report'].map(id=>card(byId[id])).join('')}</div><div class="workflow-strip"><strong>试试这条研究路径</strong><a href="catalog.html">浏览地震事件 ↗</a><span>→</span><a href="#papers">查找相关文献</a><span>→</span><a href="#notes">记录研究思路</a><span>→</span><a href="#report">组织报告</a></div>`;
  }
  function chart(kind='waveform') {
    let lines='';
    for(let x=50;x<=650;x+=100) lines+=`<path class="grid" d="M${x} 20v225"/><text x="${x}" y="265">${(x-50)/10}</text>`;
    if(kind==='spectrum') {
      const points=Array.from({length:301},(_,i)=>{const x=50+i*2;const y=220-150*Math.exp(-Math.pow((i-78)/26,2))-55*Math.exp(-Math.pow((i-185)/40,2))-7*Math.sin(i*.28);return `${x},${y.toFixed(2)}`;}).join(' ');
      return `<svg class="signal-chart" viewBox="0 0 700 290" role="img" aria-label="合成示例频谱，不对应输入文件">${lines}<path class="grid" d="M50 70h600M50 145h600M50 220h600"/><polyline class="wave" points="${points}"/><text x="580" y="286">频率 / Hz（示例）</text><text x="50" y="14">归一化幅值</text></svg>`;
    }
    ['BHZ','BHN','BHE'].forEach((label,j)=>{
      const y=60+j*75;
      lines+=`<path class="grid" d="M50 ${y}h600"/><text x="10" y="${y+4}">${label}</text>`;
      const points=Array.from({length:601},(_,i)=>{const env=i>180?Math.exp(-(i-180)/150)*26:1.5;return `${50+i},${(y+Math.sin(i*.75+j)*Math.sin(i*.123)*env).toFixed(2)}`;}).join(' ');
      lines+=`<polyline class="wave" points="${points}"/>`;
    });
    return `<svg class="signal-chart" viewBox="0 0 700 290" role="img" aria-label="三通道合成波形示例，不对应输入文件">${lines}<path class="marker" d="M230 20v220M300 20v220"/><text x="233" y="15">P 示意</text><text x="303" y="15">S 示意</text><text x="580" y="286">时间 / s（示例）</text></svg>`;
  }
  function catalogContent() {
    return `<div class="catalog-layout"><div class="catalog-map"><svg viewBox="0 0 380 280" role="img" aria-label="虚构区域与地震位置示意，非地理底图"><path d="M0 60 75 40l60 25 50-35 60 30 80-12 55 35M0 130l85-30 65 35 60-20 80 35 90-30M0 210l100-35 80 30 80-15 120 35M70 0l10 85-30 75 20 120M180 0l-10 70 40 90-35 120M300 0l-30 100 50 70-25 110" stroke-dasharray="3 5" opacity=".6"/><path d="m110 0 32 52-17 50 40 42-10 62 30 74" stroke="#ab9272" stroke-width="2"/><text x="225" y="245">虚构研究区域</text>${filteredEvents.map(e=>`<circle class="event-dot ${events.indexOf(e)===selectedEvent?'selected':''}" cx="${e.x}" cy="${e.y}" r="${e.mag*2}"/>`).join('')}</svg><span class="map-caption">位置与事件均为演示数据</span></div><div class="catalog-list">${filteredEvents.length?filteredEvents.map(e=>`<button class="event-row ${events.indexOf(e)===selectedEvent?'active':''}" data-event="${events.indexOf(e)}" aria-pressed="${events.indexOf(e)===selectedEvent}"><span class="magnitude">${e.mag.toFixed(1)}</span><span><strong>${e.place}</strong><small>${e.date} · 深度 ${e.depth} km</small></span><span>示例 ↗</span></button>`).join(''):'<p class="status-note">没有符合条件的示例事件，请调整筛选。</p>'}</div></div>${filteredEvents.length?`<div class="event-detail"><span>${events[selectedEvent].id}</span><span>${events[selectedEvent].lat}° N / ${events[selectedEvent].lon}° E</span><span>震级与坐标为虚构示例</span></div>`:''}`;
  }
  function renderCatalog() {
    return `<section class="panel"><div class="panel-header"><h2>探索事件</h2><span class="demo-label">4 条虚构事件</span></div><div class="panel-body"><form data-tool-form><div class="field-grid">${field('start','开始日期','date','2026-01-01')}${field('end','结束日期','date','2026-01-31')}${field('min','最低震级','number','0')}${field('region','研究区域','select','全部示例区域',['全部示例区域','示例区域 A','示例区域 B','示例区域 C','示例区域 D'])}</div><div class="actions"><button class="primary">${icon('search')}筛选示例事件</button><button class="secondary" type="reset">重置</button><button class="secondary" type="button" data-action="export-catalog">${icon('download')}导出示例 CSV</button></div><p id="catalog-status" role="status" class="status-note">显示 ${filteredEvents.length} 条示例事件 · 此处未接入实时地震数据。</p></form></div><div id="catalog-results">${catalogContent()}</div></section>`;
  }
  function renderChat() {
    return `<div class="work-layout"><section class="panel"><div class="panel-header"><h2>与 Terra 一起梳理问题</h2><span class="demo-label">示例对话</span></div><div class="chat-welcome"><span class="terra-mark">t<span>·</span></span><h2>今天，想探索什么？</h2><p>从一个研究问题开始，逐步组织方法、资料与证据。</p><div class="suggestions">${['如何规划一次区域地震活动性研究？','帮我列一个地震波形处理流程','阅读一篇成像论文需要关注什么？','如何组织本周的科研进展汇报？'].map(s=>`<button data-prompt="${s}">${s} ↗</button>`).join('')}</div></div><div class="messages" id="messages" aria-live="polite"></div><form class="chat-composer" data-tool-form><label for="question" class="visually-hidden">研究问题</label><textarea name="question" id="question" placeholder="输入研究问题，体验问答与思路整理流程…" required maxlength="3000"></textarea><div class="actions"><span class="chat-mode">研究思路 · 演示模式</span><button class="secondary" type="button" data-action="clear-chat">清空对话</button><button class="primary">查看示例回复 ${icon('arrow')}</button></div></form></section>${guide(['输入问题，或选择一个提示。','查看示例回复的组织方式。','把研究思路转存到笔记。'])}</div>`;
  }
  function renderMessages() {
    const el=document.getElementById('messages');if(!el)return;
    el.innerHTML=messages.map(m=>`<div class="message ${m.role}">${m.role==='assistant'?'<small>Terra · 固定回复模板，未调用 AI</small>':''}${esc(m.text)}</div>`).join('');
    el.scrollTop=el.scrollHeight;
  }
  function renderNotes() {
    if(!drafts.notes){try{const note=JSON.parse(localStorage.getItem('terra-research-note')||'null');if(note&&typeof note.title==='string'&&typeof note.body==='string')drafts.notes=note;}catch{ /* Storage may be disabled. Editing still works. */ }}
    return `<div class="work-layout"><section class="panel"><div class="panel-header"><h2>一页研究手记</h2><span>本地编辑</span></div><div class="panel-body"><form data-tool-form>${field('title','笔记标题','text','我的研究笔记')}<div class="field"><label for="note-body">研究内容</label><textarea class="note-editor" id="note-body" name="body" placeholder="研究问题\n\n已知证据\n\n初步想法\n\n下一步计划"></textarea></div><div class="actions"><button class="primary">保存到此浏览器</button><button class="secondary" type="button" data-action="export-note">${icon('download')}导出笔记</button></div><p class="status-note" id="note-status" role="status">编辑后请手动保存；仅保存在当前浏览器，不会同步到服务器。</p></form></div></section>${guide(['写下问题和对应资料。','把事实、推测与待验证项分开记录。','手动保存，或导出为 Markdown 文件。'])}</div>`;
  }
  function renderTool(t) {
    switch(t.id){
      case 'assistant': return renderChat();
      case 'catalog': return renderCatalog();
      case 'notes': return renderNotes();
      case 'waveform': return shell(upload('.mseed,.sac,.csv')+`<div class="field-grid">${field('station','台站名称','text','DEMO.ST01')}${field('channel','显示通道','select','三分量',['三分量','BHZ','BHN','BHE'])}${field('filter','处理方式','select','原始波形',['原始波形','去均值','带通滤波'])}${field('window','展示窗口（秒）','number','60')}</div>`+button('预览示例波形'),'波形与显示参数',['选择波形文件或直接体验示例。','设置台站、通道与展示窗口。','查看多通道波形和震相标记的呈现方式。']);
      case 'spectrum': return shell(upload('.mseed,.sac,.csv')+`<div class="field-grid">${field('method','分析方法','select','幅度谱',['幅度谱','功率谱密度','时频分析'])}${field('sample','采样率（Hz）','number','100')}${field('window','窗函数','select','Hann 窗',['Hann 窗','Hamming 窗','矩形窗'])}${field('segment','分段长度','select','1024',['512','1024','2048'])}</div>`+button('预览示例频谱'),'频域分析设置',['准备连续波形。','设置采样率与分析方法。','观察频谱图与结果说明的版式。']);
      case 'location': return shell(upload('.csv,.txt')+`<div class="field-grid">${field('model','速度模型','select','示例一维模型',['示例一维模型','自定义模型（待接入）'])}${field('method','定位方法','select','网格搜索',['网格搜索','迭代定位'])}${field('depth','初始深度（km）','number','10')}${field('phase','震相类型','select','P + S',['P + S','仅 P 波'])}</div>`+button('预览定位流程'),'台站与震相信息',['准备台站坐标与震相到时表。','选择速度模型和定位参数。','查看结果字段与质量控制项。']);
      case 'papers': return shell(field('query','研究主题','text','青藏高原东缘 地壳结构')+`<div class="field-grid">${field('range','时间范围','select','近五年',['近五年','近十年','不限年份'])}${field('source','检索来源','select','中心文献库',['中心文献库','开放文献（待接入）'])}</div>`+button('查看检索示例'),'查找研究线索',['输入主题、关键词或研究问题。','浏览文献卡片与相关线索。','进入论文精读，体验结构化阅读。']);
      case 'reading': return shell(upload('.pdf')+field('title','论文标题或阅读主题','text','区域地震成像的方法与证据')+field('focus','本次阅读重点','textarea','例如：数据覆盖如何影响分辨率？哪些结论仍需额外证据？')+button('查看精读示例'),'准备阅读材料',['选择一篇论文。','明确本次想回答的问题。','沿着问题、方法、证据与局限整理笔记。']);
      case 'translate': return shell(`<div class="field-grid">${field('direction','翻译方向','select','英文 → 中文',['英文 → 中文','中文 → 英文'])}${field('style','表达风格','select','学术表达',['学术表达','便于理解'])}</div>`+field('text','待翻译段落','textarea','粘贴段落，或点击「填入示例」体验翻译界面。')+`<div class="actions"><button class="primary">查看翻译示例</button><button class="secondary" type="button" data-action="sample-translation">填入示例</button></div>`,'双语阅读',['粘贴一个段落。','选择语言方向与表达风格。','查看双语对照和术语表的组织方式。']);
      case 'report': return shell(field('title','报告主题','text','区域地震活动性研究进展')+`<div class="field-grid">${field('type','报告类型','select','组会汇报',['组会汇报','研究计划','阶段总结'])}${field('audience','面向读者','select','课题组成员',['课题组成员','跨学科合作者','课程教学'])}</div>`+field('points','已有材料与要点','textarea','写下已有数据、当前进展、遇到的问题，以及希望讨论的内容。')+button('预览报告提纲'),'组织你的研究表达',['写清报告面向谁、要解决什么。','整理进展与尚未解决的问题。','查看提纲，复制到笔记继续完善。']);
      default: return '';
    }
  }
  function render() {
    capture();
    const id=catalogPage?'catalog':location.hash.slice(1)||'overview';
    if(!catalogPage && id==='catalog'){location.href='catalog.html';return;}
    current=byId[id]?id:'overview';
    if(id!==current){history.replaceState(null,'',`#${current}`);toast('未找到该工具，已返回概览。');}
    const t=byId[current];
    document.title=catalogPage?'地震目录 · EARTHQUAKE CENTER':`${t.name} · Terra 科研工作台`;
    document.getElementById('breadcrumb').textContent=t.name;
    document.querySelectorAll('.nav-link').forEach(a=>{const active=a.dataset.tool===current;a.classList.toggle('active',active);if(active)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
    workspace.innerHTML=current==='overview'?home():heading(t)+renderTool(t);
    restore();renderMessages();setMenu(false);window.scrollTo(0,0);
    workspace.focus({preventScroll:true});
  }
  if (!catalogPage) {
  let lastGroup='';
  document.getElementById('tool-nav').innerHTML=tools.filter(t=>t.id!=='catalog').map(t=>{const label=t.group!==lastGroup&&t.group!=='开始'?`<p class="nav-group">${t.group}</p>`:'';lastGroup=t.group;return `${label}<a class="nav-link" data-tool="${t.id}" href="#${t.id}">${icon(t.icon)}<span>${t.name}</span></a>`;}).join('');
  }
  function setMenu(open){if(catalogPage)return;document.getElementById('sidebar').classList.toggle('open',open);document.getElementById('sidebar').inert=!open&&innerWidth<=700;document.getElementById('scrim').hidden=!open;document.getElementById('mobile-toggle').setAttribute('aria-expanded',String(open));document.body.style.overflow=open?'hidden':'';document.querySelector('.app-shell').inert=open;if(open)document.getElementById('search-launch').focus();}
  if (!catalogPage) {
  document.getElementById('mobile-toggle').onclick=()=>setMenu(!document.getElementById('sidebar').classList.contains('open'));
  document.getElementById('scrim').onclick=()=>{setMenu(false);document.getElementById('mobile-toggle').focus();};
  document.getElementById('help-button').onclick=()=>document.getElementById('help-dialog').showModal();
  const searchDialog=document.getElementById('search-dialog');
  function searchTools(){const q=document.getElementById('tool-search').value.trim().toLowerCase();const found=tools.filter(t=>t.id!=='catalog').filter(t=>(t.name+t.desc+t.en+t.group).toLowerCase().includes(q));document.getElementById('search-results').innerHTML=found.length?found.map(t=>`<a href="#${t.id}">${icon(t.icon)}<div><span>${t.name}</span><small>${t.desc}</small></div></a>`).join(''):'<p class="status-note">没有找到工具，试试「文献」或「波形」。</p>';}
  function openSearch(){searchDialog.showModal();document.getElementById('tool-search').value='';searchTools();document.getElementById('tool-search').focus();}
  document.getElementById('search-launch').onclick=openSearch;
  document.getElementById('tool-search').oninput=searchTools;
  searchDialog.querySelector('form').addEventListener('submit',e=>{e.preventDefault();const a=document.querySelector('#search-results a');if(a)a.click();});
  searchDialog.querySelector('.key-button').onclick=e=>{e.preventDefault();searchDialog.close();};
  document.getElementById('search-results').onclick=e=>{if(e.target.closest('a')){searchDialog.close();setMenu(false);}};
  document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(!document.getElementById('help-dialog').open&&!searchDialog.open)openSearch();}if(e.key==='Escape'&&document.getElementById('sidebar').classList.contains('open')&&!searchDialog.open){setMenu(false);document.getElementById('mobile-toggle').focus();}});
  window.addEventListener('resize',()=>setMenu(false));
  }
  if(catalogPage)document.getElementById('help-button').onclick=()=>document.getElementById('help-dialog').showModal();
  window.addEventListener('hashchange',render);
  workspace.addEventListener('input',()=>{capture();if(current==='notes')document.getElementById('note-status').textContent='有尚未保存的修改。';});
  workspace.addEventListener('change',e=>{if(e.target.type==='file'){document.getElementById('file-caption').textContent=e.target.files[0]?`已选择：${e.target.files[0].name} · 仅显示文件名，不上传或解析。`:'尚未选择文件。';}capture();});
  workspace.addEventListener('reset',()=>{setTimeout(()=>{delete drafts[current];delete outputs[current];if(current==='catalog'){filteredEvents=events;selectedEvent=0;document.getElementById('catalog-results').innerHTML=catalogContent();document.getElementById('catalog-status').textContent='显示 4 条示例事件 · 此处未接入实时地震数据。';}else{const el=document.getElementById('output');if(el)el.innerHTML='<div class="empty-result">设置输入后，查看这个工具的示例输出。</div>';const caption=document.getElementById('file-caption');if(caption)caption.textContent='文件只在本机选择，不上传、不解析。';}},0);});
  function showResult(content){outputs[current]=resultBox(content);document.getElementById('output').innerHTML=outputs[current];}
  function resultFor(id,d) {
    const note='<div class="result-note">以下为固定示例，用于确认界面结构。修改参数或选择文件不会触发真实分析。</div>';
    if(id==='waveform')return note+chart()+`<p>已选择通道：${esc(d.channel)} · 界面参数窗口：${esc(d.window)} 秒。</p><p>图中仍为固定 60 秒三分量合成波形，P、S 标记仅用于展示交互位置。</p>`;
    if(id==='spectrum')return note+chart('spectrum')+`<h3>分析参数摘要</h3><p>${esc(d.method)} / ${esc(d.window)} / ${esc(d.sample)} Hz / 分段 ${esc(d.segment)}</p><p>当前固定展示幅度谱示意；功率谱和时频分析视图留待后续实现。</p>`;
    if(id==='location')return note+'<h3>01 · 读取与校验</h3><p>预留台站名称、经纬度、海拔、P/S 到时及拾取误差字段。</p><h3>02 · 定位计算</h3><p>预留速度模型选择、初始震源与迭代过程展示。</p><h3>03 · 结果与质量</h3><p>震源经纬度、深度、发震时刻、到时残差、台站分布与误差范围。</p><p>当前没有计算震源坐标，以上是拟定的输出结构。</p>';
    if(id==='papers')return note+`<p>研究主题：${esc(d.query||'未填写')} · 以下卡片均为虚构版式示例。</p>`+['区域地壳结构：数据、方法与解释','地震波形分析中的质量控制','观测覆盖与成像分辨率'].map((s,i)=>`<article class="paper-hit"><small>示例 ${String(i+1).padStart(2,'0')} / 非真实出版物</small><h3>${s}</h3><p>此处预留作者、期刊、年份、摘要片段与原文入口，后续连接文献库。</p><a href="#reading">查看精读工具 →</a></article>`).join('');
    if(id==='reading')return note+`<h3>阅读主题 · ${esc(d.title||'未填写')}</h3><h3>研究问题</h3><p>作者希望解释什么现象？它与已有研究有哪些联系？</p><h3>数据与方法</h3><p>记录数据来源、观测覆盖、预处理步骤与方法假设。</p><h3>证据与结论</h3><p>逐项对应正文、图表与结论，保留页码与原文出处。</p><h3>局限与可复现性</h3><p>检查参数敏感性、适用范围及数据和代码的开放情况。</p><p>这些是阅读提示，尚未解析所选论文。</p>`;
    if(id==='translate')return note+(d.direction==='英文 → 中文'?'<h3>示例原文</h3><p>Seismic tomography provides constraints on the velocity structure of the crust.</p><h3>示例译文</h3><p>地震层析成像为地壳速度结构提供约束。</p>':'<h3>示例原文</h3><p>地震层析成像为地壳速度结构提供约束。</p><h3>示例译文</h3><p>Seismic tomography provides constraints on the velocity structure of the crust.</p>')+'<h3>术语对照</h3><p>Seismic tomography · 地震层析成像<br>Velocity structure · 速度结构</p><p>这里展示固定句对，尚未翻译你的输入内容。</p>';
    if(id==='report')return note+`<h3>${esc(d.title||'研究报告')} · 提纲</h3><p>${esc(d.type)} / 面向${esc(d.audience)}</p><ol><li>研究背景与本次汇报目标</li><li>数据来源及当前准备情况</li><li>方法与分析流程</li><li>已有进展：图表、证据与初步认识</li><li>问题与局限：哪些结论还需验证</li><li>下一步计划与需要讨论的事项</li></ol>${d.points?`<h3>你补充的材料</h3><p style="white-space:pre-wrap">${esc(d.points)}</p>`:''}<button class="secondary" data-action="report-note">存入研究笔记的新草稿 ${icon('arrow')}</button>`;
    return note;
  }
  workspace.addEventListener('submit',e=>{
    if(!e.target.matches('[data-tool-form]'))return;e.preventDefault();capture();const d=drafts[current];
    if(current==='assistant'){
      const q=d.question.trim();if(!q)return;
      messages.push({role:'user',text:q},{role:'assistant',text:'我们可以按以下步骤梳理这个研究问题：\n\n1. 明确对象与尺度：研究区域、时间范围，以及希望解释的现象。\n2. 整理可用资料：观测数据、处理记录与相关文献。\n3. 选择分析方法：写清假设、参数与质量控制方式。\n4. 组织证据：区分已知事实、初步推断与待验证项。\n5. 记录下一步：把计划整理到研究笔记中。\n\n这是用于演示的通用回复模板，尚未针对你的问题进行分析。'});
      e.target.elements.question.value='';drafts.assistant={question:''};renderMessages();return;
    }
    if(current==='notes'){
      try{localStorage.setItem('terra-research-note',JSON.stringify(d));document.getElementById('note-status').textContent='已保存到当前浏览器。未上传或同步到服务器。';toast('研究笔记已保存在此浏览器');}catch{toast('浏览器无法保存，请使用导出笔记。');}return;
    }
    if(current==='catalog'){
      if(!d.start||!d.end||d.start>d.end||d.min===''||Number(d.min)<0){toast('请检查起止日期和最低震级。');return;}
      filteredEvents=events.filter(ev=>ev.date>=d.start&&ev.date<=d.end&&ev.mag>=Number(d.min)&&(d.region==='全部示例区域'||ev.place===d.region));
      if(filteredEvents.length)selectedEvent=events.indexOf(filteredEvents[0]);
      document.getElementById('catalog-results').innerHTML=catalogContent();document.getElementById('catalog-status').textContent=`找到 ${filteredEvents.length} 条示例事件 · 此处未接入实时地震数据。`;return;
    }
    if(['waveform','spectrum','location'].includes(current)&&['window','sample','depth'].some(k=>d[k]!==undefined&&!isNaN(Number(d[k]))&&(d[k]===''||Number(d[k])<=0))){toast('数值参数应大于零。');return;}
    showResult(resultFor(current,d));
  });
  function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  workspace.addEventListener('click',e=>{
    const prompt=e.target.closest('[data-prompt]');if(prompt){document.getElementById('question').value=prompt.dataset.prompt;capture();document.getElementById('question').focus();}
    const event=e.target.closest('[data-event]');if(event){selectedEvent=Number(event.dataset.event);document.getElementById('catalog-results').innerHTML=catalogContent();document.querySelector(`[data-event="${selectedEvent}"]`).focus();}
    const action=e.target.closest('[data-action]')?.dataset.action;if(!action)return;
    capture();
    if(action==='clear-chat'){messages.length=0;renderMessages();toast('示例对话已清空');}
    if(action==='sample-translation'){const form=workspace.querySelector('form[data-tool-form]');form.elements.text.value=form.elements.direction.value==='英文 → 中文'?'Seismic tomography provides constraints on the velocity structure of the crust.':'地震层析成像为地壳速度结构提供约束。';capture();}
    if(action==='export-note'){const d=drafts.notes;download('terra-research-note.md',`# ${d.title}\n\n${d.body||''}\n`,'text/markdown;charset=utf-8');toast('笔记已导出');}
    if(action==='export-catalog'){download('terra-demo-events.csv','\uFEFF'+['演示标记,事件编号,区域,日期,震级,深度km,经度,纬度',...filteredEvents.map(v=>`虚构示例,${v.id},${v.place},${v.date},${v.mag},${v.depth},${v.lon},${v.lat}`)].join('\n'),'text/csv;charset=utf-8');toast('已导出当前筛选的示例事件');}
    if(action==='report-note'){
      const text=document.querySelector('#output .result-body').innerText.replace('存入研究笔记的新草稿','').trim();
      let existing=drafts.notes;
      if(!existing){try{existing=JSON.parse(localStorage.getItem('terra-research-note')||'null');}catch{}}
      drafts.notes={title:existing?.title||'研究笔记',body:[existing?.body,text].filter(Boolean).join('\n\n---\n\n')};
      location.hash='notes';toast('提纲已追加到笔记草稿，请手动保存。');
    }
  });
  render();
})();
