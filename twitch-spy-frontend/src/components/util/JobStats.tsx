import React from "react";
import { ProcessingStates } from "../../backend/models";

interface JobStatProps {
  processingState: ProcessingStates;
  value: number;
}

const JobStat = ({ processingState, value }: JobStatProps) => {
  let label: string;
  let className: string;

  switch (processingState) {
    case ProcessingStates.QUEUED:
      label = "Queued";
      className = "queued-class";
      break;
    case ProcessingStates.PROCESSING:
      label = "Processing";
      className = "processing-class";
      break;
    case ProcessingStates.FINISHED:
      label = "Finished";
      className = "finished-class";
      break;
    case ProcessingStates.CANCELLED:
      label = "Cancelled";
      className = "cancelled-class";
      break;
    case ProcessingStates.FAILED:
      label = "Failed";
      className = "failed-class";
      break;
    case ProcessingStates.INVALID:
      label = "Invalid";
      className = "invalid-class";
      break;
  }

  return (
    <div className={`stat ${className}`} key={processingState}>
      <span className="stat-value" id={processingState}>
        {value}
      </span>
      <span className="stat-label">{label}</span>
    </div>
  );
};

export default JobStat;
