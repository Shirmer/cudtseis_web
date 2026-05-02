# 大规模地质学文献 RAG：增强版准确度与速度优化完整方案

> 适用场景：地质学文献规模达到数万篇，KnowledgeUnit / chunk 达到百万级到千万级。  
> 目标：在保证回答准确度、引用可靠性、地质解释保守性和系统可扩展性的前提下，让普通问答保持在可接受延迟内。  
> 推荐作为《地质学文献知识库与高级 RAG 系统规划》的第二阶段核心技术文档。

---

## 1. 核心结论

当文献达到几万篇时，不能再使用简单的：

```text
用户问题
  -> 全库 chunk 向量检索 top_k
  -> 直接交给大模型回答
```

这种方案会导致：

```text
1. 搜索空间过大。
2. 弱相关 chunk 增多。
3. 引用准确度下降。
4. 回答速度变慢。
5. LLM 输入 token 过多。
6. 成本上升。
7. 地震、断裂、灾害类回答更容易过度推断。
```

增强版推荐方案是：

```text
离线预计算
  + 分层索引
  + 地理/元数据预过滤
  + Dense + Sparse Hybrid Search
  + RRF/DBSF 融合
  + Reranker / Late Interaction 候选重排
  + Evidence Pack 预算控制
  + 普通模式 / 深度模式
  + 多级缓存
  + 流式输出
  + RAG 评估闭环
```

一句话：

```text
不要全库盲搜；
先缩小搜索空间，再高质量重排，最后只把少量强证据交给大模型。
```

---

## 2. 大规模阶段的问题本质

假设系统规模：

```text
文献数量：30,000 篇
每篇平均 chunk：80-150 个
总 chunk 数：约 240 万 - 450 万
如果包含图、表、公式和多版本解析，可能达到 500 万以上 KnowledgeUnit
```

这时系统瓶颈不再是“能不能接入大模型 API”，而是：

```text
1. 能不能快速锁定相关论文。
2. 能不能排除无关领域、无关区域、无权限文献。
3. 能不能找出真正支持回答的 evidence。
4. 能不能避免把弱相关材料塞给大模型。
5. 能不能控制在线请求的检索、重排和生成时延。
6. 能不能持续评估检索和回答质量。
```

---

## 3. 总体增强架构

```text
                              用户问题
                                 |
                                 v
                          Query Analyzer
          问题分类 / 实体抽取 / 检索预算 / 安全规则
                                 |
                                 v
                      PostgreSQL/PostGIS 预过滤
          地震位置 / 区域 / 断裂 / 年份 / 权限 / 文献类型
                                 |
                                 v
                         Paper-level Retrieval
                 geo_paper_index 中召回 top 50-200 篇论文
                                 |
                                 v
                        Section-level Retrieval
                 geo_section_index 中召回 top 20-80 个章节
                                 |
                                 v
                     Chunk-level Hybrid Retrieval
             dense vector + sparse vector/BM25 + payload filter
                                 |
                                 v
                         Fusion / RRF / DBSF
                    合并 dense 与 sparse 的候选结果
                                 |
                                 v
                  Reranker / Late Interaction Rerank
                   对 top 50-150 候选证据进行高精度重排
                                 |
                                 v
                         Diversity Control
                控制同一论文、同一章节、同一证据类型占比
                                 |
                                 v
                           Evidence Pack
                    只选择 top 8-12 条高质量证据
                                 |
                                 v
                           LLM Answer
                结构化回答 / 引用 / 不确定性 / 验证报告
```

---

## 4. 离线阶段：把重活提前做掉

大规模系统中，在线请求不能临时做重任务。

### 4.1 离线入库流程

```text
PDF / 文献元数据
  -> 文件去重
  -> 元数据去重
  -> PDF 解析
  -> 文本 / 图 / 表 / 公式抽取
  -> chunk 切分
  -> KnowledgeUnit 标准化
  -> 地质实体抽取
  -> paper summary 生成
  -> section summary 生成
  -> embedding 生成
  -> sparse representation 生成
  -> PostgreSQL 保存元数据
  -> Qdrant 写入多级索引
  -> 记录 index_version
```

### 4.2 在线请求只做

```text
query 分析
query embedding
metadata filter
向量检索
sparse 检索
融合
重排
Evidence Pack 构建
LLM 生成
```

### 4.3 严禁在线阶段做

```text
临时解析 PDF
临时给整篇论文生成 embedding
临时总结大量论文
临时遍历数据库扫描 chunk
临时无过滤全库检索
```

---

## 5. 三层核心索引

大规模 RAG 最重要的设计是三层索引。

```text
Paper Index    论文级索引
Section Index  章节级索引
Chunk Index    证据级索引
```

---

## 6. Paper Index：先找对论文

### 6.1 Collection

```text
geo_paper_index_v1
```

### 6.2 每篇论文的 point 数量

```text
普通论文：1 个 point
长论文 / 综述：2-3 个 point
大型报告：按主题拆成多个 paper-level summary point
```

### 6.3 用于 embedding 的文本

```text
title
abstract
keywords
journal
year
authors
generated_summary
main_claims
methods
regions
faults
limitations
```

示例：

```text
Title: Active faulting and seismic hazard in the Longmenshan region
Abstract: ...
Generated Summary: This paper investigates ...
Main Claims:
  - ...
Methods:
  - Seismic catalog analysis
  - Geomorphic mapping
Regions:
  - Sichuan Basin
Faults:
  - Longmenshan Fault
Limitations:
  - Lack of focal mechanism constraints
```

### 6.4 Payload

