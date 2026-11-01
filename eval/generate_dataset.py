"""Generate a scale-realistic evaluation set for issue #44.

Real usage: glossaries of 1k-3k entries and documents of 2k-10k+ words, so a
full-glossary injection is impossible. This generator builds, deterministically:

* a ~1,200-entry glossary (40 anchor terms used by the document + ~1,160 decoys)
* a ~2,100-word document per domain that uses each anchor term a few times
* annotations for the 40 anchor terms (expected occurrences computed exactly)

All text is synthetic and released as CC0; no customer data is included.

Run:
    python eval/generate_dataset.py
"""

from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
DOC_DIR = EVAL_DIR / "documents"
GLOSSARY_DIR = EVAL_DIR / "glossaries"
ANNOTATION_DIR = EVAL_DIR / "annotations"

TARGET_WORDS = 2100
GLOSSARY_SIZE = 1200
SEED = 42


def anchor_list(items):
    return [(term.strip(), trans.strip()) for term, trans in items]


TECH_ADJ = [
    ("adaptive", "自适应"), ("ambient", "环境"), ("atomic", "原子"), ("balanced", "均衡"),
    ("bounded", "有界"), ("calibrated", "校准"), ("compact", "紧凑"), ("composite", "复合"),
    ("deferred", "延迟"), ("durable", "持久"), ("elastic", "弹性"), ("federated", "联邦"),
    ("granular", "细粒度"), ("hybrid", "混合"), ("incremental", "增量"), ("layered", "分层"),
    ("local", "本地"), ("managed", "托管"), ("minimal", "最小"), ("nested", "嵌套"),
    ("offline", "离线"), ("ordered", "有序"), ("parallel", "并行"), ("persistent", "持续"),
    ("pooled", "池化"), ("predictive", "预测"), ("primary", "主"), ("regional", "区域"),
    ("resilient", "韧性"),
]
TECH_NOUN = [
    ("access plan", "访问计划"), ("audit hook", "审计钩子"), ("backlog lane", "积压通道"),
    ("bucket map", "桶映射"), ("cache probe", "缓存探针"), ("capacity guard", "容量护栏"),
    ("catalog entry", "目录条目"), ("checksum gate", "校验门"), ("cluster slot", "集群槽位"),
    ("cold lane", "冷通道"), ("commit fence", "提交栅栏"), ("config overlay", "配置覆盖层"),
    ("control token", "控制令牌"), ("cursor index", "游标索引"), ("digest table", "摘要表"),
    ("drain valve", "排空阀"), ("edge budget", "边缘预算"), ("eviction queue", "淘汰队列"),
    ("fanout ring", "扇出环"), ("fence token", "栅栏令牌"), ("flush window", "刷写窗口"),
    ("gateway shard", "网关分片"), ("hash bucket", "哈希桶"), ("health signal", "健康信号"),
    ("ingress rule", "入站规则"), ("lease token", "租约令牌"), ("log shard", "日志分片"),
    ("merge lane", "合并通道"), ("metric probe", "指标探针"), ("origin slot", "源站槽位"),
    ("partition map", "分区映射"), ("policy fence", "策略栅栏"), ("queue depth", "队列深度"),
    ("replay cursor", "重放游标"), ("route table", "路由表"), ("scan budget", "扫描预算"),
    ("shard lease", "分片租约"), ("snapshot lane", "快照通道"), ("throttle gate", "限流门"),
    ("trace shard", "追踪分片"),
]
TECH_ANCHORS = anchor_list([
    ("edge node", "边缘节点"), ("origin shield", "源站护盾"), ("cache key", "缓存键"),
    ("time to live", "存活时间"), ("purge request", "清除请求"), ("stale-while-revalidate", "过期再验证"),
    ("origin server", "源服务器"), ("request coalescing", "请求合并"), ("hit ratio", "命中率"),
    ("cold start", "冷启动"), ("backfill", "回填"), ("eviction policy", "淘汰策略"),
    ("tiered cache", "分层缓存"), ("shield cluster", "护盾集群"), ("geo-steering", "地理调度"),
    ("rate limiter", "限流器"), ("canary release", "金丝雀发布"), ("failover", "故障转移"),
    ("control plane", "控制面"), ("data plane", "数据面"), ("origin fetch", "源站回源"),
    ("cache stampede", "缓存击穿"), ("negative caching", "负缓存"), ("TLS termination", "TLS 终止"),
    ("log drain", "日志导出"), ("health probe", "健康探测"), ("edge rule", "边缘规则"),
    ("maintenance window", "维护窗口"), ("rollback plan", "回滚方案"), ("capacity headroom", "容量余量"),
    ("hot partition", "热分区"), ("write amplification", "写放大"), ("regional failover", "区域故障转移"),
    ("cache tag", "缓存标签"), ("warm standby", "热备"), ("index shard", "索引分片"),
    ("throttle budget", "限流预算"), ("retry storm", "重试风暴"), ("audit trail", "审计轨迹"),
    ("capacity planner", "容量规划器"),
])
TECH_TEMPLATES = [
    "The {term} is checked before every release.",
    "Operators record the {term} in the shift log.",
    "A failing {term} blocks the next {term}.",
    "We compare the {term} with the previous window.",
    "If the {term} drifts, the {term} is paused.",
    "The runbook explains how to recover the {term}.",
    "Each region reports its own {term} every minute.",
    "The {term} must stay within the agreed budget.",
]
TECH_FILLERS = [
    "The team reviews open incidents at the start of each shift.",
    "Changes are announced in the operations channel.",
    "Every alert links to a short runbook page.",
    "Dashboards are refreshed once per minute.",
    "The on-call engineer confirms the rollback before proceeding.",
    "Cross-region traffic is measured separately.",
    "The review board approves large changes twice a week.",
    "Reports are archived for one year.",
]

