import {lazy, Suspense, useEffect, useRef, useState} from "react";
import type {VisualizerPlayback} from './visualizer/audio';
import "./App.css";
import styles from "./App.module.css";
import URLInput from "./components/URLInput.tsx";
import MusicPlayer from "./components/AudioPlayer.tsx";
import type {Atom} from "./backend/models.ts";
import JobOverview from "./components/JobOverview.tsx";
import JobList from "./components/JobList.tsx";
import SyncPanel from "./components/SyncPanel.tsx";
import Diagnostics from "./components/Diagnostics.tsx";
import {BACKEND_URL} from "./backend/backend.ts";
import {io} from "socket.io-client";
import {useMusicQueue} from "./useMusicQueue";

const socket = io(BACKEND_URL);
const SidebarVisualizer = lazy(() => import('./visualizer/SidebarVisualizer'));

function App() {
    const [playback, setPlayback] = useState<VisualizerPlayback | null>(null);
    const syncDialogRef = useRef<HTMLDialogElement>(null);
    const [showDiagnostics, setShowDiagnostics] = useState(window.location.hash === "#diagnostics");
    useEffect(() => {
        const onHashChange = () => setShowDiagnostics(window.location.hash === "#diagnostics");
        window.addEventListener("hashchange", onHashChange);
        return () => window.removeEventListener("hashchange", onHashChange);
    }, []);
    const [pool, setPool] = useState<Atom[]>([]);
    const queue = useMusicQueue(pool);
    const {currentTrack} = queue;
    const [isConnected, setIsConnected] = useState<boolean>(socket.connected);
    const [desktopMessage, setDesktopMessage] = useState<string | undefined>(undefined);

    useEffect(() => {
        const handleConnect = () => setIsConnected(true);
        const handleDisconnect = () => setIsConnected(false);
        socket.on("connect", handleConnect);
        socket.on("disconnect", handleDisconnect);
        return () => {
            socket.off("connect", handleConnect);
            socket.off("disconnect", handleDisconnect);
        };
    }, []);

    const quitApplication = async () => {
        const token = document.querySelector<HTMLMetaElement>('meta[name="twitch-spy-shutdown-token"]')?.content;
        if (!token || token.startsWith("__TWITCH_SPY_")) return;
        await fetch(`${BACKEND_URL}/shutdown`, {
            method: "POST",
            headers: {"X-Twitch-Spy-Shutdown": token},
        });
        window.close();
    };

    const openMusicDirectory = async () => {
        const token = document.querySelector<HTMLMetaElement>('meta[name="twitch-spy-shutdown-token"]')?.content;
        try {
            const response = await fetch(`${BACKEND_URL}/open-music-directory`, {
                method: "POST",
                headers: token && !token.startsWith("__TWITCH_SPY_")
                    ? {"X-Twitch-Spy-Shutdown": token}
                    : {},
            });
            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                setDesktopMessage(data.error ?? `Could not open music folder (HTTP ${response.status})`);
                return;
            }
            setDesktopMessage("Music folder opened.");
        } catch (error) {
            setDesktopMessage(`Could not open music folder: ${String(error)}`);
        }
    };

    return (
        <div className={styles.appShell}>
            <aside className={styles.sidebar}>
                <div className={styles.brand}>
                    <div className={styles.brandTop}>
                        <span className={styles.badge}>yt-dlp</span>
                        <span
                            className={`${styles.statusDot} ${isConnected ? styles.dotOnline : styles.dotOffline}`}
                            title={isConnected ? "Backend connected" : "Backend disconnected"}
                        />
                    </div>
                    <h1 className={styles.appTitle}>twitch-spy</h1>
                    <p className={styles.appSubtitle}>music library</p>
                    <div className={styles.desktopActions}>
                        <button type="button" className={styles.desktopButton} onClick={() => { window.location.hash = "diagnostics"; setShowDiagnostics(true); }}>Health and logs</button>
                        <button type="button" className={styles.desktopButton} onClick={openMusicDirectory}>Open music folder</button>
                        <button type="button" className={styles.desktopButton} onClick={quitApplication}>Quit application</button>
                    </div>
                    {desktopMessage && <p className={styles.desktopMessage}>{desktopMessage}</p>}
                </div>

                <div className={styles.sidebarSection}>
                    <span className={styles.sectionLabel}>Download</span>
                    <URLInput socket={socket} />
                </div>

                <div className={styles.sidebarSection}>
                    <span className={styles.sectionLabel}>Queue</span>
                    <JobOverview socket={socket} />
                </div>

                <div className={styles.visualizerSlot}>
                    <Suspense fallback={<p>Loading visualizer...</p>}>
                        <SidebarVisualizer playback={playback} title={currentTrack?.content_name}/>
                    </Suspense>
                </div>

                <div className={`${styles.sidebarSection} ${styles.syncSection}`}>
                    <button type="button" className={styles.syncButton}
                        onClick={() => syncDialogRef.current?.showModal()}>
                        Sync to device
                    </button>
                </div>
            </aside>

            <dialog ref={syncDialogRef} className={styles.syncDialog} aria-labelledby="sync-title">
                <div className={styles.syncDialogHeader}>
                    <h2 id="sync-title">Sync to device</h2>
                    <button type="button" className={styles.desktopButton}
                        onClick={() => syncDialogRef.current?.close()}>Close</button>
                </div>
                <SyncPanel socket={socket} />
            </dialog>

            <main className={styles.mainContent}>
                {showDiagnostics && <Diagnostics onClose={() => { window.location.hash = ""; setShowDiagnostics(false); }} />}
                <JobList
                    socket={socket}
                    onMusicSelected={queue.selectTrack}
                    onPoolChanged={setPool}
                    currentTrack={currentTrack?.content_name}
                />
            </main>

            <div className={styles.nowPlayingDock}>
                <MusicPlayer entry={currentTrack} onPlaybackReady={setPlayback}
                    autoplay={queue.autoplay} onAutoplayChange={() => queue.setAutoplay(!queue.autoplay)}
                    shuffle={queue.shuffle} onShuffleChange={queue.toggleShuffle}
                    onNext={queue.next} onPrevious={queue.previous}
                    canNext={queue.canNext} canPrevious={queue.canPrevious} poolSize={pool.length}/>
            </div>
        </div>
    );
}

export default App;
