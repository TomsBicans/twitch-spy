import React, {useEffect, useRef, useState} from "react";
import {Socket} from "socket.io-client";
import {type Atom, ProcessingStates} from "../backend/models.ts";
import styles from "./JobList.module.css";

interface JobStatusesProps {
    socket: Socket;
    onMusicSelected: (selection: Atom) => void;
    currentTrack: string | undefined;
}

type SelectedProcessingState = ProcessingStates | "all";

const SongCard = React.memo(({job, onClick, isPlaying}: {
    job: Atom;
    onClick: () => void;
    isPlaying: boolean;
}) => {
    const cardRef = useRef<HTMLDivElement>(null);
    const [thumbnailVisible, setThumbnailVisible] = useState(false);

    useEffect(() => {
        const el = cardRef.current;
        if (!el) return;
        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setThumbnailVisible(true);
                    observer.disconnect();
                }
            },
            {rootMargin: "300px"},
        );
        observer.observe(el);
        return () => observer.disconnect();
    }, []);

    const thumbnail =
        thumbnailVisible && job.thumbnail_image_in_base64
            ? `data:image/jpeg;base64,${job.thumbnail_image_in_base64}`
            : "";

    const status = job.status.toLowerCase();
    const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);
    const statusClass = styles[status] ?? "";

    const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onClick();
        }
    };

    return (
        <div
            ref={cardRef}
            role="button"
            tabIndex={0}
            className={`${styles.card} ${statusClass} ${
                isPlaying ? styles.playing : ""
            }`}
            onClick={onClick}
            onKeyDown={handleKeyDown}
        >
            <div className={styles.thumbnail} style={{backgroundImage: `url(${thumbnail})`}} />
            <div className={styles.cardContent}>
                <div className={styles.cardHeader}>
                    <span className={styles.contentType}>
                        {job.content_type === "AUDIO" ? "Track" : job.content_type}
                    </span>
                    <span className={styles.statusChip}>{statusLabel}</span>
                </div>
                <h3 className={styles.jobName}>{job.content_name || "Untitled"}</h3>
                <p className={styles.jobUrl}>{job.url}</p>
            </div>
        </div>
    );
});

export const JobList = ({
                            socket,
                            onMusicSelected,
                            currentTrack,
                        }: JobStatusesProps) => {
    const [jobs, setJobs] = useState<Array<Atom>>([]);
    const [loading, setLoading] = useState(true);
    const [selectedJobProcessingState, setSelectedJobProcessingState] =
        useState<SelectedProcessingState>(ProcessingStates.FINISHED);
    const [searchQuery, setSearchQuery] = useState("");

    const updateAtomStatus = (data: Atom) => {
        setJobs((prevJobs) => {
            const existingJob = prevJobs.find((job) => job.id === data.id);
            if (existingJob) {
                return prevJobs.map((job) =>
                    job.id === data.id ? {...job, ...data} : job
                );
            }
            return [{...data}, ...prevJobs];
        });
    };

    useEffect(() => {
        const handleBatch = (data: Atom[]) => { setJobs(data); setLoading(false); };
        const handleUpdate = (data: Atom) => updateAtomStatus(data);

        socket.on("initial_jobs", handleBatch);
        socket.on("atom_update_status", handleUpdate);
        socket.emit("request_initial_data");

        return () => {
            socket.off("initial_jobs", handleBatch);
            socket.off("atom_update_status", handleUpdate);
        };
    }, [socket]);

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
        onMusicSelected(job);
    };

    const filteredJobs = filterJobs(
        jobs,
        selectedJobProcessingState,
        searchQuery.toLowerCase()
    );

    const emptyStateMessage = searchQuery
        ? "No matches yet. Try different keywords or clear the filters."
        : selectedJobProcessingState === ProcessingStates.FINISHED
            ? "Downloading is quiet. Finished tracks will land here once processed."
            : "Queue something new and we will list it right away.";

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div>
                    <h2 className={styles.title}>Library</h2>
                    <p className={styles.caption}>
                        Your downloaded tracks — click any to play.
                    </p>
                </div>
                <div className={styles.filterCluster}>
                    <label className={styles.filterLabel} htmlFor="statusFilter">
                        Status
                    </label>
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
            </div>
            <div className={styles.searchRow}>
                <div className={styles.searchField}>
                    <input
                        type="text"
                        placeholder="Search by title or URL"
                        value={searchQuery}
                        onChange={handleSearchChange}
                        className={styles.searchInput}
                        aria-label="Search tracks"
                    />
                </div>
            </div>
            <div className={styles.gridContainer}>
                {loading ? (
                    <div className={styles.loadingState}>
                        <span className={styles.spinner} aria-hidden="true" />
                        <p className={styles.loadingText}>Loading library…</p>
                    </div>
                ) : filteredJobs.length === 0 ? (
                    <div className={styles.emptyState}>
                        <span className={styles.emptyGlow} aria-hidden="true" />
                        <h3>Nothing here just yet</h3>
                        <p>{emptyStateMessage}</p>
                    </div>
                ) : (
                    filteredJobs.map((job) => (
                        <SongCard
                            key={job.id}
                            job={job}
                            onClick={() => handleCardClick(job)}
                            isPlaying={currentTrack === job.content_name}
                        />
                    ))
                )}
            </div>
        </div>
    );
};

export default JobList;
