import {useState} from 'react'
import './App.css'
import styles from "./App.module.css";
import URLInput from "./components/URLInput.tsx";
import SystemDashboard from "./components/system/SystemDashboard.tsx";
import MusicPlayer from "./components/AudioPlayer.tsx";
import type {Atom} from "./backend/models.ts";
import JobOverview from './components/JobOverview.tsx';
import JobList from './components/JobList.tsx';
import {BACKEND_URL} from "./backend/backend.ts";
import {io} from "socket.io-client";

const socket = io(BACKEND_URL);

function App() {
    const [currentTrack, setCurrentTrack] = useState<Atom | undefined>(undefined);

    const onMusicSelected = (selection: Atom) => {
        setCurrentTrack(selection);
    };

    return (
        <>
            <div>
                <h1>twitch-spy-music panel</h1>
                <div className={styles.container}>
                    <div className={styles.innerPanel}>
                        <URLInput/>
                    </div>
                    <div className={styles.innerPanel}>
                        <SystemDashboard/>
                    </div>
                </div>
                <MusicPlayer entry={currentTrack}/>
                <JobOverview socket={socket}/>
                <JobList
                    socket={socket}
                    onMusicSelected={onMusicSelected}
                    currentTrack={currentTrack?.content_name}
                />
            </div>
        </>
    )
}

export default App
