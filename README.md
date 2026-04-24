# Plate Solver Service

> Lean HTTP microservice for Astrometry.net plate solving. FastAPI wrapper around `solve-field` with optional PHP and Python clients. Runs locally, no external APIs.

Schlanker HTTP-Microservice, der Astroaufnahmen hochgeladen bekommt und RA, Dec, Rotation und Sichtfeld (FOV) zurückgibt. Basiert auf **Astrometry.net** (`solve-field`) mit einem **FastAPI**-Wrapper.

Alles lokal — keine externen APIs, keine API-Keys, kein Internet beim Solven nötig (nur einmalig beim Download der Index-Dateien).

---

## Quickstart

```bash
git clone https://github.com/DEIN-USER/plate-solver-service
cd plate-solver-service

sudo apt install astrometry.net astrometry-data-2mass-05 python3-venv
python3 -m venv venv && venv/bin/pip install -r requirements.txt

venv/bin/python app.py
# → curl http://127.0.0.1:8011/solve -F "file=@test.jpg"
```

Das reicht für einen ersten Test. Für produktive Setups siehe **[Installation](#installation-produktiv)** unten: systemd-Service, dedizierter Systembenutzer, passende Index-Dateien.

---

## Wer nutzt das?

Dieser Service wurde ursprünglich für den **[Sky Atlas](https://github.com/DEIN-USER/sky-atlas)** entwickelt, der beim Upload von Astrofotos automatisch deren Position bestimmt. Er ist aber stack-unabhängig — jede Anwendung mit HTTP-Client kann ihn ansprechen (PHP, Python, Node, curl, …).

---

## Projektstruktur

```
plate-solver-service/
├── app.py                      ← FastAPI-Microservice
├── solver.py                   ← solve-field Wrapper
├── requirements.txt            ← Python-Abhängigkeiten
├── systemd/
│   └── platesolve.service      ← systemd-Unit
├── examples/
│   └── client.php              ← PHP-Referenz-Client
└── README.md
```

---

## Systemvoraussetzungen

- Linux-Server (Debian / Ubuntu / Raspberry Pi OS / etc.)
- Python ≥ 3.9
- ca. 500 MB – 2 GB freier Speicher für Index-Dateien
- Root-Zugriff für die Installation der Systempakete

Getestet auf Ubuntu 22.04 (aarch64 und x86_64). Auf anderen Distributionen sind die Paketnamen ggf. anzupassen (`dnf install astrometry.net` auf Fedora etc.).

---

## Installation (produktiv)

### 1. Systemabhängigkeiten

```bash
sudo apt install astrometry.net python3-venv
```

### 2. Index-Dateien (Sternkataloge)

Astrometry.net benötigt vorkompilierte Index-Dateien, die "Skymarks" für die Objekterkennung enthalten. Jede Index-Datei ist für eine bestimmte **Quad-Größe** optimiert — diese sollte **10–100 %** des kleineren Bildfeldes betragen.

**Beispiel-Installation** für typische Astrofoto-Setups (Bildfeld ~30′–80′, z. B. Seestar S50, DWARF 3, kleine Refraktoren):

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

> **Wenn du unsicher bist**, installiere großzügig — überflüssige Index-Dateien verlangsamen das Solven nur geringfügig, fehlende verhindern es ganz.

### 3. Python-Umgebung

```bash
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

### 4. systemd-Service

Empfohlen: eigener unprivilegierter Systembenutzer.

```bash
sudo useradd --system --shell /usr/sbin/nologin --home-dir /opt/platesolve platesolve
sudo mkdir -p /opt/platesolve
sudo cp -r . /opt/platesolve/
sudo chown -R platesolve:platesolve /opt/platesolve
```

Service-Datei (im Repo unter `systemd/platesolve.service`) nach `/etc/systemd/system/` kopieren:

```bash
sudo cp systemd/platesolve.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now platesolve
sudo systemctl status platesolve
```

Inhalt `systemd/platesolve.service`:

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

Der Service bindet auf `127.0.0.1:8011` — **nicht** von außen erreichbar. Für Remote-Nutzung einen Reverse-Proxy (nginx/Apache) mit Authentifizierung vorschalten.

---

## API-Nutzung

### Endpoint

```
POST http://127.0.0.1:8011/solve
Content-Type: multipart/form-data
```

### Parameter

| Feld | Typ | Beschreibung |
|---|---|---|
| `file` | File | **Erforderlich.** JPG, PNG, TIFF oder FITS |
| `scale_low` | float | Untere Grenze Pixelskala in arcsec/px |
| `scale_high` | float | Obere Grenze Pixelskala in arcsec/px |
| `ra_hint` | float | RA-Hinweis in Grad J2000 |
| `dec_hint` | float | Dec-Hinweis in Grad J2000 |
| `radius_hint` | float | Suchradius in Grad (mit RA/Dec-Hint, Default 5°) |

Alle außer `file` sind optional. Je mehr Hints, desto schneller das Solve (Blind: bis 2 min, mit Skala: ~10–30 s, mit Position: oft < 10 s).

### Beispiele (curl)

```bash
# Blind solve
curl -s -X POST http://127.0.0.1:8011/solve \
     -F "file=@test.jpg" | python3 -m json.tool

# Mit Pixelskala-Hints
curl -s -X POST http://127.0.0.1:8011/solve \
     -F "file=@test.jpg" \
     -F "scale_low=2.0" \
     -F "scale_high=2.8" | python3 -m json.tool

# Mit Positionshinweis (am schnellsten)
curl -s -X POST http://127.0.0.1:8011/solve \
     -F "file=@test.jpg" \
     -F "scale_low=2.0" \
     -F "scale_high=2.8" \
     -F "ra_hint=83.82" \
     -F "dec_hint=-5.39" \
     -F "radius_hint=5" | python3 -m json.tool
```

### Response

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

| Feld | Bedeutung |
|---|---|
| `ra` | Rektaszension Bildmitte, Grad J2000 |
| `dec` | Deklination Bildmitte, Grad J2000 |
| `rotation` | Positionswinkel Nord, Grad |
| `scale_arcsec_per_px` | Pixelskala in arcsec/px |
| `fov_width_deg` | Gesichtsfeld Breite in Grad |
| `fov_height_deg` | Gesichtsfeld Höhe in Grad |

Bei Fehler liefert der Service HTTP 4xx/5xx mit JSON-Body `{"detail": "…"}` oder `{"error": "…"}`.

---

## Pixelskala berechnen

```
Pixelskala [arcsec/px] = (FOV_Breite [°] × 3600) / Bildbreite [px]
```

**Beispiel:** 1080 × 1920 px Sensor mit ~0.72° × 1.27° FOV:

```
0.72 × 3600 / 1080 ≈ 2.4 arcsec/px
→ scale_low=2.0  scale_high=2.8
```

Online-Rechner für Teleskop-/Kamera-Kombinationen: [astronomy.tools/calculators/field_of_view](https://astronomy.tools/calculators/field_of_view).

---

## Beispiel-Integration (PHP)

Der Referenz-Client liegt unter `examples/client.php`:

```php
require_once 'examples/client.php';

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
    echo 'Fehler: ' . $e->getMessage();
}
```

### Timeouts für PHP-Clients

Der mitgelieferte Client wartet standardmäßig **180 Sekunden**. `max_execution_time` (PHP) und das Server-Timeout (Apache/nginx) müssen **mindestens so hoch** sein:

```ini
; php.ini
max_execution_time = 180
```

```apache
# Apache
Timeout 300
```

---

## Beispiel-Integration (Python)

```python
import requests

with open('test.jpg', 'rb') as f:
    r = requests.post(
        'http://127.0.0.1:8011/solve',
        files={'file': f},
        data={
            'scale_low':  2.0,
            'scale_high': 2.8,
            'ra_hint':    83.82,
            'dec_hint':  -5.39,
        },
        timeout=180,
    )

r.raise_for_status()
result = r.json()
print(f"RA {result['ra']:.4f}  Dec {result['dec']:.4f}")
```

---

## Betrieb & Wartung

```bash
# Logs live verfolgen
journalctl -u platesolve -f

# Service neu starten (z. B. nach Änderungen an app.py)
sudo systemctl restart platesolve

# Service stoppen
sudo systemctl stop platesolve

# Temporäre Bilder aufräumen (images/ wächst unbegrenzt)
find /opt/platesolve/images/ -type f -mtime +30 -delete
```

Den Cleanup als systemd-Timer automatisieren oder per Cron.

---

## Troubleshooting

**"Connection refused" / Service nicht erreichbar**
- Läuft `platesolve.service`? → `sudo systemctl status platesolve`
- Bindet er auf 127.0.0.1:8011? → `ss -tlnp | grep 8011`
- Logs: `journalctl -u platesolve -n 50`

**"Kein Match gefunden" bei bekannt gutem Bild**
- Passende Index-Dateien installiert? → `apt list --installed | grep astrometry-data`
- Pixelskala korrekt geschätzt? → siehe [Pixelskala berechnen](#pixelskala-berechnen)
- Bildfeld zu klein/groß für vorhandene Quads? → zusätzliche Index-Dateien von [data.astrometry.net](https://data.astrometry.net/) laden

**Solve dauert > 2 Minuten**
- Ohne Hints ist Blind-Solve langsam. Pixelskala-Hints bringen Faktor 5–10, Positions-Hints nochmal Faktor 10.
- Zu viele Index-Dateien geladen? Aufräumen kann helfen.

---

## Referenzen

- [Astrometry.net Code README](https://astrometry.net/doc/readme.html) — Offizielle Dokumentation
- [Index-Dateien-Download](https://data.astrometry.net/) — Alle Serien und Skalen
- [GitHub: dstndstn/astrometry.net](https://github.com/dstndstn/astrometry.net) — Quellcode
- Lang, D. et al. (2010): *Astrometry.net: Blind astrometric calibration of arbitrary astronomical images*, AJ 137, 1782–1800 — [arXiv:0910.2233](https://arxiv.org/abs/0910.2233)

---

## Lizenz

MIT — siehe [LICENSE](LICENSE).

Astrometry.net selbst steht unter BSD-3 und muss bei wissenschaftlicher Nutzung zitiert werden (siehe obiges Paper).
