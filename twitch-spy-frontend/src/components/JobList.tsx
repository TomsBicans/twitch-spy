import React, { useState } from "react";
import { Socket } from "socket.io-client";
import { Atom, ProcessingStates } from "../backend/models";
import styles from "./JobList.module.css";

interface JobStatusesProps {
  socket: Socket;
}

type SelectedProcessingState = ProcessingStates | "all";

export const JobList = ({ socket }: JobStatusesProps) => {
  const [jobs, setJobs] = useState<Array<Atom>>([]);
  const [selectedJobProcessingState, setSelectedJobProcessingState] =
    useState<SelectedProcessingState>(ProcessingStates.FINISHED);

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

  const getStatusEmoji = (status: string) => {
    switch (status.toLowerCase()) {
      case "finished":
        return "✅";
      case "processing":
        return "🔄";
      case "failed":
        return "❌";
      default:
        return "❓";
    }
  };

  const filterJobs = (
    jobs: Array<Atom>,
    processingState: SelectedProcessingState
  ) => {
    if (processingState === "all") {
      return jobs;
    }
    return jobs.filter((job) => job.status === processingState);
  };

  const handleFilterChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedJobProcessingState(
      event.target.value as SelectedProcessingState
    );
  };

  const filteredJobs = filterJobs(jobs, selectedJobProcessingState);

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Song List</h2>
      <div className={styles.filterContainer}>
        <label htmlFor="statusFilter">Filter by status: </label>
        <select
          id="statusFilter"
          value={selectedJobProcessingState}
          onChange={handleFilterChange}
          className={styles.filterSelect}
        >
          <option value="all">All</option>
          {Object.values(ProcessingStates).map((state) => (
            <option key={state} value={state}>
              {state}
            </option>
          ))}
        </select>
      </div>
      <div className={styles.gridContainer}>
        {filteredJobs.map((job) => (
          <div key={job.id} className={styles.card}>
            <div className={styles.cardHeader}>
              <span className={styles.contentType}>
                {job.content_type === "AUDIO" ? "🎵" : "🎵"}
              </span>
              <span className={styles.status}>
                {getStatusEmoji(job.status)}
              </span>
            </div>
            <h3 className={styles.jobName}>{job.content_name || "Unnamed"}</h3>
            <p className={styles.jobUrl}>{job.url}</p>
            <div
              className={`${styles.statusBar} ${styles[job.status.toLowerCase()]}`}
            >
              {job.status}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default JobList;
