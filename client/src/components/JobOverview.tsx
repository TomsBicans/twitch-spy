import React, { useEffect, useState } from "react";
import { Socket } from "socket.io-client";
import JobStat from "./util/JobStats.tsx";
import { JobStatistics, ProcessingStates } from "../backend/models.ts";
import styles from "./JobOverview.module.css";

interface JobOverviewProps {
  socket: Socket;
}

export const JobOverview = ({ socket }: JobOverviewProps) => {
  const [jobStats, setJobStats] = useState<JobStatistics>({
    [ProcessingStates.QUEUED]: 0,
    [ProcessingStates.PROCESSING]: 0,
    [ProcessingStates.FINISHED]: 0,
    [ProcessingStates.FAILED]: 0,
    [ProcessingStates.CANCELLED]: 0,
    [ProcessingStates.INVALID]: 0,
  });

  const panelConfig = [
    { state: ProcessingStates.QUEUED, visible: true },
    { state: ProcessingStates.PROCESSING, visible: true },
    { state: ProcessingStates.FAILED, visible: true },
    { state: ProcessingStates.FINISHED, visible: true },
    { state: ProcessingStates.CANCELLED, visible: false },
    { state: ProcessingStates.INVALID, visible: false },
  ];

  useEffect(() => {
    socket.on("statistics_update", (data) => {
      // console.log(data);
      setJobStats((prevStats) => ({
        ...prevStats,
        ...data,
      }));
    });

    socket.emit("request_initial_data");
  }, []);

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Local Library Statistics</h2>
      <div className={styles.jobStats}>
        {panelConfig
          .filter((config) => config.visible)
          .map((config) => (
            <JobStat
              key={config.state}
              processingState={config.state}
              value={jobStats[config.state]}
            />
          ))}
      </div>
    </div>
  );
};

export default JobOverview;
