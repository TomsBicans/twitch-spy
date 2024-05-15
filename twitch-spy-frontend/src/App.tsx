import React, { useEffect, useState } from "react";
import io from "socket.io-client";
import "./App.css";
import URLInput from "./components/URLInput";
import JobList from "./components/JobList";

const socket = io("localhost:5000"); // Socket to backend

const App: React.FC = () => {
  const [jobStats, setJobStats] = useState({
    queued: 0,
    processing: 0,
    finished: 0,
    cancelled: 0,
    failed: 0,
    invalid: 0,
  });

  useEffect(() => {
    socket.on("statistics_update", (data) => {
      console.log(data);
      setJobStats((prevStats) => ({
        ...prevStats,
        ...data,
      }));
    });

    socket.emit("request_initial_data");
  }, []);

  return (
    <div className="App">
      <h1>yt-dlp-music panel</h1>

      <URLInput />
      <h2>Job Statistics</h2>
      <div id="jobStats">
        {Object.entries(jobStats).map(([key, value]) => (
          <div className="stat" key={key}>
            <span className="stat-value" id={key}>
              {value}
            </span>
            <span className="stat-label">
              {key.charAt(0).toUpperCase() + key.slice(1)}
            </span>
          </div>
        ))}
      </div>

      <JobList socket={socket} />
    </div>
  );
};

export default App;
