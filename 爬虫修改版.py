"""
@header({
  searchable: 1,
  filterable: 0,
  quickSearch: 1,
  title: 'nJAV',
  lang: 'hipy'
})
"""
# -*- coding: utf-8 -*-
import re
import sys
from urllib.parse import quote
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        pass

    def getName(self):
        return "nJAV"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [200, "video/MP2T", b""]

    host = 'https://www.thisav66.com'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.thisav66.com/cn/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    # ==================== 首页 ====================
    # type_id 使用完整相对路径（不含域名）
    # 官方导航显示以下路径无 dm 前缀即可访问；若实测 404，可改为 dmNNN/cn/xxx
    def homeContent(self, filter):
        classes = [
            {"type_name": "最近更新", "type_id": "cn/new"},
            {"type_name": "新作上市", "type_id": "cn/release"},
            {"type_name": "中文字幕", "type_id": "cn/chinese-subtitle"},
            {"type_name": "无码流出", "type_id": "cn/uncensored-leak"},
            {"type_name": "VR", "type_id": "cn/genres/VR"},
            {"type_name": "女优一览", "type_id": "cn/actresses"},
            {"type_name": "类型", "type_id": "cn/genres"},
            {"type_name": "发行商", "type_id": "cn/makers"},
        ]
        return {'class': classes}

    def homeVideoContent(self):
        return self.categoryContent("cn/new", 1, False, {})

    # ==================== 列表解析 ====================
    def _parse_cards(self, doc):
        """按 div.thumbnail.group 精确解析视频卡片"""
        videos = []
        seen = set()

        for item in doc('div.thumbnail.group').items():
            a = item('a[href]').eq(0)
            href = (a.attr('href') or '').strip()
            if not href:
                continue

            # 番号始终是 URL 最后一段
            vid = href.rstrip('/').split('/')[-1]
            if not vid or len(vid) < 2:
                continue

            # 标题：卡片底部 div.my-2 a
            name = item('div.my-2 a').text().strip()
            if not name:
                name = (item('img').attr('alt') or '').strip()
            if not name:
                name = vid

            # 封面：img[data-src] 已为绝对地址
            pic = item('img[data-src]').attr('data-src') or ''
            if not pic:
                src = item('img').attr('src') or ''
                if src and not src.startswith('data:'):
                    pic = src
            if pic.startswith('//'):
                pic = 'https:' + pic
            elif pic.startswith('/'):
                pic = self.host + pic

            # 角标：第一个非空的 span.absolute.bottom-1
            remarks = ''
            for span in item('span.absolute.bottom-1').items():
                t = span.text().strip()
                if t:
                    remarks = t
                    break

            if vid in seen:
                continue
            seen.add(vid)

            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remarks,
                "style": {"type": "rect", "ratio": 1.78}
            })
        return videos

    # ==================== 分类列表 ====================
    def _full_url(self, tid, pg=1):
        tid = tid.strip('/')
        base = f"{self.host}/{tid}"
        if pg and str(pg) != "1":
            return f"{base}?page={pg}"
        return base

    def categoryContent(self, tid, pg, filter, extend):
        url = self._full_url(tid, pg)
        videos = []
        try:
            res = self.fetch(url, headers=self.headers)
            text = res.text or ''
            if self._is_cloudflare_challenge(text):
                print(f"[nJAV] Cloudflare challenge on {url}")
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
            videos = self._parse_cards(pq(text))
        except Exception as e:
            print(f"[nJAV] categoryContent error: {e}")

        return {
            'list': videos,
            'page': pg,
            'pagecount': 999,
            'limit': len(videos),
            'total': 999
        }

    # ==================== 详情 ====================
    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        url = f"{self.host}/cn/{vid}"
        try:
            res = self.fetch(url, headers=self.headers)
            doc = pq(res.text)
        except Exception:
            return {'list': [self._empty_vod(vid)]}

        name = doc('h1').text().strip()
        if not name:
            name = doc('meta[property="og:title"]').attr('content') or vid

        pic = doc('meta[property="og:image"]').attr('content') or ''
        if not pic:
            pic = doc('video').attr('poster') or ''
        if pic.startswith('//'):
            pic = 'https:' + pic
        elif pic.startswith('/'):
            pic = self.host + pic

        content = doc('meta[name="description"]').attr('content') or ''
        if not content:
            content = doc('div.prose, div.description, div.mt-4').text().strip()

        vod = {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": pic,
            "vod_content": content,
            "vod_play_from": "nJAV",
            "vod_play_url": f"播放${vid}"
        }
        return {"list": [vod]}

    def _empty_vod(self, vid):
        return {
            "vod_id": vid, "vod_name": vid, "vod_pic": "",
            "vod_play_from": "nJAV", "vod_play_url": f"播放${vid}"
        }

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg="1"):
        keyword = quote(key.strip(), safe='')
        url = f"{self.host}/cn/search/{keyword}"
        if pg and str(pg) != "1":
            url += f"?page={pg}"
        try:
            res = self.fetch(url, headers=self.headers)
            videos = self._parse_cards(pq(res.text))
        except Exception:
            videos = []
        return {"list": videos, "page": int(pg) if str(pg).isdigit() else 1}

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags):
        url = f"{self.host}/cn/{id}"
        try:
            res = self.fetch(url, headers=self.headers)
        except Exception:
            return {"parse": 1, "url": url, "header": self.headers}

        text = (res.text or '').replace('\\/', '/').replace('\\u002F', '/')

        # 策略 1：<source src="...m3u8...">
        m = re.search(r'<source[^>]+src=["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', text, re.I)
        if m:
            return self._play(m.group(1))

        # 策略 2：通用 m3u8
        m = re.search(r'(https?://[^\s"\'<>\\]+\.m3u8(?:\?[^\s"\'<>\\]*)?)', text)
        if m:
            return self._play(m.group(1))

        # 策略 3：JS 变量
        m = re.search(r'(?:videoUrl|playUrl|m3u8|source|src)\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']', text, re.I)
        if m:
            return self._play(m.group(1))

        # 兜底：交给框架嗅探
        return {"parse": 1, "url": url, "header": self.headers}

    def _play(self, m3u8_url):
        return {
            "parse": 0,
            "playUrl": "",
            "url": m3u8_url,
            "header": self.headers
        }

    # ==================== 工具 ====================
    def _is_cloudflare_challenge(self, text):
        if not text:
            return False
        keys = ('Just a moment', '__cf_chl_opt', 'cf-browser-verification',
                'challenge-platform', 'Checking your browser')
        return any(k in text for k in keys)
