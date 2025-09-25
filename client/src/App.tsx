import {useEffect, useState} from "react";
import "./App.css";
import styles from "./App.module.css";
import URLInput from "./components/URLInput.tsx";
import SystemDashboard from "./components/system/SystemDashboard.tsx";
import MusicPlayer from "./components/AudioPlayer.tsx";
import type {Atom} from "./backend/models.ts";
import JobOverview from "./components/JobOverview.tsx";
import JobList from "./components/JobList.tsx";
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

    const onMusicSelected = (selection: Atom) => {
        setCurrentTrack(selection);
    };

    return (
        <div className={styles.appShell}>
            <header className={styles.header}>
                <div className={styles.branding}>
                    <span className={styles.badge}>yt-dlp companion</span>
                    <h1 className={styles.title}>twitch-spy music studio</h1>
                    <p className={styles.subtitle}>
                        Queue fresh tracks, watch the pipeline, keep the ambience.
                    </p>
                </div>
                <div className={styles.statusCluster}>
                    <span
                        className={`${styles.statusPill} ${
                            isConnected ? styles.statusPillOnline : styles.statusPillOffline
                        }`}
                    >
                        {isConnected ? "Live backend connection" : "Backend disconnected"}
                    </span>
                    {currentTrack && (
                        <span className={styles.nowPlayingHint}>
                            Now playing: {currentTrack.content_name}
                        </span>
                    )}
                </div>
            </header>

            <main className={styles.mainGrid}>
                <section className={styles.panel}>
                    <URLInput />
                </section>
                <section className={styles.panel}>
                    <SystemDashboard />
                </section>
                <section className={styles.panel}>
                    <JobOverview socket={socket} />
                </section>
                <section className={`${styles.panel} ${styles.libraryPanel}`}>
                    <JobList
                        socket={socket}
                        onMusicSelected={onMusicSelected}
                        currentTrack={currentTrack?.content_name}
                    />
                </section>
            </main>
            <div className={styles.playerSpacer} aria-hidden="true" />
            <div className={styles.nowPlayingDock}>
                <section className={`${styles.panel} ${styles.nowPlayingPanel}`}>
                    <div className={styles.nowPlayingContent}>
                        <MusicPlayer entry={currentTrack} />
                    </div>
                </section>
            </div>
        </div>
    );
}

export default App;
