<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { apiUrl } from '../config/api'

type PaperDetail = {
  id: string
  title: string
  authorsText: string
  journal: string
  year: number
  doi: string
  url: string
  topics: string[]
  evidenceType: string
  abstractPreview: string
  parserStatus: Record<string, string>
  cer: { claim: string; evidence: string; reasoning: string; citation: string }
  relations: Array<{ source: string; relation: string; target: string }>
  evidencePack: {
    claim: string
    evidence: Array<{ text: string; source: string; locator: string; confidence: number }>
    citation: string
    confidence: number
    unsupported: boolean
  }
  validation: {
    grounding: number
    citationRelevant: boolean
    safety: string
    overPrediction: boolean
    passed: boolean
  }
  professionalInterpretation: {
    headline: string
    summary: string
    coreConclusion: string
    regionalApplicability: string
    citationGuidance: string
    methodLimitations: string
    bestForQuestions: string[]
    notSupportedConclusions: string[]
    sections: Array<{ title: string; content: string }>
    recommendedUse: string[]
    uncertainty: string
  }
  chunks: Array<{ type: string; content: string; ordinal: number }>
}

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const error = ref('')
const paper = ref<PaperDetail | null>(null)

const paperId = computed(() => String(route.params.paperId || ''))

const loadPaper = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(apiUrl(`/papers/${encodeURIComponent(paperId.value)}`))
    if (!res.ok) throw new Error(res.status === 404 ? '论文不存在' : `Paper API failed with ${res.status}`)
    paper.value = (await res.json()) as PaperDetail
  } catch (err) {
    error.value = err instanceof Error ? err.message : '论文详情暂时不可用'
  } finally {
    loading.value = false
  }
}

onMounted(loadPaper)
</script>

<template>
  <main class="detail-page">
    <header class="topbar">
      <button class="ghost-button" @click="router.push('/papers')">返回检索</button>
      <strong>CDUT SEISLAB · PAPER INTERPRETATION</strong>
      <button class="ghost-button" @click="router.push('/')">首页</button>
    </header>

    <div v-if="loading" class="state-card">正在加载论文详情...</div>
    <div v-else-if="error" class="state-card">{{ error }}</div>

    <template v-else-if="paper">
      <section class="hero">
        <div>
          <span class="kicker">Professional Interpretation</span>
          <h1>{{ paper.professionalInterpretation.headline }}</h1>
          <p>{{ paper.professionalInterpretation.summary }}</p>
          <div class="meta-row">
            <span>{{ paper.journal }}</span>
            <span>{{ paper.year }}</span>
            <span>{{ paper.evidenceType }}</span>
            <span>{{ paper.authorsText }}</span>
          </div>
        </div>
        <aside class="verdict" :class="{ passed: paper.validation.passed }">
          <span>Validation</span>
          <strong>{{ paper.validation.passed ? 'PASS' : 'REVIEW' }}</strong>
          <p>Grounding {{ paper.validation.grounding.toFixed(3) }}</p>
          <p>Citation {{ paper.validation.citationRelevant ? 'pass' : 'review' }}</p>
          <p>Safety {{ paper.validation.safety }}</p>
        </aside>
      </section>

      <section class="summary-grid">
        <article class="summary-card primary">
          <span class="kicker">Core Conclusion</span>
          <h2>核心结论</h2>
          <p>{{ paper.professionalInterpretation.coreConclusion }}</p>
        </article>
        <article class="summary-card">
          <span class="kicker">Regional Applicability</span>
          <h2>适用范围</h2>
          <p>{{ paper.professionalInterpretation.regionalApplicability }}</p>
        </article>
        <article class="summary-card">
          <span class="kicker">Citation Guidance</span>
          <h2>引用建议</h2>
          <p>{{ paper.professionalInterpretation.citationGuidance }}</p>
        </article>
        <article class="summary-card caution">
          <span class="kicker">Method Limits</span>
          <h2>方法边界</h2>
          <p>{{ paper.professionalInterpretation.methodLimitations }}</p>
        </article>
      </section>

      <section class="layout">
        <article class="main-panel">
          <section class="block">
            <span class="kicker">Seismic Reading</span>
            <h2>地震专业解读</h2>
            <article
              v-for="section in paper.professionalInterpretation.sections"
              :key="section.title"
              class="interpret-section"
            >
              <h3>{{ section.title }}</h3>
              <p>{{ section.content }}</p>
            </article>
          </section>

          <section class="block">
            <span class="kicker">Claim Evidence Reasoning Citation</span>
            <h2>证据链</h2>
            <div class="cer-grid">
              <article><strong>Claim</strong><p>{{ paper.cer.claim }}</p></article>
              <article><strong>Evidence</strong><p>{{ paper.cer.evidence }}</p></article>
              <article><strong>Reasoning</strong><p>{{ paper.cer.reasoning }}</p></article>
              <article><strong>Citation</strong><p>{{ paper.cer.citation }}</p></article>
            </div>
          </section>

          <section class="block">
            <span class="kicker">Evidence Pack</span>
            <h2>证据包</h2>
            <div class="confidence">
              <span>Confidence {{ paper.evidencePack.confidence.toFixed(2) }}</span>
              <span :class="{ warn: paper.evidencePack.unsupported }">
                {{ paper.evidencePack.unsupported ? 'unsupported' : 'supported' }}
              </span>
            </div>
            <article
              v-for="evidence in paper.evidencePack.evidence"
              :key="`${evidence.locator}-${evidence.text}`"
              class="evidence-item"
            >
              <strong>{{ evidence.locator }} · {{ evidence.confidence.toFixed(2) }}</strong>
              <p>{{ evidence.text }}</p>
            </article>
          </section>

          <section class="block">
            <span class="kicker">Expert Use</span>
            <h2>适合回答的问题</h2>
            <div class="question-list">
              <article v-for="item in paper.professionalInterpretation.bestForQuestions" :key="item" class="question-card">
                {{ item }}
              </article>
            </div>
          </section>
        </article>

        <aside class="side-panel">
          <section class="block">
            <h2>主题与用途</h2>
            <div class="tag-list">
              <span v-for="topic in paper.topics" :key="topic">{{ topic }}</span>
            </div>
            <div class="tag-list">
              <span v-for="item in paper.professionalInterpretation.recommendedUse" :key="item">{{ item }}</span>
            </div>
          </section>

          <section class="block">
            <h2>解析状态</h2>
            <div v-for="[name, status] in Object.entries(paper.parserStatus)" :key="name" class="kv-row">
              <span>{{ name }}</span>
              <strong>{{ status }}</strong>
            </div>
          </section>

          <section class="block">
            <h2>语义切块</h2>
            <article v-for="chunk in paper.chunks" :key="`${chunk.type}-${chunk.ordinal}`" class="chunk">
              <strong>{{ chunk.type }}</strong>
              <p>{{ chunk.content }}</p>
            </article>
          </section>

          <section class="block">
            <h2>轻量图谱关系</h2>
            <div v-for="relation in paper.relations" :key="`${relation.relation}-${relation.target}`" class="kv-row">
              <span>{{ relation.relation }}</span>
              <strong>{{ relation.target }}</strong>
            </div>
          </section>

          <section class="block warning">
            <h2>慎用提醒</h2>
            <article
              v-for="item in paper.professionalInterpretation.notSupportedConclusions"
              :key="item"
              class="caution-item"
            >
              <p>{{ item }}</p>
            </article>
          </section>

          <section class="block warning">
            <h2>不确定性</h2>
            <p>{{ paper.professionalInterpretation.uncertainty }}</p>
          </section>
        </aside>
      </section>
    </template>
  </main>
