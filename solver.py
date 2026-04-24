"""
solver.py – Wrapper um astrometry.net solve-field
Gibt RA, Dec, Rotation, Pixelskala und FOV zurück.
"""

import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


# ── Standardwerte ────────────────────────────────────────────────────────────

SCALE_LOW  = 1.5    # arcsec/px – untere Grenze (konservativ für unbekannte Bilder)
SCALE_HIGH = 3.5    # arcsec/px – obere Grenze
CPU_LIMIT  = 120    # Sekunden bis Abbruch

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".fits", ".fit", ".fts", ".tiff", ".tif"}


class SolveError(Exception):
    """Wird geworfen wenn Plate Solving fehlschlägt."""
    pass


# ── Interne Hilfsfunktionen ──────────────────────────────────────────────────

def _parse_wcs(wcs_path: Path, img_w: int, img_h: int) -> dict:
    """Liest WCS via astropy – robust gegenüber FITS-Formatvarianten."""
    from astropy.io import fits

    with fits.open(wcs_path) as hdul:
        h = hdul[0].header
        try:
            crval1 = float(h['CRVAL1'])
            crval2 = float(h['CRVAL2'])
            cd1_1  = float(h['CD1_1'])
            cd1_2  = float(h['CD1_2'])
            cd2_1  = float(h['CD2_1'])
            cd2_2  = float(h['CD2_2'])
        except KeyError as e:
            raise SolveError(f"WCS-Key fehlt: {e}")

    scale_deg    = math.sqrt(cd1_1**2 + cd1_2**2)
    scale_arcsec = scale_deg * 3600.0
    rotation     = math.degrees(math.atan2(cd1_2, -cd1_1))

    return {
        "ra":                  round(crval1, 6),
        "dec":                 round(crval2, 6),
        "rotation":            round(rotation, 3),
        "scale_arcsec_per_px": round(scale_arcsec, 4),
        "fov_width_deg":       round(scale_deg * img_w, 5),
        "fov_height_deg":      round(scale_deg * img_h, 5),
    }


def _image_size_pil(path: Path) -> tuple[int, int]:
    """Gibt (width, height) via Pillow zurück."""
    from PIL import Image
    with Image.open(path) as img:
        return img.size


def _image_size_fits(path: Path) -> tuple[int, int]:
    """Gibt (width, height) eines FITS-Bildes zurück."""
    from astropy.io import fits
    with fits.open(path) as hdul:
        h = hdul[0].header
        return int(h["NAXIS1"]), int(h["NAXIS2"])


def _to_jpeg(src: Path, dst: Path) -> None:
    """Konvertiert ein beliebiges Bild nach JPEG (RGB, 95% Qualität)."""
    from PIL import Image
    with Image.open(src) as img:
        img.convert("RGB").save(dst, "JPEG", quality=95)


# ── Öffentliche API ──────────────────────────────────────────────────────────

def solve(
    image_path: str | Path,
    scale_low:  float = SCALE_LOW,
    scale_high: float = SCALE_HIGH,
    ra_hint:    Optional[float] = None,
    dec_hint:   Optional[float] = None,
    radius:     Optional[float] = None,
) -> dict:
    """
    Führt astrometry.net Plate Solving für eine Bilddatei durch.

    Args:
        image_path:  Pfad zur Bilddatei (.jpg, .png, .fits, .tiff …)
        scale_low:   Untere Pixelskala in arcsec/px (default 1.5)
        scale_high:  Obere Pixelskala in arcsec/px (default 3.5)
        ra_hint:     Optionaler RA-Startwert in Grad J2000 (beschleunigt Suche)
        dec_hint:    Optionaler Dec-Startwert in Grad J2000
        radius:      Suchradius in Grad (nur sinnvoll mit ra_hint/dec_hint)

    Returns:
        {
          ra, dec,                    # Bildmitte, Grad J2000
          rotation,                   # Positionswinkel Nord, Grad
          scale_arcsec_per_px,        # Pixelskala
          fov_width_deg,              # Gesichtsfeld Breite
          fov_height_deg,             # Gesichtsfeld Höhe
        }

    Raises:
        SolveError: solve-field nicht gefunden, Datei ungültig oder kein Match
    """
    if not shutil.which("solve-field"):
        raise SolveError(
            "solve-field nicht gefunden. "
            "Installation: sudo apt install astrometry.net"
        )

    src = Path(image_path).resolve()
    if not src.exists():
        raise SolveError(f"Datei nicht gefunden: {src}")

    suffix = src.suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise SolveError(f"Nicht unterstütztes Format: {suffix}")

    with tempfile.TemporaryDirectory(prefix="platesolve_") as tmpdir:
        tmp = Path(tmpdir)
        is_fits = suffix in (".fits", ".fit", ".fts")

        # Bildgröße ermitteln & ggf. nach JPEG konvertieren
        try:
            if is_fits:
                img_w, img_h = _image_size_fits(src)
                work_file = tmp / "input.fits"
                shutil.copy(src, work_file)
            else:
                img_w, img_h = _image_size_pil(src)
                work_file = tmp / "input.jpg"
                _to_jpeg(src, work_file)
        except Exception as e:
            raise SolveError(f"Bildverarbeitung fehlgeschlagen: {e}")

        cmd = [
            "solve-field",
            "--no-plots",
            "--overwrite",
            "--dir",         str(tmp),
            "--scale-units", "arcsecperpix",
            "--scale-low",   str(scale_low),
            "--scale-high",  str(scale_high),
            "--downsample",  "2",
            "--cpulimit",    str(CPU_LIMIT),
            str(work_file),
        ]

        if ra_hint is not None and dec_hint is not None:
            cmd += ["--ra", str(ra_hint), "--dec", str(dec_hint)]
            if radius is not None:
                cmd += ["--radius", str(radius)]

        proc = subprocess.run(cmd, capture_output=True, text=True)

        wcs_file = tmp / "input.wcs"
        if not wcs_file.exists():
            log_tail = (proc.stdout + proc.stderr)[-600:]
            raise SolveError(f"Kein Match gefunden.\n\n{log_tail}")

        return _parse_wcs(wcs_file, img_w, img_h)
