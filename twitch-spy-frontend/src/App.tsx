import React, { useEffect, useState } from "react";
import io from "socket.io-client";
import "./App.css";
import URLInput from "./components/URLInput";

const socket = io(window.location.origin);

const App: React.FC = () => {
  const [jobStats, setJobStats] = useState({
    queued: 0,
    processing: 0,
    finished: 0,
    cancelled: 0,
    failed: 0,
    invalid: 0,
  });

  const [jobs, setJobs] = useState<Array<any>>([]);

  useEffect(() => {
    socket.on("atom_update_status", (data) => {
      console.log(data);
      updateAtomStatus(data);
    });

    socket.on("statistics_update", (data) => {
      console.log(data);
      setJobStats((prevStats) => ({
        ...prevStats,
        ...data,
      }));
    });

    socket.emit("request_initial_data");
  }, []);

  const updateAtomStatus = (data: any) => {
    setJobs((prevJobs) => {
      const existingJob = prevJobs.find((job) => job.id === data.id);
      if (existingJob) {
        return prevJobs.map((job) =>
          job.id === data.id ? { ...job, ...data } : job,
        );
      }
      return [{ ...data }, ...prevJobs];
    });
  };

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

      <h2>Job Statuses</h2>
      <table className="jobs-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Content type</th>
            <th>URL</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="jobStatuses">
          {jobs.map((job) => (
            <tr
              key={job.id}
              id={job.id}
              className={`tr-status-${job.status.toLowerCase()}`}
            >
              <td>{job.content_name}</td>
              <td>{job.content_type}</td>
              <td>{job.url}</td>
              <td className={`statusColumn status-${job.status.toLowerCase()}`}>
                {job.status}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default App;
