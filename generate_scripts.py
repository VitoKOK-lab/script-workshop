"""
每日腳本建議生成器 v2
- 抓取 TA 相關 RSS 熱門話題
- 生成 20 支腳本：10支從熱門話題出發，10支改寫過去高分影片
- 讀取拒絕記錄，避免不適合方向
- 儲存話題紀錄到 data/trends.json
"""
import os, json, urllib.request, urllib.error, xml.etree.ElementTree as ET
from datetime import datetime, timezone

DASHBOARD_URL     = "https://raw.githubusercontent.com/VitoKOK-lab/meta-dashboard/main/data/videos.json"
SCRIPTS_PATH      = "data/scripts.json"
TRENDS_PATH       = "data/trends.json"
GITHUB_MODELS_URL = "https://models.inference.ai.azure.com/chat/completions"

# ── TA 關鍵字過濾 ──────────────────────────────────────────────────────────────
TA_KEYWORDS = [
    '穿搭','時尚','美妝','保養','護膚','彩妝','香水',
    '明星','韓劇','台劇','偶像劇','電影','歌手','演員',
    '婚姻','愛情','感情','夫妻','媽媽','婆媳','家庭','孩子','親子',
    '女性','女人','姊妹','閨蜜',
    '珠寶','寶石','水晶','戒指','項鍊','手鍊','耳環',
    '星座','塔羅','能量','風水',
    '旅行','下午茶','美食','咖啡','甜點',
    '健康','瘦身','養生','減重',
    '職場','理財','投資','副業',
    '流行','趨勢','話題','熱門',
]

RSS_SOURCES = [
    ("Google Trends TW", "https://trends.google.com/trending/rss?geo=TW"),
    ("女人迷",           "https://womany.net/feed"),
    ("ETtoday 娛樂",     "https://star.ettoday.net/rss.xml"),
    ("三立娛樂",         "https://www.setn.com/rss.aspx?NewsType=10"),
]

