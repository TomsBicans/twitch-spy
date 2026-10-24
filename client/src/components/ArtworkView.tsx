import {useEffect, useRef, useState} from "react";
import type {CSSProperties} from "react";
import {ArrowLeft, Music2} from "lucide-react";
import styles from "./ArtworkView.module.css";

interface ArtworkViewProps {
    artwork?: string;
    title?: string;
    color: string;
    onClose: () => void;
}

export default function ArtworkView({artwork, title, color, onClose}: ArtworkViewProps) {
    const closeRef = useRef<HTMLButtonElement>(null);
    const [failedArtwork, setFailedArtwork] = useState<string>();
    const visibleArtwork = artwork !== failedArtwork ? artwork : undefined;

    useEffect(() => {
        const previousFocus = document.activeElement;
        const previousOverflow = document.documentElement.style.overflow;
        document.documentElement.style.overflow = "hidden";
        closeRef.current?.focus({preventScroll: true});
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key !== "Escape" || event.defaultPrevented || document.fullscreenElement
                || document.querySelector("dialog[open]")) return;
            event.preventDefault();
            onClose();
        };
        document.addEventListener("keydown", onKeyDown);
        return () => {
            document.documentElement.style.overflow = previousOverflow;
            document.removeEventListener("keydown", onKeyDown);
            if (previousFocus instanceof HTMLElement && previousFocus.isConnected) {
                previousFocus.focus({preventScroll: true});
            }
        };
    }, [onClose]);

    return (
        <section id="artwork-view" aria-label="Expanded artwork" className={styles.view}
            style={{"--artwork-color": color} as CSSProperties}>
            {visibleArtwork && <div key={visibleArtwork} className={styles.backdrop} aria-hidden="true"
                style={{backgroundImage: `url("${visibleArtwork}")`}}/>}
            <div className={styles.shade} aria-hidden="true"/>
            <div className={styles.toolbar}>
                <button ref={closeRef} type="button" onClick={onClose} className={styles.backButton}>
                    <ArrowLeft size={18}/> Back to library
                </button>
                <span className={styles.label}>Artwork view</span>
            </div>
            <div className={styles.picture}>
                {visibleArtwork ? <img key={visibleArtwork} src={visibleArtwork}
                    alt={`Artwork for ${title ?? "current track"}`} onError={() => setFailedArtwork(visibleArtwork)}/>
                    : <div className={styles.placeholder}>
                        <Music2 size={72} strokeWidth={1}/>
                        <p>No artwork for this track</p>
                    </div>}
            </div>
            <div className={styles.caption} aria-live="polite" aria-atomic="true">
                <span className={styles.label}>Now playing</span>
                <h2>{title ?? "No track selected"}</h2>
            </div>
        </section>
    );
}