RULE_ADJ = [
    ("Ashen", "灰烬"), ("Pale", "苍白"), ("Silent", "寂静"), ("Broken", "破碎"),
    ("Burning", "燃烧"), ("Frozen", "冰封"), ("Hollow", "空洞"), ("Gilded", "镀金"),
    ("Crimson", "绯红"), ("Wandering", "游荡"), ("Forgotten", "遗忘"), ("Whispering", "低语"),
    ("Sable", "黑貂"), ("Verdant", "苍翠"), ("Iron", "铁"), ("Glass", "玻璃"),
    ("Storm", "风暴"), ("Lantern", "提灯"), ("Dusk", "暮色"), ("Dawn", "黎明"),
    ("Cinder", "烬"), ("Mourning", "哀悼"), ("Hidden", "隐秘"), ("Thorn", "荆棘"),
    ("Salt", "盐"), ("Ember", "余烬"), ("Raven", "渡鸦"), ("Winter", "寒冬"),
    ("Warden's", "守望者的"), ("Nameless", "无名"),
]
RULE_NOUN = [
    ("Vow", "誓约"), ("Sigil", "符印"), ("Crown", "王冠"), ("Pact", "契约"),
    ("Gate", "门"), ("Blade", "刃"), ("Lantern", "提灯"), ("Road", "之路"),
    ("Choir", "合唱团"), ("Mask", "面具"), ("Tower", "塔"), ("Bell", "钟"),
    ("Mark", "印记"), ("Court", "宫廷"), ("Reach", "岬"), ("Wood", "林"),
    ("Tide", "潮"), ("Vault", "宝库"), ("Hand", "之手"), ("Covenant", "盟约"),
    ("Rite", "仪式"), ("Song", "歌"), ("Hollow", "空壳"), ("Gate", "之门"),
    ("Ledger", "账簿"), ("Compass", "罗经"), ("Fleet", "舰队"), ("Ember", "余烬"),
    ("Oath", "誓言"), ("Throne", "王座"), ("Shard", "碎片"), ("Veil", "帷幕"),
    ("Beacon", "信标"), ("Hearth", "炉火"), ("Ward", "守护"), ("Path", "小径"),
    ("Dawn", "黎明"), ("Frost", "霜"), ("Relic", "遗物"), ("Torch", "火炬"),
]
RULE_ANCHORS = anchor_list([
    ("the Ashen Crown", "灰烬王冠"), ("Warden", "守望者"), ("Ember die", "余烬骰"),
    ("Sigil", "符印"), ("Hollow", "空壳"), ("the Rift", "裂隙"), ("Ashen Pact", "灰烬契约"),
    ("Brand", "烙印"), ("Vow", "誓约"), ("Resolve", "决心"), ("Scorched Mark", "焦痕"),
    ("Cinder Step", "烬步"), ("Emberwright", "烬匠"), ("the Pale Court", "苍白宫廷"),
    ("Nightglass", "夜玻璃"), ("Oathbreaker", "背誓者"), ("Hearthstone", "炉石"),
    ("Whisperwood", "低语林"), ("the Long Dark", "长夜"), ("Duskwarden", "暮卫"),
    ("Thornwake", "荆棘苏醒"), ("Sable Hand", "黑貂之手"), ("Last Lantern", "最后提灯"),
    ("Ash Tide", "灰潮"), ("Fading", "消隐"), ("Runekeeper", "符文守护者"),
    ("Wraithbound", "缚灵者"), ("Ember Vault", "余烬宝库"), ("Cinderfall", "烬落"),
    ("Dawnfire", "晨火"),
])
RULE_TEMPLATES = [
    "A {term} is tested whenever the party rests.",
    "The rules call for one {term} before the scene ends.",
    "If the {term} fails, the group gains a {term}.",
    "Every {term} must be recorded on the character sheet.",
    "The narrator may spend a {term} to raise the stakes.",
    "A {term} cannot be removed without the {term}.",
    "Players describe how their {term} changes the scene.",
    "The {term} is resolved before the next session.",
]
RULE_FILLERS = [
    "Sessions run for about three hours.",
    "The narrator describes the scene before dice are rolled.",
    "Players take turns declaring actions.",
    "The table agrees on tone before the first session.",
    "Downtime is handled between sessions.",
    "The group keeps a shared map of the region.",
    "New players may ask for a rules summary at any time.",
    "The session ends with a short recap.",
]