FALLBACK_THEMES = [
    {"title":"婆婆說我買太多珠寶了","theme":"家庭幽默","type":"commerce",
     "hook":"「妳又在網路上買珠寶？」（老公偷偷點收藏）","outline":"婆婆念→老公護航→一起下單","why":"婆媳話題共鳴強，帶貨自然"},
    {"title":"30歲後才懂的穿搭道理","theme":"生活教學","type":"traffic",
     "hook":"25歲的我根本不知道這件事","outline":"錯誤示範→頓悟→現在的做法","why":"35+女性強烈共鳴"},
    {"title":"這顆石頭讓我多賺了一倍","theme":"能量/財運","type":"commerce",
     "hook":"我不迷信，但這件事太巧了","outline":"懷疑→嘗試→結果改變","why":"財運話題點擊率極高"},
    {"title":"假裝自己不需要任何東西","theme":"衝動購物","type":"commerce",
     "hook":"購物車裡已經加了87件","outline":"嘴硬→手軟→收到包裹狂喜","why":"有消費力女性自嘲必共鳴"},
    {"title":"行家才知道的寶石排行榜","theme":"知識揭密","type":"traffic",
     "hook":"鑽石只排第五名！","outline":"顛覆認知→逐一說明→最後推薦","why":"知識型影片分享率高"},
    {"title":"老公說貴，我說你不懂","theme":"夫妻幽默","type":"commerce",
     "hook":"「這個多少？」「不貴，很值得。」","outline":"老公質疑→太太解釋→老公信服","why":"夫妻互動題材百看不厭"},
    {"title":"月薪三萬穿出百萬感","theme":"穿搭教學","type":"commerce",
     "hook":"你以為這套很貴嗎？告訴你…","outline":"視覺驚喜→逐件揭價→搭配技巧","why":"平替內容流量最穩定"},
    {"title":"今天是個好日子，必須買點什麼","theme":"儀式感","type":"commerce",
     "hook":"不需要理由，心情好就是理由","outline":"日常美好→自我獎勵→入手過程","why":"儀式感消費是核心TA的消費行為"},
    {"title":"這12星座各自需要什麼能量","theme":"星座能量","type":"commerce",
     "hook":"你的星座今年最需要的一顆石","outline":"每座對應→原因解析→推薦商品","why":"星座內容持續高互動"},
    {"title":"有錢人不說的珠寶投資法","theme":"理財視角","type":"traffic",
     "hook":"她說珠寶是最好的資產之一","outline":"刻板印象破除→真實資料→選擇建議","why":"投資視角吸引理性消費者"},
    {"title":"我的每日微奢儀式","theme":"精緻生活","type":"commerce",
     "hook":"5分鐘讓自己像換了一個人","outline":"平凡早晨→加入儀式→整天狀態不同","why":"儀式感是消費動機核心"},
    {"title":"媽媽不應該委屈自己","theme":"情感共鳴","type":"traffic",
     "hook":"上次買給自己的禮物是什麼時候？","outline":"付出→忽視自己→值得被寵愛","why":"媽媽族群情感需求極高"},
    {"title":"這樣搭珠寶顯瘦10斤","theme":"穿搭教學","type":"commerce",
     "hook":"脖子變長了？其實是項鍊的功勞","outline":"對比示範→原理解析→推薦款式","why":"顯瘦話題女性必點"},
    {"title":"閨蜜送我這個，我哭了","theme":"情感故事","type":"traffic",
     "hook":"不是因為貴，是因為她記住了","outline":"收到禮物→情感回憶→珠寶的意義","why":"情感故事分享率最高"},
    {"title":"星期一能量補充指南","theme":"能量/星座","type":"commerce",
     "hook":"週一症候群？試試這個方法","outline":"週一低能量→能量石介紹→一週狀態提升","why":"週一話題每週必有共鳴"},
    {"title":"40歲後更要打扮自己","theme":"熟齡時尚","type":"traffic",
     "hook":"她說40歲是女人第二個青春","outline":"刻板印象→反轉→具體做法","why":"40+女性自我認同強需求"},
    {"title":"這條項鍊陪我走過最難的時候","theme":"情感寶石","type":"commerce",
     "hook":"不是迷信，是心理支撐","outline":"困難時期→寶石陪伴→走出來了","why":"情感依附讓商品有故事"},
    {"title":"下午茶配什麼珠寶最對味","theme":"生活美學","type":"commerce",
     "hook":"朋友說我今天搭得太好看了","outline":"場合介紹→穿搭邏輯→完美下午茶look","why":"下午茶+穿搭雙熱門話題"},
    {"title":"讓老公主動買珠寶的方法","theme":"夫妻互動","type":"commerce",
     "hook":"從來不主動的他，上週突然說…","outline":"日常暗示→他的轉變→心法分享","why":"夫妻互動+購物話題必爆"},
    {"title":"韓系VS台系珠寶戴法大不同","theme":"風格比較","type":"traffic",
     "hook":"韓妞這樣戴，台灣女生這樣戴","outline":"風格差異→各自優點→混搭公式","why":"比較類影片完播率極高"},
]


def fetch_trends():
    """抓取今日 TA 相關熱門話題"""
    all_topics, sources_ok, raw_items = [], [], []
    for name, url in RSS_SOURCES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as r:
                content = r.read().decode("utf-8", errors="ignore")
            root = ET.fromstring(content)
            titles = [el.text.strip() for item in root.findall(".//item")
                      if (el := item.find("title")) is not None and el.text]
            picked = titles[:15] if name == "Google Trends TW" \
                     else [t for t in titles[:40] if any(kw in t for kw in TA_KEYWORDS)][:8]
            if picked:
                all_topics.extend(picked); sources_ok.append(name)
                raw_items.extend({"source": name, "title": t} for t in picked)
                print(f"[TREND] {name}: {len(picked)} 則")
            else:
                print(f"[TREND] {name}: 無 TA 相關話題")
        except Exception as e:
            print(f"[WARN] {name}: {e}")
    return all_topics[:25], sources_ok, raw_items[:25]


