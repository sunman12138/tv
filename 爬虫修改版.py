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
        'Referer': f'{host}/{dm}/cn/',
    }

    def _base(self):
        return f'{self.host}/{self.dm}/cn'

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

    def _parse_cards(self, doc):
        videos = []
        for item in doc('div.group').items():
            a = item('a[href]').eq(0)
            href = a.attr('href') or ''
            if not href or '/search/' in href:
                continue

            vid = href.rstrip('/').split('/')[-1]
            if not vid or len(vid) < 3:
                continue

            name = a.text().strip()
            if not name:
                name = item('img').attr('alt') or item('img').attr('title') or vid

            pic = item('img').attr('data-src') or item('img').attr('src') or ''
            if pic.startswith('//'):
                pic = 'https:' + pic
            elif pic.startswith('/'):
                pic = self.host + pic

            remarks = ''
            for span in item('span').items():
                txt = span.text().strip()
                if txt and any(k in txt for k in ['中文字幕', '无码', 'HD', ':', '分钟']):
                    remarks = txt
                    break

            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remarks,
                "style": {"type": "rect", "ratio": 1.78}
            })

        seen = set()
        unique = []
        for v in videos:
            if v['vod_id'] not in seen:
                seen.add(v['vod_id'])
                unique.append(v)
        return unique

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self._base()}/{tid}?page={pg}"
        try:
            res = self.fetch(url, headers=self.headers)
            doc = pq(res.text)
            videos = self._parse_cards(doc)
        except Exception:
            videos = []

        return {
            'list': videos,
            'page': pg,
            'pagecount': 999,
            'limit': len(videos),
            'total': 999
        }

    def detailContent(self, ids):
        vid = ids[0]
        url = f"{self._base()}/{vid}"
        try:
            res = self.fetch(url, headers=self.headers)
            doc = pq(res.text)
        except Exception:
            return {'list': [self._empty_vod(vid)]}

        name = doc('h1').text().strip()
        if not name:
            name = doc('meta[property="og:title"]').attr('content') or vid

        pic = doc('meta[property="og:image"]').attr('content') or doc('video').attr('poster') or ''
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
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
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

    def searchContent(self, key, quick, pg="1"):
        keyword = quote(key.strip())
        url = f"{self._base()}/search/{keyword}?page={pg}"
        try:
            res = self.fetch(url, headers=self.headers)
            doc = pq(res.text)
            videos = self._parse_cards(doc)
        except Exception:
            videos = []
        return {"list": videos, "page": int(pg)}

    def playerContent(self, flag, id, vipFlags):
        url = f"{self._base()}/{id}"
        try:
            res = self.fetch(url, headers=self.headers)
        except Exception:
            return {"parse": 1, "url": url, "header": self.headers}

        text = res.text.replace('\\/', '/')   # 兼容 JS 转义斜杠

        source_match = re.search(
            r'<source[^>]+src=["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            text, re.I
        )
        if source_match:
            return self._play(source_match.group(1))

        m3u8_match = re.search(
            r'(https?://[^\s"\'<>\\]+\.m3u8(?:\?[^\s"\'<>\\]*)?)',
            text
        )
        if m3u8_match:
            return self._play(m3u8_match.group(1))

        js_match = re.search(
            r'(?:videoUrl|playUrl|m3u8|source)\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            text, re.I
        )
        if js_match:
            return self._play(js_match.group(1))

        return {"parse": 1, "url": url, "header": self.headers}

    def _play(self, m3u8_url):
        return {
            "parse": 0,
            "playUrl": "",
            "url": m3u8_url,
            "header": self.headers
        }
