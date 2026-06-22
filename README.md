# MinuteMeeting

Applicazione desktop per la generazione automatica di verbali di riunione con trascrizione, allineamento temporale e riconoscimento automatico degli speaker.

## Funzionalità

- Registrazione audio dal microfono in tempo reale
- Importazione di file audio (WAV, MP3, FLAC, OGG) e video (MP4, MKV, AVI, MOV)
- Trascrizione con allineamento a livello di parola (WhisperX + faster-whisper)
- Rilevamento dell'attività vocale (SpeechBrain VAD)
- Identificazione automatica degli speaker (ECAPA-TDNN + clustering)
- Visualizzazione colorata per speaker con esportazione in testo
- **Pannello impostazioni** con selezione del modello Whisper, lingua e contesto iniziale
- Build Windows come installer `.exe` via GitHub Actions + Inno Setup

---

## Prerequisiti di sistema

| Strumento | Versione | Ruolo |
|-----------|----------|-------|
| Python | 3.10 – 3.12 | Runtime (3.13+ non supportato dai pacchetti ML) |
| Poetry | 1.8+ | Gestione dipendenze |
| Git | qualsiasi | Installazione di WhisperX da GitHub |
| ffmpeg | qualsiasi | Estrazione traccia audio da file video |

### Python 3.10 – 3.12

**macOS**
```bash
brew install pyenv
pyenv install 3.12.9
pyenv local 3.12.9
```

**Linux (Ubuntu/Debian)**
```bash
sudo apt update && sudo apt install -y build-essential libssl-dev zlib1g-dev \
     libbz2-dev libreadline-dev libsqlite3-dev curl git
curl https://pyenv.run | bash
pyenv install 3.12.9
pyenv local 3.12.9
```

**Windows** — scarica l'installer ufficiale da https://www.python.org/downloads/ (scegli 3.10–3.12), oppure:
```powershell
winget install pyenv-win
pyenv install 3.12.9
pyenv local 3.12.9
```

### Poetry

```bash
# macOS / Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

### ffmpeg

| OS | Comando |
|----|---------|
| macOS | `brew install ffmpeg` |
| Ubuntu/Debian | `sudo apt install ffmpeg` |
| Windows | `winget install Gyan.FFmpeg` |

> Su Windows, dopo l'installazione, verifica che la cartella `bin` di ffmpeg sia nel `PATH` di sistema e riavvia il terminale.

---

## Installazione per sviluppo

```bash
git clone https://github.com/pbellagente/MinuteMeeting.git
cd MinuteMeeting
poetry install
poetry run minute-meeting
```

> La prima esecuzione scarica automaticamente i pesi pre-addestrati di WhisperX e SpeechBrain (1–3 GB in `~/.cache`). Assicurati di avere spazio sufficiente e connessione stabile.

### Apple Silicon

`torch` viene installato da PyPI con il backend Metal già integrato. Tuttavia né SpeechBrain né WhisperX/ctranslate2 supportano MPS: entrambi i backend girano su CPU su Apple Silicon.

### GPU NVIDIA (CUDA)

Dopo `poetry install`, sostituisci torch con la variante CUDA:
```bash
poetry run pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```
Sostituisci `cu121` con la versione CUDA del tuo sistema.

---

## Impostazioni

Le preferenze si configurano direttamente nell'interfaccia:

**Barra degli strumenti → Impostazioni…** (Ctrl+,)

| Impostazione | Valori | Default |
|---|---|---|
| Modello Whisper | base / **small** / medium / large-v3 | small |
| Lingua | Auto-rileva / it / en / fr / de / … | Auto-rileva |
| Contesto | Testo libero (≤ 900 caratteri) | vuoto |
| Riduzione rumore | on / **off** | off |

Le preferenze vengono salvate automaticamente tra una sessione e l'altra.

**Contesto**: una breve descrizione della riunione (partecipanti, argomenti, acronimi) migliora significativamente la precisione su terminologia specialistica.

---

## Eseguire i test

```bash
poetry run pytest tests/ -v
```

La suite comprende 31 test (1 skip su macchine senza MPS) che coprono clustering, preprocessing, worker, device detection ed estrazione audio — senza richiedere modelli ML né hardware audio.

---

## Struttura del progetto

```
MinuteMeeting/
├── pyproject.toml
├── minute_meeting.spec          # spec PyInstaller (cross-platform)
├── installer/
│   └── minute_meeting.iss       # script Inno Setup (Windows installer)
├── scripts/
│   └── build.py                 # poetry run python scripts/build.py
├── .github/workflows/
│   └── build-windows.yml        # CI: build installer Windows su tag v*
├── minute_meeting/
│   ├── main.py
│   ├── audio/
│   │   ├── recorder.py          # registrazione microfono (sounddevice)
│   │   ├── extractor.py         # estrazione audio da video (ffmpeg)
│   │   └── preprocessor.py      # normalizzazione + riduzione rumore opzionale
│   ├── transcription/
│   │   └── transcriber.py       # trascrizione + allineamento (WhisperX)
│   ├── diarization/
│   │   ├── vad.py               # Voice Activity Detection (SpeechBrain)
│   │   ├── speaker.py           # embedding speaker (ECAPA-TDNN)
│   │   └── clustering.py        # assegnazione speaker (scikit-learn)
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── worker.py            # pipeline in QThread
│   │   ├── widgets/
│   │   │   ├── recorder_widget.py
│   │   │   ├── settings_dialog.py
│   │   │   └── transcript_widget.py
│   │   └── styles/main.qss
│   └── utils/
│       ├── device.py            # rilevamento device (cpu/cuda/mps)
│       └── env_check.py         # controllo runtime ffmpeg
└── tests/
    ├── test_basic.py
    ├── test_device.py
    ├── test_extractor.py
    ├── test_preprocessor.py
    └── test_worker.py
```

---

## Distribuzione Windows

### Automatica (GitHub Actions)

Crea un tag e fai push — il workflow costruisce e pubblica il `.exe` installer automaticamente:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Il workflow scarica ffmpeg, compila con PyInstaller e confeziona l'installer con Inno Setup. L'artefatto viene allegato alla GitHub Release.

### Manuale (su macchina Windows)

```powershell
# 1. Scarica ffmpeg.exe nella root del progetto
choco install ffmpeg
Copy-Item (Get-Command ffmpeg).Source -Destination ffmpeg.exe

# 2. Build
poetry run python scripts/build.py

# 3. Installer
iscc installer\minute_meeting.iss
# Output: dist\MinuteMeeting-Setup-0.1.0.exe
```

> Il bundle include ffmpeg automaticamente — l'utente finale non deve installare nulla.

---

## Risoluzione dei problemi

**`poetry install` fallisce su WhisperX** — verifica che `git` sia nel PATH: `git --version`.

**Errore microfono su macOS** — verifica il permesso in Impostazioni di sistema → Privacy e sicurezza → Microfono. Se l'autorizzazione è stata negata in precedenza: `tccutil reset Microphone`.

**Nessun audio registrato** — verifica che il microfono predefinito del sistema abbia sensibilità sufficiente. Il livello viene mostrato in tempo reale nella barra della UI.

**Trascrizione di bassa qualità** — usa un modello più grande (medium o large-v3) e/o fornisci un contesto nelle impostazioni con i termini tecnici specifici della riunione.

**Bundle macOS bloccato** — macOS potrebbe bloccare eseguibili non firmati:
```bash
xattr -cr dist/MinuteMeeting/MinuteMeeting
```

---

## Licenza

Distribuito sotto licenza [MIT](LICENSE).