```json
{
  "paper_id": "doi_xxx",
  "title": "Active faulting and seismic hazard in ...",
  "authors": ["..."],
  "year": 2024,
  "doi": "10.xxxx/xxxx",
  "journal": "...",
  "regions": ["Sichuan Basin"],
  "faults": ["Longmenshan Fault"],
  "topics": ["active fault", "seismic hazard"],
  "methods": ["seismic catalog", "geomorphology"],
  "access_level": "public",
  "license": "open_access",
  "index_version": "geo-rag-v1"
}
```

### 6.5 作用

```text
1. 全库问答先缩小到几十或几百篇论文。
2. 地震事件分析先找到相关区域文献。
3. 主题问答先找到核心综述和高相关论文。
4. 避免直接扫描百万级 chunk。
```

---

## 7. Section Index：再找对章节

### 7.1 Collection

```text
geo_section_index_v1
```

### 7.2 每个章节一个 point

常见章节：

```text
Abstract
Introduction
Regional Geology
Geological Setting
Tectonic Setting
Methods
Data
Results
Discussion
Conclusion
Figure Captions
Tables
Appendix
```

### 7.3 用于 embedding 的文本

```text
section_title
section_summary
section_keywords
page_start
page_end
section_entities
```

### 7.4 Payload

```json
{
  "section_id": "doi_xxx:section:geological_setting",
  "paper_id": "doi_xxx",
  "title": "Example Paper",
  "section": "Geological Setting",
  "page_start": 3,
  "page_end": 6,
  "regions": ["Sichuan Basin"],
  "faults": ["Longmenshan Fault"],
  "topics": ["tectonic setting", "active fault"],
  "index_version": "geo-rag-v1"
}
```

### 7.5 作用

```text
1. 减少 chunk 级噪声。
2. 把问题路由到正确章节。
3. 帮助多篇论文对比时按章节组织证据。
4. 提高回答结构性。
```

---

## 8. Chunk Index：最终找证据

### 8.1 Collection

```text
geo_chunk_index_v1
```

### 8.2 内容类型

```text
text
figure_caption
table_caption
table_content
equation_description
method
claim
limitation
```

### 8.3 Payload

```json
{
  "unit_id": "doi_xxx:text:p12:c003",
  "paper_id": "doi_xxx",
  "section_id": "doi_xxx:section:results",
  "document_id": "doi_xxx_v1",
  "content_type": "text",
  "title": "Example Paper",
  "section": "Results",
  "page": 12,
  "bbox": [120, 233, 480, 310],
  "year": 2024,
  "doi": "10.xxxx/xxxx",
  "regions": ["Sichuan Basin"],
  "faults": ["Longmenshan Fault"],
  "topics": ["earthquake", "active fault"],
  "methods": ["focal mechanism"],
  "access_level": "public",
  "parser": "mineru",
  "embedding_model": "text-embedding-3-small",
  "index_version": "geo-rag-v1"
}
```

### 8.4 作用

```text
1. 最终 evidence 来源。
2. 支持引用、页码、bbox。
3. 支持 Evidence Pack。
4. 支持回答可追溯。
```

---

## 9. 可选第四层：Figure/Table/Equation Index

当系统支持多模态后增加：

```text
geo_multimodal_index_v1
```

包含：

```text
figure caption
figure description
table markdown
table summary
equation latex
equation explanation
image uri
bbox
page
related text units
```

作用：

```text
1. 图表问答。
2. 公式问答。
3. PDF 定位。
4. 论文证据展示。
```

---

## 10. Query Analyzer：让系统知道应该怎么搜

大规模系统中，用户原始问题不能直接进检索器。

### 10.1 Query Analyzer 输入

```json
{
  "question": "这个地震是不是跟龙门山断裂有关？",
  "context": {
    "event_id": "usgs_xxx",
    "lat": 31.0,
    "lon": 103.4,
    "magnitude": 5.6,
    "depth": 10
  }
}
```

### 10.2 Query Analyzer 输出

```json
{
  "mode": "event_analysis",
  "intent": "tectonic_relation",
  "topics": ["tectonic setting", "active fault", "seismicity"],
  "regions": ["Sichuan Basin"],
  "faults": ["Longmenshan Fault"],
  "methods": ["focal mechanism", "seismic catalog", "InSAR"],
  "content_types": ["text", "figure_caption", "table_content"],
  "year_range": [1990, 2026],
  "risk_level": "scientific_explanation",
  "retrieval_budget": "normal",
  "uncertainty_rules": [
    "Do not infer causative fault from magnitude and location alone.",
    "Mention missing focal mechanism evidence if unavailable."
  ]
}
```

### 10.3 模式分类

```text
paper_qa           单篇论文问答
global_qa          全库问答
event_analysis     地震事件分析
region_analysis    区域分析
fault_analysis     断裂分析
method_query       方法问答
comparison         多论文对比
deep_report        深度科研分析
```

### 10.4 Query Rewrite

原问题：

```text
这个地震是不是跟龙门山断裂有关？
```

改写成：

```text
Longmenshan Fault tectonic setting seismicity
Sichuan Basin active fault earthquake
focal mechanism Longmenshan region earthquake
historical seismicity Longmenshan Fault
seismic hazard Longmenshan Fault
```

---

## 11. Metadata Filter：准确度和速度的核心

### 11.1 必须抽取和保存的字段

```text
paper_id
document_id
section_id
content_type
section
year
region
fault
topic
method
access_level
license
source_type
parser
embedding_model
index_version
```

### 11.2 必须建立 payload index 的字段

