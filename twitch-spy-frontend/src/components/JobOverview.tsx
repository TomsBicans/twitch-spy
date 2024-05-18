import React, { useEffect, useState } from "react";
import { Socket } from "socket.io-client";
import JobStat, {
  JobStatKey,
  JobStatistics,
  ProcessingStates,
} from "./util/JobStats";
import "./JobOverview.css";

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
          <JobStat
            key={key}
            processingState={key as JobStatKey}
            value={value}
          />
        ))}
      </div>
    </div>
  );
};

export default JobOverview;
