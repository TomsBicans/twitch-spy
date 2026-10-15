import React, {useEffect, useRef, useState} from "react";
import AudioPlayer, {RHAP_UI} from "react-h5-audio-player";
import "react-h5-audio-player/lib/styles.css";
import {BACKEND_URL} from "../backend/backend.ts";
import CurrentTrackDisplay from "./CurrentTrackDisplay.tsx";
import type {Atom} from "../backend/models.ts";
import styles from "./AudioPlayer.module.css";
import {getAudioAnalysis, releaseAudioAnalysis} from "../visualizer/audio";
import type {AudioAnalysis, VisualizerPlayback} from "../visualizer/audio";
import {SkipBack, SkipForward} from "lucide-react";

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
    onAutoplayChange, shuffle, onShuffleChange, onNext, onPrevious, canNext, canPrevious, poolSize}) => {
    const [currentTrack, setCurrentTrack] = useState<string | undefined>();
    const [trackColor, setTrackColor] = useState<string>("#4a4a4a");
    const [isPlaying, setIsPlaying] = useState(false);
    const playerRef = useRef<AudioPlayer>(null);
    const [playerError, setPlayerError] = useState('');
    const analysisRef = useRef<AudioAnalysis | null>(null);
    const artwork = entry?.thumbnail_image_in_base64
        ? `data:image/jpeg;base64,${entry.thumbnail_image_in_base64}`
        : entry?.thumbnail_url ? `${BACKEND_URL}${entry.thumbnail_url}` : undefined;

    useEffect(() => {
        document.title = isPlaying && entry?.content_name ? entry.content_name : "twitch-spy";
        return () => { document.title = "twitch-spy"; };
    }, [isPlaying, entry?.content_name]);

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

    const togglePlay = async () => {
        const audio = playerRef.current?.audio?.current;
        if (!audio) return;
        if (isPlaying) {
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
    };

    return (
        <div className={styles.playerShell}>
            <div className={styles.leftPane}>
                <CurrentTrackDisplay title={entry?.content_name} color={trackColor} artwork={artwork}/>
            </div>
            <div className={styles.centerPane}>
                <div className={styles.transport}>
                <button type="button" className={styles.skipButton} onClick={onPrevious}
                    aria-label="Previous song" disabled={!canPrevious}><SkipBack size={20}/></button>
                <button
                    className={styles.playButton}
                    onClick={togglePlay}
                    aria-label={isPlaying ? "Pause" : "Play"}
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
                    ref={playerRef}
                    autoPlay
                    autoPlayAfterSrcChange
                    src={currentTrack}
                    crossOrigin="anonymous"
                    showJumpControls={false}
                    customControlsSection={[RHAP_UI.VOLUME_CONTROLS]}
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
            {playerError && <p role="alert" className={styles.playerError}>{playerError}</p>}
        </div>
    );
};

export default MusicPlayer;