```text
paper_id
section_id
content_type
section
year
region
fault
topic
method
access_level
index_version
```

### 11.3 为什么重要

```text
1. 带过滤条件的检索更快。
2. 无权限文献不会进入候选集。
3. 不同 embedding 版本不会混用。
4. 区域/断裂/主题问题能提前缩小搜索空间。
5. 地震事件分析能结合 PostGIS 做空间过滤。
```

---

## 12. PostGIS 地理预过滤

地震事件分析不能全库盲搜。

### 12.1 流程

```text
用户点击地震事件
  -> 读取经纬度、震级、深度、时间
  -> PostGIS 查询附近区域、断裂、历史事件
  -> 得到 region/fault/tectonic_setting
  -> 构造 Qdrant filter
  -> 再进入 paper/section/chunk 检索
```

### 12.2 示例

```text
事件：四川盆地边缘 M5.6
PostGIS 返回：
  region = Sichuan Basin
  fault_candidates = Longmenshan Fault, Xianshuihe Fault
  tectonic_setting = eastern Tibetan Plateau margin
```

Qdrant filter：

```json
{
  "should": [
    {"key": "regions", "match": {"value": "Sichuan Basin"}},
    {"key": "faults", "match": {"value": "Longmenshan Fault"}}
  ],
  "must": [
    {"key": "access_level", "match": {"value": "public"}},
    {"key": "index_version", "match": {"value": "geo-rag-v1"}}
  ]
}
```

### 12.3 地质解释规则

```text
1. 不能仅凭震级、深度和位置断定发震断层。
2. 没有震源机制时必须说明不能确定断层运动性质。
3. 没有余震分布、InSAR、GNSS 时不能断言破裂过程。
4. 灾害风险必须基于证据，不能凭空预测。
```

---

## 13. Hybrid Search：Dense + Sparse

### 13.1 为什么需要 hybrid

Dense embedding 擅长语义相似：

```text
“活动断裂对地震危险性有什么影响”
≈ “active fault and seismic hazard relationship”
```

Sparse / BM25 擅长精确匹配：

```text
Longmenshan Fault
Wenchuan earthquake
InSAR
GNSS
Mw 7.9
strike-slip
```

地质学场景必须两者结合。

---

### 13.2 推荐流程

```text
query
  -> dense embedding
  -> sparse representation / BM25 query
  -> dense search top 80
  -> sparse search top 80
  -> RRF 或 DBSF 融合
  -> rerank top 20
  -> Evidence Pack top 8-12
```

### 13.3 Qdrant 方案

```text
一个 collection 中保存：
  dense_vector
  sparse_vector
```

优势：

```text
1. 架构简单。
2. dense/sparse 可以统一在 Qdrant 完成。
3. 可以使用 RRF 融合。
4. 不需要额外 OpenSearch 组件。
```

### 13.4 OpenSearch/BM25 方案

```text
Qdrant：dense vector
OpenSearch：BM25 / keyword / phrase search
Fusion：RRF / weighted fusion
```

优势：

```text
1. 关键词检索更成熟。
2. 方便调试。
3. 支持复杂检索语法。
```

劣势：

```text
1. 多一个系统。
2. 运维复杂。
3. 需要维护结果融合。
```

### 13.5 推荐取舍

```text
第二阶段早期：
  Qdrant dense + payload filter

第二阶段中期：
  Qdrant dense + sparse hybrid

如果专业名词精确检索仍不够：
  再引入 OpenSearch/BM25
```

---

## 14. Fusion：RRF / DBSF

### 14.1 RRF

RRF 用于融合多个检索列表：

```text
dense result
sparse result
section result
paper result
```

优点：

```text
1. 简单稳定。
2. 不需要校准不同检索器分数。
3. 适合第一版 hybrid search。
```

### 14.2 DBSF

DBSF 基于分数分布融合。

优点：

```text
1. 在分数可比较或可标准化时效果更细。
2. 可作为 RRF 后的增强。
```

建议：

```text
先用 RRF。
评估集稳定后，再比较 RRF 与 DBSF。
```

---

## 15. Reranker：最终证据质量控制

### 15.1 为什么必须有 reranker

向量检索负责粗召回，不应直接决定最终 evidence。

Reranker 判断：

```text
1. 这个 chunk 是否真正回答了问题。
2. 这个 chunk 是直接支持、间接支持还是背景信息。
3. 这个 chunk 是否只是出现关键词。
4. 这个 chunk 是否适合作为 citation。
```

### 15.2 可选方案

```text
第一版：
  LLM rerank

第二版：
  bge-reranker
  jina-reranker
  cohere-rerank

第三版：
  地质领域微调 reranker
```

### 15.3 推荐流程

```text
hybrid search top 80-150
  -> reranker top 20-40
  -> diversity control top 8-12
```

---

## 16. Late Interaction / ColBERT：更强但要谨慎使用

### 16.1 优点

Late Interaction / ColBERT 使用 token-level 匹配，适合：

```text
复杂长问题
专业术语密集问题
多条件地质问题
图表和文本混合问题
```

### 16.2 问题

```text
1. 存储成本更高。
2. 计算成本更高。
3. 全库使用会明显拖慢系统。
4. 插入和索引开销较大。
```

### 16.3 推荐用法

不要作为默认全库第一层检索。

推荐：

```text
dense + sparse 召回 top 100
  -> ColBERT / late-interaction rerank
  -> Evidence Pack
```

只在以下场景启用：

```text
1. 深度分析模式。
2. 检索置信度低。
3. 普通 reranker 分数接近。
4. 复杂科研问题。
5. 多篇论文对比。
```

