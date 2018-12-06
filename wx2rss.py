#!/usr/local/bin/python3

from requests_html import HTMLSession
from datetime import datetime,timedelta,timezone
import argparse
import json
import sys,traceback

rss_template = '''<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
 <title>{title}</title>
 <description>{desc}</description>
 <link>{link}</link>
 <image>
   <url>{image}</url>
   <link>{link}</link>
   <title>{title}></title>
 </image>

 {items}
</channel>
</rss>
'''

rss_item_template = '''
<item>
<title>{title}</title>
<description>{desc}</description>
<link>{link}</link>
<guid isPermaLink="false">{guid}</guid>
<pubDate>{pubdate}</pubDate>
</item>
'''

class HTMLParseException(Exception):
    pass

def wrap_cdata(s):
    s.replace("]]>","]]]]><![CDATA[>")
    return "<![CDATA[" + s + "]]>"

def fetch_page(name):
    session = HTMLSession()
    resp = session.get("https://weixin.sogou.com/weixin?type=1&s_from=input&query={}&ie=utf8&_sug_=n&_sug_type_=".format(name))
    resp.raise_for_status()
    a = resp.html.find(".news-box .news-list2 li .img-box a", first=True)
    if not a or "href" not in a.attrs: raise HTMLParseException(name)
    resp = session.get(a.attrs["href"])
    resp.raise_for_status()
    resp.html.render()
    return resp.html

def parse_page_el(el):
    title_el = el.find(".weui_media_title",first=True)
    if not title_el: raise HTMLParseException("no meui_media_title")
    title = title_el.text
    link = "http://mp.weixin.qq.com" + title_el.attrs["hrefs"]
    desc = el.find(".weui_media_desc",first=True).text
    ts = int(el.find(".weui_media_hd",first=True).attrs["data-t"][:10])

    return {"title":title, "desc":desc, "link":link, "date": datetime.fromtimestamp(ts, timezone(timedelta(hours=8)))}


def parse_page(html):
    print(html.url)
    title = html.find(".profile_nickname",first=True).text
    logo = html.find(".radius_avatar img",first=True).attrs["src"]
    desc = html.find(".profile_desc_value",first=True).text
    l = html.find(".weui_msg_card")
    items = [parse_page_el(el) for el in l]

    return {"title":title, "desc":desc, "link":html.url, "logo":logo, "items" : items}

def gen_rss(info):
    items = []
    for item in info["items"]:
        items.append(rss_item_template.format(
            title = wrap_cdata(item["title"]), 
            desc = wrap_cdata(item["desc"]), 
            link = wrap_cdata(item["link"]), 
            guid = wrap_cdata(item["title"]), 
            pubdate = item["date"].strftime("%a, %d %b %Y %H:%M:%S %z")
            ))

    return rss_template.format(
            items = "".join(items), 
            title = wrap_cdata(info["title"]), 
            desc = wrap_cdata(info["desc"]), 
            link = wrap_cdata(info["link"]), 
            image = wrap_cdata(info["logo"])
            )

def wx2rss(name):
    try:
        html= fetch_page(name)
        info = parse_page(html)
        return gen_rss(info)
    except:
        print("gen rss error:", name, file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)

def main():
    p = argparse.ArgumentParser(description = "gen feeder from WeChat Official Accounts")
    p.add_argument("-f", dest="from_file", action="store_true", help="read from file")
    p.add_argument("name")
    args = p.parse_args()

    if args.from_file:
        with open(args.name) as f:
            t = json.load(f)
            for k,v in t.items():
                rss = wx2rss(k)
                if rss:
                    with open(v,"w") as wf:
                        wf.write(rss)
    else:
        rss = wx2rss(args.name)
        if rss:
            print(rss)

if __name__ == "__main__":
    main()
