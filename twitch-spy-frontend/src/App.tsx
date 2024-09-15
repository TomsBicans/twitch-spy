import React, { useState } from "react";
import io from "socket.io-client";
import "./App.css";
import URLInput from "./components/URLInput";
import JobList, { MusicEntity } from "./components/JobList";
import JobOverview from "./components/JobOverview";
import SystemDashboard from "./components/system/SystemDashboard";
import MusicPlayer from "./components/AudioPlayer";
import styles from "./App.module.css";
import { BACKEND_URL } from "./backend/backend";

const socket = io(BACKEND_URL);

const App: React.FC = () => {
  const [currentTrack, setCurrentTrack] = useState<string | undefined>(
    undefined
  );

  const onMusicSelected = (selection: MusicEntity) => {
    setCurrentTrack(selection.title);
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
      <MusicPlayer title={currentTrack} />
      <JobOverview socket={socket} />
      <JobList
        socket={socket}
        onMusicSelected={onMusicSelected}
        currentTrack={currentTrack}
      />
    </div>
  );
};

export default App;
