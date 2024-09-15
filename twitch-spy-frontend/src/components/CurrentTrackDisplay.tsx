import React from "react";
import styles from "./CurrentTrackDisplay.module.css";

interface CurrentTrackDisplayProps {
  title: string | undefined;
}

const CurrentTrackDisplay: React.FC<CurrentTrackDisplayProps> = ({ title }) => {
  return (
    <div className={styles.container}>
      <div className={styles.nowPlaying}>Now Playing</div>
      <div className={styles.trackTitle}>{title || "No track selected"}</div>
    </div>
  );
};

export default CurrentTrackDisplay;