NOVEL_FIRST = [
    ("Corin", "科林"), ("Edda", "埃达"), ("Fen", "芬"), ("Isolde", "伊索尔德"),
    ("Jarek", "雅雷克"), ("Lira", "莉拉"), ("Mira", "米拉"), ("Nils", "尼尔斯"),
    ("Orla", "奥拉"), ("Perrin", "佩林"), ("Quill", "奎尔"), ("Rhea", "瑞娅"),
    ("Soren", "索伦"), ("Tamsin", "塔姆辛"), ("Ulric", "乌尔里克"), ("Vesna", "韦斯娜"),
    ("Wren", "雷恩"), ("Yara", "雅拉"), ("Zane", "赞恩"), ("Ansel", "安塞尔"),
    ("Bree", "布里"), ("Cass", "卡斯"), ("Doran", "多兰"), ("Elise", "埃莉斯"),
    ("Falk", "法尔克"), ("Greta", "格蕾塔"), ("Hale", "黑尔"), ("Ivo", "伊沃"),
    ("Juno", "朱诺"), ("Kell", "凯尔"),
]
NOVEL_EPITHET = [
    ("Voss", "沃斯"), ("Marlowe", "马洛"), ("Quinn", "奎因"), ("Ashby", "阿什比"),
    ("Blackwater", "布莱克沃特"), ("Crane", "克兰"), ("Dunmore", "邓莫尔"), ("Elder", "埃尔德"),
    ("Fairweather", "费尔韦瑟"), ("Grey", "格雷"), ("Hollis", "霍利斯"), ("Ives", "艾夫斯"),
    ("Kirk", "柯克"), ("Lowell", "洛厄尔"), ("Marsh", "马什"), ("North", "诺斯"),
    ("Orton", "奥顿"), ("Pike", "派克"), ("Reed", "里德"), ("Stone", "斯通"),
    ("Thorne", "索恩"), ("Vale", "韦尔"), ("West", "韦斯特"), ("Yarrow", "亚罗"),
    ("Ashford", "阿什福德"), ("Bram", "布拉姆"), ("Cole", "科尔"), ("Dane", "戴恩"),
    ("Ellis", "埃利斯"), ("Frost", "弗罗斯特"), ("Gale", "盖尔"), ("Holt", "霍尔特"),
    ("Irving", "欧文"), ("Jasper", "贾斯珀"), ("Kerr", "克尔"), ("Lund", "伦德"),
    ("Mercer", "默瑟"), ("Nash", "纳什"), ("Pryce", "普赖斯"), ("Rowan", "罗文"),
]
NOVEL_ANCHORS = anchor_list([
    ("Marin Voss", "马林·沃斯"), ("the Saltglass Sea", "盐玻璃海"), ("Lumen Reef", "流明礁"),
    ("the Quiet Tide", "静潮"), ("Ashen Harbor", "灰港"), ("Kestrel", "凯斯特雷尔"),
    ("the Concordat", "协定"), ("Tidewright", "潮汐编织者"), ("beacon lattice", "信标阵"),
    ("star compass", "星盘罗经"), ("the Drowned Bell", "沉钟"), ("Mirelle", "米雷尔"),
    ("obsidian buoy", "黑曜浮标"), ("the Echo Current", "回声洋流"), ("cartographer", "制图师"),
    ("salt script", "盐文"), ("lantern gull", "灯鸥"), ("the Widow's Reach", "寡妇岬"),
    ("brineglass", "卤玻璃"), ("the Ninth Chart", "第九海图"), ("harbor warden", "港务官"),
    ("tide ledger", "潮汐账簿"), ("the Broken Meridian", "破碎子午线"), ("glasswing", "玻璃翼"),
    ("the Sable Fleet", "黑貂舰队"), ("quiet water", "静水"), ("keel song", "龙骨之歌"),
    ("the Lantern Coast", "提灯海岸"), ("drift marker", "漂流标记"), ("the Returning", "归返"),
])
NOVEL_TEMPLATES = [
    "{term} watched the horizon until the light failed.",
    "The {term} had not been seen for eleven years.",
    "She wrote the {term} into the log before dawn.",
    "No one spoke of the {term} after that night.",
    "The {term} moved slowly through the fog.",
    "He measured the {term} twice and said nothing.",
    "By morning the {term} was gone.",
    "The {term} still pointed the wrong way.",
]
NOVEL_FILLERS = [
    "The wind carried salt across the deck.",
    "They ate in silence and checked the ropes again.",
    "The lamp burned lower as the hours passed.",
    "Someone laughed, then stopped.",
    "The chart had been copied by three different hands.",
    "Rain came and went before noon.",
    "The crew kept to their own corners.",
    "Nothing about the harbor looked familiar.",
]

