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
  const [trackColor, setTrackColor] = useState<string>("#4a4a4a");

  useEffect(() => {
    if (entry) {
      setCurrentTrack(`${BACKEND_URL}/audio/${entry.content_name}`);
      // You would need to implement a function to get the dominant color of the track
      // For now, we'll use a placeholder function
      setTrackColor(getRandomColor());
    }
  }, [entry]);

  const handleNextTrack = () => {
    console.log("Next track functionality can be implemented here.");
    // Implement logic to fetch or select the next track title and update the state
  };

  // Updated function to generate a valid random color
  const getRandomColor = () => {
    return (
      "#" +
      Math.floor(Math.random() * 16777215)
        .toString(16)
        .padStart(6, "0")
    );
  };

  return (
    <>
      <CurrentTrackDisplay title={entry?.content_name} color={trackColor} />
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
