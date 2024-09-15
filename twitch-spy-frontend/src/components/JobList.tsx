import React, { useState } from "react";
import { Socket } from "socket.io-client";
import { Atom, ProcessingStates } from "../backend/models";
import styles from "./JobList.module.css";

interface JobStatusesProps {
  socket: Socket;
  onMusicSelected: (selection: MusicEntity) => void;
  currentTrack: string | undefined;
}

export interface MusicEntity {
  url: string;
  title: string;
}

type SelectedProcessingState = ProcessingStates | "all";

const SongCard = ({
  job,
  onClick,
  isPlaying,
}: {
  job: Atom;
  onClick: () => void;
  isPlaying: boolean;
}) => {
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

  const thumbnail = job.thumbnail_image_in_base64
    ? `data:image/jpeg;base64,${job.thumbnail_image_in_base64}`
    : "";
  return (
    <div
      className={`${styles.card} ${isPlaying ? styles.playing : ""}`}
      style={{ backgroundImage: `url(${thumbnail})` }}
      onClick={onClick}
    >
      <div className={styles.cardHeader}>
        <span className={styles.contentType}>
          {job.content_type === "AUDIO" ? "🎵" : "🎵"}
        </span>
        <span className={styles.status}>{getStatusEmoji(job.status)}</span>
      </div>
      <h3 className={styles.jobName}>{job.content_name || "Unnamed"}</h3>
      <p className={styles.jobUrl}>{job.url}</p>
      <div
        className={`${styles.statusBar} ${styles[job.status.toLowerCase()]}`}
      >
        {job.status}
      </div>
    </div>
  );
};

export const JobList = ({
  socket,
  onMusicSelected,
  currentTrack,
}: JobStatusesProps) => {
  const [jobs, setJobs] = useState<Array<Atom>>([]);
  const [selectedJobProcessingState, setSelectedJobProcessingState] =
    useState<SelectedProcessingState>(ProcessingStates.FINISHED);
  const [searchQuery, setSearchQuery] = useState("");

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

  const filterJobs = (
    jobs: Array<Atom>,
    processingState: SelectedProcessingState,
    query: string
  ) => {
    const tokenizedQuery = query.split(" ").filter((q) => q.length > 0);
    return jobs.filter((job) => {
      const matchesState =
        processingState === "all" || job.status === processingState;
      const matchesQuery =
        tokenizedQuery.length === 0 ||
        tokenizedQuery.every(
          (token) =>
            (job.content_name?.toLowerCase() || "").includes(token) ||
            job.url.toLowerCase().includes(token)
        );
      return matchesState && matchesQuery;
    });
  };

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value);
  };

  const handleFilterChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedJobProcessingState(
      event.target.value as SelectedProcessingState
    );
  };

  const handleCardClick = (job: Atom) => {
    onMusicSelected({ url: job.url, title: job.content_name || "Unnamed" });
  };

  const filteredJobs = filterJobs(
    jobs,
    selectedJobProcessingState,
    searchQuery
  );

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
        <input
          type="text"
          placeholder="Search songs..."
          value={searchQuery}
          onChange={handleSearchChange}
          className={styles.searchInput}
        />
      </div>
      <div className={styles.gridContainer}>
        {filteredJobs.map((job) => (
          <SongCard
            key={job.id}
            job={job}
            onClick={() => handleCardClick(job)}
            isPlaying={currentTrack === job.content_name}
          />
        ))}
      </div>
    </div>
  );
};

export default JobList;
