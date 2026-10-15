# Music visualizer

The visualizer is a live sidebar preview and expandable Three.js view of the existing player.
No separate audio player or preset language is involved. WebGL2 and Web Audio are
required; graphics failures leave the playback controls available.

## Adding presets

`client/src/visualizer/presets.ts` defines the `VisualizerPreset` registry. Each
entry supplies a stable ID, name, description, and `create()` factory returning:

- `root`: a Three.js object added to the shared scene.
- `update(frame)`: updates geometry/materials using shared audio and timing data.
- `dispose()`: releases every owned geometry, material, texture, and GPU resource.

The renderer owns the scene, perspective camera, resize handling, animation
scheduling, and renderer cleanup. Presets can use meshes, particles, lines, or
Three.js shader materials without changing the playback or UI layers. Larger
preset collections can move factories into separate modules and load them on demand.

`AudioFrame` contains frequency magnitudes (0–255), waveform samples centered at
128, normalized bass and overall energy, elapsed active time, intensity, and the
camera-motion preference. The analyser uses a 2048-point FFT. Frequency bins are
linear; their Hz spacing is `AudioContext.sampleRate / analyser.fftSize`.
The current presets avoid expensive lighting, shadows, and postprocessing.
Treat frame arrays as read-only and reuse geometry and buffers between frames.

## Audio lifetime

`audio.ts` caches one source/analyser per HTML audio element. The source connects
directly to the output and separately to the analyser, so removing a scene cannot
disconnect playback. Starting playback initializes and resumes the audio context.
Changing tracks reuses that graph; only unmounting the player closes it.
The audio element requests anonymous CORS. The normal same-origin backend and
Vite proxy work without extra configuration; a separate audio host must allow
the frontend origin for Web Audio analysis.

## Resource limits and interaction

Eco caps rendering at 30 fps and device pixel ratio 1. High caps at 60 fps and
pixel ratio 1.5. The sidebar uses Eco and starts automatically on playback.
Expanding disposes the preview renderer; closing restores the preview with the
selected preset. Paused, offscreen, and background views stop requesting continuous
animation frames. The OS reduced-motion setting
disables camera motion initially; audio-reactive geometry remains enabled.

The sidebar offers Expand and direct Fullscreen controls. Its fullscreen action
mounts the dialog synchronously to preserve browser user activation. The native
modal dialog contains its fullscreen and transport controls. Escape
exits fullscreen through the browser, or closes the dialog when windowed. H toggles
settings and transport visibility outside form fields. Focus returns to the
launcher on close. Unsupported fullscreen is disabled and failures are reported.

## Validation

Run `npm run build` in `client`. With Vite on port 5173, run:

```powershell
uv run --with playwright python tests/check_visualizer_browser.py
```

The browser check uses Edge and generated PCM audio to verify real analyser data,
all scenes, seeking, pause/resume, volume, mute, loop, fullscreen, repeated opening,
track changes, and the mobile layout. Screenshots go to `dist/visualizer-checks`.