</template>

<style scoped>
.detail-page {
  min-height: 100vh;
  background: #f8fafc;
  color: #111827;
  font-family: "Helvetica Neue", "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 40px;
  background: rgba(255, 255, 255, 0.94);
  border-bottom: 1px solid #e5e7eb;
  backdrop-filter: blur(12px);
}

.ghost-button {
  border: 1px solid #111827;
  border-radius: 6px;
  padding: 9px 14px;
  background: #fff;
  color: #111827;
  font-weight: 800;
  cursor: pointer;
}

.hero,
.summary-grid,
.layout,
.state-card {
  width: min(1240px, 88vw);
  margin: 24px auto 0;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 24px;
  align-items: end;
  padding: 30px 0 8px;
}

.kicker {
  display: inline-block;
  margin-bottom: 10px;
  color: #dc2626;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 1.6px;
  text-transform: uppercase;
}

.hero h1 {
  margin: 0 0 14px;
  font-size: 42px;
  line-height: 1.15;
}

.hero p,
.block p {
  color: #4b5563;
  font-size: 14px;
  line-height: 1.75;
}

.meta-row,
.tag-list,
.confidence {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.meta-row span,
.tag-list span,
.confidence span {
  padding: 6px 10px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #111827;
  font-size: 12px;
  font-weight: 800;
}

.verdict,
.block,
.state-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.verdict {
  padding: 18px;
}

.verdict span {
  color: #6b7280;
  font-size: 12px;
  font-weight: 900;
}

.verdict strong {
  display: block;
  margin: 8px 0 12px;
  color: #b45309;
  font-size: 26px;
}

.verdict.passed strong {
  color: #166534;
}

.verdict p {
  margin: 6px 0;
  color: #4b5563;
  font-size: 13px;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
  align-items: start;
  padding-bottom: 60px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}

.summary-card {
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.summary-card h2 {
  margin: 0 0 10px;
  font-size: 18px;
}

.summary-card p {
  margin: 0;
}

.summary-card.primary {
  background: #fff7ed;
}

.summary-card.caution {
  background: #f8fafc;
}

.block {
  padding: 20px;
}

.block + .block {
  margin-top: 16px;
}

.block h2 {
  margin: 0 0 14px;
  font-size: 21px;
}

.interpret-section {
  padding-left: 14px;
  border-left: 3px solid #dc2626;
}

.interpret-section + .interpret-section {
  margin-top: 16px;
}

.interpret-section h3 {
  margin: 0 0 8px;
  font-size: 16px;
}

.cer-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.cer-grid article,
.evidence-item,
.chunk,
.question-card,
.caution-item {
  padding: 14px;
  border-radius: 8px;
  background: #f8fafc;
}

.cer-grid strong,
.evidence-item strong,
.chunk strong {
  display: block;
  margin-bottom: 8px;
  color: #1d4ed8;
  font-size: 13px;
}

.confidence {
  margin-bottom: 12px;
}

.confidence span {
  background: #dcfce7;
  color: #166534;
}

.confidence .warn {
  background: #fee2e2;
  color: #991b1b;
}

.evidence-item + .evidence-item,
.chunk + .chunk {
  margin-top: 10px;
}

.question-list {
  display: grid;
  gap: 10px;
}

.question-card {
  color: #334155;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.6;
}

.caution-item + .caution-item {
  margin-top: 10px;
}

.caution-item p {
  margin: 0;
}

.kv-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #f1f5f9;
  color: #4b5563;
  font-size: 13px;
}

.kv-row strong {
  color: #111827;
  text-align: right;
}

.warning {
  background: #fff7ed;
}

.state-card {
  padding: 28px;
  color: #6b7280;
  text-align: center;
}

@media (max-width: 980px) {
  .hero,
  .summary-grid,
  .layout,
  .cer-grid {
    grid-template-columns: 1fr;
  }
}
</style>