DOMAINS = {
    "technical_doc": {
        "title": "Operating the Northwind Edge Cache",
        "anchors": TECH_ANCHORS,
        "templates": TECH_TEMPLATES,
        "fillers": TECH_FILLERS,
        "decoys": [(a + " " + n, ta + tn) for (a, ta) in TECH_ADJ for (n, tn) in TECH_NOUN],
    },
    "rulebook": {
        "title": "Ashfall: Quickstart Rules",
        "anchors": RULE_ANCHORS,
        "templates": RULE_TEMPLATES,
        "fillers": RULE_FILLERS,
        "decoys": [("the " + a + " " + n, ta + tn) for (a, ta) in RULE_ADJ for (n, tn) in RULE_NOUN],
    },
    "novel": {
        "title": "The Cartographer of Quiet Tides (excerpt)",
        "anchors": NOVEL_ANCHORS,
        "templates": NOVEL_TEMPLATES,
        "fillers": NOVEL_FILLERS,
        "decoys": [(f + " " + e, tf + "·" + te) for (f, tf) in NOVEL_FIRST for (e, te) in NOVEL_EPITHET],
    },
}

SECTIONS = ["Setting and scope", "Daily routine", "Failure handling", "Change control", "Records and review", "Open questions"]


def build_glossary(domain, rng):
    anchor_terms = {term.lower() for term, _ in domain["anchors"]}
    rows = [(term, trans) for term, trans in domain["anchors"]]
    seen = set(anchor_terms)
    decoy_rows = []
    for term, trans in domain["decoys"]:
        key = term.lower()
        if key in seen or key.startswith("the the "):
            continue
        seen.add(key)
        decoy_rows.append((term, trans))
    rng.shuffle(decoy_rows)
    rows.extend(decoy_rows[: max(GLOSSARY_SIZE - len(rows), 0)])
    return rows