---

## 17. Evidence Pack 预算控制

大模型不能读取过多证据。

### 17.1 普通模式预算

```text
Evidence 数量：8-12 条
每条长度：300-800 中文字或等价英文 token
总上下文：6k-12k tokens
输出长度：500-1200 中文字
目标时延：5-10 秒
```

### 17.2 深度模式预算

```text
Evidence 数量：15-25 条
每条长度：500-1000 中文字或等价英文 token
总上下文：15k-30k tokens
输出长度：1500-3000 中文字
目标时延：15-30 秒
```

### 17.3 Diversity Control

规则：

```text
全库问答：
  每篇论文最多 2-3 个 chunk。
  至少覆盖 3-5 篇不同论文。

单篇论文问答：
  不限制同一论文，但限制同一章节重复。

区域分析：
  优先不同年份、不同方法、不同文献来源。

地震事件分析：
  优先区域构造、活动断裂、历史地震、震源机制、危险性研究。

方法问答：
  优先 methods / data / discussion 章节。

综述型问题：
  优先 review paper 和高引用/高质量来源。
```

### 17.4 Evidence 类型

每条 evidence 标记：

```text
direct_support      直接支持
indirect_support    间接支持
background          背景信息
conflicting         冲突证据
weak_support        弱支持
missing             缺失证据提示
```

回答规则：

```text
1. 核心结论必须由 direct_support 支撑。
2. background 不能支撑强结论。
3. weak_support 必须配合不确定性说明。
4. conflicting 必须在回答中说明分歧。
5. missing 必须转化为“当前证据不足”。
```

---

## 18. 自适应检索预算 Adaptive Retrieval Budget

不同问题不应该用同样重的检索流程。

### 18.1 简单问题

例如：

```text
什么是震源机制解？
什么是活动断裂？
```

预算：

```text
paper top 20
section top 10
chunk top 30
rerank top 10
evidence top 6
```

目标：

```text
3-6 秒
```

---

### 18.2 普通专业问题

例如：

```text
活动断裂和地震危险性之间有什么关系？
```

预算：

```text
paper top 50-100
section top 20-30
chunk dense top 80
chunk sparse top 80
rerank top 20
evidence top 8-12
```

目标：

```text
5-10 秒
```

---

### 18.3 地震事件分析

预算：

```text
PostGIS 预过滤
paper top 100
section top 30
chunk dense top 80
chunk sparse top 80
rerank top 20
evidence top 8-12
```

目标：

```text
6-12 秒
```

---

### 18.4 深度科研分析

例如：

```text
比较 2008 年汶川地震相关研究中关于龙门山断裂活动性的不同解释。
```

预算：

```text
paper top 200
section top 80
chunk dense top 150
chunk sparse top 150
rerank top 40
late-interaction rerank optional
evidence top 15-25
claim verification on
```

目标：

```text
15-30 秒
```

---

## 19. 缓存策略

### 19.1 Query Embedding Cache

```text
key = hash(normalized_query)
value = query_embedding
ttl = 7-30 days
```

适合：

```text
重复问题
常见概念
热门区域
热门断裂
```

---

### 19.2 Retrieval Cache

```text
key = hash(query + filters + mode + index_version)
value = retrieved_unit_ids
ttl = 1-7 days
```

注意：

```text
index_version 变化后缓存自动失效。
```

---

### 19.3 Evidence Pack Cache

```text
key = hash(query + filters + reranker_version + index_version)
value = evidence_pack
ttl = 1-7 days
```

适合：

```text
全库通用问题
热门区域分析
固定论文问答
重复地震事件分析
```

---

### 19.4 Answer Cache

```text
key = hash(question + evidence_pack_ids + prompt_version)
value = structured_answer
ttl = 1-30 days
```

适合：

```text
什么是活动断裂？
震源机制解有什么意义？
地震危险性和活动断裂有什么关系？
```

不适合：

```text
用户私有文献
权限敏感问题
刚刚更新的索引
需要最新文献的问题
```

---

### 19.5 Cache 失效规则

缓存 key 必须包含：

```text
index_version
embedding_model
reranker_version
prompt_version
access_scope
user_permission_scope
```

否则可能出现：

```text
1. 用旧索引回答新问题。
2. 无权限用户看到内部文献证据。
3. 换模型后仍使用旧检索结果。
```

---

## 20. Qdrant 性能优化

### 20.1 Payload Index

必须为高频过滤字段建立 payload index：

```text
paper_id
section_id
region
fault
topic
method
year
content_type
access_level
index_version
```

### 20.2 HNSW 参数

根据模式调节：

```text
普通模式：
  ef_search 较低
  top_k 较小
  优先速度

深度模式：
  ef_search 较高
  top_k 较大
  优先召回
```

### 20.3 Quantization

规模达到百万级 chunk 后考虑：

```text
geo_chunk_index:
  scalar quantization

geo_paper_index:
  可暂不量化，保证第一层召回质量

geo_section_index:
  视数据量决定
```

注意：

```text
量化会影响召回质量，必须用评估集比较：
  recall@10
  context precision
  citation accuracy
  faithfulness
```

### 20.4 On-disk Vectors

内存压力大时：

```text
1. 原始向量 on disk。
2. 量化向量尽量留内存。
3. 热门 collection 或热门分片保留内存。
```

### 20.5 分片与副本

生产阶段：

```text
sharding:
  扩展容量

replication:
  提高吞吐和可用性
```

### 20.6 Collection 拆分建议

不要把所有内容都放进一个 collection。

