"""
同步已發布腳本的成效資料（播放數、分數）
"""
import json, urllib.request

SCRIPTS_PATH  = "data/scripts.json"
DASHBOARD_URL = "https://raw.githubusercontent.com/VitoKOK-lab/meta-dashboard/main/data/videos.json"

with open(SCRIPTS_PATH, 'r', encoding='utf-8') as f:
    db = json.load(f)

try:
    req = urllib.request.Request(DASHBOARD_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        vdata = json.load(r)
    videos = vdata.get('videos', {})
except Exception as e:
    print(f'無法取得影片資料: {e}')
    videos = {}

updated = 0
for s in db['scripts']:
    vid_id = s.get('video_id')
    if vid_id and vid_id in videos:
        v = videos[vid_id]
        s['score'] = v.get('score')
        s['plays'] = v.get('plays')
        if s['status'] == 'published':
            s['status'] = 'tracking'
        updated += 1

if updated:
    with open(SCRIPTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(f'已同步 {updated} 支腳本成效')
else:
    print('無需同步')
