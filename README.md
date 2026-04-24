# Plate Solver Microservice

Optionaler Microservice für Sky Atlas, der beim Bild-Upload automatisch die Position, Rotation und das Sichtfeld einer Astroaufnahme bestimmt. Basiert auf **Astrometry.net** (`solve-field`) mit einem schlanken **FastAPI**-Wrapper und einem **PHP-Client**.

Alles lokal — keine externen APIs, keine API-Keys, kein Internet beim Solven nötig (nur einmalig beim Download der Index-Dateien).

---

## Systemvoraussetzungen

- Linux-Server (Debian / Ubuntu / Raspberry Pi OS / etc.)
- Python ≥ 3.9
- PHP ≥ 8.0 mit `curl`-Extension (für den Client)
- ca. 500 MB – 2 GB freier Speicher für Index-Dateien (abhängig vom Bildfeld)
- Root-Zugriff für die Installation der Systempakete

Getestet wurde das Setup auf Ubuntu 22.04 (aarch64 und x86_64). Auf anderen Distributionen sind die Paketnamen ggf. anzupassen (`dnf install astrometry.net` auf Fedora etc.).

---

## 1. Systemabhängigkeiten

### 1.1 Astrometry.net

```bash
sudo apt install astrometry.net python3-venv
```

### 1.2 Index-Dateien (Sternkataloge)

Astrometry.net benötigt vorkompilierte Index-Dateien, die "Skymarks" für die Objekterkennung enthalten. Jede Index-Datei ist für eine bestimmte **Quad-Größe** optimiert — diese sollte **10–100 %** des kleineren Bildfeldes betragen.

**Beispiel-Installation** für typische Astrofoto-Setups (Bildfeld ~30′ – 80′, z. B. Seestar S50, DWARF 3, kleine Refraktoren):

```bash
sudo apt install astrometry-data-2mass-04   # Quads  8'–11'
sudo apt install astrometry-data-2mass-05   # Quads 11'–16'
sudo apt install astrometry-data-2mass-06   # Quads 16'–22'
sudo apt install astrometry-data-2mass-07   # Quads 22'–30'
sudo apt install astrometry-data-tycho2-08  # Quads 30'–44'
sudo apt install astrometry-data-tycho2-09  # Quads 44'–60'
```

#### Welche Quads brauche ich?

Die apt-Pakete decken nur einen Teil der verfügbaren Skalen ab. Für Weitwinkelaufnahmen (≥ 1°) oder sehr schmale Felder (< 5′) müssen Index-Dateien direkt heruntergeladen werden:

**🔗 https://data.astrometry.net/** — offizielle Quelle mit allen Serien und Skalen

Die wichtigsten Serien im Überblick:

| Serie | Katalog | Empfohlen für |
|---|---|---|
| `4100` | Tycho-2 | Bilder > 1° (Weitwinkel, Großfeld) |
| `4200` | 2MASS | Allrounder, alle Skalen 0–19 verfügbar |
| `5200 LIGHT` | Tycho-2 + Gaia DR2 | Bilder < 1° (**empfohlen** für DSO-Aufnahmen) |
| `5200 HEAVY` | wie LIGHT + Gaia-Metadaten | wie LIGHT, zusätzlich mit Stern-Magnituden |

**Skala-zu-Bildgröße-Faustregel** (jede Stufe ≈ √2):

| Skalen-Nr. | Quad-Größe | Passt zu Bildbreite |
|---|---|---|
| 0 | 2–2.8′ | ~6′ |
| 2 | 4–5.6′ | ~12′ |
| 4 | 8–11′ | ~24′ |
| 5 | 11–16′ | ~30–45′ |
| 6 | 16–22′ | ~1° |
| 7 | 22–30′ | ~1–1.5° |
| 8 | 30–42′ | ~2° |
| 10 | 60–85′ | ~4° |
| 12 | 120–170′ | ~8° |

**Auswahlregel:** Lade Index-Dateien mit Quad-Größen zwischen 10 % und 100 % deines Bildfeldes. Für ein 1°-Bild (60′) wären das also Skalen 3 bis 9.

