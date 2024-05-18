import React, { useState } from "react";
import { Socket } from "socket.io-client";
import { ProcessingStates } from "./util/JobStats";

enum PLATFORM {
  TWITCH = "TWITCH",
  YOUTUBE = "YOUTUBE",
  UNDEFINED = "UNDEFINED",
}

enum CONTENT_MODE {
  VIDEO = "VIDEO",
  AUDIO = "AUDIO",
  BOTH = "BOTH",
}

interface Atom {
  id: string; // UUID
  url: string;
  url_valid: boolean;
  platform: PLATFORM;
  single_item: boolean;
  content_type: CONTENT_MODE;
  content_name?: string; // Optional
  download_dir: string;
  status: ProcessingStates;
}

interface JobStatusesProps {
  socket: Socket;
}

export const JobStatuses = ({ socket }: JobStatusesProps) => {
  const [jobs, setJobs] = useState<Array<Atom>>([]);

  const updateAtomStatus = (data: Atom) => {
    setJobs((prevJobs) => {
      const existingJob = prevJobs.find((job) => job.id === data.id);
      if (existingJob) {
        return prevJobs.map((job) =>
          job.id === data.id ? { ...job, ...data } : job
        );
      }
      return [{ ...data }, ...prevJobs];
    });
  };

  socket.on("atom_update_status", (data) => {
    console.log(data);
    updateAtomStatus(data);
  });

  return (
    <div>
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

export default JobStatuses;
