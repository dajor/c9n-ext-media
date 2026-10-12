# c9n-ext-media

ffmpeg, Tesseract, poppler und qpdf als optionale Erweiterung für c9n (Video, Audio, Texterkennung, PDF).

Diese Erweiterung wird getrennt vom c9n-Kern gebaut und hat **eine eigene Version** (Tags `v<version>`, Datei `VERSION`).
Sie läuft als eigener Dienst und wird in c9n unter *Einstellungen → Erweiterungen* aktiviert, aktualisiert,
ausgeschaltet und entfernt. Jedes Release enthält ein Image-Archiv, `extension.json` und `SHA256SUMS`;
c9n prüft Prüfsumme, Image-Kennung, Version und Verträglichkeit, bevor es etwas startet.

## Aufbau
- `server.py`: HTTP-Dienst auf Port 9301 unter `/<Token>/` (Token: `C9N_EXT_TOKEN`): `ocr`, `exec` (Allowlist: ffmpeg, ffprobe, tesseract, pdftotext, pdftoppm, pdfinfo, qpdf), `health`.
- Arbeitet auf dem gemeinsamen Datenordner `/data` (c9n erklärt das im Manifest: `service.shared_data`); eigener Zustand in `/state`.
- `tests/test_server.py`: Regeln der Ablehnung (Pfade, Netzwerk, Werkzeuge, Token).
- `scripts/smoke.py`: Beweis im laufenden Container (OCR, ffmpeg, poppler, qpdf, Ablehnungen).
- `.github/workflows/release.yml`: testet, baut, prüft, verpackt; Modus `publish` veröffentlicht das Release.

## Neue Version
`VERSION` und `RELEASE_NOTES.md` (erste Zeile `# c9n-ext-media <Version>`) ändern, dann den Workflow *Release* mit Modus `publish` starten.
