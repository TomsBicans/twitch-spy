import React, { useEffect, useRef, useState } from "react";
import { Socket } from "socket.io-client";

interface JobOverviewProps {
  socket: Socket;
}

export const JobOverview = ({ socket }: JobOverviewProps) => {
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
    <div>
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
    </div>
  );
};

export default JobOverview;
