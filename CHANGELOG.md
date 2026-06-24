# Changelog

Tutte le modifiche rilevanti sono documentate in questo file.
Formato basato su [Keep a Changelog](https://keepachangelog.com/it/1.0.0/),
versioning secondo [Semantic Versioning](https://semver.org/lang/it/).

---

## [1.1.0] — 2026-06-24

### Aggiunto
- **Cancellazione elaborazione**: bottone "Annulla" nella status bar per interrompere la
  pipeline tra uno step e l'altro (VAD → embedding → clustering → trascrizione) senza
  chiudere l'applicazione.

### Migliorato
- **Prestazioni assegnazione speaker**: `_merge_speakers` riscritta con `bisect` — complessità
  O(n log m) invece di O(n×m); su riunioni lunghe con molti segmenti il costo è trascurabile.
- **Riuso del modello Whisper tra run**: `Transcriber` ora cachato a livello di classe; cambiare
  lingua o prompt non provoca il ricaricamento del modello da disco.

### Corretto
- **`_load()` in VAD e SpeakerEmbedder**: restituisce ora il tipo concreto (`VAD` /
  `EncoderClassifier`) eliminando il narrowing implicito post-assert che causava warning
  statici con mypy/pyright.
- **Import inutilizzati rimossi**: `from pathlib import Path` eliminato da `vad.py` e
  `speaker.py` dopo la centralizzazione di `CACHE_DIR` in `utils/paths.py`.
- **`sd.query_devices` in recorder widget**: ripristinato `.get()` (più robusto con oggetti
  dict-like di sounddevice) al posto del check `isinstance(dev, dict)`.
- **`initial_prompt` con fallback difensivo**: se faster-whisper cambia la struttura interna
  di `model.options`, il codice tenta automaticamente il kwarg diretto prima di propagare
  l'errore.

### Refactor
- `CACHE_DIR` centralizzato in `minute_meeting/utils/paths.py` (era duplicato in `vad.py`
  e `speaker.py`).

---

## [1.0.0] — 2026-06-24

### Aggiunto
- **Dark mode adattivo**: rileva automaticamente il tema di sistema (chiaro/scuro) tramite
  `QGuiApplication.styleHints().colorScheme()` (Qt ≥ 6.5) con fallback sulla luminosità
  della palette per versioni precedenti. Il tema commuta live senza riavvio.
- **Registrazione audio di sistema su macOS**: cattura loopback via BlackHole virtual audio
  driver; il widget di registrazione mostra lo stato del loopback nella status bar.
- **Stima tempo rimanente durante la trascrizione**: calcola l'ETA in base alla durata
  dell'audio e al numero di core CPU, aggiornata ad ogni step della pipeline. Al termine
  viene mostrato il tempo totale impiegato.
- **Test di integrazione loopback**: suite di test per la scoperta del dispositivo loopback
  su macOS, Linux e Windows, senza hardware audio richiesto.

### Corretto
- **Level meter microfono sempre al massimo**: il RMS veniva calcolato su dati `int16` grezzi
  (range 0–32 768) ma scalato con un fattore progettato per float normalizzati; qualsiasi
  voce udibile mandava il cursore al 100%. Ora normalizzato a float32 `[-1, 1]` con scala
  `× 50 000` (voce a −20 dBFS → 50% della barra).
- **Installazione ffmpeg in CI su Windows**: sostituito `choco install ffmpeg` (feed
  Chocolatey instabile) con l'action `FedericoCarboni/setup-ffmpeg@v3`.
- **Permessi GitHub Actions per la creazione di release**: aggiunto `contents: write`
  al job di build per consentire a `softprops/action-gh-release` di pubblicare la release.

### Modificato
- **`pyproject.toml` migrato a PEP 621**: metadati di progetto nel formato standard;
  dipendenze allineate alle specifiche di Poetry 1.8+.
- Il QSS viene ora applicato a livello `QApplication` (non solo `QMainWindow`), così
  il tema si propaga anche ai dialog (impostazioni, export, messaggi di errore).

---

## [0.1.0] — 2026-06-22

Rilascio iniziale.

### Aggiunto
- Trascrizione audio/video con WhisperX e allineamento a livello di parola.
- Diarizzazione speaker con SpeechBrain VAD + ECAPA-TDNN + AgglomerativeClustering.
- Riduzione del rumore opzionale via `noisereduce`.
- Estrazione audio da file video (MP4, MKV, AVI, MOV, WebM) tramite ffmpeg.
- Registrazione microfono live con `sounddevice`.
- Interfaccia grafica PySide6 con progress bar, transcript colorato per speaker ed export testo.
- Build Windows con PyInstaller + Inno Setup tramite GitHub Actions.
- Supporto modelli Whisper: `base`, `small`, `medium`, `large-v3`.
- Rilevamento automatico lingua o selezione manuale (14 lingue).
- Prompt iniziale configurabile per migliorare l'accuratezza della trascrizione.
