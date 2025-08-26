import React, { useEffect, useState } from "react";
import AudioPlayer from "react-h5-audio-player";
import "react-h5-audio-player/lib/styles.css";
import { BACKEND_URL } from "../backend/backend.ts";
import CurrentTrackDisplay from "./CurrentTrackDisplay.tsx";
import { Atom } from "../backend/models.ts";

interface AudioPlayerProps {
  entry: Atom | undefined;
}

const MusicPlayer: React.FC<AudioPlayerProps> = ({ entry }) => {
  const [currentTrack, setCurrentTrack] = useState<string | undefined>();
  const [trackColor, setTrackColor] = useState<string>("#4a4a4a");

  useEffect(() => {
    if (entry) {
      setCurrentTrack(`${BACKEND_URL}/audio/${entry.content_name}`);
      if (entry.thumbnail_image_in_base64) {
        getAverageColor(entry.thumbnail_image_in_base64).then(setTrackColor);
      } else {
        setTrackColor(getRandomColor());
      }
    }
  }, [entry]);

  const getAverageColor = (base64Image: string): Promise<string> => {
    return new Promise((resolve) => {
      const img = new Image();
      img.src = `data:image/jpeg;base64,${base64Image}`;
      img.onload = () => {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          resolve(getRandomColor());
          return;
        }
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0, img.width, img.height);
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imageData.data;
        let r = 0,
          g = 0,
          b = 0;
        let count = 0;

        for (let i = 0; i < data.length; i += 4) {
          // Skip transparent pixels
          if (data[i + 3] < 255) continue;

          r += data[i];
          g += data[i + 1];
          b += data[i + 2];
          count++;
        }

        if (count > 0) {
          r = Math.round(r / count);
          g = Math.round(g / count);
          b = Math.round(b / count);
          resolve(`rgb(${r},${g},${b})`);
        } else {
          resolve(getRandomColor());
        }
      };
      img.onerror = () => {
        resolve(getRandomColor());
      };
    });
  };

  const handleNextTrack = () => {
    console.log("Next track functionality can be implemented here.");
    // Implement logic to fetch or select the next track title and update the state
  };

  const getRandomColor = () => {
    const r = Math.floor(Math.random() * 256);
    const g = Math.floor(Math.random() * 256);
    const b = Math.floor(Math.random() * 256);
    return `rgb(${r},${g},${b})`;
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