推荐：

```text
geo_paper_index_v1
geo_section_index_v1
geo_chunk_index_v1
geo_multimodal_index_v1
```

好处：

```text
1. 每层索引调参独立。
2. paper/section 可以高召回，chunk 可以重速度。
3. 图表索引不会污染正文检索。
4. 后续迁移和重建更清晰。
```

---

## 21. LLM 生成速度优化

### 21.1 控制输入长度

```text
普通模式：
  evidence 8-12 条
  总上下文 6k-12k tokens

深度模式：
  evidence 15-25 条
  总上下文 15k-30k tokens
```

### 21.2 固定 Prompt 前缀

将固定内容放在 prompt 前部：

```text
system role
citation rules
uncertainty rules
地震解释保守规则
output JSON schema
```

动态内容放后面：

```text
question
evidence pack
```

这样更容易命中 prompt cache。

### 21.3 Structured Outputs

回答强制结构化：

```json
{
  "answer": "...",
  "claims": [
    {
      "claim": "...",
      "evidence_ids": ["E1", "E3"],
      "confidence": "medium"
    }
  ],
  "citations": [
    {
      "evidence_id": "E1",
      "paper_id": "...",
      "page": 12,
      "unit_id": "..."
    }
  ],
  "uncertainty": [
    "..."
  ],
  "missing_evidence": [
    "..."
  ]
}
```

### 21.4 Streaming

前端必须流式显示：

```text
0-1 秒：
  正在分析问题类型

1-2 秒：
  已找到候选论文

2-4 秒：
  已筛选证据

4 秒后：
  开始流式输出回答

回答后：
  补全引用卡片和验证报告
```

### 21.5 分阶段接口

```text
POST /api/rag/query
  -> 返回 run_id

GET /api/rag/runs/{run_id}/status
  -> 返回检索进度

GET /api/rag/runs/{run_id}/evidence
  -> 返回证据

SSE /api/rag/runs/{run_id}/stream
  -> 流式回答

GET /api/rag/runs/{run_id}/validation
  -> 返回验证报告
```

---

## 22. 普通模式与深度模式

### 22.1 普通模式

默认模式。

目标：

```text
3-10 秒内返回主要回答
P95 <= 10 秒
```

特点：

```text
检索预算中等
Evidence 8-12 条
轻量验证
流式输出
适合绝大多数用户问题
```

### 22.2 深度模式

用户主动触发。

目标：

```text
15-30 秒内返回完整分析
```

特点：

```text
检索预算更大
Evidence 15-25 条
启用 late-interaction rerank
启用 Claim Verification
检查冲突证据
输出更完整报告
```

### 22.3 为什么要分模式

```text
1. 不让简单问题拖慢。
2. 给复杂问题足够证据。
3. 用户预期更明确。
4. 成本和速度可控。
```

---

## 23. 不同场景的完整流程

### 23.1 单篇论文问答

```text
question + paper_id
  -> Query Analyzer
  -> Qdrant filter: paper_id
  -> chunk hybrid search
  -> rerank top 8-12
  -> Evidence Pack
  -> LLM answer
```

目标：

```text
3-6 秒
```

---

### 23.2 全库普通问答

```text
question
  -> Query Analyzer
  -> paper_index top 50-100
  -> section_index top 20-30
  -> chunk_index hybrid top 80
  -> rerank top 20
  -> diversity top 8-12
  -> Evidence Pack
  -> LLM answer
```

目标：

```text
5-10 秒
```

---

### 23.3 地震事件分析

```text
event_id
  -> 读取 event 参数
  -> PostGIS 查询附近区域/断裂
  -> Query Analyzer 生成地质查询
  -> paper_index top 100
  -> section_index top 30
  -> chunk hybrid top 80
  -> rerank top 20
  -> Evidence Pack
  -> LLM answer with uncertainty
```

目标：

```text
6-12 秒
```

---

### 23.4 多篇论文对比

```text
selected_paper_ids
  -> 每篇论文内部检索 top 5-8
  -> 合并候选
  -> rerank
  -> 按论文分组 Evidence Pack
  -> LLM comparison answer
```

目标：

```text
8-15 秒
```

---

### 23.5 深度科研分析

```text
question
  -> Query Analyzer
  -> paper top 200
  -> section top 80
  -> chunk dense top 150
  -> chunk sparse top 150
  -> fusion
  -> rerank top 40
  -> optional late-interaction rerank
  -> evidence top 15-25
  -> LLM answer
  -> Claim Verification
  -> Validation Report
```

目标：

```text
15-30 秒
```

---

## 24. API 设计

### 24.1 Query

```http
POST /api/rag/query
```

请求：

```json
{
  "question": "活动断裂和地震危险性之间有什么关系？",
  "mode": "global_qa",
  "speed_mode": "normal",
  "filters": {
    "regions": ["Sichuan Basin"],
    "year_range": [2000, 2026]
  }
}
```

返回：

```json
{
  "run_id": "rag_run_xxx",
  "status": "running"
}
```

---

### 24.2 Status

```http
GET /api/rag/runs/{run_id}/status
```

返回：

```json
{
  "run_id": "rag_run_xxx",
  "stage": "reranking",
  "progress": 0.62,
  "message": "已筛选出 18 条候选证据"
}
```

---

### 24.3 Evidence

```http
GET /api/rag/runs/{run_id}/evidence
```

返回：

