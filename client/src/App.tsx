import {useEffect, useState} from "react";
import "./App.css";
import styles from "./App.module.css";
import URLInput from "./components/URLInput.tsx";
import MusicPlayer from "./components/AudioPlayer.tsx";
import type {Atom} from "./backend/models.ts";
import JobOverview from "./components/JobOverview.tsx";
import JobList from "./components/JobList.tsx";
import SyncPanel from "./components/SyncPanel.tsx";
import {BACKEND_URL} from "./backend/backend.ts";
import {io} from "socket.io-client";

const socket = io(BACKEND_URL);

function App() {
    const [currentTrack, setCurrentTrack] = useState<Atom | undefined>(undefined);
    const [isConnected, setIsConnected] = useState<boolean>(socket.connected);

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
                </div>

                <div className={styles.sidebarSection}>
                    <span className={styles.sectionLabel}>Download</span>
                    <URLInput />
                </div>

                <div className={styles.sidebarSection}>
                    <span className={styles.sectionLabel}>Queue</span>
                    <JobOverview socket={socket} />
                </div>

                <div className={styles.sidebarSection}>
                    <span className={styles.sectionLabel}>Sync to device</span>
                    <SyncPanel socket={socket} />
                </div>
            </aside>

            <main className={styles.mainContent}>
                <JobList
                    socket={socket}
                    onMusicSelected={(atom) => setCurrentTrack(atom)}
                    currentTrack={currentTrack?.content_name}
                />
            </main>

            <div className={styles.nowPlayingDock}>
                <MusicPlayer entry={currentTrack} />
            </div>
        </div>
    );
}

export default App;
