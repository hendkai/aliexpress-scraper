# AliExpress Product Scraper

Ein leistungsstarkes und benutzerfreundliches Web-Interface zum Scrapen von Produktdaten von AliExpress mit fortschrittlichem Produktvarianten-System und automatischer Preisüberwachung.

![MIT License](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)

## Screenshots

### Such-Interface
![Search Interface](screenshots/Capture1.PNG)

### Ergebnisse und Feldauswahl
![Field Selection and Results](screenshots/Capture.PNG)

## 🌟 Hauptfeatures

### 🛍️ **Produktvarianten-System**
- **Automatische Variant-Erkennung**: Multi-Level-Fallback (API → Interactive → HTML-Analyse)
- **Intelligente Gruppierung**: Varianten werden automatisch nach Produktgruppen organisiert
- **Echte Produktbilder**: Authentische AliExpress-Bilder für jede Variante
- **Automatisches Tracking**: Alle gefundenen Varianten werden automatisch überwacht

### 📊 **Produktüberwachung & Tracking**
- **Preishistorie-Charts**: Visuelle Darstellung von Preisverläufen mit Chart.js
- **Selektives Tracking**: Produkte einzeln oder automatisch für Überwachung auswählen
- **Echtzeit-Updates**: Automatische Aktualisierung von Preisen und neuen Varianten
- **Detaillierte Produktseiten**: Umfassende Ansicht mit Varianten, Preishistorie und Store-Infos

### 🌐 **Erweiterte Navigation**
- **Browse-Galerie**: Durchsuchen aller Produkte mit Filtern und Sortierung
- **Such-System**: Volltext-Suche über alle Produkttitel
- **Settings-Bereich**: Datenbankmanagement, Statistiken und Export-Funktionen
- **Responsive Design**: Optimiert für Desktop und mobile Geräte

### 🚀 **Scraping-Engine**
- **API-basiertes Scraping**: Schnelle und effiziente Datenerfassung über die AliExpress-API
- **Intelligentes Session-Management**: Browser-Automatisierung nur für initiale Cookie-Erfassung
- **Anti-Block-Schutz**: 
  - Konfigurierbare Verzögerung zwischen Anfragen (0,2–10 Sekunden)
  - Serielle Verarbeitung zur Vermeidung von Blockaden
  - Session-Caching zur Minimierung von Browser-Automatisierung
- **Echtzeit-Streaming**: Live-Updates während des Scraping-Prozesses

### 📈 **Automatisierung**
- **Zeitgesteuertes Scraping**: Keyword-basierte automatische Produktaktualisierung
- **Scheduler-System**: Konfigurierbare Intervalle für verschiedene Suchbegriffe
- **Background-Processing**: Automatische Preisüberwachung ohne Benutzerinteraktion
- **Umfassendes Logging**: Detaillierte Protokollierung aller Scraping-Aktivitäten

## 🏗️ Projektstruktur

```
aliexpress-scraper/
├── app.py                      # Flask Web-App mit erweitertem Routing
├── scraper.py                  # Zentrale Scraping-Logik mit Variant-System
├── models.py                   # SQLAlchemy Datenbankmodelle
├── scheduler.py                # Automatisches, zeitgesteuertes Scraping
├── templates/                  # Jinja2-Templates für die Weboberfläche
│   ├── index.html             # Haupt-Scraping-Interface
│   ├── browse.html            # Produkt-Galerie mit Filtern
│   ├── product_detail.html    # Detailansicht mit Varianten & Charts
│   ├── search.html            # Suchfunktion
│   ├── settings.html          # Admin-Bereich
│   └── ...                    # Weitere Templates
├── results/                    # Exportierte CSV- und JSON-Dateien
├── aliexpress_scraper.db      # SQLite-Datenbankdatei
└── session_cache.json         # Zwischengespeicherte Sessiondaten
```

## 📦 Installation

1. Repository klonen:
```bash
git clone https://github.com/ImranDevPython/aliexpress-scraper.git
cd aliexpress-scraper
```

2. Abhängigkeiten installieren:
```bash
pip install -r requirements.txt
```

## 🚀 Nutzung

### 1. Anwendung starten
```bash
python app.py
```

### 2. Web-Interface öffnen
```
http://localhost:5000
```

### 3. Navigation und Features

#### **Hauptseite (Scraping)**
- Suchbegriff eingeben (z.B. "3D Filament", "Bluetooth Kopfhörer")
- Anzahl der zu scrapenden Seiten wählen (1–60)
- Felder auswählen und Filter setzen
- Anfrageverzögerung einstellen (empfohlen: 1 Sekunde)
- Scraping starten und Echtzeit-Fortschritt beobachten

#### **Browse-Galerie** (`/browse`)
- Alle Produkte in einer übersichtlichen Galerie durchsuchen
- Filter nach Kategorie, Store, oder nur getrackte Produkte
- Sortierung nach Preis, Bewertung, Bestellungen oder Aktualität
- Pagination für große Produktmengen

#### **Produktdetails** (`/product/<id>`)
- Vollständige Produktinformationen mit Preishistorie-Chart
- **Varianten-Galerie**: Alle verfügbaren Produktvarianten mit echten Bildern
- **Update-Button**: Automatisches Finden und Tracken neuer Varianten
- **Tracking-Control**: Produkt für Preisüberwachung aktivieren/deaktivieren
- Direktlink zur originalen AliExpress-Seite

#### **Suche** (`/search`)
- Volltext-Suche über alle gespeicherten Produkte
- Schnelle Filterung nach Produkttiteln

