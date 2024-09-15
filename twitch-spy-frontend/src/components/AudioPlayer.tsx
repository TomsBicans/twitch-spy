import React, { useEffect, useState } from "react";
import AudioPlayer from "react-h5-audio-player";
import "react-h5-audio-player/lib/styles.css";
import { BACKEND_URL } from "../backend/backend";
import CurrentTrackDisplay from "./CurrentTrackDisplay";
import { Atom } from "../backend/models";

interface AudioPlayerProps {
  entry: Atom | undefined;
}

const MusicPlayer: React.FC<AudioPlayerProps> = ({ entry }) => {
  const [currentTrack, setCurrentTrack] = useState<string | undefined>();

  useEffect(() => {
    if (entry) {
      setCurrentTrack(`${BACKEND_URL}/audio/${entry.content_name}`);
    }
  }, [entry]);

  const handleNextTrack = () => {
    console.log("Next track functionality can be implemented here.");
    // Implement logic to fetch or select the next track title and update the state
  };

  return (
    <>
      <CurrentTrackDisplay title={entry?.content_name} />
      <AudioPlayer
        autoPlay
        src={currentTrack}
        showJumpControls={true}
        onEnded={handleNextTrack}
        style={{
          backgroundColor: entry ? "#f5f5f5" : "#e5e5e5",
          color: entry ? "#000" : "#808080",
        }}
      />
    </>
  );
};

export default MusicPlayer;
