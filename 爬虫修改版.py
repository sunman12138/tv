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
        return [200, "video/MP2T", "", ""]

    host = 'https://www.thisav66.com'
    dm = 'dm247'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.thisav66.com/dm247/cn/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    def _base(self):
        return f'{self.host}/{self.dm}/cn'

    # ==================== 首页 ====================
    def homeContent(self, filter):
        classes = [
            {"type_name": "最近更新", "type_id": "new"},
            {"type_name": "新作上市", "type_id": "release"},
            {"type_name": "中文字幕", "type_id": "chinese-subtitle"},
            {"type_name": "无码流出", "type_id": "uncensored-leak"},
            {"type_name": "VR", "type_id": "genres/VR"},
            {"type_name": "今日热门", "type_id": "today-hot"},
            {"type_name": "本周热门", "type_id": "weekly-hot"},
            {"type_name": "本月热门", "type_id": "monthly-hot"},
            {"type_name": "素人", "type_id": "amateur"},
            {"type_name": "亚洲AV", "type_id": "asia"},
            {"type_name": "麻豆传媒", "type_id": "madou"},
        ]
        return {'class': classes}

    def homeVideoContent(self):
        return self.categoryContent("new", 1, False, {})

    # ==================== 列表解析 ====================
    def _parse_cards(self, doc):
        videos = []
        seen = set()

        # 优先精确选择器，兜底 div.group
        cards = doc('div.thumbnail.group')
        if not cards:
            cards = doc('div.group')

        for item in cards.items():
            a = item('a[href]').eq(0)
            href = (a.attr('href') or '').strip()
            if not href or '/search/' in href:
                continue

            vid = href.rstrip('/').split('/')[-1]
            if not vid or len(vid) < 2:
                continue

            # 标题：卡片底部 div.my-2 a → 链接文本 → img alt → 番号
            name = item('div.my-2 a').text().strip()
            if not name:
                name = a.text().strip()
            if not name:
                name = (item('img').attr('alt') or item('img').attr('title') or '').strip()
            if not name:
                name = vid

            # 封面：img[data-src] 已是绝对地址，过滤 base64 占位
            pic = item('img[data-src]').attr('data-src') or ''
            if not pic:
                src = item('img').attr('src') or ''
                if src and not src.startswith('data:'):
                    pic = src
            if pic.startswith('//'):
                pic = 'https:' + pic
            elif pic.startswith('/'):
                pic = self.host + pic

            # 角标：中英文字幕 / 无码 / 时长
            remarks = ''
            for span in item('span').items():
                txt = span.text().strip()
                if not txt:
                    continue
                if any(k in txt for k in ['中文字幕', '英文字幕', '无码', 'HD', 'VR']):
                    remarks = txt
                    break
                if re.fullmatch(r'\d{1,2}:\d{2}(:\d{2})?', txt):
                    remarks = txt
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
    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self._base()}/{tid}?page={pg}"
        videos = []
        try:
            res = self.fetch(url, headers=self.headers)
            text = res.text or ''
            if self._is_cf_challenge(text):
                print(f"[nJAV] CF challenge: {url}")
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
            videos = self._parse_cards(pq(text))
        except Exception as e:
            print(f"[nJAV] category error: {e}")

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
        url = f"{self._base()}/{vid}"
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
        url = f"{self._base()}/search/{keyword}?page={pg}"
        try:
            res = self.fetch(url, headers=self.headers)
            videos = self._parse_cards(pq(res.text))
        except Exception:
            videos = []
        return {"list": videos, "page": int(pg) if str(pg).isdigit() else 1}

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags):
        url = f"{self._base()}/{id}"
        try:
            res = self.fetch(url, headers=self.headers)
        except Exception:
            return {"parse": 1, "url": url, "header": self.headers}

        text = (res.text or '').replace('\\/', '/').replace('\\u002F', '/')

        m = re.search(r'<source[^>]+src=["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', text, re.I)
        if m:
            return self._play(m.group(1))

        m = re.search(r'(https?://[^\s"\'<>\\]+\.m3u8(?:\?[^\s"\'<>\\]*)?)', text)
        if m:
            return self._play(m.group(1))

        m = re.search(r'(?:videoUrl|playUrl|m3u8|source|src)\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']', text, re.I)
        if m:
            return self._play(m.group(1))

        return {"parse": 1, "url": url, "header": self.headers}

    def _play(self, m3u8_url):
        return {
            "parse": 0,
            "playUrl": "",
            "url": m3u8_url,
            "header": self.headers
        }

    # ==================== 工具 ====================
    def _is_cf_challenge(self, text):
        if not text:
            return False
        keys = ('Just a moment', '__cf_chl_opt', 'cf-browser-verification',
                'challenge-platform', 'Checking your browser')
        return any(k in text for k in keys)
