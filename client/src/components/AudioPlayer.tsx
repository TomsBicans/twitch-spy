import React, {useEffect, useRef, useState} from "react";
import AudioPlayer, {RHAP_UI} from "react-h5-audio-player";
import "react-h5-audio-player/lib/styles.css";
import {BACKEND_URL} from "../backend/backend.ts";
import CurrentTrackDisplay from "./CurrentTrackDisplay.tsx";
import type {Atom} from "../backend/models.ts";
import styles from "./AudioPlayer.module.css";

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
}

const MusicPlayer: React.FC<AudioPlayerProps> = ({entry}) => {
    const [currentTrack, setCurrentTrack] = useState<string | undefined>();
    const [trackColor, setTrackColor] = useState<string>("#4a4a4a");
    const [isPlaying, setIsPlaying] = useState(false);
    const playerRef = useRef<any>(null);

    useEffect(() => {
        if (entry) {
            setCurrentTrack(`${BACKEND_URL}/audio/${entry.content_name}`);
            if (entry.thumbnail_image_in_base64) {
                getAverageColor(entry.thumbnail_image_in_base64).then(setTrackColor);
            } else {
                setTrackColor(getRandomColor());
            }
        }
    }, [entry]);

    const getAverageColor = (base64Image: string): Promise<string> => {
        return new Promise((resolve) => {
            const img = new Image();
            img.src = `data:image/jpeg;base64,${base64Image}`;
            img.onload = () => {
                const canvas = document.createElement("canvas");
                const ctx = canvas.getContext("2d");
                if (!ctx) {
                    resolve(getRandomColor());
                    return;
                }
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0, img.width, img.height);
                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                const data = imageData.data;
                let r = 0,
                    g = 0,
                    b = 0;
                let count = 0;

                for (let i = 0; i < data.length; i += 4) {
                    // Skip transparent pixels
                    if (data[i + 3] < 255) continue;

                    r += data[i];
                    g += data[i + 1];
                    b += data[i + 2];
                    count++;
                }

                if (count > 0) {
                    r = Math.round(r / count);
                    g = Math.round(g / count);
                    b = Math.round(b / count);
                    resolve(`rgb(${r},${g},${b})`);
                } else {
                    resolve(getRandomColor());
                }
            };
            img.onerror = () => {
                resolve(getRandomColor());
            };
        });
    };

    const handleNextTrack = () => {
        console.log("Next track functionality can be implemented here.");
    };

    const togglePlay = () => {
        const audio = playerRef.current?.audio?.current;
        if (!audio) return;
        if (isPlaying) {
            audio.pause();
        } else {
            audio.play();
        }
    };

    const getRandomColor = () => {
        const r = Math.floor(Math.random() * 256);
        const g = Math.floor(Math.random() * 256);
        const b = Math.floor(Math.random() * 256);
        return `rgb(${r},${g},${b})`;
    };

    return (
        <div className={styles.playerShell}>
            <div className={styles.leftPane}>
                <CurrentTrackDisplay title={entry?.content_name} color={trackColor}/>
            </div>
            <div className={styles.centerPane}>
                <button
                    className={styles.playButton}
                    onClick={togglePlay}
                    aria-label={isPlaying ? "Pause" : "Play"}
                >
                    {isPlaying ? <PauseIcon/> : <PlayIcon/>}
                </button>
            </div>
            <div className={styles.rightPane}>
                <AudioPlayer
                    ref={playerRef}
                    autoPlay
                    autoPlayAfterSrcChange
                    src={currentTrack}
                    showJumpControls={false}
                    customControlsSection={[RHAP_UI.VOLUME_CONTROLS]}
                    customProgressBarSection={[
                        RHAP_UI.CURRENT_TIME,
                        RHAP_UI.PROGRESS_BAR,
                        RHAP_UI.CURRENT_LEFT_TIME,
                    ]}
                    onPlay={() => setIsPlaying(true)}
                    onPause={() => setIsPlaying(false)}
                    onEnded={() => {
                        setIsPlaying(false);
                        handleNextTrack();
                    }}
                />
            </div>
        </div>
    );
};

export default MusicPlayer;
