import React, { useState } from "react";
import { Socket } from "socket.io-client";
import { Atom } from "../backend/models";

interface JobStatusesProps {
  socket: Socket;
}

export const JobList = ({ socket }: JobStatusesProps) => {
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
              <td>
                <a href={job.url}>{job.url}</a>
              </td>
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

export default JobList;
