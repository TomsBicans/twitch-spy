import {useEffect, useRef, useState} from 'react';
import {flushSync} from 'react-dom';
import {Expand, Maximize} from 'lucide-react';
import type {VisualizerPlayback} from './audio';
import {presets} from './presets';
import VisualizerCanvas from './VisualizerCanvas';
import MusicVisualizer from './MusicVisualizer';
import FrameRateSelect from './FrameRateSelect';
import type {FrameRate} from './FrameRateSelect';
import styles from './SidebarVisualizer.module.css';
import {isVisualizerShortcut} from './shortcuts';

interface Props {
    playback: VisualizerPlayback | null;
    title?: string;
    trackColor?: string;
}

export default function SidebarVisualizer({playback, title, trackColor = "#4a4a4a"}: Props) {
    const [colorTheme, setColorTheme] = useState<"artwork" | "system">("artwork");
    const color = colorTheme === "artwork" ? trackColor : undefined;
    const [expanded, setExpanded] = useState(false);
    const [startImmersive, setStartImmersive] = useState(false);
    const [frameRate, setFrameRate] = useState<FrameRate>('30');
    const [presetId, setPresetId] = useState(presets[0].id);
    const [paused, setPaused] = useState(true);
    const [error, setError] = useState('');
    const [motion] = useState(() => !window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    const fullscreenRef = useRef<HTMLDivElement>(null);
    const preset = presets.find(item => item.id === presetId) ?? presets[0];
    const audio = playback?.audio;

    useEffect(() => {
        if (!audio) return;
        const sync = () => setPaused(audio.paused);
        sync();
        audio.addEventListener('play', sync);
        audio.addEventListener('pause', sync);
        audio.addEventListener('ended', sync);
        return () => {
            audio.removeEventListener('play', sync);
            audio.removeEventListener('pause', sync);
            audio.removeEventListener('ended', sync);
        };
    }, [audio]);

    useEffect(() => {
        if (!playback || expanded) return;
        const keyDown = async (event: KeyboardEvent) => {
            if (!isVisualizerShortcut(event, 'f') || !document.fullscreenEnabled
                || document.querySelector('dialog[open]')) return;
            event.preventDefault();
            setError('');
            flushSync(() => {
                setStartImmersive(true);
                setExpanded(true);
            });
            try {
                await fullscreenRef.current?.requestFullscreen();
            } catch (cause) {
                setExpanded(false);
                setStartImmersive(false);
                setError(`Could not enter fullscreen: ${String(cause)}`);
            }
        };
        document.addEventListener('keydown', keyDown);
        return () => document.removeEventListener('keydown', keyDown);
    }, [playback, expanded]);

    const openFullscreen = async () => {
        setError('');
        // Mount the fullscreen target within the click's user activation.
        flushSync(() => setExpanded(true));
        try {
            await fullscreenRef.current?.requestFullscreen();
        } catch (cause) {
            setExpanded(false);
            setError(`Could not enter fullscreen: ${String(cause)}`);
        }
    };

    return <>
        <section className={styles.preview} aria-label="Live music preview">
            <header className={styles.header}>
                <span>VISUALIZER</span>
                <FrameRateSelect className={styles.frameRate} value={frameRate} onChange={setFrameRate}/>
                <span className={styles.status}><i data-playing={Boolean(audio && !paused)}/>{audio ? paused ? 'Paused' : 'Live' : 'Ready'}</span>
            </header>
            <div className={styles.scene}>
                {playback && !expanded
                    ? <VisualizerCanvas color={color} {...playback} preset={preset} quality="low" frameRate={frameRate} intensity={1} motion={motion}/>
                    : <div className={styles.placeholder}><span aria-hidden="true">◉</span><p>{expanded ? 'Expanded view is open' : 'Play a track to bring this space to life'}</p></div>}
            </div>
            <footer className={styles.footer}>
                <p className={styles.title} title={title}>{title ?? 'Your music, in motion'}</p>
                <div className={styles.actions}>
                    <button disabled={!playback} onClick={() => setExpanded(true)} aria-label="Expand visualizer"><Expand size={14}/>Expand</button>
                    <button disabled={!playback || !document.fullscreenEnabled} onClick={openFullscreen} aria-label="Fullscreen visualizer" title="Press F for fullscreen without controls"><Maximize size={14}/>Fullscreen</button>
                </div>
                {error && <p role="alert">{error}</p>}
            </footer>
        </section>
        {expanded && playback && <MusicVisualizer color={color} colorTheme={colorTheme} onColorThemeChange={setColorTheme} {...playback} title={title ?? 'Music'}
            presetId={presetId} onPresetChange={setPresetId} fullscreenRef={fullscreenRef}
            frameRate={frameRate} onFrameRateChange={setFrameRate}
            startImmersive={startImmersive}
            onClose={() => { setExpanded(false); setStartImmersive(false); }}/>}
    </>;
}
