import React, { useState } from "react";
import io from "socket.io-client";
import "./App.css";
import URLInput from "./components/URLInput";
import JobList from "./components/JobList";
import LocalLibraryStatistics from "./components/JobOverview";
import SystemDashboard from "./components/system/SystemDashboard";
import MusicPlayer from "./components/AudioPlayer";
import styles from "./App.module.css";
import { BACKEND_URL } from "./backend/backend";
import { Atom } from "./backend/models";
import { Settings } from "lucide-react";

const socket = io(BACKEND_URL);

const App: React.FC = () => {
  const [currentTrack, setCurrentTrack] = useState<Atom | undefined>(undefined);
  const [isSystemDashboardExpanded, setIsSystemDashboardExpanded] =
    useState(false);

  const onMusicSelected = (selection: Atom) => {
    setCurrentTrack(selection);
  };

  const toggleSystemDashboard = () => {
    setIsSystemDashboardExpanded(!isSystemDashboardExpanded);
  };

  return (
    <div className="App">
      <h1>twitch-spy-music panel</h1>
      <div
        className={`${styles.containerWrapper} ${isSystemDashboardExpanded ? styles.expanded : ""}`}
      >
        <div
          className={styles.systemDashboardHeader}
          onClick={toggleSystemDashboard}
        >
          <h2>System Dashboard</h2>
          <Settings className={styles.gearIcon} />
        </div>
        <div className={styles.container}>
          <div className={styles.innerPanel}>
            <URLInput />
          </div>
          <div className={styles.innerPanel}>
            <SystemDashboard />
          </div>
          <div className={styles.innerPanel}>
            <LocalLibraryStatistics socket={socket} />
          </div>
        </div>
      </div>
      <MusicPlayer entry={currentTrack} />

      <JobList
        socket={socket}
        onMusicSelected={onMusicSelected}
        currentTrack={currentTrack?.content_name}
      />
    </div>
  );
};

export default App;
