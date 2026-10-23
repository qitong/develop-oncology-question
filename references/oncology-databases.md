# 肿瘤选题数据库地图

按"用来回答选题中的哪个问题"组织。括号里的 skill 名都是**可选增强**，没安装时直接用表中的 API 或网址。✅ = 有公开 API，`scripts/onco_scan.py` 已接入或可用 curl 直接调用；🌐 = 只能网页检索（用 WebSearch/WebFetch 或 /browse）；🔑 = 需注册或 token。

## 1. 已知什么？（文献）

| 数据源 | 用途 | 访问 |
|---|---|---|
| PubMed / MEDLINE | 主文献库；用 MeSH（如 `"Stomach Neoplasms"[MeSH]`）+ 发表类型过滤 | ✅ E-utilities `esearch/esummary/efetch` |
| Europe PMC | 全文检索 + 预印本（`SRC:PPR`）+ 引用关系 | ✅ `https://www.ebi.ac.uk/europepmc/webservices/rest/search` |
| medRxiv / bioRxiv | 最新预印本 | ✅ 走 Europe PMC，或用 `scientific-skills:biorxiv-database` |
| OpenAlex | 引用网络、高被引、作者/机构图谱（找"批评者"） | ✅ `https://api.openalex.org/works?search=`（无 key 时每日额度很小） |
| Cochrane Library | 已有系统评价，避免重复做 Meta | 🌐 |
| 会议摘要：ASCO / ASCO GI / ESMO / ESMO GI / WCGIC / CSCO / AACR | **最新**阴性/阳性结果，往往比正刊早 1–2 年；撞车检查必查 | 🌐（ASCO：meetings.asco.org；ESMO：Annals of Oncology 增刊） |
| 中国知网 / 万方 / 中华医学期刊网 | 中文文献、国内单中心经验 | 🌐 |

PubMed 实用检索块：
- 研究类型：`randomized controlled trial[pt]`、`meta-analysis[pt]`、`"Clinical Trial, Phase III"[pt]`
- 时间：`2022:2026[dp]`
- 真实世界：`(real-world OR "real world" OR retrospective OR registry)`
- 中国人群：`(China OR Chinese)[ad] OR (Chinese[tiab])`

## 2. 谁在做？（试验注册，撞车检查与竞争格局）

| 数据源 | 用途 | 访问 |
|---|---|---|
| ClinicalTrials.gov | 全球注册；状态、分期、终点、入排标准 | ✅ API v2 `https://clinicaltrials.gov/api/v2/studies?query.cond=&query.intr=&query.term=` |
| ChiCTR 中国临床试验注册中心 | 大量国内研究者发起研究（IIT）只在这里注册 | 🌐 https://www.chictr.org.cn/ |
| WHO ICTRP | 汇总 ChiCTR、JPRN、EU CTR、CTRI 等 | 🌐 https://trialsearch.who.int/ |
| 药物临床试验登记与信息公示平台（CDE） | 国内注册类试验、竞品管线 | 🌐 http://www.chinadrugtrials.org.cn/ |
| EU CTIS | 欧洲试验 | 🌐 |

ClinicalTrials.gov 常用字段：`fields=NCTId,BriefTitle,OverallStatus,Phase,PrimaryOutcome,EligibilityCriteria,EnrollmentCount,StartDate`；过滤：`filter.overallStatus=RECRUITING`、`query.term=AREA[Phase]PHASE3`。深入分析可用 `scientific-skills:clinicaltrials-database` 或 `anthropic-skills:clinical-trial-landscape`。

## 3. 标准是什么？（指南与监管，界定"未满足需求"）

| 数据源 | 用途 | 访问 |
|---|---|---|
| NCCN 指南 | 推荐等级 2B/3、"no data"、"clinical trial preferred"的位置就是证据空白 | 🌐🔑（免费注册） |
| CSCO 指南 | 中国诊疗标准；Ⅱ/Ⅲ级推荐、"缺乏中国人群数据" | 🌐 |
| ESMO 指南 + ESMO-MCBS | 临床获益量级评分，判断"阳性但获益小" | 🌐 |
| FDA 药品说明书 / 审批 | 适应症边界、上市后要求（PMR） | ✅ openFDA（`scientific-skills:fda-database`） |
| NMPA / CDE 审评报告 | 国内适应症、附条件批准的确证性研究要求 | 🌐 |

