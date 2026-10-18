"""Export only successful public post fields, never private drafts or credentials."""
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlparse


def featured_records(history):
    items=[]
    for record in reversed(history.records()):
        publication=record.get('publication') or {}
        draft=record.get('draft') or {}
        post=publication.get('permalink','')
        link=draft.get('deeplink','')
        if record['status'] not in ('published','notified','notification_failed'):
            continue
        if urlparse(post).hostname!='www.threads.com' or urlparse(link).hostname!='link.coupang.com':
            continue
        items.append({'id':'post-'+str(publication.get('post_id') or record['id']),
            'number':record['id'][:6].upper(),'productId':record['product_id'],'name':record['product_name'],
            'url':link,'postUrl':post,'date':datetime.fromtimestamp(record['created'],ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d'),
            'image':draft.get('productImage',''),'price':draft.get('productPrice'),
            'priceDate':draft.get('priceCapturedAt'),'category':'Threads 소개'})
    return list(reversed(items))