def build_document(domain, rng):
    anchors = list(domain["anchors"])
    rng.shuffle(anchors)
    templates = domain["templates"]
    fillers = domain["fillers"]
    used = {term: 0 for term, _ in anchors}
    lines = ["# " + domain["title"], ""]
    words = len(domain["title"].split())
    section_count = len(SECTIONS)
    per_section = max(TARGET_WORDS // section_count, 200)
    anchor_index = 0

    for section in SECTIONS:
        lines.append("## " + section)
        lines.append("")
        section_words = 0
        while section_words < per_section:
            term = anchors[anchor_index % len(anchors)][0]
            anchor_index += 1
            template = templates[rng.randrange(len(templates))]
            sentence = template.format(term=term)
            if "{term}" in sentence:
                sentence = template.replace("{term}", term)
            lines.append(sentence)
            used[term] = used.get(term, 0) + len(re.findall(r"(?i)" + re.escape(term), sentence))
            section_words += len(sentence.split())
            if section_words >= per_section:
                break
            filler = fillers[rng.randrange(len(fillers))]
            lines.append(filler)
            section_words += len(filler.split())
        lines.append("")
        words += section_words
    return "\n".join(lines) + "\n", used


def count_occurrences(text, term):
    pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", re.IGNORECASE)
    return len(pattern.findall(text))


def main() -> int:
    rng = random.Random(SEED)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    GLOSSARY_DIR.mkdir(parents=True, exist_ok=True)
    ANNOTATION_DIR.mkdir(parents=True, exist_ok=True)

    for doc, domain in DOMAINS.items():
        glossary = build_glossary(domain, rng)
        text, _ = build_document(domain, rng)

        with (GLOSSARY_DIR / (doc + ".csv")).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["term", "translation", "reason"])
            for term, trans in glossary:
                writer.writerow([term, trans, "标准译名"])
        (DOC_DIR / (doc + ".md")).write_text(text, encoding="utf-8")

        terms = []
        total = 0
        for term, trans in domain["anchors"]:
            occurrences = count_occurrences(text, term)
            terms.append({"term": term, "translation": trans, "occurrences": occurrences})
            total += occurrences
        missing = [item["term"] for item in terms if item["occurrences"] == 0]
        if missing:
            print("WARNING missing anchors:", missing)
        payload = {
            "doc": doc,
            "document": "documents/" + doc + ".md",
            "glossary": "glossaries/" + doc + ".csv",
            "source_language": "en",
            "target_language": "zh",
            "matching": "case-insensitive whole phrase; generated anchors only",
            "term_count": len(terms),
            "glossary_size": len(glossary),
            "document_words": len(text.split()),
            "total_occurrences": total,
            "terms": terms,
        }
        (ANNOTATION_DIR / (doc + ".json")).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("%s: glossary=%d, words=%d, anchors=%d, occurrences=%d" % (doc, len(glossary), len(text.split()), len(terms), total))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