def save_trends(today, topics, sources, raw_items):
    try:
        with open(TRENDS_PATH, "r", encoding="utf-8") as f:
            tdb = json.load(f)
    except Exception:
        tdb = {"entries": []}
    tdb["entries"] = [e for e in tdb["entries"] if e.get("date") != today]
    tdb["entries"].insert(0, {"date": today, "sources": sources, "topics": topics, "items": raw_items})
    tdb["entries"] = tdb["entries"][:30]
    tdb["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(TRENDS_PATH, "w", encoding="utf-8") as f:
        json.dump(tdb, f, ensure_ascii=False, indent=2)
    print(f"[TREND] 已儲存 {len(raw_items)} 則話題")


def fetch_top_videos():
    try:
        req = urllib.request.Request(DASHBOARD_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        vids = list(data.get("videos", {}).values())
        vids = [v for v in vids if isinstance(v, dict)]
        return sorted(vids, key=lambda v: v.get("score", 0), reverse=True)[:12]
    except Exception as e:
        print(f"[WARN] 無法取得儀表板資料: {e}")
        return []


def build_video_context(top_videos):
    lines = [f"{i}. {(v.get('title') or '')[:30]} | {v.get('score',0)}分 | {v.get('type','')} | {v.get('plays',0):,}播"
             for i, v in enumerate(top_videos, 1)]
    return "\n".join(lines) if lines else "（暫無資料）"


def get_rewrite_candidates(db):
    """取得過去成效好的腳本作為改寫參考"""
    good = [s for s in db.get("scripts", [])
            if s.get("status") in ("tracking", "published") and s.get("score")
            or s.get("status") in ("approved", "filming")]
    good.sort(key=lambda s: s.get("score") or 0, reverse=True)
    return good[:8]


def build_rejects_context(db):
    """建立拒絕方向說明，告訴 AI 要避開"""
    rejects = db.get("rejects", [])[-20:]
    if not rejects:
        return ""
    lines = [f"- 主題「{r.get('theme','')}」，鉤子「{r.get('hook','')}」→ 老闆覺得不適合，請避免"
             for r in rejects]
    return "\n".join(lines)


def call_github_models(prompt, token):
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": 5000,
        "response_format": {"type": "json_object"}
    }).encode("utf-8")
    req = urllib.request.Request(
        GITHUB_MODELS_URL, data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        result = json.loads(r.read().decode("utf-8"))
    return json.loads(result["choices"][0]["message"]["content"])


def generate_with_ai(top_videos, trends_topics, db, token):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    video_ctx   = build_video_context(top_videos)
    trends_ctx  = "\n".join(f"- {t}" for t in trends_topics) if trends_topics else "（今日無法取得話題資料）"
    rejects_ctx = build_rejects_context(db)

    # 改寫候選（過去成效好的腳本）
    rewrites = get_rewrite_candidates(db)
    rewrite_ctx = "\n".join(
        f"{i}. 【{s.get('title','')}】主題：{s.get('theme','')}，分數：{s.get('score') or '未知'}"
        for i, s in enumerate(rewrites, 1)
    ) if rewrites else "（尚無足夠成效資料，請自行發揮改寫）"

    reject_block = f"\n\n【絕對要避開的方向（老闆已拒絕）】\n{rejects_ctx}" if rejects_ctx else ""

    prompt = f"""你是泰熙爾珠寶品牌的短影音腳本總編輯。

受眾（TA）：35-55歲台灣女性，有消費力，關注家庭關係（婆媳/夫妻/親子）、時尚穿搭、精緻生活、情感共鳴、珠寶/能量寶石。

【今日台灣熱門話題（TA相關，來自RSS）】
{trends_ctx}

【我們過去成效好的影片（供改寫參考）】
{rewrite_ctx}

【我們最近高分影片（了解有效方向）】
{video_ctx}{reject_block}

今日日期：{today}

請生成20支今日短影片腳本建議（30-90秒），分兩組：
- 第1-10支（熱門話題組）：從今日熱門話題出發，轉化為TA感興趣的角度，必須呼應今日話題
- 第11-20支（改寫高分組）：從我們過去成效好的影片出發，換全新角度、新鉤子、新切入點改寫

每支都要有讓人忍不住繼續看的「前3秒鉤子」。{(' 特別注意：'+ rejects_ctx[:80] +'⋯ 這類方向完全不要出現') if rejects_ctx else ''}

回傳純JSON（不要加markdown）：
{{"scripts":[{{"title":"片名（15字內）","theme":"主題（例：家庭幽默/能量寶石/穿搭教學）","type":"commerce或traffic","hook":"前3秒鉤子（20字內）","outline":"三段大綱（開場→中段→結尾，各一句）","why":"為什麼現在拍有效（可提今日話題或改寫自哪部影片，20字）"}}]}}"""

    try:
        result = call_github_models(prompt, token)
        scripts = result.get("scripts", [])
        if len(scripts) >= 10:
            print(f"[OK] GitHub Models 生成 {len(scripts)} 支建議")
            return scripts
    except Exception as e:
        print(f"[WARN] GitHub Models 失敗: {e}，改用備用樣板")
    return None


def make_script_entry(idx, s, today):
    return {
        "id":           f"{today.replace('-','')}-{idx:02d}",
        "created_at":   today,
        "title":        s.get("title", ""),
        "theme":        s.get("theme", ""),
        "type":         s.get("type", "traffic"),
        "hook":         s.get("hook", ""),
        "outline":      s.get("outline", ""),
        "why":          s.get("why", ""),
        "full_script":  "",
        "status":       "suggested",
        "video_id":     None,
        "platform":     None,
        "published_at": None,
        "notes":        "",
        "tags":         [],
        "score":        None,
        "plays":        None,
    }


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    token = os.environ.get("GITHUB_TOKEN", "")
    force = os.environ.get("FORCE_REGEN", "").lower() == "true"

    try:
        with open(SCRIPTS_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception:
        db = {"version": "1.0", "scripts": [], "rejects": []}

    if force:
        before = len(db["scripts"])
        db["scripts"] = [s for s in db["scripts"]
                         if not (s.get("created_at") == today and s.get("status") == "suggested")]
        print(f"[FORCE] 已清除 {before - len(db['scripts'])} 支今日建議")

    existing_today = [s for s in db["scripts"] if s.get("created_at") == today and s.get("status") == "suggested"]
    if existing_today:
        print(f"[SKIP] 今日已有 {len(existing_today)} 支建議，跳過")
        return

    # 抓話題 + 影片
    trends_topics, sources_ok, raw_items = fetch_trends()
    save_trends(today, trends_topics, sources_ok, raw_items)
    top_videos = fetch_top_videos()

    # 生成 20 支
    ai_scripts = generate_with_ai(top_videos, trends_topics, db, token) if token else None
    raw_list   = ai_scripts if ai_scripts else FALLBACK_THEMES

    new_entries = [make_script_entry(i + 1, s, today) for i, s in enumerate(raw_list[:20])]

    existing_ids = {s["id"] for s in db["scripts"]}
    added = [e for e in new_entries if e["id"] not in existing_ids]
    db["scripts"] = added + db["scripts"]
    db["updated_at"] = datetime.now(timezone.utc).isoformat()
    if "rejects" not in db:
        db["rejects"] = []

    with open(SCRIPTS_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    src = f"GitHub Models AI + 熱門話題（{len(trends_topics)} 則）" if ai_scripts else "備用樣板"
    print(f"[DONE] {today} 新增 {len(added)} 支腳本建議（{src}）")
    rejects_n = len(db.get("rejects", []))
    if rejects_n:
        print(f"[LEARN] 已學習 {rejects_n} 個不適合方向")


if __name__ == "__main__":
    main()