## 4. 生物学上靠谱吗？（分子与机制）

| 数据源 | 用途 | 访问 |
|---|---|---|
| cBioPortal | 突变/CNA/融合频率、共突变、与生存的关联；含 TCGA、MSK-IMPACT、AACR GENIE 及部分亚洲队列 | ✅ `https://www.cbioportal.org/api`（脚本已接入） |
| GDC / TCGA | 原始组学 + 临床数据下载 | ✅ `https://api.gdc.cancer.gov` |
| AACR Project GENIE | 大规模真实世界临床测序 | ✅ cBioPortal（genie.cbioportal.org，🔑） |
| COSMIC | 体细胞突变目录、突变特征（signature） | 🔑（`scientific-skills:cosmic-database`） |
| OncoKB | 变异可行动性等级（FDA 认可） | 🔑 API；网页可免费查 |
| CIViC | 社区整理的临床证据（A–E 级） | ✅ GraphQL `https://civicdb.org/api/graphql`（脚本已接入） |
| Open Targets | 靶点–疾病关联评分、已知药物 | ✅ GraphQL（`scientific-skills:opentargets-database`） |
| DepMap | 细胞系依赖性（CRISPR），判断靶点是否 essential | 🌐 / 下载 |
| GEO / ArrayExpress | 公开表达谱，验证队列 | ✅（`scientific-skills:geo-database`） |
| CELLxGENE / TISCH2 | 单细胞图谱、肿瘤微环境 | ✅ / 🌐（`scientific-skills:cellxgene-census`） |
| TCIA | 影像组学数据 | 🌐 |
| HPA 人类蛋白图谱 | 蛋白表达（IHC）、正常组织表达（毒性预判） | 🌐 |

⚠️ **基因组频率不等于生物标志物阳性率**：CLDN18.2、PD-L1 CPS、HER2 IHC 这类标志物是**蛋白表达**。cBioPortal 里 CLDN18 的基因组改变只有约 2%，但 CLDN18.2 IHC 阳性（≥75% 肿瘤细胞 2+/3+）约占胃癌的 38%。估算亚组规模前，要先确认标志物是哪个层面的（DNA / RNA / 蛋白 / 影像）。

## 5. 做得出来吗？（流行病学与可行性）

| 数据源 | 用途 | 访问 |
|---|---|---|
| GLOBOCAN / GCO | 全球与中国发病率、死亡率 | 🌐 https://gco.iarc.who.int/ |
| 国家癌症中心年报 | 中国发病与分期构成 | 🌐 |
| SEER | 美国人群分期、生存，可做真实世界分析 | 🌐🔑 SEER*Stat |
| NCDB | 美国医院登记 | 🔑 |
| 本院 HIS / 专病库 / 随访库 | 真正决定能否入组的数字 | 本地 |

入组可行性粗估：`年就诊量 × 目标分期比例 × 标志物阳性率 × 入排通过率（通常 30–50%）× 同意率（60–80%）`

## 常用 API 速查（不依赖任何 skill）

```bash
# Open Targets：靶点检索（GraphQL）
curl -s -X POST https://api.platform.opentargets.org/api/v4/graphql -H 'Content-Type: application/json' \
  -d '{"query":"{ search(queryString:\"CLDN18\", entityNames:[\"target\"]){ hits{ id name } } }"}'
# GEO：数据集检索（E-utilities，db=gds）
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&term=gastric+cancer+AND+immunotherapy&retmode=json"
# openFDA：药品说明书
curl -s "https://api.fda.gov/drug/label.json?search=openfda.generic_name:zolbetuximab&limit=1"
# GDC/TCGA：项目病例数
curl -s "https://api.gdc.cancer.gov/projects/TCGA-STAD?fields=summary.case_count"
```

## 6. 跨领域借鉴（Peters 的"同形问题"）

- **跨瘤种**：同一靶点、同一机制在其他瘤种的结局（例：HER2 从乳腺癌到胃癌再到结直肠癌；MSI-H 不限瘤种获批）。cBioPortal 泛癌队列 + CIViC 按 gene 不限 disease 检索即可。
- **跨方法学**：因果推断（target trial emulation）、机器学习、数字病理、ctDNA 动态监测、PRO 电子化随访。
- **跨学科**：生态学（肿瘤进化/适应性治疗）、药理学（PK/PD 模型给药）、行为科学（依从性）。
