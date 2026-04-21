"""
每日腳本建議生成器
使用 GitHub Models API（免費）讀取儀表板資料並生成10支腳本建議
"""
import os, json, urllib.request, urllib.error
from datetime import datetime, timezone

DASHBOARD_URL = "https://raw.githubusercontent.com/VitoKOK-lab/meta-dashboard/main/data/videos.json"
SCRIPTS_PATH  = "data/scripts.json"
GITHUB_MODELS_URL = "https://models.inference.ai.azure.com/chat/completions"

# ── 主題框架（AI 失敗時的備用樣板） ───────────────────────────────────────────
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
]

def fetch_top_videos():
    """從儀表板抓取高分影片"""
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

def build_context(top_videos):
    lines = []
    for i, v in enumerate(top_videos, 1):
        t = (v.get("title") or "")[:30]
        lines.append(f"{i}. {t} | {v.get('score',0)}分 | {v.get('type','')} | {v.get('plays',0):,}播")
    return "\n".join(lines) if lines else "（暫無資料）"

def call_github_models(prompt, token):
    """呼叫 GitHub Models API"""
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": 3000,
        "response_format": {"type": "json_object"}
    }).encode("utf-8")

    req = urllib.request.Request(
        GITHUB_MODELS_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        result = json.loads(r.read().decode("utf-8"))
    return json.loads(result["choices"][0]["message"]["content"])

def generate_with_ai(top_videos, token):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    context = build_context(top_videos)
    prompt = f"""你是泰熙爾珠寶品牌的短影音腳本總編輯。

受眾（TA）：35-55歲台灣女性，有消費力，關注家庭關係、時尚穿搭、精緻生活、情感共鳴、珠寶/寶石。

最近高分影片（參考成效好的方向）：
{context}

今日日期：{today}

請生成10支今日短影片腳本建議（30-90秒）。
不一定要跟珠寶直接相關，只要是同樣TA有興趣的話題都可以。
每支都要有讓人忍不住繼續看的「前3秒鉤子」。

回傳純JSON（不要加markdown）：
{{"scripts":[{{"title":"片名（15字內）","theme":"主題（例：家庭幽默/能量寶石/穿搭教學）","type":"commerce或traffic","hook":"前3秒鉤子（20字內）","outline":"三段大綱（開場→中段→結尾，各一句）","why":"為什麼現在拍這個有效（20字）"}}]}}"""

    try:
        result = call_github_models(prompt, token)
        scripts = result.get("scripts", [])
        if scripts:
            print(f"[OK] GitHub Models 生成 {len(scripts)} 支建議")
            return scripts
    except Exception as e:
        print(f"[WARN] GitHub Models 失敗: {e}，改用備用樣板")
    return None

def make_script_entry(idx, s, today):
    return {
        "id": f"{today.replace('-','')}-{idx:02d}",
        "created_at": today,
        "title": s.get("title", ""),
        "theme": s.get("theme", ""),
        "type": s.get("type", "traffic"),
        "hook": s.get("hook", ""),
        "outline": s.get("outline", ""),
        "why": s.get("why", ""),
        "full_script": "",
        "status": "suggested",
        "video_id": None,
        "platform": None,
        "published_at": None,
        "notes": "",
        "tags": [],
        "score": None,
        "plays": None,
    }

def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    token = os.environ.get("GITHUB_TOKEN", "")
    force = os.environ.get("FORCE_REGEN", "").lower() == "true"

    # 載入現有資料庫
    try:
        with open(SCRIPTS_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception:
        db = {"version": "1.0", "scripts": []}

    # 強制模式：清除今日已有建議
    if force:
        before = len(db["scripts"])
        db["scripts"] = [s for s in db["scripts"]
                         if not (s.get("created_at") == today and s.get("status") == "suggested")]
        print(f"[FORCE] 已清除 {before - len(db['scripts'])} 支今日建議，強制重新生成")

    # 今天已有建議就跳過
    existing_today = [s for s in db["scripts"] if s.get("created_at") == today and s.get("status") == "suggested"]
    if existing_today:
        print(f"[SKIP] 今日（{today}）已有 {len(existing_today)} 支建議，跳過生成")
        return

    # 抓高分影片
    top_videos = fetch_top_videos()

    # 生成建議
    ai_scripts = generate_with_ai(top_videos, token) if token else None
    raw_list   = ai_scripts if ai_scripts else FALLBACK_THEMES

    new_entries = [make_script_entry(i + 1, s, today) for i, s in enumerate(raw_list[:10])]

    # 加到資料庫最前面
    existing_ids = {s["id"] for s in db["scripts"]}
    added = [e for e in new_entries if e["id"] not in existing_ids]
    db["scripts"] = added + db["scripts"]
    db["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(SCRIPTS_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    src = "GitHub Models AI" if ai_scripts else "備用樣板"
    print(f"[DONE] {today} 新增 {len(added)} 支腳本建議（{src}）")

if __name__ == "__main__":
    main()
