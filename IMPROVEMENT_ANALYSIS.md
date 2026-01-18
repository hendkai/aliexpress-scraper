# AliExpress Scraper - Analyse und Verbesserungsvorschläge

## Zusammenfassung der Analyse

Nach Live-Tests mit DrissionPage und Analyse der AliExpress-Website wurden folgende Hauptprobleme identifiziert:

### Hauptprobleme

1. **Anti-Bot-Systeme**: AliExpress nutzt AWSC/CAPTCHA und Punish-Systeme im Headless-Modus
2. **Client-Side Rendering (CSR)**: Die Seite lädt Daten dynamisch über JavaScript
3. **Leere Seiten im Headless-Modus**: Produktseiten zeigen nur minimales HTML
4. **Veraltete Selektoren**: `data-sku-col` Attribute fehlen, wenn Anti-Bot aktiv ist
5. **API-Endpunkt-Status**: Der aktuelle API-Endpunkt `/fn/search-pc/index` ist nicht im HTML referenziert

### Technische Erkenntnisse

#### Suchseite
- **Status**: Stark blockiert im Headless-Modus
- **HTML-Größe**: Nur 113 Zeilen (CAPTCHA-Seite)
- **Produktcontainer**: 0 gefunden
- **JavaScript-Daten**: Keine window.__INITIAL_STATE__ vorhanden

#### Produktseite
- **Status**: Teilweise funktionsfähig
- **HTML-Größe**: 865 Zeilen
- **window.runParams**: Leer (`{}`)
- **window._d_c_.DCData**: Enthält Bilddaten und Config
- **CSR-Modus**: `window._d_c_.isCSR = true`
- **Bildpfade**: In `imagePathList` verfügbar

## Verbesserungsvorschläge

### 1. Anti-Bot-Umgehung verbessern

**Problem**: Headless-Browser wird erkannt
**Lösung**:
```python
def enhanced_browser_stealth():
    co = ChromiumOptions()

    # KRITISCH: Nicht headless für erste Session
    # co.headless()  # ENTFERNEN!

    # Stealth-Features
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--disable-web-security')
    co.set_argument('--disable-features=IsolateOrigins,site-per-process')
    co.set_argument('--disable-site-isolation-trials')

    # Fingerprint-Anpassungen
    co.set_argument('--window-size=1920,1080')
    co.set_argument('--start-maximized')

    # WebGL/Canvas Fingerprinting umgehen
    co.set_argument('--use-gl=swiftshader')
    co.set_argument('--enable-webgl')

    # Realistic user agent
    co.set_user_agent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    return co
```

### 2. CSR-Daten-Extraktion implementieren

**Problem**: Daten werden nicht im initialen HTML geladen
**Lösung**: Warten auf JavaScript-Rendering

```python
def wait_for_csr_data(browser_page, timeout=30):
    """
    Warte bis CSR-Daten vollständig geladen sind
    """
    import time
    start_time = time.time()

    while time.time() - start_time < timeout:
        # Prüfe auf verschiedene Indikatoren
        html = browser_page.html

        # Check 1: Produktbilder geladen
        if 'imagePathList' in html:
            # Check 2: Produkttitel vorhanden
            title_elem = browser_page.ele('[data-pl=product-title]', timeout=1)
            if title_elem:
                # Check 3: Preise geladen
                price_elem = browser_page.ele('[class*="price"]', timeout=1)
                if price_elem:
                    print("✓ CSR-Daten vollständig geladen")
                    return True

        time.sleep(1)

    print("⚠ Timeout beim Laden der CSR-Daten")
    return False
```

### 3. Neue API-Endpunkte identifizieren

**Problem**: Aktueller API-Endpunkt möglicherweise veraltet
**Lösung**: Network-Traffic abfangen

