import React, {useEffect, useRef, useState} from "react";
import {Socket} from "socket.io-client";
import {type Atom, ProcessingStates} from "../backend/models.ts";
import styles from "./JobList.module.css";
import {BACKEND_URL} from "../backend/backend.ts";

interface JobStatusesProps {
    socket: Socket;
    onMusicSelected: (selection: Atom) => void;
    currentTrack: string | undefined;
}

type SelectedProcessingState = ProcessingStates | "all";
const PAGE_SIZE = 48;

interface LibraryPage {
    jobs: Atom[];
    total: number;
    next_offset: number | null;
}

const RETRIABLE_STATES = new Set<ProcessingStates>([
    ProcessingStates.FAILED,
    ProcessingStates.INVALID,
    ProcessingStates.CANCELLED,
]);

const SongCard = React.memo(({job, onClick, isPlaying, onRetry}: {
    job: Atom;
    onClick: () => void;
    isPlaying: boolean;
    onRetry: () => void;
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

    const thumbnail = thumbnailVisible
        ? job.thumbnail_image_in_base64
            ? `data:image/jpeg;base64,${job.thumbnail_image_in_base64}`
            : job.thumbnail_url ? `${BACKEND_URL}${job.thumbnail_url}` : ""
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
                {job.status === ProcessingStates.FAILED && (
                    <details
                        className={styles.errorDetails}
                        onClick={(event) => event.stopPropagation()}
                        onKeyDown={(event) => event.stopPropagation()}
                    >
                        <summary>Error details</summary>
                        <pre>{job.error_message || "Error details were not recorded. Retry this download to capture the reason."}</pre>
                    </details>
                )}
                {RETRIABLE_STATES.has(job.status) && (
                    <button
                        className={styles.retryButton}
                        onClick={(e) => { e.stopPropagation(); onRetry(); }}
                        aria-label="Retry download"
                    >
                        Retry
                    </button>
                )}
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
    const [total, setTotal] = useState(0);
    const [loadError, setLoadError] = useState("");
    const [reloadKey, setReloadKey] = useState(0);
    const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
    const [selectedJobProcessingState, setSelectedJobProcessingState] =
        useState<SelectedProcessingState>(ProcessingStates.FINISHED);
    const [searchQuery, setSearchQuery] = useState("");

    useEffect(() => {
        let controller: AbortController;
        let nextPageTimer: ReturnType<typeof setTimeout>;
        const updates = new Map<string, Atom>();
        const handleUpdate = (data: Atom) => {
            updates.set(data.id, data);
            setJobs((previous) => previous.some((job) => job.id === data.id)
                ? previous.map((job) => job.id === data.id ? {...job, ...data} : job)
                : [data, ...previous]);
        };
        const requestData = () => {
            controller?.abort();
            clearTimeout(nextPageTimer);
            controller = new AbortController();
            const {signal} = controller;
            const received = new Map<string, Atom>();
            updates.clear();
            setLoading(true);
            setLoadError("");

            const loadPage = async (offset: number) => {
                try {
                    const response = await fetch(`${BACKEND_URL}/library?offset=${offset}`, {signal});
                    if (!response.ok) throw new Error(`Library request failed (${response.status})`);
                    const page: LibraryPage = await response.json();
                    if (signal.aborted) return;
                    for (const job of page.jobs) received.set(job.id, job);
                    // Live status changes take precedence over an in-flight page.
                    for (const [id, job] of updates) received.set(id, {...received.get(id), ...job});
                    const snapshot = [...received.values()];
                    setJobs((previous) => {
                        if (page.next_offset === null) return snapshot;
                        const merged = new Map(previous.map((job) => [job.id, job]));
                        for (const job of snapshot) merged.set(job.id, job);
                        return [...merged.values()];
                    });
                    setTotal(page.total);
                    const nextOffset = page.next_offset;
                    if (nextOffset === null) {
                        setLoading(false);
                    } else {
                        // Give the browser a chance to paint before requesting another batch.
                        nextPageTimer = setTimeout(() => void loadPage(nextOffset), 50);
                    }
                } catch (error) {
                    if (signal.aborted) return;
                    console.error("Library loading failed:", error);
                    setLoadError("Could not finish loading the library. Your loaded tracks are still available.");
                    setLoading(false);
                }
            };
            void loadPage(0);
        };

        socket.on("atom_update_status", handleUpdate);
        socket.on("connect", requestData);
        requestData();

        return () => {
            controller.abort();
            clearTimeout(nextPageTimer);
            socket.off("atom_update_status", handleUpdate);
            socket.off("connect", requestData);
        };
    }, [socket, reloadKey]);

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
        setVisibleCount(PAGE_SIZE);
    };

    const handleFilterChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
        setVisibleCount(PAGE_SIZE);
        setSelectedJobProcessingState(
            event.target.value as SelectedProcessingState
        );
    };

    const handleCardClick = (job: Atom) => {
        onMusicSelected(job);
    };

    const handleRetry = async (job: Atom) => {
        try {
            await fetch(`${BACKEND_URL}/jobs/${job.id}/retry`, {method: "POST"});
        } catch (error) {
            console.error("Retry failed:", error);
        }
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
            {loading && (
                <p className={styles.loadingText} role="status">
                    {jobs.length === 0 ? "Loading your first tracks…" :
                        `Loading library… ${jobs.length} of ${Math.max(total, jobs.length)} tracks available. You can already browse and play.`}
                </p>
            )}
            {loadError && (
                <div role="alert">
                    <p>{loadError}</p>
                    <button className={styles.filterSelect} onClick={() => setReloadKey((key) => key + 1)}>Retry loading</button>
                </div>
            )}
            <div className={styles.gridContainer}>
                {loading && jobs.length === 0 ? (
                    Array.from({length: 6}, (_, index) => (
                        <div key={index} className={styles.skeletonCard} aria-hidden="true">
                            <span /><span /><span />
                        </div>
                    ))
                ) : filteredJobs.length === 0 && !loadError ? (
                    <div className={styles.emptyState}>
                        <span className={styles.emptyGlow} aria-hidden="true" />
                        <h3>{loading ? "Looking for matching tracks…" : "Nothing here just yet"}</h3>
                        <p>{loading ? "More tracks are still loading. Matches will appear here as they arrive." : emptyStateMessage}</p>
                    </div>
                ) : (
                    filteredJobs.slice(0, visibleCount).map((job) => (
                        <SongCard
                            key={job.id}
                            job={job}
                            onClick={() => handleCardClick(job)}
                            isPlaying={currentTrack === job.content_name}
                            onRetry={() => handleRetry(job)}
                        />
                    ))
                )}
            </div>
            {filteredJobs.length > 0 && (
                <div className={styles.listFooter}>
                    <p className={styles.loadingText}>
                        Showing {Math.min(visibleCount, filteredJobs.length)} of {filteredJobs.length} matching tracks{loading ? " loaded so far" : ""}
                    </p>
                    {visibleCount < filteredJobs.length && (
                        <button className={styles.filterSelect} onClick={() => setVisibleCount((count) => count + PAGE_SIZE)}>
                            Show more tracks
                        </button>
                    )}
                </div>
            )}
        </div>
    );
};

export default JobList;
