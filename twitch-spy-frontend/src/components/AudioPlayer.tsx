import React, { useEffect, useState } from "react";
import AudioPlayer from "react-h5-audio-player";
import "react-h5-audio-player/lib/styles.css";
import { BACKEND_URL } from "../backend/backend";
import CurrentTrackDisplay from "./CurrentTrackDisplay";

interface AudioPlayerProps {
  title: string | undefined;
}

const MusicPlayer: React.FC<AudioPlayerProps> = ({ title }) => {
  const [currentTrack, setCurrentTrack] = useState<string | undefined>();

  useEffect(() => {
    if (title) {
      setCurrentTrack(`${BACKEND_URL}/audio/${title}`);
    }
  }, [title]);

  const handleNextTrack = () => {
    console.log("Next track functionality can be implemented here.");
    // Implement logic to fetch or select the next track title and update the state
  };

  return (
    <>
      <CurrentTrackDisplay title={title} />
      <AudioPlayer
        autoPlay
        src={currentTrack}
        showJumpControls={true}
        onEnded={handleNextTrack}
        style={{
          backgroundColor: title ? "#f5f5f5" : "#e5e5e5",
          color: title ? "#000" : "#808080",
        }}
      />
    </>
  );
};

export default MusicPlayer;
