import {useEffect, useLayoutEffect, useRef, useState} from "react";
import {History, ListMusic, LocateFixed, Music2, Play, Shuffle, X} from "lucide-react";
import type {Atom} from "../backend/models";
import {getArtworkUrl} from "../backend/artwork";
import type {QueueEntry} from "../useMusicQueue";
import styles from "./PlaybackQueue.module.css";

interface PlaybackQueueProps {
    currentTrack?: Atom;
    history: QueueEntry[];
    upcoming: QueueEntry[];
    shuffle: boolean;
    autoplay: boolean;
    loading: boolean;
    onJump: (position: number) => void;
    onClose: () => void;
}

function Cover({track}: {track: Atom}) {
    const url = getArtworkUrl(track);
    const [failed, setFailed] = useState<string>();
    return <span className={styles.cover} aria-hidden="true">
        {url && failed !== url
            ? <img src={url} alt="" loading="lazy" onError={() => setFailed(url)}/>
            : <Music2 size={20}/>}
    </span>;
}

export default function PlaybackQueue({currentTrack, history, upcoming, shuffle, autoplay,
    loading, onJump, onClose}: PlaybackQueueProps) {
    const [visible, setVisible] = useState(40);
    const [visibleHistory, setVisibleHistory] = useState(5);
    const closeRef = useRef<HTMLButtonElement>(null);
    const listRef = useRef<HTMLDivElement>(null);
    const currentRef = useRef<HTMLLIElement>(null);
    const close = useRef(onClose);
    close.current = onClose;
    const currentPosition = upcoming[0] ? upcoming[0].position - 1
        : history.length ? history[history.length - 1].position + 1 : 0;

    const scrollToCurrent = () => {
        const list = listRef.current;
        const row = currentRef.current;
        if (!list || !row) return;
        list.scrollTop = Math.max(0, row.offsetTop - Math.min(120, list.clientHeight * 0.3));
    };

    useLayoutEffect(() => {
        scrollToCurrent();
    }, [currentTrack?.url, currentPosition, loading]);

    useEffect(() => {
        const previousFocus = document.activeElement;
        closeRef.current?.focus({preventScroll: true});
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key !== "Escape" || event.defaultPrevented || document.fullscreenElement
                || document.querySelector("dialog[open]")) return;
            event.preventDefault();
            close.current();
        };
        document.addEventListener("keydown", onKeyDown);
        return () => {
            document.removeEventListener("keydown", onKeyDown);
            if (previousFocus instanceof HTMLElement && previousFocus.isConnected) {
                previousFocus.focus({preventScroll: true});
            }
        };
    }, []);

    const previousEntries = history.slice(-visibleHistory);
    const renderEntry = ({track, position}: QueueEntry, past: boolean) => <li key={position}
        data-queue-state={past ? "past" : "upcoming"} className={past ? styles.past : undefined}>
        <button type="button" onClick={() => onJump(position)}
            aria-label={`Play ${track.content_name}`} className={styles.track}>
            <span className={styles.number}>{position < 0 ? <History size={12}/>
                : String(position + 1).padStart(2, "0")}</span>
            <Cover track={track}/><span className={styles.trackTitle} title={track.content_name}>
                {track.content_name}</span><Play size={14} className={styles.playIcon}/>
        </button>
    </li>;

    return <aside id="playback-queue" aria-label="Playback queue" className={styles.panel}>
        <header className={styles.header}>
            <div><span className={styles.eyebrow}>Your listening session</span>
                <h2><ListMusic size={22}/> Queue</h2></div>
            <button ref={closeRef} type="button" className={styles.iconButton}
                onClick={onClose} aria-label="Close playback queue"><X size={19}/></button>
        </header>
        <div className={styles.session}>
            <span>{shuffle ? <Shuffle size={13}/> : <ListMusic size={13}/>}
                {shuffle ? "Shuffled" : "In order"}</span>
            <span className={autoplay ? styles.enabled : undefined}>
                <i/>{autoplay ? "Autoplay on" : "Autoplay off"}</span>
        </div>
        <div className={styles.listHeader}>
            <span>{history.length} played <span aria-hidden="true">·</span> {upcoming.length} up next</span>
            {currentTrack && <button type="button" onClick={scrollToCurrent}
                aria-label="Jump to current song" title="Scroll to the current song">
                <LocateFixed size={13}/> Current</button>}
        </div>
        <div ref={listRef} className={styles.trackList} id="queue-tracks">
            {currentTrack ? <>
                {history.length > visibleHistory && <button type="button" className={styles.showEarlier}
                    onClick={() => setVisibleHistory(count => count + 40)}>
                    <History size={13}/> Show earlier songs ({history.length - visibleHistory})
                </button>}
                <ol className={styles.tracks} aria-label="Playback sequence">
                    {previousEntries.map(entry => renderEntry(entry, true))}
                    <li ref={currentRef} className={styles.current} aria-current="true" data-queue-state="current">
                        <span className={styles.eyebrow}>Now playing</span>
                        <div className={styles.currentRow}>
                            <span className={styles.number}>{currentPosition < 0 ? <Music2 size={12}/>
                                : String(currentPosition + 1).padStart(2, "0")}</span>
                            <Cover track={currentTrack}/>
                            <strong title={currentTrack.content_name}>{currentTrack.content_name}</strong>
                            <span className={styles.soundBars} aria-hidden="true"><i/><i/><i/></span>
                        </div>
                    </li>
                    {upcoming.slice(0, visible).map(entry => renderEntry(entry, false))}
                </ol>
                {upcoming.length > visible && <button type="button" className={styles.showMore}
                    onClick={() => setVisible(count => count + 40)}>Show more songs</button>}
                {!upcoming.length && <p className={styles.listCaption}>
                    {loading ? "Loading your sequence…" : "Nothing up next"}
                </p>}
            </> : <div className={styles.empty}><Music2 size={32} strokeWidth={1}/>
                <h3>{loading ? "Loading your sequence" : "Your queue starts here"}</h3>
                <p>{loading ? "Your saved position will be ready when the library finishes loading."
                    : "Choose a song from your library to start listening."}</p>
            </div>}
        </div>
        <footer className={styles.footer}>Bookmark this page to return to this sequence.</footer>
    </aside>;
}
