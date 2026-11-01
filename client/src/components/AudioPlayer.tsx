import React, {useCallback, useEffect, useRef, useState} from "react";
import AudioPlayer, {RHAP_UI} from "react-h5-audio-player";
import "react-h5-audio-player/lib/styles.css";
import {BACKEND_URL} from "../backend/backend.ts";
import {getArtworkUrl} from "../backend/artwork.ts";
import CurrentTrackDisplay from "./CurrentTrackDisplay.tsx";
import VolumeControl from "./VolumeControl";
import {readVolumeSettings, saveVolumeSettings} from "./volume";
import type {Atom} from "../backend/models.ts";
import styles from "./AudioPlayer.module.css";
import {getAudioAnalysis, releaseAudioAnalysis} from "../visualizer/audio";
import type {AudioAnalysis, VisualizerPlayback} from "../visualizer/audio";
import {ListMusic, SkipBack, SkipForward} from "lucide-react";

const PlayIcon = () => (
    <svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26">
        <path d="M8 5v14l11-7z"/>
    </svg>
);

const PauseIcon = () => (
    <svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26">
        <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
    </svg>
);

interface AudioPlayerProps {
    entry: Atom | undefined;
    onPlaybackReady: (playback: VisualizerPlayback) => void;
    onTrackColorChange?: (color: string) => void;
    autoplay: boolean;
    onAutoplayChange: () => void;
    shuffle: boolean;
    onShuffleChange: () => void;
    onNext: () => void;
    onPrevious: () => void;
    canNext: boolean;
    canPrevious: boolean;
    poolSize: number;
    artworkExpanded?: boolean;
    onArtworkToggle?: () => void;
    queueOpen: boolean;
    onQueueToggle: () => void;
}

const getAverageColor = (imageUrl: string): Promise<string> => {
    return new Promise((resolve) => {
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => {
            const canvas = document.createElement("canvas");
            const ctx = canvas.getContext("2d");
            if (!ctx) {
                resolve("#4a4a4a");
                return;
            }
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0, img.width, img.height);
            let data: Uint8ClampedArray;
            try {
                data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
            } catch {
                resolve("#4a4a4a");
                return;
            }
            let r = 0;
            let g = 0;
            let b = 0;
            let count = 0;

            for (let i = 0; i < data.length; i += 4) {
                if (data[i + 3] < 255) continue;
                r += data[i];
                g += data[i + 1];
                b += data[i + 2];
                count++;
            }

            if (count === 0) {
                resolve("#4a4a4a");
                return;
            }
            resolve(`#${[r, g, b].map(value => Math.round(value / count).toString(16).padStart(2, "0")).join("")}`);
        };
        img.onerror = () => resolve("#4a4a4a");
        img.src = imageUrl;
    });
};