```python
def intercept_api_calls(browser_page):
    """
    Fange API-Calls ab, um neue Endpunkte zu finden
    """
    # DrissionPage unterstützt teilweise Packet-Sniffing
    # Alternative: Browser DevTools Protocol verwenden

    # Für jetzt: JavaScript-Injection zum Logging
    js_inject = """
    (function() {
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            console.log('FETCH:', args[0]);
            return originalFetch.apply(this, args);
        };

        const originalXHR = window.XMLHttpRequest.prototype.open;
        window.XMLHttpRequest.prototype.open = function(method, url) {
            console.log('XHR:', method, url);
            return originalXHR.apply(this, arguments);
        };
    })();
    """

    browser_page.run_js(js_inject)
```

### 4. Verbesserte Variant-Detection

**Problem**: Varianten nicht gefunden wegen fehlender HTML-Struktur
**Lösung**: Multi-Source-Ansatz

```python
def enhanced_variant_detection(browser_page, product_id):
    """
    Mehrstufiger Ansatz zur Variant-Detection
    """
    variants = []

    # Methode 1: CSR-Daten aus window._d_c_.DCData
    try:
        dc_data_script = """
        return window._d_c_ && window._d_c_.DCData
            ? JSON.stringify(window._d_c_.DCData)
            : null;
        """
        dc_data = browser_page.run_js(dc_data_script)
        if dc_data:
            data = json.loads(dc_data)
            # Bild-Pfade als Proxy für Varianten
            if 'imagePathList' in data:
                variants_from_images = extract_variants_from_images(
                    data['imagePathList']
                )
                variants.extend(variants_from_images)
    except:
        pass

    # Methode 2: Dynamisch gerenderte SKU-Elemente
    try:
        # Warte auf SKU-Rendering
        time.sleep(5)
        sku_elements = browser_page.eles('[data-sku-col]', timeout=10)
        variants_from_sku = extract_variants_from_elements(sku_elements)
        variants.extend(variants_from_sku)
    except:
        pass

    # Methode 3: API-Call für SKU-Daten
    try:
        # Versuche direkten API-Call
        sku_api_url = f"https://www.aliexpress.com/aegis/product/sku/{product_id}"
        variants_from_api = fetch_variants_via_api(sku_api_url)
        variants.extend(variants_from_api)
    except:
        pass

    return deduplicate_variants(variants)
```

### 5. Session-Management verbessern

**Problem**: Session-Cache führt zu Blockierung
**Lösung**: Intelligenteres Cookie-Management

```python
def smart_session_management():
    """
    Verwalte Sessions intelligent mit Rotation
    """
    # Nutze mehrere Session-Pools
    session_pool = SessionPool(size=5)

    # Rotiere Sessions
    current_session = session_pool.get_fresh_session()

    # Checke Session-Gesundheit
    if not is_session_healthy(current_session):
        current_session = session_pool.create_new_session()

    return current_session

class SessionPool:
    def __init__(self, size=5):
        self.size = size
        self.sessions = []
        self.current_index = 0

    def get_fresh_session(self):
        if len(self.sessions) < self.size:
            self.sessions.append(self.create_session())

        session = self.sessions[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.sessions)
        return session

    def create_session(self):
        # Session-Erstellung mit Browser
        return create_fresh_session_with_browser()
```

### 6. Intelligente Wartezeiten

**Problem**: Feste Wartezeiten sind ineffizient
**Lösung**: Adaptive Wartezeiten basierend auf Seitenzustand

```python
def smart_wait_for_element(browser_page, selectors, timeout=30):
    """
    Warte intelligent auf mehrere mögliche Selektoren
    """
    start_time = time.time()
    check_interval = 0.5

    while time.time() - start_time < timeout:
        for selector in selectors:
            try:
                elem = browser_page.ele(selector, timeout=check_interval)
                if elem and elem.text.strip():
                    return elem, selector
            except:
                continue

        time.sleep(check_interval)

    return None, None

# Verwendung:
price_selectors = [
    '.price--currentPriceText--V8_y_b5',
    '.product-price-value',
    '[class*="currentPrice"]',
    '[class*="price"][class*="current"]',
]

price_elem, found_selector = smart_wait_for_element(
    browser_page,
    price_selectors,
    timeout=20
)

if price_elem:
    print(f"✓ Preis gefunden mit Selector: {found_selector}")
```

