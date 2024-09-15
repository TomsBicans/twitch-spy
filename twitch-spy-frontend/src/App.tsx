import React, { useState } from "react";
import io from "socket.io-client";
import "./App.css";
import URLInput from "./components/URLInput";
import JobList from "./components/JobList";
import JobOverview from "./components/JobOverview";
import SystemDashboard from "./components/system/SystemDashboard";
import MusicPlayer from "./components/AudioPlayer";
import styles from "./App.module.css";
import { BACKEND_URL } from "./backend/backend";
import { Atom } from "./backend/models";

const socket = io(BACKEND_URL);

const App: React.FC = () => {
  const [currentTrack, setCurrentTrack] = useState<Atom | undefined>(undefined);

  const onMusicSelected = (selection: Atom) => {
    setCurrentTrack(selection);
  };

  return (
    <div className="App">
      <h1>twitch-spy-music panel</h1>
      <div className={styles.container}>
        <div className={styles.innerPanel}>
          <URLInput />
        </div>
        <div className={styles.innerPanel}>
          <SystemDashboard />
        </div>
      </div>
      <MusicPlayer entry={currentTrack} />
      <JobOverview socket={socket} />
      <JobList
        socket={socket}
        onMusicSelected={onMusicSelected}
        currentTrack={currentTrack?.content_name}
      />
    </div>
  );
};

export default App;