```json
{
  "evidence_pack": {
    "evidence": [
      {
        "evidence_id": "E1",
        "unit_id": "doi_xxx:text:p12:c003",
        "paper_id": "doi_xxx",
        "title": "...",
        "year": 2024,
        "page": 12,
        "section": "Discussion",
        "support_type": "direct_support",
        "text": "..."
      }
    ],
    "missing_evidence": [
      "未找到震源机制证据"
    ]
  }
}
```

---

### 24.4 Stream

```http
GET /api/rag/runs/{run_id}/stream
```

使用 SSE 返回：

```text
event: token
data: 根据当前证据，...

event: citation
data: {"evidence_id": "E1", "paper_id": "...", "page": 12}

event: done
data: {"status": "completed"}
```

---

### 24.5 Validation

```http
GET /api/rag/runs/{run_id}/validation
```

返回：

```json
{
  "passed": true,
  "unsupported_claims": [],
  "warnings": [
    "缺少震源机制证据，因此不能确定断层运动性质。"
  ],
  "confidence": 0.82
}
```

---

## 25. 数据表扩展

### 25.1 paper_summaries

```text
paper_summaries
  id
  paper_id
  abstract
  generated_summary
  main_claims_json
  methods_json
  regions_json
  faults_json
  limitations_json
  embedding_id
  created_at
```

### 25.2 section_summaries

```text
section_summaries
  id
  section_id
  paper_id
  section_title
  summary
  page_start
  page_end
  topics_json
  regions_json
  faults_json
  embedding_id
  created_at
```

### 25.3 retrieval_runs

```text
retrieval_runs
  id
  run_id
  question
  mode
  speed_mode
  query_plan_json
  filters_json
  paper_candidates_json
  section_candidates_json
  chunk_candidates_json
  reranked_json
  latency_json
  created_at
```

### 25.4 evidence_packs

```text
evidence_packs
  id
  pack_id
  run_id
  evidence_json
  missing_evidence_json
  uncertainty_rules_json
  created_at
```

### 25.5 cache_entries

```text
cache_entries
  id
  cache_key
  cache_type
  index_version
  prompt_version
  value_json
  expires_at
  created_at
```

---

## 26. 后端服务拆分

```text
backend/app/services/
  query_analyzer.py
  paper_retriever.py
  section_retriever.py
  chunk_retriever.py
  hybrid_search_service.py
  fusion_service.py
  reranker_service.py
  late_interaction_service.py
  diversity_service.py
  evidence_pack_service.py
  rag_answer_service.py
  rag_cache_service.py
  rag_metrics_service.py
  event_geo_filter_service.py
```

各服务职责：

```text
query_analyzer:
  分析问题、抽取实体、决定检索预算。

paper_retriever:
  论文级召回。

section_retriever:
  章节级召回。

chunk_retriever:
  KnowledgeUnit 级召回。

hybrid_search_service:
  dense + sparse 检索。

fusion_service:
  RRF / DBSF 融合。

reranker_service:
  候选证据重排。

late_interaction_service:
  高精度复杂问题重排。

diversity_service:
  控制证据多样性。

evidence_pack_service:
  构建 Evidence Pack。

rag_answer_service:
  调用大模型生成结构化回答。

rag_cache_service:
  查询、检索、证据、回答缓存。

event_geo_filter_service:
  PostGIS 地理预过滤。
```

---

## 27. 在线问答伪代码

```python
def answer_question(question: str, mode: str, speed_mode: str, filters: dict):
    # 1. 问题分析
    query_plan = query_analyzer.analyze(
        question=question,
        mode=mode,
        speed_mode=speed_mode,
        filters=filters,
    )

    # 2. 检查回答缓存
    cached_answer = rag_cache.get_answer(query_plan.answer_cache_key)
    if cached_answer:
        return cached_answer

    # 3. 检查 Evidence Pack 缓存
    cached_pack = rag_cache.get_evidence_pack(query_plan.evidence_cache_key)
    if cached_pack:
        evidence_pack = cached_pack
    else:
        # 4. 论文级召回
        paper_candidates = paper_retriever.search(
            query=query_plan.paper_query,
            filters=query_plan.paper_filters,
            top_k=query_plan.paper_top_k,
        )

        # 5. 章节级召回
        section_candidates = section_retriever.search(
            query=query_plan.section_query,
            filters={
                **query_plan.section_filters,
                "paper_id": paper_candidates.paper_ids,
            },
            top_k=query_plan.section_top_k,
        )

        # 6. chunk 级 dense 检索
        dense_results = chunk_retriever.dense_search(
            query=query_plan.chunk_query,
            filters={
                **query_plan.chunk_filters,
                "paper_id": paper_candidates.paper_ids,
            },
            top_k=query_plan.chunk_dense_top_k,
        )

        # 7. chunk 级 sparse 检索
        sparse_results = chunk_retriever.sparse_search(
            query=query_plan.keyword_query,
            filters={
                **query_plan.chunk_filters,
                "paper_id": paper_candidates.paper_ids,
            },
            top_k=query_plan.chunk_sparse_top_k,
        )

        # 8. 融合
        fused_results = fusion_service.rrf(
            dense_results=dense_results,
            sparse_results=sparse_results,
        )

        # 9. 普通 rerank
        reranked = reranker_service.rerank(
            query=question,
            candidates=fused_results,
            top_k=query_plan.rerank_top_k,
        )

        # 10. 可选 late-interaction rerank
        if query_plan.use_late_interaction:
            reranked = late_interaction_service.rerank(
                query=question,
                candidates=reranked,
                top_k=query_plan.late_interaction_top_k,
            )

        # 11. 多样性控制
        selected = diversity_service.select(
            candidates=reranked,
            max_chunks_per_paper=query_plan.max_chunks_per_paper,
            max_chunks_per_section=query_plan.max_chunks_per_section,
            evidence_count=query_plan.evidence_count,
        )

        # 12. Evidence Pack
        evidence_pack = evidence_pack_service.build(
            question=question,
            mode=mode,
            query_plan=query_plan,
            evidence=selected,
        )

        rag_cache.set_evidence_pack(
            key=query_plan.evidence_cache_key,
            value=evidence_pack,
        )

    # 13. LLM 结构化回答
    answer = rag_answer_service.generate(
        question=question,
        evidence_pack=evidence_pack,
        output_schema="geo_rag_answer_v1",
        stream=True,
    )

    # 14. 可选验证
    if query_plan.enable_claim_verification:
        validation = claim_verifier.verify(
            answer=answer,
            evidence_pack=evidence_pack,
        )
        answer["validation"] = validation

    # 15. 记录运行信息
    rag_metrics_service.record(
        question=question,
        query_plan=query_plan,
        evidence_pack=evidence_pack,
        answer=answer,
    )

    # 16. 缓存回答
    rag_cache.set_answer(
        key=query_plan.answer_cache_key,
        value=answer,
    )

    return answer
```