### 7. Error Recovery System

**Problem**: Fehler führen zum kompletten Abbruch
**Lösung**: Robustes Error-Handling mit Retry-Logic

```python
def scrape_with_retry(func, max_retries=3, backoff=2):
    """
    Retry-Decorator für Scraping-Funktionen
    """
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = backoff ** attempt
                    print(f"⚠ Fehler: {e}. Retry {attempt+1}/{max_retries} in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"✗ Alle Retries fehlgeschlagen: {e}")
                    raise
    return wrapper

# Verwendung:
@scrape_with_retry
def scrape_product_page(url):
    # Scraping-Logik
    pass
```

## Prioritäten für Implementierung

### Hoch (Sofort)
1. ✅ Anti-Bot-Umgehung verbessern (Non-Headless für Session-Init)
2. ✅ CSR-Daten-Extraktion implementieren
3. ✅ Smart-Wait-Mechanismen

### Mittel (Diese Woche)
4. Neue API-Endpunkte identifizieren
5. Session-Pool implementieren
6. Error-Recovery verbessern

### Niedrig (Später)
7. Network-Traffic-Interception
8. Advanced Fingerprinting-Umgehung

## Nächste Schritte

1. **Testen ohne Headless**: Session-Initialisierung mit sichtbarem Browser
2. **CSR-Wait implementieren**: Warten auf vollständiges JavaScript-Rendering
3. **Multi-Selector-Ansatz**: Flexible Element-Suche mit mehreren Selektoren
4. **Logging verbessern**: Detailliertes Logging für Debugging

## Code-Beispiel: Verbesserter Scraper

```python
def improved_scrape_product(product_url):
    """
    Verbesserter Produkt-Scraper mit allen Best Practices
    """
    # 1. Setup Browser mit Stealth
    co = enhanced_browser_stealth()
    browser = WebPage(chromium_options=co)

    try:
        # 2. Lade Seite
        print(f"Loading: {product_url}")
        browser.get(product_url, timeout=30)

        # 3. Warte auf CSR-Daten
        if not wait_for_csr_data(browser):
            print("⚠ CSR-Daten nicht vollständig geladen")

        # 4. Extrahiere Daten mit Multi-Source
        variants = enhanced_variant_detection(browser, product_id)

        # 5. Extrahiere Preise mit Smart-Wait
        price_elem, _ = smart_wait_for_element(
            browser,
            price_selectors,
            timeout=20
        )

        return {
            'variants': variants,
            'price': price_elem.text if price_elem else None,
            'success': True
        }

    except Exception as e:
        print(f"✗ Error: {e}")
        return {'success': False, 'error': str(e)}

    finally:
        browser.quit()
```

## Monitoring und Metrics

Implementiere Logging für:
- Session-Erfolgsrate
- Anti-Bot-Erkennungen
- Scraping-Geschwindigkeit
- Fehlertypen und -häufigkeit

```python
# Metrics-Tracking
metrics = {
    'total_requests': 0,
    'successful_requests': 0,
    'blocked_requests': 0,
    'avg_response_time': 0,
    'variant_detection_success_rate': 0
}

def update_metrics(success, response_time, variants_found):
    metrics['total_requests'] += 1
    if success:
        metrics['successful_requests'] += 1
    else:
        metrics['blocked_requests'] += 1

    # Update averages
    metrics['avg_response_time'] = (
        (metrics['avg_response_time'] * (metrics['total_requests'] - 1) + response_time)
        / metrics['total_requests']
    )
```

## Fazit

Die Hauptverbesserungen konzentrieren sich auf:
1. **Bessere Anti-Bot-Umgehung**: Non-Headless-Modus für Session-Init
2. **CSR-Awareness**: Warten auf dynamisches JavaScript-Rendering
3. **Robustheit**: Multi-Source-Ansatz und Error-Recovery
4. **Performance**: Smart-Waiting statt fixer Delays

Mit diesen Verbesserungen sollte der Scraper deutlich zuverlässiger und effizienter arbeiten.