Weitere Details und die vollständige Skalen-Tabelle: **[astrometry.net/doc/readme.html](https://astrometry.net/doc/readme.html)**

> **Wenn du unsicher bist**, installiere großzügig — überflüssige Index-Dateien verlangsamen das Solven nur geringfügig, fehlende verhindern es ganz. Beim Blind-Solve ohne Positionshinweis sollten die vermuteten Skalen inklusive je einer Stufe darüber und darunter vorhanden sein.

---

## 2. Projektverzeichnis

Empfohlene Struktur (Pfad frei wählbar, hier `/opt/platesolve` als Beispiel):

```
/opt/platesolve/
├── app.py              ← FastAPI-Microservice
├── solver.py           ← solve-field Wrapper
├── requirements.txt    ← Python-Abhängigkeiten
├── platesolve.php      ← PHP-Client für die Web-Anwendung
├── images/             ← Temporäre Bilddaten (auto-erstellt)
└── venv/               ← Python-Umgebung (nach Setup)
```

Legge das Verzeichnis an und übernimm die Dateien aus dem Repository:

```bash
sudo mkdir -p /opt/platesolve
sudo chown $USER:$USER /opt/platesolve
cd /opt/platesolve
# app.py, solver.py, requirements.txt, platesolve.php hierher kopieren
```

---

## 3. Python-Umgebung einrichten

```bash
cd /opt/platesolve

python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
```

Inhalt `requirements.txt`:

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
astropy==6.1.0
Pillow==10.3.0
```

---

## 4. systemd-Service

Empfohlen: eigener unprivilegierter Systembenutzer für den Service.

```bash
sudo useradd --system --shell /usr/sbin/nologin --home-dir /opt/platesolve platesolve
sudo chown -R platesolve:platesolve /opt/platesolve
```

Service-Datei nach `/etc/systemd/system/platesolve.service`:

```ini
[Unit]
Description=Plate Solver Microservice
After=network.target

[Service]
Type=simple
User=platesolve
Group=platesolve
WorkingDirectory=/opt/platesolve
ExecStart=/opt/platesolve/venv/bin/python app.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=platesolve
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

Aktivieren und starten:

```bash
sudo systemctl daemon-reload
sudo systemctl enable platesolve
sudo systemctl start platesolve

# Status prüfen
sudo systemctl status platesolve
```

Der Service bindet auf `127.0.0.1:8011` — **nicht** von außen erreichbar. Für Remote-Nutzung einen Reverse-Proxy (nginx/Apache) mit Auth vorschalten.

---

## 5. Manueller Test (curl)

```bash
# Minimal – Blind Solve (langsam, bis zu 2 min)
curl -s -X POST http://127.0.0.1:8011/solve \
     -F "file=@/pfad/zum/bild.jpg" | python3 -m json.tool

# Mit Pixelskala-Hints (deutlich schneller)
curl -s -X POST http://127.0.0.1:8011/solve \
     -F "file=@/pfad/zum/bild.jpg" \
     -F "scale_low=2.0" \
     -F "scale_high=2.8" | python3 -m json.tool

# Mit Positionshinweis (am schnellsten, meist < 10 s)
curl -s -X POST http://127.0.0.1:8011/solve \
     -F "file=@/pfad/zum/bild.jpg" \
     -F "scale_low=2.0" \
     -F "scale_high=2.8" \
     -F "ra_hint=83.82" \
     -F "dec_hint=-5.39" \
     -F "radius_hint=5" | python3 -m json.tool
```

Beispielantwort:

```json
{
    "ok": true,
    "original": "test.jpg",
    "ra": 154.49624,
    "dec": 21.728935,
    "rotation": 12.773,
    "scale_arcsec_per_px": 2.3739,
    "fov_width_deg": 0.71217,
    "fov_height_deg": 1.26609
}
```

| Feld                  | Bedeutung                           |
|-----------------------|-------------------------------------|
| `ra`                  | Rektaszension Bildmitte, Grad J2000 |
| `dec`                 | Deklination Bildmitte, Grad J2000   |
| `rotation`            | Positionswinkel Nord, Grad          |
| `scale_arcsec_per_px` | Pixelskala in arcsec/px             |
| `fov_width_deg`       | Gesichtsfeld Breite in Grad         |
| `fov_height_deg`      | Gesichtsfeld Höhe in Grad           |

---

## 6. Pixelskala berechnen

```
Pixelskala [arcsec/px] = (FOV_Breite [°] × 3600) / Bildbreite [px]
```

**Beispiel:** 1080 × 1920 px Sensor mit ~0.72° × 1.27° FOV:

```
0.72 × 3600 / 1080 ≈ 2.4 arcsec/px
→ scale_low=2.0  scale_high=2.8
```

Richtwerte für gängige Teleskop-/Kamera-Kombinationen findet man oft in den Datenblättern der Hersteller oder per Online-Rechner wie [astronomy.tools/calculators/field_of_view](https://astronomy.tools/calculators/field_of_view).

---

## 7. PHP-Integration

`platesolve.php` in die Web-Anwendung einbinden:

```php
require_once '/opt/platesolve/platesolve.php';

try {
    $result = platesolve(
        '/absoluter/pfad/zum/bild.jpg',
        scaleLow:   2.0,   // optional
        scaleHigh:  2.8,   // optional
        raHint:     83.82, // optional – beschleunigt Suche erheblich
        decHint:   -5.39,  // optional
        radiusHint: 5.0,   // optional – Suchradius in Grad
    );

    echo $result['ra'];                  // 83.822134
    echo $result['dec'];                 // -5.391234
    echo $result['rotation'];            // 12.34
    echo $result['scale_arcsec_per_px']; // 2.4012
    echo $result['fov_width_deg'];       // 0.7204
    echo $result['fov_height_deg'];      // 1.2808

} catch (RuntimeException $e) {
    // Fehlermeldung aus dem Microservice (nicht erreichbar,
    // kein Match, HTTP-Fehler, etc.)
    echo 'Fehler: ' . $e->getMessage();
}
```

### Timeouts

Der PHP-Client wartet standardmäßig **180 Sekunden**. `max_execution_time` (PHP) und das Server-Timeout (Apache/nginx) müssen **mindestens so hoch** sein, sonst bricht die Verbindung vorzeitig ab.

```ini
; php.ini
max_execution_time = 180
```

```apache
# Apache
Timeout 300
```

---

## 8. Betrieb & Wartung

```bash
# Logs live verfolgen
journalctl -u platesolve -f

# Service neu starten (z. B. nach Änderungen an app.py)
sudo systemctl restart platesolve

# Service stoppen
sudo systemctl stop platesolve

# Alte Bilder aufräumen (images/ wächst unbegrenzt)
find /opt/platesolve/images/ -type f -mtime +30 -delete
```

Als systemd-Timer automatisieren (Datei `/etc/systemd/system/platesolve-cleanup.timer` + passender Service) oder klassisch per Cron.

---

## Troubleshooting

**"Service nicht erreichbar"**
- Läuft `platesolve.service`? → `sudo systemctl status platesolve`
- Bindet er auf 127.0.0.1:8011? → `ss -tlnp | grep 8011`

**"Kein Match gefunden" bei bekannt gutem Bild**
- Passende Index-Dateien installiert? → `apt list --installed | grep astrometry-data`
- Pixelskala korrekt geschätzt? → siehe Abschnitt 6
- Bildfeld zu klein/groß für vorhandene Quads? → zusätzliche Index-Dateien von [data.astrometry.net](https://data.astrometry.net/) laden

**Solve dauert > 2 Minuten**
- Ohne Hints ist Blind-Solve langsam. Pixelskala-Hints bringen Faktor 5–10, Positions-Hints nochmal Faktor 10.
- Zu viele Index-Dateien geladen? Engine lädt nur die passenden — aber mehr Skalen = mehr Kandidaten. Aufräumen hilft.

---

## Referenzen

- [Astrometry.net Code README](https://astrometry.net/doc/readme.html) — Offizielle Dokumentation
- [Index-Dateien-Download](https://data.astrometry.net/) — Alle Serien und Skalen
- [GitHub: dstndstn/astrometry.net](https://github.com/dstndstn/astrometry.net) — Quellcode
- Lang, D. et al. (2010): *Astrometry.net: Blind astrometric calibration of arbitrary astronomical images*, AJ 137, 1782–1800 — [arXiv:0910.2233](https://arxiv.org/abs/0910.2233)