---

## 28. 性能目标

### 28.1 延迟目标

| 场景 | 目标耗时 | P95 目标 |
|---|---:|---:|
| 单篇论文问答 | 3-6 秒 | <= 6 秒 |
| 全库普通问答 | 5-10 秒 | <= 10 秒 |
| 地震事件分析 | 6-12 秒 | <= 12 秒 |
| 多篇论文对比 | 8-15 秒 | <= 15 秒 |
| 深度科研分析 | 15-30 秒 | <= 30 秒 |
| PDF 入库 | 分钟级 | 不影响在线问答 |

### 28.2 质量目标

```text
Top-10 retrieval hit rate >= 80%
Citation accuracy >= 95%
Unsupported claim rate <= 5-10%
Faithfulness >= 0.85
Context precision >= 0.75
普通问答 evidence 数量 <= 12
普通问答输入上下文 <= 12k tokens
```

---

## 29. 监控指标

必须记录：

```text
run_id
query_id
mode
speed_mode
question_hash
filters
paper_top_k
section_top_k
chunk_dense_top_k
chunk_sparse_top_k
rerank_top_k
evidence_count
retrieval_latency_ms
paper_retrieval_latency_ms
section_retrieval_latency_ms
chunk_retrieval_latency_ms
fusion_latency_ms
rerank_latency_ms
llm_latency_ms
validation_latency_ms
total_latency_ms
input_tokens
output_tokens
cache_hit_type
citation_count
unsupported_claim_count
faithfulness_score
context_precision_score
```

用于分析：

```text
1. 慢在检索、重排还是 LLM。
2. 哪类问题最慢。
3. 哪些查询经常缓存命中。
4. 哪些问题检索失败。
5. 哪些回答 unsupported claim 高。
6. 量化或 HNSW 调参是否损害质量。
```

---

## 30. 评估体系

### 30.1 测试集

建立 100-300 个测试问题，覆盖：

```text
单篇论文问答
全库概念问答
区域构造背景
活动断裂
地震事件分析
震源机制
灾害风险
方法问答
证据不足问题
冲突证据问题
```

### 30.2 指标

```text
retrieval_hit_rate
context_precision
context_recall
faithfulness
answer_relevancy
citation_accuracy
unsupported_claim_rate
latency_p50
latency_p95
```

### 30.3 回归测试

每次改变：

```text
embedding model
chunk strategy
parser
reranker
hybrid fusion
HNSW 参数
quantization
prompt
```

都必须跑评估集。

---

## 31. 更好的方案检查与取舍

### 31.1 直接使用更大的长上下文模型？

不推荐作为默认方案。

优点：

```text
实现简单。
可以容纳更多上下文。
```

缺点：

```text
成本高。
速度慢。
引用控制弱。
长上下文中间信息可能被忽略。
每次都塞大量证据浪费。
不能替代检索系统。
```

推荐：

```text
只在深度模式中，对已经筛选后的 Evidence Pack 使用长上下文。
```

---

### 31.2 全库 ColBERT / Late Interaction？

不推荐默认全库使用。

优点：

```text
精度高。
复杂查询效果好。
```

缺点：

```text
存储和计算成本高。
插入慢。
索引开销大。
全库默认使用会拖慢普通问答。
```

推荐：

```text
作为候选集 top 100 后的重排器。
只在深度模式、低置信度或复杂问题中启用。
```

---

### 31.3 OpenSearch/BM25 替代 Qdrant sparse？

不作为第一选择，但可作为增强。

优点：

```text
关键词检索成熟。
专业名词精确匹配强。
调试方便。
```

缺点：

```text
多一个组件。
部署和维护复杂。
需要结果融合。
```

推荐：

```text
先用 Qdrant dense + sparse hybrid。
如果术语检索仍不够，再加入 OpenSearch。
```

---

### 31.4 GraphRAG？

适合作为后期增强，不适合作为主检索替代。

优点：

```text
适合区域-断裂-地震-论文之间的关系导航。
适合多跳问题。
适合知识探索。
```

缺点：

```text
构图成本高。
实体抽取错误会传播。
地质关系复杂，人工校验成本高。
对普通问答速度未必更快。
```

推荐：

```text
第二阶段后期做“地质实体图谱”。
主问答仍以分层 RAG 为核心。
```

---

### 31.5 完全依赖 Agent 多轮检索？

