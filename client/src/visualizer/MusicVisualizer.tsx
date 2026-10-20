import {useEffect, useRef, useState} from 'react';
import type {RefObject} from 'react';
import type {AudioAnalysis} from './audio';
import {presets} from './presets';
import VisualizerCanvas from './VisualizerCanvas';
import FrameRateSelect from './FrameRateSelect';
import type {FrameRate} from './FrameRateSelect';
import styles from './MusicVisualizer.module.css';
import {isVisualizerShortcut} from './shortcuts';

interface Props {
    audio: HTMLAudioElement;
    analysis: AudioAnalysis;
    title: string;
    color?: string;
    colorTheme: "artwork" | "system";
    onColorThemeChange: (theme: "artwork" | "system") => void;
    onClose: () => void;
    presetId: string;
    onPresetChange: (id: string) => void;
    fullscreenRef: RefObject<HTMLDivElement | null>;
    frameRate: FrameRate;
    onFrameRateChange: (value: FrameRate) => void;
    startImmersive?: boolean;
}

function timestamp(seconds: number): string {
    if (!Number.isFinite(seconds)) return '0:00';
    return `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60).toString().padStart(2, '0')}`;
}

export default function MusicVisualizer({audio, analysis, color, colorTheme, onColorThemeChange, title, onClose, presetId, onPresetChange, fullscreenRef, frameRate, onFrameRateChange, startImmersive = false}: Props) {
    const dialog = useRef<HTMLDialogElement>(null);
    const viewport = fullscreenRef;
    const hideButton = useRef<HTMLButtonElement>(null);
    const [intensity, setIntensity] = useState(1);
    const [quality, setQuality] = useState<'low' | 'high'>('low');
    const [motion, setMotion] = useState(() => !window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    const [hidden, setHidden] = useState(startImmersive);
    const previousView = useRef<{fullscreen: boolean; hidden: boolean; focus: Element | null} | null>(
        startImmersive ? {fullscreen: false, hidden: false, focus: null} : null);
    const fullscreenPending = useRef(false);
    const [fullscreen, setFullscreen] = useState(false);
    const [error, setError] = useState('');
    const [playback, setPlayback] = useState({paused: audio.paused, time: audio.currentTime, duration: audio.duration, volume: audio.volume, muted: audio.muted, loop: audio.loop});
    const preset = presets.find(item => item.id === presetId) ?? presets[0];

    useEffect(() => {
        const element = dialog.current!;
        const previousFocus = document.activeElement;
        element.showModal();
        return () => {
            element.close();
            if (previousFocus instanceof HTMLElement) previousFocus.focus();
        };
    }, []);

    useEffect(() => {
        const sync = () => setPlayback({paused: audio.paused, time: audio.currentTime, duration: audio.duration, volume: audio.volume, muted: audio.muted, loop: audio.loop});
        const events = ['play', 'pause', 'ended', 'timeupdate', 'durationchange', 'volumechange', 'loadedmetadata', 'emptied'];
        events.forEach(event => audio.addEventListener(event, sync));
        const fullscreenChanged = () => setFullscreen(document.fullscreenElement === viewport.current);
        document.addEventListener('fullscreenchange', fullscreenChanged);
        return () => {
            events.forEach(event => audio.removeEventListener(event, sync));
            document.removeEventListener('fullscreenchange', fullscreenChanged);
        };
    }, [audio, viewport]);

    useEffect(() => {
        const restore = () => {
            const previous = previousView.current;
            previousView.current = null;
            if (previous) setHidden(previous.hidden);
            if (startImmersive) onClose();
            else {
                const focus = previous?.focus;
                requestAnimationFrame(() => {
                    if (focus instanceof HTMLElement && focus.isConnected) focus.focus();
                });
            }
        };
        const fullscreenChanged = () => {
            if (!document.fullscreenElement && previousView.current) restore();
        };
        const keyDown = async (event: KeyboardEvent) => {
            if (!isVisualizerShortcut(event, 'f')) return;
            event.preventDefault();
            if (fullscreenPending.current || !document.fullscreenEnabled) return;
            fullscreenPending.current = true;
            try {
                setError('');
                if (previousView.current) {
                    if (!previousView.current.fullscreen && document.fullscreenElement === viewport.current) {
                        await document.exitFullscreen();
                    }
                    if (previousView.current) restore();
                } else {
                    previousView.current = {
                        fullscreen: document.fullscreenElement === viewport.current,
                        hidden,
                        focus: document.activeElement,
                    };
                    if (!previousView.current.fullscreen) await viewport.current?.requestFullscreen();
                    setHidden(true);
                    viewport.current?.focus();
                }
            } catch (cause) {
                if (!document.fullscreenElement && previousView.current) restore();
                setError(`Fullscreen is unavailable: ${String(cause)}`);
            } finally {
                fullscreenPending.current = false;
            }
        };
        document.addEventListener('keydown', keyDown);
        document.addEventListener('fullscreenchange', fullscreenChanged);
        return () => {
            document.removeEventListener('keydown', keyDown);
            document.removeEventListener('fullscreenchange', fullscreenChanged);
        };
    }, [hidden, onClose, startImmersive, viewport]);

    const togglePlayback = async () => {
        try {
            setError('');
            await analysis.context.resume();
            if (audio.paused) await audio.play();
            else audio.pause();
        } catch (cause) { setError(`Playback failed: ${String(cause)}`); }
    };
    const toggleFullscreen = async () => {
        try {
            setError('');
            if (document.fullscreenElement === viewport.current) await document.exitFullscreen();
            else await viewport.current?.requestFullscreen();
        } catch (cause) { setError(`Fullscreen is unavailable: ${String(cause)}`); }
    };
    const duration = Number.isFinite(playback.duration) ? playback.duration : 0;

    return <dialog ref={dialog} className={styles.dialog} aria-label="Music visualizer" onCancel={onClose}
        onKeyDown={event => {
            if (isVisualizerShortcut(event.nativeEvent, 'h')) {
                setHidden(value => !value);
                hideButton.current?.focus();
            }
        }}>
        <div ref={viewport} className={styles.viewport} tabIndex={-1}>
        <div className={styles.stage}>
            <VisualizerCanvas color={color} audio={audio} analysis={analysis} preset={preset} intensity={intensity} motion={motion} quality={quality} frameRate={frameRate}/>
        </div>
        <div className={styles.actions}>
            <button ref={hideButton} onClick={() => setHidden(value => !value)} aria-expanded={!hidden} aria-controls="visualizer-controls">{hidden ? 'Show controls' : 'Hide controls'} <kbd>H</kbd></button>
            <button onClick={toggleFullscreen} disabled={!document.fullscreenEnabled} title="Press F for fullscreen without controls">{fullscreen ? 'Exit fullscreen' : 'Fullscreen'}</button>
            <button onClick={onClose} aria-label="Close visualizer">Close</button>
        </div>
        {!hidden && <div id="visualizer-controls" className={styles.controls}>
            <header><span className={styles.eyebrow}>NOW PLAYING / VISUALIZER</span><h2>{title}</h2><p>{preset.description}</p></header>
            <div className={styles.options}>
                <label>Scene<select aria-label="Scene" value={presetId} onChange={event => onPresetChange(event.target.value)}>{presets.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
                <label>Colors<select aria-label="Colors" value={colorTheme} onChange={event => onColorThemeChange(event.target.value as "artwork" | "system")}><option value="artwork">Match artwork</option><option value="system">System</option></select></label>
                <label>Quality<select aria-label="Quality" value={quality} onChange={event => setQuality(event.target.value as 'low' | 'high')}><option value="low">Eco</option><option value="high">High</option></select></label>
                <label>Frame rate<FrameRateSelect value={frameRate} onChange={onFrameRateChange}/></label>
                <label>Intensity<input type="range" min="0.2" max="2" step="0.1" value={intensity} onChange={event => setIntensity(Number(event.target.value))}/></label>
                <label className={styles.check}><input type="checkbox" checked={motion} onChange={event => setMotion(event.target.checked)}/>Camera motion</label>
            </div>
            <div className={styles.transport}>
                <button onClick={togglePlayback}>{playback.paused ? 'Play' : 'Pause'}</button>
                <span>{timestamp(playback.time)}</span>
                <input aria-label="Seek" type="range" min="0" max={duration || 1} step="0.1" value={Math.min(playback.time, duration)} disabled={!duration} onChange={event => { const time = Number(event.target.value); audio.currentTime = time; setPlayback(value => ({...value, time})); }}/>
                <span>{timestamp(duration)}</span>
                <button onClick={() => { audio.muted = !audio.muted; }}>{playback.muted ? 'Unmute' : 'Mute'}</button>
                <input className={styles.volume} aria-label="Volume" type="range" min="0" max="1" step="0.01" value={playback.volume} onChange={event => { const volume = Number(event.target.value); audio.volume = volume; setPlayback(value => ({...value, volume})); }}/>
                <button aria-pressed={playback.loop} onClick={() => { audio.loop = !audio.loop; setPlayback(value => ({...value, loop: audio.loop})); }}>Loop</button>
            </div>
        </div>}
        {error && <p className={styles.error} role="alert">{error}</p>}
        </div>
    </dialog>;
}


