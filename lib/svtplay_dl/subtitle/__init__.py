import xml.etree.ElementTree as ET
import json
import re
from svtplay_dl.log import log
from svtplay_dl.utils import is_py2, is_py3, get_http_data
from svtplay_dl.output import output


class subtitle(object):
    def __init__(self, options, subtype, url):
        self.url = url
        self.subtitle = None
        self.options = options
        self.subtype = subtype

    def download(self):
        error, subdata = get_http_data(self.url, cookiejar=self.options.cookies)
        if error:
            log.error("Can't download subtitle")
            return

        data = None
        if self.subtype == "tt":
            data = self.tt(subdata)
        if self.subtype == "json":
            data = self.json(subdata)
        if self.subtype == "sami":
            data = self.sami(subdata)
        if self.subtype == "smi":
            data = self.smi(subdata)
        if self.subtype == "wrst":
            data = self.wrst(subdata)

        file_d = output(self.options, "srt")
        if hasattr(file_d, "read") is False:
            return
        file_d.write(data)
        file_d.close()

    def tt(self, subdata):
        i = 1
        data = ""
        tree = ET.ElementTree(ET.fromstring(subdata))
        xml = tree.find("{http://www.w3.org/2006/10/ttaf1}body").find("{http://www.w3.org/2006/10/ttaf1}div")
        plist = list(xml.findall("{http://www.w3.org/2006/10/ttaf1}p"))
        for node in plist:
            tag = norm(node.tag)
            if tag == "p" or tag == "span":
                begin = node.attrib["begin"]
                if not ("dur" in node.attrib):
                    duration = node.attrib["duration"]
                else:
                    duration = node.attrib["dur"]
                if not ("end" in node.attrib):
                    begin2 = begin.split(":")
                    duration2 = duration.split(":")
                    sec = float(begin2[2]) + float(duration2[2])
                    end = "%02d:%02d:%06.3f" % (int(begin[0]), int(begin[1]), sec)
                else:
                    end = node.attrib["end"]
                data += '%s\n%s --> %s\n' % (i, begin.replace(".", ","), end.replace(".", ","))
                data = tt_text(node, data)
                data += "\n"
                i += 1

        if is_py2:
            data = data.encode('utf8')
        return data

    def json(self, subdata):
        data = json.loads(subdata)
        number = 1
        subs = ""
        for i in data:
            subs += "%s\n%s --> %s\n" % (number, timestr(int(i["startMillis"])), timestr(int(i["endMillis"])))
            if is_py2:
                subs += "%s\n\n" % i["text"].encode("utf-8")
            else:
                subs += "%s\n\n" % i["text"]
            number += 1

        return subs

    def sami(self, subdata):
        tree = ET.XML(subdata)
        subt = tree.find("Font")
        subs = ""
        n = 0
        for i in subt.getiterator():
            if i.tag == "Subtitle":
                n = i.attrib["SpotNumber"]

                if i.attrib["SpotNumber"] == "1":
                    subs += "%s\n%s --> %s\n" % (i.attrib["SpotNumber"], timecolon(i.attrib["TimeIn"]), timecolon(i.attrib["TimeOut"]))
                else:
                    subs += "\n%s\n%s --> %s\n" % (i.attrib["SpotNumber"], timecolon(i.attrib["TimeIn"]), timecolon(i.attrib["TimeOut"]))
            else:
                if int(n) > 0:
                    subs += "%s\n" % i.text

        if is_py2:
            subs = subs.encode('utf8')
        return subs

    def smi(self, subdata):
        if is_py3:
            subdata = subdata.decode("latin1")
        recomp = re.compile(r'<SYNC Start=(\d+)>\s+<P Class=\w+>(.*)\s+<SYNC Start=(\d+)>\s+<P Class=\w+>', re.M|re.I|re.U)
        number = 1
        subs = ""
        TAG_RE = re.compile(r'<[^>]+>')
        bad_char = re.compile(r'\x96')
        for i in recomp.finditer(subdata):
            subs += "%s\n%s --> %s\n" % (number, timestr(i.group(1)), timestr(i.group(3)))
            text = "%s\n\n" % TAG_RE.sub('', i.group(2).replace("<br>", "\n"))
            if text[0] == "\x0a":
                text = text[1:]
            subs += text
            number += 1
        recomp = re.compile(r'\r')
        text = bad_char.sub('-', recomp.sub('', subs)).replace('&quot;', '"')
        return text

    def wrst(self, subdata):
        recomp = re.compile(r"(\d+)\r\n([\d:\.]+ --> [\d:\.]+)?([^\r\n]+)?\r\n([^\r\n]+)\r\n(([^\r\n]*)\r\n)?")
        srt = ""
        subtract = False
        for i in recomp.finditer(subdata):
            number = int(i.group(1))
            match = re.search(r'(\d+):(\d+):([\d\.]+) --> (\d+):(\d+):([\d\.]+)', i.group(2))
            hour1 = int(match.group(1))
            hour2 = int(match.group(4))
            if number == 1:
                if hour1 > 9:
                    subtract = True
            if subtract:
                hour1 -= 10
                hour2 -= 10
            time = "%s:%s:%s --> %s:%s:%s" % (hour1, match.group(2), match.group(3).replace(".", ","), hour2, match.group(5), match.group(6).replace(".", ","))
            sub = "%s\n%s\n%s\n" % (i.group(1), time, i.group(4))
            if len(i.group(6)) > 0:
                sub += "%s\n" % i.group(6)
            sub += "\n"
            sub = re.sub('<[^>]*>', '', sub)
            srt += sub

        return srt

def timestr(msec):
    """
    Convert a millisecond value to a string of the following
    format:

        HH:MM:SS,SS

    with 10 millisecond precision. Note the , seperator in
    the seconds.
    """
    sec = float(msec) / 1000

    hours = int(sec / 3600)
    sec -= hours * 3600

    minutes = int(sec / 60)
    sec -= minutes * 60

    output = "%02d:%02d:%05.2f" % (hours, minutes, sec)
    return output.replace(".", ",")

def timecolon(data):
    match = re.search(r"(\d+:\d+:\d+):(\d+)", data)
    return "%s,%s" % (match.group(1), match.group(2))

def norm(name):
    if name[0] == "{":
        _, tag = name[1:].split("}")
        return tag
    else:
        return name

def tt_text(node, data):
    if node.text:
        data += "%s\n" % node.text.strip(' \t\n\r')
    for i in node:
        if i.text:
            data += "%s\n" % i.text.strip(' \t\n\r')
        if i.tail:
            text = i.tail.strip(' \t\n\r')
            if text:
                data += "%s\n" % text
    return data
