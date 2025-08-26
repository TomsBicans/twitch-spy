import React from "react";
import { ProcessingStates } from "../../backend/models.ts";
import styles from "./JobStats.module.css";

interface JobStatProps {
  processingState: ProcessingStates;
  value: number;
}

const JobStat = ({ processingState, value }: JobStatProps) => {
  let label: string;
  let icon: string;

  switch (processingState) {
    case ProcessingStates.QUEUED:
      label = "Queued";
      icon = "🕒";
      break;
    case ProcessingStates.PROCESSING:
      label = "Processing";
      icon = "⚙️";
      break;
    case ProcessingStates.FINISHED:
      label = "Finished";
      icon = "✅";
      break;
    case ProcessingStates.CANCELLED:
      label = "Cancelled";
      icon = "🚫";
      break;
    case ProcessingStates.FAILED:
      label = "Failed";
      icon = "❌";
      break;
    case ProcessingStates.INVALID:
      label = "Invalid";
      icon = "⚠️";
      break;
  }

  return (
    <div
      className={`${styles.stat} ${styles[processingState]}`}
      key={processingState}
    >
      <span className={styles.icon}>{icon}</span>
      <span className={styles.statValue} id={processingState}>
        {value}
      </span>
      <span className={styles.statLabel}>{label}</span>
    </div>
  );
};

export default JobStat;
