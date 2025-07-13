# AliExpress Product Scraper

Ein leistungsstarkes und benutzerfreundliches Web-Interface zum Scrapen von Produktdaten von AliExpress über deren inoffizielle API.

![MIT License](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)

## Screenshots

### Such-Interface
![Search Interface](screenshots/Capture1.PNG)

### Ergebnisse und Feldauswahl
![Field Selection and Results](screenshots/Capture.PNG)

## Features

- 🌐 **Web-Oberfläche**: Intuitive UI für einfache Bedienung
- 🚀 **API-basiertes Scraping**: Schnelle und effiziente Datenerfassung über die AliExpress-API
- 🔒 **Intelligentes Session-Management**: Browser-Automatisierung nur für initiale Cookie-Erfassung
- 🛡️ **Anti-Block-Schutz**: 
  - Konfigurierbare Verzögerung zwischen Anfragen (0,2–10 Sekunden)
  - Serielle Verarbeitung zur Vermeidung von Blockaden
  - Session-Caching zur Minimierung von Browser-Automatisierung
- 📊 **Flexible Datenexporte**:
  - JSON-Format für vollständige Datensicherung
  - CSV-Format für Tabellenkalkulationen
- 🎯 **Feldauswahl**: Exakte Auswahl der zu extrahierenden Produktdetails
- 🔍 **Erweiterte Filter**:
  - Preisbereich
  - Rabatt-Deals
  - Kostenloser Versand
- 📝 **Echtzeit-Logging**: Live-Log der Scraping-Prozesse
- ⏰ **Automatisches Scraping**: Zeitgesteuerte Aktualisierung und Keyword-basierte Überwachung

## Projektstruktur

- `app.py` – Flask Web-App mit Datenbankintegration
- `scraper.py` – Zentrale Scraping-Logik und AliExpress-API
- `models.py` – SQLAlchemy Datenbankmodelle
- `scheduler.py` – Automatisches, zeitgesteuertes Scraping
- `templates/` – Jinja2-Templates für die Weboberfläche
- `results/` – Exportierte CSV- und JSON-Dateien
- `instance/aliexpress_scraper.db` – SQLite-Datenbankdatei
- `session_cache.json` – Zwischengespeicherte Sessiondaten

## Installation

1. Repository klonen:
```bash
git clone https://github.com/hendkai/aliexpress-scraper.git
cd aliexpress-scraper
```

2. Abhängigkeiten installieren:
```bash
pip install -r requirements.txt
```

## Nutzung

1. Web-Oberfläche starten:
```bash
python app.py
```

2. Im Browser öffnen:
```
http://localhost:5000
```

3. In der Weboberfläche:
   - Suchbegriff eingeben
   - Anzahl der zu scrapenden Seiten wählen (1–60)
   - Felder auswählen
   - Optionale Filter setzen (Preis, Rabatt, Versand)
   - Anfrageverzögerung einstellen (empfohlen: 1 Sekunde)
   - Scraping starten und Fortschritt beobachten

4. Ergebnisse werden im Ordner `results/` gespeichert als:
   - `aliexpress_[keyword]_extracted.json`
   - `aliexpress_[keyword]_extracted.csv`

## Automatisches Scraping

Das System unterstützt zeitgesteuertes, automatisches Scraping über den eingebauten Scheduler (`scheduler.py`).
- Keywords können mit Intervall gepflegt werden (z.B. alle 6h).
- Preisverläufe und neue Produkte werden automatisch aktualisiert.
- Verwaltung und Statusanzeige über die Weboberfläche unter "Settings".

## Datenbankstruktur (Kernmodelle)

- **Product**: Produktdaten, Varianten, Shop, Preis, Status, Tracking
- **PriceHistory**: Historische Preisverläufe
- **SearchKeyword**: Überwachte Suchbegriffe und deren Intervalle
- **ScrapingLog**: Protokollierung aller Scraping-Aktivitäten

## Verfügbare Felder

- Product ID
- Title
- Sale Price
- Original Price
- Discount (%)
- Currency
- Rating
- Orders Count
- Store Name
- Store ID
- Store URL
- Product URL
- Image URL

## Best Practices

1. **Anfrageverzögerung**:
   - Standard: 1 Sekunde zwischen Anfragen
   - Niedrigere Werte (0,2–0,5s) erhöhen das Blockier-Risiko
2. **Seitenanzahl**:
   - Maximal: 60 Seiten pro Suche
   - Mit Filtern gezielter suchen
3. **Session-Management**:
   - Sessiondaten werden 30 Minuten zwischengespeichert
   - Bei Problemen Cookies löschen und Browser neu starten

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz – siehe [LICENSE](LICENSE).

## Hinweis

Dieses Tool dient ausschließlich zu Bildungszwecken. Nutzung auf eigene Verantwortung und unter Beachtung der AliExpress-Nutzungsbedingungen. 