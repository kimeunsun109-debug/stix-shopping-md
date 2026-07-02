# -*- coding: utf-8
import sqlite3, shutil
from pathlib import Path
src = Path.home() / "AppData/Local/Google/Chrome/User Data/Default/History"
dst = Path(__file__).parent / "_hist_tmp/History"
dst.parent.mkdir(exist_ok=True)
shutil.copy2(src, dst)
con = sqlite3.connect(dst)
cur = con.cursor()
cur.execute(
    """SELECT url, title FROM urls
    WHERE url LIKE '%wing.coupang%'
    AND (url LIKE '%modify%' OR url LIKE '%registration%' OR url LIKE '%price%')
    ORDER BY last_visit_time DESC LIMIT 20"""
)
for u, t in cur.fetchall():
    print(u)
    print(" ", t[:80] if t else "")
con.close()