#### **Settings** (`/settings`)
- Datenbankstatistiken und -verwaltung
- Datenexport für getrackte Produkte
- Bereinigung alter Daten
- System-Übersicht

### 4. Variant-System nutzen

Das Herzstück der Anwendung ist das intelligente Produktvarianten-System:

1. **Varianten automatisch finden**: Auf einer Produktdetailseite den "Update"-Button klicken
2. **Multi-Level-Erkennung**: Das System versucht automatisch:
   - API-basierte Variant-Extraktion
   - Interactive Browser-Navigation
   - Intelligente HTML-Analyse mit produktspezifischen Regeln
3. **Automatisches Tracking**: Alle gefundenen Varianten werden automatisch überwacht
4. **Echte Bilder**: Authentische AliExpress-Produktbilder für jede Variante

## 🗄️ Datenbankstruktur

### Kernmodelle
- **Product**: Produktdaten, Varianten, Shop, Preis, Status, Tracking
  - `product_id`: AliExpress Produkt-ID (gruppiert Varianten)
  - `sku_id`: Eindeutige SKU für spezifische Varianten
  - `variant_title`: Variantenbeschreibung (z.B. "1KG Red", "Size L")
  - `is_tracked`: Tracking-Status für Preisüberwachung
- **PriceHistory**: Historische Preisverläufe mit Zeitstempel
- **SearchKeyword**: Überwachte Suchbegriffe und deren Intervalle
- **ScrapingLog**: Protokollierung aller Scraping-Aktivitäten

### Variant-Gruppierung
Produkte werden über das `product_id`-Feld gruppiert. Alle Varianten eines Produkts teilen sich die gleiche `product_id`, haben aber unterschiedliche `sku_id`s.

## 📋 Verfügbare Felder

- **Product ID** - AliExpress Produkt-Identifikator
- **SKU ID** - Eindeutige Varianten-Identifikator
- **Title** - Produkttitel
- **Variant Title** - Variantenbeschreibung
- **Sale Price** - Verkaufspreis
- **Original Price** - Ursprungspreis
- **Discount (%)** - Rabatt-Prozentsatz
- **Currency** - Währung
- **Rating** - Produktbewertung
- **Orders Count** - Anzahl Bestellungen
- **Store Name** - Shop-Name
- **Store ID** - Shop-Identifikator
- **Store URL** - Shop-Link
- **Product URL** - Produktlink
- **Image URL** - Produktbild

## ⚙️ Automatisches Scraping & Scheduling

### Keyword-Management
1. **Keywords hinzufügen**: Über `/keywords` Suchbegriffe mit Intervallen definieren
2. **Automatische Überwachung**: Scheduler führt regelmäßige Suchen durch
3. **Preishistorie**: Automatische Aktualisierung getrackerter Produkte
4. **Logs einsehen**: Über `/logs` alle Scraping-Aktivitäten überwachen

### Empfohlene Intervalle
- **Häufige Updates**: 1-6 Stunden für wichtige Produkte
- **Regelmäßige Checks**: 12-24 Stunden für Standard-Überwachung
- **Wöchentliche Scans**: 168 Stunden für umfassende Marktanalyse

## 🛡️ Best Practices

### 1. **Anfrageverzögerung**
- **Standard**: 1 Sekunde zwischen Anfragen
- **Automatisches Scraping**: 2 Sekunden (konservativer)
- **Niedrigere Werte** (0,2–0,5s) erhöhen das Blockier-Risiko

### 2. **Seitenanzahl**
- **Manuell**: Bis zu 60 Seiten pro Suche
- **Automatisch**: Maximal 3 Seiten zur Serverschonung
- **Mit Filtern** gezielter suchen für bessere Ergebnisse

### 3. **Session-Management**
- **Cache-Dauer**: 30 Minuten für optimale Performance
- **Bei Problemen**: `session_cache.json` löschen und Browser neu starten
- **Stealth-Modus**: Automatische User-Agent-Rotation

### 4. **Variant-Optimierung**
- **Update-Frequenz**: Nicht öfter als alle 24 Stunden pro Produkt
- **Batch-Processing**: Mehrere Produkte gleichzeitig aktualisieren
- **Tracking-Strategie**: Nur relevante Varianten dauerhaft tracken

## 🔧 Erweiterte Features

### API-Endpunkte
- `GET /api/products` - Produktliste mit Pagination
- `POST /api/product/<id>/update` - Produkt und Varianten aktualisieren
- `POST /api/product/<id>/track` - Tracking aktivieren/deaktivieren
- `GET /api/product/<id>/price_history` - Preishistorie abrufen

### Datenexport
- **JSON**: Vollständige Datensicherung mit Metadaten
- **CSV**: Tabellenkalkulation-kompatibel
- **Automatisch**: Backup nach jedem Scraping-Vorgang

### Debugging
- `GET /debug/product/<id>` - Variant-Debug-Informationen
- Umfangreiche Console-Logs für Entwicklung
- Test-Skripte für Variant-System-Validierung

## 📜 Lizenz

Dieses Projekt steht unter der MIT-Lizenz – siehe [LICENSE](LICENSE).

## ⚠️ Hinweis

Dieses Tool dient ausschließlich zu Bildungszwecken. Nutzung auf eigene Verantwortung und unter Beachtung der AliExpress-Nutzungsbedingungen. Das Scraping sollte respektvoll und mit angemessenen Verzögerungen erfolgen.

## 🤝 Beitragen

Beiträge sind willkommen! Bitte erstellen Sie Issues für Bugs oder Feature-Requests, und Pull Requests für Code-Verbesserungen.

---

**Entwickelt mit ❤️ für die E-Commerce-Datenanalyse**