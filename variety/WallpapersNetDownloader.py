# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Peter Levi <peterlevi@peterlevi.com>
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import urllib2
from bs4 import BeautifulSoup
import random
import re

import logging
from variety import Downloader

logger = logging.getLogger('variety')

random.seed()

class WallpapersNetDownloader(Downloader.Downloader):
    def __init__(self, parent, category_url):
        super(WallpapersNetDownloader, self).__init__(parent, "Wallpapers.net", category_url)
        self.host = "http://wallpapers.net"
        self.queue = []

    @staticmethod
    def fetch(url):
        content = urllib2.urlopen(url, timeout=20).read()
        return BeautifulSoup(content)

    @staticmethod
    def validate(url):
        logger.info("Validating WN url " + url)
        try:
            if not url.startswith("http://"):
                url = "http://" + url
            if not url.lower().startswith("http://www.wallpapers.net") and not url.lower().startswith("http://wallpapers.net"):
                return False

            s = WallpapersNetDownloader.fetch(url)
            walls = [wall.find("div", "thumb") for wall in s.findAll("li", "wall")]
            return len(walls) > 0
        except Exception:
            logger.exception("Error while validating URL, proabably bad URL")
            return False

    def download_one(self):
        logger.info("Downloading an image from Wallpapers.net, " + self.location)
        logger.info("Queue size: %d" % len(self.queue))

        if not self.queue:
            self.fill_queue()
        if not self.queue:
            logger.info("WN Queue still empty after fill request - probably wrong URL?")
            return None

        wallpaper_url = self.queue.pop()
        logger.info("Wallpaper URL: " + wallpaper_url)

        s = self.fetch(wallpaper_url)
        img_url = self.host + s.find('a', text=re.compile("Original format"))['href']
        logger.info("Image page URL: " + img_url)

        s = self.fetch(img_url)
        src_url = s.img['src']
        logger.info("Image src URL: " + src_url)

        return self.save_locally(wallpaper_url, src_url)

    def fill_queue(self):
        logger.info("Category URL: " + self.location)
        s = self.fetch(self.location)
        mp = 0
        urls = [url['href'] for x in s.find_all('div', 'pagination') for url in x.find_all('a') if
                url['href'].index('/page/') > 0]

        if urls:
            for h in urls:
                page = h[h.index("/page/") + 6:]
                mp = max(mp, int(page))

            # special case the top wallpapers - limit to the best 200 pages
            if self.location.find("top_wallpapers"):
                mp = min(mp, 200)

            page = random.randint(0, mp)
            h = urls[0]
            page_url = self.host + h[:h.index("/page/") + 6] + str(page)

            logger.info("Page URL: " + page_url)
            s = self.fetch(page_url)
        else:
            logger.info("Single page in category")

        walls = [self.host + x.a['href'] for x in s.find_all('div', 'thumb')]
        walls = [x for x in walls if x not in self.parent.banned]

        self.queue.extend(walls)

        random.shuffle(self.queue)
        if len(self.queue) >= 8:
            self.queue = self.queue[:len(self.queue)//2]
            # only use randomly half the images from the page -
            # if we ever hit that same page again, we'll still have what to download

        logger.info("WN queue populated with %d URLs" % len(self.queue))