import {useEffect, useMemo, useState} from "react";
import {Socket} from "socket.io-client";
import JobStat from "./util/JobStats.tsx";
import {type JobStatistics, ProcessingStates} from "../backend/models.ts";
import styles from "./JobOverview.module.css";

interface JobOverviewProps {
    socket: Socket;
}

export const JobOverview = ({socket}: JobOverviewProps) => {
    const [jobStats, setJobStats] = useState<JobStatistics>({
        [ProcessingStates.QUEUED]: 0,
        [ProcessingStates.PROCESSING]: 0,
        [ProcessingStates.FINISHED]: 0,
        [ProcessingStates.FAILED]: 0,
        [ProcessingStates.CANCELLED]: 0,
        [ProcessingStates.INVALID]: 0,
    });

    const panelConfig = [
        {state: ProcessingStates.QUEUED, visible: true},
        {state: ProcessingStates.PROCESSING, visible: true},
        {state: ProcessingStates.FAILED, visible: true},
        {state: ProcessingStates.FINISHED, visible: true},
        {state: ProcessingStates.CANCELLED, visible: false},
        {state: ProcessingStates.INVALID, visible: false},
    ];

    useEffect(() => {
        const handleStatsUpdate = (data: JobStatistics) => {
            setJobStats((prevStats) => ({
                ...prevStats,
                ...data,
            }));
        };

        socket.on("statistics_update", handleStatsUpdate);
        socket.emit("request_initial_data");

        return () => {
            socket.off("statistics_update", handleStatsUpdate);
        };
    }, [socket]);

    const totalJobs = useMemo(
        () =>
            panelConfig
                .filter((config) => config.visible)
                .reduce((acc, config) => acc + jobStats[config.state], 0),
        [jobStats]
    );

    const isCalm = totalJobs === 0;

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h2 className={styles.title}>Download pulse</h2>
                <p className={styles.caption}>
                    {isCalm
                        ? "The queue is relaxed. Drop some links to get the vibe going."
                        : "Live snapshot of queued, processing, finished, and failed downloads."}
                </p>
            </div>
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
