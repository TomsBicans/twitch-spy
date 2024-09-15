import React, { useEffect, useRef } from "react";
import styles from "./CurrentTrackDisplay.module.css";

interface CurrentTrackDisplayProps {
  title: string | undefined;
  color: string;
}

const CurrentTrackDisplay: React.FC<CurrentTrackDisplayProps> = ({
  title,
  color,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const validateColor = (color: string): string => {
    const hexRegex = /^#?([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/;
    if (hexRegex.test(color)) {
      return color.startsWith("#") ? color : `#${color}`;
    }
    return "#000000"; // Default to black if invalid
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;

    const resizeCanvas = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };

    const createGradient = (time: number) => {
      const gradient = ctx.createLinearGradient(
        0,
        0,
        canvas.width,
        canvas.height
      );
      const validColor = validateColor(color);
      const secondColor = adjustColor(validColor, 30);

      const offset1 = (Math.sin(time * 0.1) + 1) / 2;
      const offset2 = (Math.sin(time * 0.1 + Math.PI) + 1) / 2;

      gradient.addColorStop(offset1, validColor);
      gradient.addColorStop(offset2, secondColor);

      return gradient;
    };

    const adjustColor = (color: string, amount: number) => {
      const hex = color.replace("#", "");
      const num = parseInt(hex, 16);
      const r = Math.min(255, Math.max(0, (num >> 16) + amount));
      const g = Math.min(255, Math.max(0, ((num >> 8) & 0x00ff) + amount));
      const b = Math.min(255, Math.max(0, (num & 0x0000ff) + amount));
      return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, "0")}`;
    };

    const animate = () => {
      const time = Date.now() * 0.001;
      const gradient = createGradient(time);

      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      animationFrameId = requestAnimationFrame(animate);
    };

    resizeCanvas();
    animate();

    window.addEventListener("resize", resizeCanvas);

    return () => {
      window.removeEventListener("resize", resizeCanvas);
      cancelAnimationFrame(animationFrameId);
    };
  }, [color]);

  return (
    <div className={styles.container}>
      <canvas ref={canvasRef} className={styles.backgroundCanvas} />
      <div className={styles.contentWrapper}>
        <div className={styles.content}>
          <div className={styles.nowPlaying}>Now Playing</div>
          <div className={styles.trackTitle}>
            {title || "No track selected"}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CurrentTrackDisplay;
