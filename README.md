# WaveControl

Standalone Python application for real-time audio playback, analysis, and
visualization.

## Features

- Load and play WAV/MP3/FLAC files with loop, pause, and reverse controls.
- Callback-based audio engine exposes the current buffer for analysis and
  visualization.
- Time state manager tracks playhead and accumulated time for synchronization.
- Event bus decouples beat, loop, and transport notifications.
- BPM detection with manual override and beat clock.
- Image sequence playback synchronized to audio time.
- Pygame renderer with waveform dots, particles, and beat flashes.

## Usage

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the app with an audio file, optionally providing an image directory:

```bash
python -m wavecontrol.main path/to/audio.wav --images path/to/images
```
