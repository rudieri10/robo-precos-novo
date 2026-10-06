"""Testa acesso às 3 plataformas a partir do runner do GitHub (IP dos EUA).
Modo 'http': curl_cffi imitando Chrome.
Modo 'browser': Playwright headless Chromium.
"""
import sys
import re
import json

URLS = {
    'homedepot': 'https://www.homedepot.com/p/310969646',
    'lowes': 'https://www.lowes.com/pd/EIGHT-DOORS-LW-503-Acab-Final-Clear-Glass-32-80-35/2555919',
    'wayfair': 'https://www.wayfair.com/home-improvement/pdp/80-in-28-in-503-acab-final-eightdoorswf-EITD1051-02.html',
}

MARCAS_BLOQUEIO = ['access denied', 'px-captcha', 'are you a robot', 'edgesuite', 'request blocked', 'unusual traffic']


def resumo(nome, status, html):
    html_lower = html.lower()
    bloqueio = any(m in html_lower for m in MARCAS_BLOQUEIO)
    achou = {}
    for bloco in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S):
        try:
            dados = json.loads(bloco)
        except Exception:
            continue
        itens = dados if isinstance(dados, list) else [dados]
        for d in itens:
            if isinstance(d, dict) and d.get('@type') == 'Product':
                offers = d.get('offers') or {}
                agg = d.get('aggregateRating') or {}
                achou = {
                    'preco': offers.get('price') if isinstance(offers, dict) else None,
                    'rating': agg.get('ratingValue'),
                    'reviews': agg.get('ratingCount') or agg.get('reviewCount'),
                }
    print(f"RESULTADO {nome}: HTTP {status} - {len(html)} bytes - {'BLOQUEIO' if bloqueio else 'OK'} - JSON-LD: {json.dumps(achou, ensure_ascii=False) if achou else 'nenhum'}")


if sys.argv[1] == 'http':
    from curl_cffi import requests
    for nome, url in URLS.items():
        try:
            r = requests.get(url, impersonate='chrome131', timeout=40)
            resumo(nome, r.status_code, r.text)
        except Exception as e:
            print(f"RESULTADO {nome}: EXCECAO {str(e)[:120]}")
else:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale='en-US',
            viewport={'width': 1366, 'height': 768},
        )
        for nome, url in URLS.items():
            page = ctx.new_page()
            try:
                resp = page.goto(url, timeout=45000, wait_until='domcontentloaded')
                page.wait_for_timeout(4000)
                resumo(nome, resp.status if resp else 0, page.content())
            except Exception as e:
                print(f"RESULTADO {nome}: EXCECAO {str(e)[:120]}")
            finally:
                page.close()
        browser.close()
