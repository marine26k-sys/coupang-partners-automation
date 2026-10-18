"""Stable public product references and verified publication navigation."""
from urllib.parse import urlparse


def enrich_navigation(products, previous, posts=()):
    numbers = dict(previous.get('productNumbers', {}))
    next_number = max((v for v in numbers.values() if isinstance(v, int)), default=0)
    links = {}
    for post in posts:
        url = post.get('postUrl', '')
        if urlparse(url).scheme == 'https' and urlparse(url).hostname == 'www.threads.com':
            links[str(post.get('productId'))] = url
    for product in products:
        pid = product['id']
        if pid not in numbers:
            next_number += 1
            numbers[pid] = next_number
        product['catalogNumber'] = f"{numbers[pid]:03d}"
        if pid in links:
            product['relatedPostUrl'] = links[pid]
    return numbers