不推荐作为主流程。

优点：

```text
看起来灵活。
可以处理开放任务。
```

缺点：

```text
延迟不可控。
成本不可控。
结果不稳定。
难以复现和评估。
```

推荐：

```text
主流程保持确定性 pipeline。
Agent 只用于深度分析、query rewrite 或报告生成辅助。
```

---

### 31.6 pgvector 承担全部向量检索？

不推荐用于数百万 chunk 的主向量库。

推荐分工：

```text
PostgreSQL/PostGIS：
  业务数据、地理查询、状态、权限、审计。

Qdrant：
  大规模向量检索、payload filter、hybrid search、量化、分片。
```

---

## 32. 推荐落地路线

### 32.1 MVP 后第一轮增强

目标：先解决“几万篇之前的架构准备”。

```text
1. 建 paper_index。
2. 建 section_index。
3. 保留 chunk_index。
4. 增加 payload index。
5. 增加 Query Analyzer。
6. 增加 Evidence Pack budget。
7. 增加普通模式 / 深度模式。
8. 增加 retrieval cache。
```

---

### 32.2 第二轮增强

目标：提高准确度。

```text
1. 增加 sparse search。
2. 增加 hybrid search。
3. 增加 RRF fusion。
4. 增加 reranker。
5. 增加 diversity control。
6. 增加 RAGAS 评估集。
7. 增加 citation accuracy 评估。
```

---

### 32.3 第三轮增强

目标：提高速度和规模能力。

```text
1. 增加 scalar quantization。
2. 增加 on-disk vectors。
3. 调整 HNSW 参数。
4. 增加 Qdrant sharding / replication。
5. 增加 streaming 输出。
6. 优化 prompt cache。
```

---

### 32.4 第四轮增强

目标：高级检索和科研级分析。

```text
1. 增加 late-interaction rerank。
2. 增加 Claim Verification。
3. 增加冲突证据检测。
4. 增加 OpenSearch/BM25，视情况。
5. 增加 GraphRAG，视情况。
6. 增加深度科研报告模式。
```

---

## 33. 最终推荐配置

### 33.1 普通问答默认配置

```text
paper_top_k = 80
section_top_k = 30
chunk_dense_top_k = 80
chunk_sparse_top_k = 80
rerank_top_k = 20
evidence_count = 10
max_chunks_per_paper = 3
max_chunks_per_section = 2
use_late_interaction = false
enable_claim_verification = light
```

### 33.2 单篇论文问答配置

```text
paper_filter = selected paper_id
section_top_k = 20
chunk_dense_top_k = 50
chunk_sparse_top_k = 50
rerank_top_k = 12
evidence_count = 8
max_chunks_per_section = 3
use_late_interaction = false
```

### 33.3 地震事件分析配置

```text
use_postgis_prefilter = true
paper_top_k = 100
section_top_k = 40
chunk_dense_top_k = 100
chunk_sparse_top_k = 100
rerank_top_k = 25
evidence_count = 12
max_chunks_per_paper = 3
enable_uncertainty_rules = true
```

### 33.4 深度分析配置

```text
paper_top_k = 200
section_top_k = 80
chunk_dense_top_k = 150
chunk_sparse_top_k = 150
rerank_top_k = 40
late_interaction_top_k = 25
evidence_count = 20
max_chunks_per_paper = 4
enable_claim_verification = full
enable_conflict_detection = true
```

---

## 34. 最终结论

对于数万篇地质学文献，最佳路线不是简单换更强的大模型，也不是直接扩大 top_k，而是：

```text
离线阶段：
  预计算 paper summary、section summary、chunk embedding、地质实体和多级索引。

在线阶段：
  Query Analyzer 先确定搜索意图；
  PostGIS 和 metadata filter 先缩小范围；
  Paper Index 先找论文；
  Section Index 再找章节；
  Chunk Index 找最终证据；
  Hybrid Search 提升术语和语义召回；
  Reranker / Late Interaction 提高证据质量；
  Evidence Pack 控制上下文；
  LLM 只基于证据回答；
  Streaming 和缓存保证体验；
  RAGAS 和自建测试集持续评估。
```

一句话总结：

```text
几万篇文献不是问题；
问题是不能全库盲搜。
正确方案是“离线预计算 + 分层召回 + 混合检索 + 高精度重排 + 证据预算 + 缓存 + 流式输出”。
```

---

## 35. 参考资料

```text
Qdrant Filtering:
https://qdrant.tech/documentation/search/filtering/

Qdrant Payload Index:
https://qdrant.tech/documentation/manage-data/payload/

Qdrant Indexing:
https://qdrant.tech/documentation/manage-data/indexing/

Qdrant Hybrid Queries:
https://qdrant.tech/documentation/search/hybrid-queries/

Qdrant Quantization:
https://qdrant.tech/documentation/manage-data/quantization/

Qdrant Multivectors / Late Interaction:
https://qdrant.tech/documentation/tutorials-search-engineering/using-multivector-representations/

Qdrant Reranking Hybrid Search:
https://qdrant.tech/documentation/tutorials-search-engineering/reranking-hybrid-search/

OpenAI Prompt Caching:
https://developers.openai.com/api/docs/guides/prompt-caching

OpenAI Structured Outputs:
https://developers.openai.com/api/docs/guides/structured-outputs

OpenAI Streaming:
https://developers.openai.com/api/docs/guides/streaming-responses

OpenAI Embeddings:
https://developers.openai.com/api/docs/guides/embeddings

RAGAS Faithfulness:
https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/

RAGAS Context Precision:
https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/
```
