# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import re
import json
import copy

from svtplay_dl.service import Service, OpenGraphThumbMixin
from svtplay_dl.utils import get_http_data
from svtplay_dl.utils.urllib import unquote_plus
from svtplay_dl.fetcher.http import HTTP
from svtplay_dl.log import log

class Youplay(Service, OpenGraphThumbMixin):
    supported_domains = ['www.affarsvarlden.se']

    def get(self, options):
        error, data = self.get_urldata()
        if error:
            log.error("Can't get the page.")
            return

        if self.exclude(options):
            return

        match = re.search(r'script async defer src="(//content.youplay.se[^"]+)"', data)
        if not match:
            log.error("Cant find video info")
            return

        error, data = get_http_data("http:%s" % match.group(1))
        if error:
            log.error("Cant get video info")
            return
        match = re.search(r'decodeURIComponent\("([^"]+)"\)\)', data)
        if not match:
            log.error("Can't decode video info")
            return
        data = unquote_plus(match.group(1))
        match = re.search(r"videoData = ({[^;]+});", data)
        if not match:
            log.error("Cant find vidoe info")
            return
        # fix broken json.
        regex = re.compile(r"\s(\w+):")
        data = regex.sub(r"'\1':", match.group(1))
        data = data.replace("'", "\"")
        j = re.sub(r"{\s*(\w)", r'{"\1', data)
        j = j.replace("\n", "")
        j = re.sub(r'",\s*}', '"}', j)
        jsondata = json.loads(j)
        for i in jsondata["episode"]["sources"]:
            match = re.search(r"mp4_(\d+)", i)
            if match:
                yield HTTP(copy.copy(options), jsondata["episode"]["sources"][i], match.group(1))
