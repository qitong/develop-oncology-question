#!/usr/bin/env python3
"""onco_scan.py — 肿瘤研究问题的"证据地形"快速扫描（仅用标准库）。

聚合以下公开接口，输出一份 Markdown 报告，供 develop-oncology-question 各阶段使用：
  PubMed (E-utilities)      文献体量、近年趋势、RCT/综述/Meta 数量、最新文献
  Europe PMC                预印本（medRxiv/bioRxiv/Research Square 等）
  ClinicalTrials.gov v2     在研/已完成试验、分期与状态分布（撞车检查）
  cBioPortal                基因突变/拷贝数改变频率（亚组规模估算）
  CIViC                     临床可行动性证据（证据等级 A–E）

用法示例：
  python3 onco_scan.py --condition "gastric cancer" --intervention "zolbetuximab"
  python3 onco_scan.py --condition "colorectal cancer" --gene KRAS --study coadread_tcga_pan_can_atlas_2018
  python3 onco_scan.py --condition "esophageal squamous cell carcinoma" --pubmed-extra "neoadjuvant AND immunotherapy" -o scan.md

所有数字都是检索时点的"粗略地形"，不能替代系统检索。下结论前请人工核对检索式和原文。
"""
import argparse
import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter

UA = {"User-Agent": "onco_scan/1.0 (research-question coaching)"}
THIS_YEAR = dt.date.today().year


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _post(url, payload, timeout=30):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={**UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def safe(section):
    def deco(fn):
        def wrap(*a, **k):
            try:
                return fn(*a, **k)
            except Exception as e:  # 单个数据源失败不影响整体报告
                return f"## {section}\n\n> ⚠️ 查询失败：{e}\n"
        return wrap
    return deco


# ---------------- PubMed ----------------
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def pm_count(term):
    q = urllib.parse.urlencode({"db": "pubmed", "term": term, "retmode": "json", "retmax": 0})
    time.sleep(0.35)  # 无 API key 时 NCBI 限速 3 次/秒
    return int(_get(f"{EUTILS}/esearch.fcgi?{q}")["esearchresult"]["count"])


def pm_recent(term, n=8):
    q = urllib.parse.urlencode({"db": "pubmed", "term": term, "retmode": "json",
                                "retmax": n, "sort": "pub_date"})
    time.sleep(0.35)
    ids = _get(f"{EUTILS}/esearch.fcgi?{q}")["esearchresult"]["idlist"]
    if not ids:
        return []
    time.sleep(0.35)
    s = _get(f"{EUTILS}/esummary.fcgi?db=pubmed&retmode=json&id={','.join(ids)}")["result"]
    return [(i, s[i].get("pubdate", ""), s[i].get("source", ""), s[i].get("title", "")) for i in ids]


@safe("PubMed 文献地形")
def pubmed_section(base, years):
    lo = THIS_YEAR - years + 1
    rows = [
        ("全部", base),
        (f"近 {years} 年", f"({base}) AND {lo}:{THIS_YEAR}[dp]"),
        ("RCT", f"({base}) AND randomized controlled trial[pt]"),
        ("Meta 分析 / 系统评价", f"({base}) AND (meta-analysis[pt] OR systematic review[pt])"),
        ("综述", f"({base}) AND review[pt]"),
        ("指南 / 共识", f"({base}) AND (guideline[pt] OR practice guideline[pt] OR consensus[ti])"),
    ]
    out = [f"## PubMed 文献地形\n\n检索式：`{base}`\n", "| 类别 | 篇数 |", "|---|---|"]
    for name, t in rows:
        out.append(f"| {name} | {pm_count(t)} |")
    trend = []
    for y in range(THIS_YEAR - 4, THIS_YEAR + 1):
        trend.append(f"{y}: {pm_count(f'({base}) AND {y}[dp]')}")
    out.append("\n**年度趋势**：" + " · ".join(trend))
    out.append("\n**最新文献**：")
    for pmid, date, src, title in pm_recent(base):
        out.append(f"- {date} *{src}* — {title} (PMID [{pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/))")
    out.append("\n**最新 RCT**：")
    for pmid, date, src, title in pm_recent(f"({base}) AND randomized controlled trial[pt]", 5):
        out.append(f"- {date} *{src}* — {title} (PMID [{pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/))")
    return "\n".join(out) + "\n"


# ---------------- Europe PMC 预印本 ----------------
@safe("预印本（Europe PMC）")
def preprint_section(query):
    q = urllib.parse.urlencode({"query": f"({query}) AND SRC:PPR", "format": "json",
                                "pageSize": 6, "sort": "FIRST_PDATE_D desc"})
    d = _get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?{q}")
    out = [f"## 预印本（Europe PMC）\n\n检索：`{query}`，共 {d.get('hitCount', 0)} 篇，最新：\n"]
    for r in d.get("resultList", {}).get("result", []):
        out.append(f"- {r.get('firstPublicationDate', '')} *{r.get('bookOrReportDetails', {}).get('publisher', r.get('source', ''))}* — {r.get('title', '')} ({r.get('doi', r.get('id', ''))})")
    out.append("\n> 预印本未经同行评议，只作为\"领域正在往哪走\"的信号。")
    return "\n".join(out) + "\n"


# ---------------- ClinicalTrials.gov ----------------
@safe("在研 / 已注册试验（ClinicalTrials.gov）")
def ctgov_section(cond, intr, other, max_fetch=300):
    params = {"pageSize": 100, "countTotal": "true",
              "fields": "NCTId,BriefTitle,OverallStatus,Phase,StartDate,EnrollmentCount,LeadSponsorName,LocationCountry"}
    if cond:
        params["query.cond"] = cond
    if intr:
        params["query.intr"] = intr
    if other:
        params["query.term"] = other
    studies, token, total = [], None, 0
    while True:
        p = dict(params)
        if token:
            p["pageToken"] = token
        d = _get("https://clinicaltrials.gov/api/v2/studies?" + urllib.parse.urlencode(p))
        total = d.get("totalCount", total)
        studies += d.get("studies", [])
        token = d.get("nextPageToken")
        if not token or len(studies) >= max_fetch:
            break

    def g(s, *path, default=""):
        cur = s.get("protocolSection", {})
        for k in path:
            cur = cur.get(k, {}) if isinstance(cur, dict) else {}
        return cur or default

    status = Counter(g(s, "statusModule", "overallStatus") for s in studies)
    phase = Counter("/".join(g(s, "designModule", "phases", default=["NA"])) for s in studies)
    countries = Counter()
    for s in studies:
        for c in {l.get("country") for l in g(s, "contactsLocationsModule", "locations", default=[]) if l.get("country")}:
            countries[c] += 1
    active = [s for s in studies if g(s, "statusModule", "overallStatus") in
              ("RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION")]
    active.sort(key=lambda s: g(s, "statusModule", "startDateStruct", "date"), reverse=True)

    q = " / ".join(x for x in [f"疾病={cond}" if cond else "", f"干预={intr}" if intr else "", f"其他={other}" if other else ""] if x)
    out = [f"## 在研 / 已注册试验（ClinicalTrials.gov）\n\n检索：{q}；共 **{total}** 项（统计基于前 {len(studies)} 项）\n",
           "**状态**：" + "，".join(f"{k} {v}" for k, v in status.most_common()),
           "\n**分期**：" + "，".join(f"{k} {v}" for k, v in phase.most_common()),
           "\n**主要国家（含中心数≥1）**：" + "，".join(f"{k} {v}" for k, v in countries.most_common(8)),
           f"\n**正在进行 / 即将开始的试验（{len(active)} 项，按开始日期倒序，列前 15）**：\n",
           "| NCT | 分期 | 状态 | 开始 | 样本量 | 申办方 | 标题 |", "|---|---|---|---|---|---|---|"]
    for s in active[:15]:
        nct = g(s, "identificationModule", "nctId")
        out.append("| [{0}](https://clinicaltrials.gov/study/{0}) | {1} | {2} | {3} | {4} | {5} | {6} |".format(
            nct, "/".join(g(s, "designModule", "phases", default=["NA"])),
            g(s, "statusModule", "overallStatus"), g(s, "statusModule", "startDateStruct", "date"),
            g(s, "designModule", "enrollmentInfo", "count"), g(s, "sponsorCollaboratorsModule", "leadSponsor", "name"),
            g(s, "identificationModule", "briefTitle").replace("|", "/")))
    out.append("\n> 中国研究者注意：很多研究只在 ChiCTR 注册，需另查 https://www.chictr.org.cn/ 或 WHO ICTRP https://trialsearch.who.int/ 。")
    return "\n".join(out) + "\n"


# ---------------- cBioPortal ----------------
CBIO = "https://www.cbioportal.org/api"


@safe("基因组改变频率（cBioPortal）")
def cbio_section(genes, study):
    sl = _get(f"{CBIO}/sample-lists/{study}_all")
    n = sl["sampleCount"]
    profiles = {p["molecularProfileId"] for p in _get(f"{CBIO}/studies/{study}/molecular-profiles")}
    out = [f"## 基因组改变频率（cBioPortal：`{study}`，n={n}）\n",
           "| 基因 | 突变样本 | 扩增 | 深缺失 | 任一改变（近似） | 常见突变 |", "|---|---|---|---|---|---|"]
    for g in genes:
        eid = _get(f"{CBIO}/genes/{g}")["entrezGeneId"]
        mut, amp, dele, top = set(), set(), set(), Counter()
        if f"{study}_mutations" in profiles:
            for m in _post(f"{CBIO}/molecular-profiles/{study}_mutations/mutations/fetch?projection=SUMMARY",
                           {"entrezGeneIds": [eid], "sampleListId": f"{study}_all"}):
                mut.add(m["sampleId"])
                top[m.get("proteinChange", "")] += 1
        if f"{study}_gistic" in profiles:
            for c in _post(f"{CBIO}/molecular-profiles/{study}_gistic/discrete-copy-number/fetch?discreteCopyNumberEventType=HOMDEL_AND_AMP&projection=SUMMARY",
                           {"entrezGeneIds": [eid], "sampleListId": f"{study}_all"}):
                (amp if c["alteration"] == 2 else dele).add(c["sampleId"])
        anyalt = mut | amp | dele
        pct = lambda s: f"{len(s)} ({len(s) / n:.1%})"
        out.append(f"| {g} | {pct(mut)} | {pct(amp)} | {pct(dele)} | {pct(anyalt)} | {', '.join(k for k, _ in top.most_common(4))} |")
    out.append(f"\n> 浏览：https://www.cbioportal.org/study/summary?id={study} 。TCGA 以欧美人群为主，"
               "亚洲/中国人群频率请对照本土队列（如 cBioPortal 中的亚洲研究、或已发表的中国人群基因组数据）。")
    return "\n".join(out) + "\n"


@safe("cBioPortal 研究列表")
def cbio_studies(keyword):
    d = _get(f"{CBIO}/studies?keyword={urllib.parse.quote(keyword)}&projection=SUMMARY")
    d.sort(key=lambda s: -s.get("allSampleCount", 0))
    out = [f"## cBioPortal 相关队列（关键词 `{keyword}`）\n", "| studyId | 样本数 | 名称 |", "|---|---|---|"]
    for s in d[:15]:
        out.append(f"| `{s['studyId']}` | {s.get('allSampleCount', '')} | {s.get('name', '')} |")
    return "\n".join(out) + "\n"


# ---------------- CIViC ----------------
@safe("临床可行动性证据（CIViC）")
def civic_section(genes, disease):
    out = ["## 临床可行动性证据（CIViC）\n"]
    for g in genes:
        args = f'molecularProfileName:"{g}", first:50'
        if disease:
            args += f', diseaseName:"{disease}"'
        q = "{ evidenceItems(%s){ totalCount nodes{ id evidenceLevel evidenceType significance molecularProfile{name} disease{name} therapies{name} } } }" % args
        d = _post("https://civicdb.org/api/graphql", {"query": q})["data"]["evidenceItems"]
        lv = Counter(n["evidenceLevel"] for n in d["nodes"])
        tp = Counter(n["evidenceType"] for n in d["nodes"])
        out.append(f"**{g}**{'（' + disease + '）' if disease else ''}：共 {d['totalCount']} 条；等级 " +
                   "，".join(f"{k}:{v}" for k, v in sorted(lv.items())) + "；类型 " + "，".join(f"{k}:{v}" for k, v in tp.items()))
        for n in sorted(d["nodes"], key=lambda n: n["evidenceLevel"])[:6]:
            out.append(f"- [{n['evidenceLevel']}] {n['molecularProfile']['name']} · {n['disease']['name'] if n['disease'] else ''} · "
                       f"{n['evidenceType']}/{n['significance']} · {', '.join(t['name'] for t in n['therapies'])} "
                       f"(https://civicdb.org/evidence/{n['id']})")
        out.append("")
    out.append("> CIViC 是社区整理的数据库，未必全面；精准用药级别另查 OncoKB（https://www.oncokb.org/ ）与 NCCN/CSCO 指南。")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description="肿瘤研究问题证据地形扫描")
    ap.add_argument("--condition", help="瘤种，英文，如 'gastric cancer'")
    ap.add_argument("--intervention", help="干预/药物，如 'zolbetuximab' 或 'PD-1'")
    ap.add_argument("--gene", action="append", default=[], help="基因符号，可多次使用")
    ap.add_argument("--study", help="cBioPortal studyId，如 stad_tcga_pan_can_atlas_2018")
    ap.add_argument("--find-studies", help="按关键词列出 cBioPortal 队列，如 'gastric'")
    ap.add_argument("--civic-disease", help="CIViC 疾病名过滤，如 'Stomach'")
    ap.add_argument("--pubmed", help="自定义 PubMed 检索式（覆盖自动生成）")
    ap.add_argument("--pubmed-extra", help="追加到自动 PubMed 检索式的 AND 条件（基因默认不并入检索式，需要时写在这里）")
    ap.add_argument("--ct-term", help="ClinicalTrials.gov 额外关键词（query.term）")
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--skip", default="", help="跳过数据源，逗号分隔：pubmed,preprint,ctgov,cbio,civic")
    ap.add_argument("-o", "--output", help="输出 Markdown 文件路径")
    a = ap.parse_args()
    skip = set(filter(None, a.skip.split(",")))

    base = a.pubmed or " AND ".join(f"({x})" for x in [a.condition, a.intervention, a.pubmed_extra] if x)
    parts = [f"# 肿瘤证据地形扫描\n\n生成时间：{dt.datetime.now():%Y-%m-%d %H:%M}　|　"
             f"瘤种：{a.condition or '-'}　|　干预：{a.intervention or '-'}　|　基因：{', '.join(a.gene) or '-'}\n"]
    if base and "pubmed" not in skip:
        parts.append(pubmed_section(base, a.years))
    if base and "preprint" not in skip:
        parts.append(preprint_section(base))
    if (a.condition or a.intervention or a.ct_term) and "ctgov" not in skip:
        parts.append(ctgov_section(a.condition, a.intervention, a.ct_term))
    if a.find_studies and "cbio" not in skip:
        parts.append(cbio_studies(a.find_studies))
    if a.gene and a.study and "cbio" not in skip:
        parts.append(cbio_section(a.gene, a.study))
    if a.gene and "civic" not in skip:
        parts.append(civic_section(a.gene, a.civic_disease))
    parts.append("---\n*本报告为自动检索的粗略地形，仅供选题讨论；关键判断须回到原文与系统检索。*\n")
    md = "\n".join(parts)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"已写入 {a.output}", file=sys.stderr)
    print(md)


if __name__ == "__main__":
    main()