const MusicPlayer: React.FC<AudioPlayerProps> = ({entry, onPlaybackReady, onTrackColorChange, autoplay,
    onAutoplayChange, shuffle, onShuffleChange, onNext, onPrevious, canNext, canPrevious, poolSize,
    artworkExpanded = false, onArtworkToggle, queueOpen, onQueueToggle}) => {
    const [currentTrack, setCurrentTrack] = useState<string | undefined>();
    const [trackColor, setTrackColor] = useState<string>("#4a4a4a");
    const [isPlaying, setIsPlaying] = useState(false);
    const playerRef = useRef<AudioPlayer>(null);
    const [volumeSettings] = useState(readVolumeSettings);
    const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);
    const attachPlayer = useCallback((player: AudioPlayer | null) => {
        playerRef.current = player;
        const audio = player?.audio.current ?? null;
        if (audio) audio.muted = volumeSettings.muted;
        setAudioElement(audio);
    }, [volumeSettings]);
    const [playerError, setPlayerError] = useState('');
    const analysisRef = useRef<AudioAnalysis | null>(null);
    const artwork = getArtworkUrl(entry);

    useEffect(() => {
        document.title = isPlaying && entry?.content_name ? entry.content_name : "twitch-spy";
        return () => { document.title = "twitch-spy"; };
    }, [isPlaying, entry?.content_name]);

    useEffect(() => {
        if (!("mediaSession" in navigator)) return;
        const session = navigator.mediaSession;
        const handlers: [MediaSessionAction, MediaSessionActionHandler | null][] = [
            ["nexttrack", canNext ? onNext : null],
            ["previoustrack", canPrevious ? onPrevious : null],
        ];
        const registered: MediaSessionAction[] = [];
        for (const [action, handler] of handlers) {
            try {
                session.setActionHandler(action, handler);
                registered.push(action);
            } catch (error) {
                if (!(error instanceof DOMException) || error.name !== "NotSupportedError") throw error;
                console.warn(`Media session action ${action} is not supported`, error);
            }
        }
        return () => {
            for (const action of registered) session.setActionHandler(action, null);
        };
    }, [canNext, canPrevious, onNext, onPrevious]);

    useEffect(() => {
        const audio = playerRef.current?.audio.current;
        return () => { if (audio) releaseAudioAnalysis(audio); };
    }, []);

    const prepareVisualizer = async () => {
        const audio = playerRef.current?.audio.current;
        if (!audio) return;
        try {
            setPlayerError('');
            const analysis = getAudioAnalysis(audio);
            analysisRef.current = analysis;
            onPlaybackReady({audio, analysis});
            await analysis.context.resume();
        } catch (error) {
            setPlayerError(`Could not start visualizer: ${String(error)}`);
        }
    };

    useEffect(() => {
        if (entry) {
            setCurrentTrack(`${BACKEND_URL}/audio/${encodeURIComponent(entry.content_name)}`);
        }
    }, [entry]);

    useEffect(() => {
        let cancelled = false;
        const applyColor = (color: string) => {
            if (cancelled) return;
            setTrackColor(color);
            onTrackColorChange?.(color);
        };
        applyColor("#4a4a4a");
        if (artwork) void getAverageColor(artwork).then(applyColor);
        return () => { cancelled = true; };
    }, [artwork, onTrackColorChange]);

    const togglePlay = useCallback(async () => {
        const audio = playerRef.current?.audio?.current;
        if (!audio || !currentTrack) return;
        if (!audio.paused) {
            audio.pause();
        } else {
            try {
                await analysisRef.current?.context.resume();
                await audio.play();
                setPlayerError('');
            } catch (error) {
                setPlayerError(`Playback failed: ${String(error)}`);
            }
        }
    }, [currentTrack]);

    useEffect(() => {
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key !== " " || event.defaultPrevented || event.isComposing
                || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey
                || !currentTrack) return;
            if (event.target instanceof Element
                && (event.target.closest('input, textarea, select, button, a[href], [role="button"], [role="slider"]')
                    || (event.target instanceof HTMLElement && event.target.isContentEditable))) return;
            event.preventDefault();
            if (!event.repeat) void togglePlay();
        };
        document.addEventListener("keydown", onKeyDown);
        return () => document.removeEventListener("keydown", onKeyDown);
    }, [currentTrack, togglePlay]);

    return (
        <div className={styles.playerShell}>
            <div className={styles.leftPane}>
                <CurrentTrackDisplay title={entry?.content_name} color={trackColor} artwork={artwork}
                    artworkExpanded={artworkExpanded} onArtworkToggle={onArtworkToggle}/>
            </div>
            <div className={styles.centerPane}>
                <div className={styles.transport}>
                <button type="button" className={styles.skipButton} onClick={onPrevious}
                    aria-label="Previous song" disabled={!canPrevious}><SkipBack size={20}/></button>
                <button
                    className={styles.playButton}
                    onClick={togglePlay}
                    aria-label={isPlaying ? "Pause" : "Play"}
                    title="Play / pause (Space)"
                    disabled={!currentTrack}
                >
                    {isPlaying ? <PauseIcon/> : <PlayIcon/>}
                </button>
                <button type="button" className={styles.skipButton} onClick={onNext}
                    aria-label="Next song" disabled={!canNext}><SkipForward size={20}/></button>
                </div>
                <div className={styles.modes}>
                    <button type="button" aria-pressed={autoplay} onClick={onAutoplayChange}
                        title="Continue to the next matching song when this song ends">Autoplay</button>
                    <button type="button" aria-pressed={shuffle} onClick={onShuffleChange}
                        title="Play matching songs in random order">Shuffle</button>
                </div>
                <span className={styles.poolCount}>{poolSize} matching {poolSize === 1 ? "song" : "songs"}</span>
            </div>
            <div className={styles.rightPane}>
                <AudioPlayer
                    ref={attachPlayer}
                    volume={volumeSettings.volume}
                    onVolumeChange={() => {
                        const audio = playerRef.current?.audio.current;
                        if (audio) saveVolumeSettings(audio);
                    }}
                    autoPlay
                    autoPlayAfterSrcChange
                    src={currentTrack}
                    crossOrigin="anonymous"
                    showJumpControls={false}
                    customControlsSection={audioElement ? [<VolumeControl key="volume" audio={audioElement}/>] : []}
                    customProgressBarSection={[
                        RHAP_UI.CURRENT_TIME,
                        RHAP_UI.PROGRESS_BAR,
                        RHAP_UI.CURRENT_LEFT_TIME,
                    ]}
                    onPlay={() => {
                        setIsPlaying(true);
                        void prepareVisualizer();
                    }}
                    onPause={() => setIsPlaying(false)}
                    onPlayError={(error) => {
                        setIsPlaying(false);
                        setPlayerError(`Playback failed: ${String(error)}`);
                    }}
                    onError={() => {
                        setIsPlaying(false);
                        setPlayerError("Could not load this song. Try another track.");
                    }}
                    onEnded={() => {
                        setIsPlaying(false);
                        if (autoplay && canNext) onNext();
                    }}
                />
            </div>
            <button type="button" className={styles.queueButton} onClick={onQueueToggle}
                aria-label={queueOpen ? "Hide playback queue" : "Show playback queue"}
                aria-expanded={queueOpen} aria-controls="playback-queue" title="Playback queue">
                <ListMusic size={21}/><span>Queue</span>
            </button>
            {playerError && <p role="alert" className={styles.playerError}>{playerError}</p>}
        </div>
    );
};

export default MusicPlayer;
