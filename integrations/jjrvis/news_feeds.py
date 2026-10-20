"""Fixed public RSS sources for the private news reader; no arbitrary URL fetching."""
import time
import re
import html
from email.utils import parsedate_to_datetime
import threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, wait
from urllib.parse import urlsplit
import httpx
from market_news import read_news
SOURCES={
 'local-leicester':('BBC News · Leicestershire','https://feeds.bbci.co.uk/news/england/leicester/rss.xml'),
 'fox-world':('Fox News · World','https://moxie.foxnews.com/google-publisher/world.xml'),
 'uk':('BBC News · UK','https://feeds.bbci.co.uk/news/uk/rss.xml'),
 'world':('BBC News · World','https://feeds.bbci.co.uk/news/world/rss.xml'),
 'technology':('BBC News · Technology','https://feeds.bbci.co.uk/news/technology/rss.xml'),
 'entertainment':('BBC News · Entertainment','https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml'),
 'science':('BBC News · Science','https://feeds.bbci.co.uk/news/science_and_environment/rss.xml'),
 'sky-world':('Sky News · World','https://feeds.skynews.com/feeds/rss/world.xml'),
 'sky-business':('Sky News · Business','https://feeds.skynews.com/feeds/rss/business.xml'),
 'politics':('Sky News · Politics','https://feeds.skynews.com/feeds/rss/politics.xml'),
 'aljazeera':('Al Jazeera','https://www.aljazeera.com/xml/rss/all.xml'),
 'guardian':('The Guardian · World','https://www.theguardian.com/world/rss'),
 'france24':('France 24','https://www.france24.com/en/rss'),
}
CATEGORY={'local-leicester':'local','fox-world':'world','sky-world':'world','sky-business':'trading','aljazeera':'world','guardian':'world','france24':'world'}
DOMAINS={'www.foxnews.com','www.bbc.co.uk','www.bbc.com','bbc.co.uk','bbc.com','news.sky.com','www.aljazeera.com','www.theguardian.com','www.france24.com'}
CACHE={}; LOCK=threading.Lock()
# A shared pool lets an individual slow publisher finish in the background
# without making every briefing wait for it or starting duplicate requests.
POOL=ThreadPoolExecutor(max_workers=len(SOURCES)+1, thread_name_prefix='jjrvis-news')
JOBS={}; RESULTS={}; JOB_LOCK=threading.Lock()
READ_BUDGET_SECONDS=4.0
def parse_rss(text, category, source):
    root=ET.fromstring(text)
    items=[]
    for item in root.findall('./channel/item')[:25]:
        url=item.findtext('link',''); title=item.findtext('title','')
        if urlsplit(url).scheme!='https' or urlsplit(url).hostname not in DOMAINS or not title: continue
        image=''
        image_hosts={'ichef.bbci.co.uk','e3.365dm.com','i.guim.co.uk','s.france24.com','a57.foxnews.com','static.foxnews.com'}
        for node in item.iter():
            if node.tag not in ('{http://search.yahoo.com/mrss/}thumbnail','{http://search.yahoo.com/mrss/}content','enclosure'):continue
            candidate=node.get('url','')
            if urlsplit(candidate).scheme=='https' and urlsplit(candidate).hostname in image_hosts:
                image=candidate;break
        summary=html.unescape(re.sub('<[^>]+>',' ',item.findtext('description','')))
        summary=re.sub(r'\s+',' ',summary).strip()[:350]
        items.append({'title':title[:500],'url':url,'published_at':item.findtext('pubDate',''),'source':source,'category':CATEGORY.get(category,category),'image':image,'summary':summary,'breaking':bool(re.search(r'\bbreaking\b',title,re.I))})
    return items

def feed(category):
    source,url=SOURCES[category]
    with LOCK:
        cached=CACHE.get(category)
        if cached and time.time()-cached['attempt_at']<120: return cached
    try:
        response=httpx.get(url,timeout=8,follow_redirects=False);response.raise_for_status()
        if len(response.content)>1000000: raise ValueError('Feed too large')
        items=parse_rss(response.content,category,source)
        result={'state':'connected','items':items,'fetched_at':time.time(),'attempt_at':time.time()}
    except (httpx.HTTPError,ValueError,ET.ParseError):
        result={**(cached or {'items':[]}), 'state':'cached_unavailable' if cached else 'unavailable','attempt_at':time.time()}
    with LOCK: CACHE[category]=result
    return result

def _collect(key):
    result=read_news() if key=='CNBC' else feed(key)
    with JOB_LOCK:
        RESULTS[key]=result
    return result


def read_all(max_wait=READ_BUDGET_SECONDS):
    keys=['CNBC', *SOURCES]
    with JOB_LOCK:
        jobs={}
        for key in keys:
            job=JOBS.get(key)
            if job is None or job.done():
                job=POOL.submit(_collect,key)
                JOBS[key]=job
            jobs[key]=job
    # All publishers start together. The response has one shared deadline,
    # not CNBC's timeout followed by successive waves of RSS timeouts.
    wait(jobs.values(),timeout=max(0,min(float(max_wait),READ_BUDGET_SECONDS)))
    with JOB_LOCK:
        snapshots=dict(RESULTS)
    items=[];states={}
    for key,job in jobs.items():
        pending=not job.done()
        try:
            result=job.result() if not pending else snapshots.get(key,{})
        except Exception:
            result={**snapshots.get(key,{}),'state':'cached_unavailable' if snapshots.get(key,{}).get('items') else 'unavailable'}
        source='CNBC' if key=='CNBC' else SOURCES[key][0]
        rows=result.get('items',[])
        if key=='CNBC':
            rows=[{**row,'source':'CNBC','category':'trading'} for row in rows]
        items.extend(rows)
        states[source]=('cached_refreshing' if rows else 'unavailable_refreshing') if pending else result.get('state','unavailable')
    unique={n['url']:n for n in items}
    def timestamp(n):
        raw=n.get('published_at','')
        try:return parsedate_to_datetime(raw).timestamp()
        except (ValueError,TypeError,OverflowError):
            try:
                from datetime import datetime
                return datetime.fromisoformat(raw.replace('Z','+00:00')).timestamp()
            except (ValueError,TypeError,AttributeError):return 0
    items=sorted(unique.values(),key=timestamp,reverse=True)
    return {'items':items,'sources':states,'checked_at':time.time()}
