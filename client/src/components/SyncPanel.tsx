import React, {useEffect, useState} from "react";
import {Socket} from "socket.io-client";
import {BACKEND_URL} from "../backend/backend.ts";
import type {SyncPlan, SyncProgress, SyncResult} from "../backend/models.ts";
import styles from "./SyncPanel.module.css";

interface SyncPanelProps {
    socket: Socket;
}

type Phase =
    | {tag: "idle"}
    | {tag: "checking"}
    | {tag: "no_device"}
    | {tag: "device_ready"; devices: string[]}
    | {tag: "planning"}
    | {tag: "plan_ready"; plan: SyncPlan}
    | {tag: "syncing"; plan: SyncPlan; progress: SyncProgress | null}
    | {tag: "complete"; result: SyncResult}
    | {tag: "error"; message: string};

function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

// Strip a common path prefix for display (e.g. "/sdcard/SdCardBackup/Music/Foo" → "Foo")
function stripPrefix(path: string, prefix: string): string {
    const p = prefix.endsWith("/") ? prefix : prefix + "/";
    return path.startsWith(p) ? path.slice(p.length) : path;
}

const SyncPanel: React.FC<SyncPanelProps> = ({socket}) => {
    const [phase, setPhase] = useState<Phase>({tag: "idle"});
    const [showDetails, setShowDetails] = useState(true);

    // Listen for Socket.IO events emitted by the backend during execute.
    useEffect(() => {
        const onProgress = (data: SyncProgress) => {
            setPhase((prev) => {
                if (prev.tag !== "syncing") return prev;
                return {...prev, progress: data};
            });
        };

        const onComplete = (data: SyncResult) => {
            setPhase({tag: "complete", result: data});
        };

        socket.on("sync_progress", onProgress);
        socket.on("sync_complete", onComplete);
        return () => {
            socket.off("sync_progress", onProgress);
            socket.off("sync_complete", onComplete);
        };
    }, [socket]);

    // ── Actions ──────────────────────────────────────────────────────────────

    const checkDevice = async () => {
        setPhase({tag: "checking"});
        try {
            const res = await fetch(`${BACKEND_URL}/sync/devices`);
            const data = await res.json();
            if (data.connected) {
                setPhase({tag: "device_ready", devices: data.devices});
            } else {
                setPhase({tag: "no_device"});
            }
        } catch {
            setPhase({tag: "error", message: "Could not reach backend"});
        }
    };

    const buildPlan = async () => {
        setPhase({tag: "planning"});
        try {
            const res = await fetch(`${BACKEND_URL}/sync/plan`, {method: "POST"});
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                setPhase({tag: "error", message: data.error ?? `HTTP ${res.status}`});
                return;
            }
            const plan: SyncPlan = await res.json();
            setPhase({tag: "plan_ready", plan});
        } catch (err) {
            setPhase({tag: "error", message: String(err)});
        }
    };

    const confirmSync = async (plan: SyncPlan) => {
        setPhase({tag: "syncing", plan, progress: null});
        try {
            await fetch(`${BACKEND_URL}/sync/execute`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(plan),
            });
            // Completion arrives via sync_complete socket event.
        } catch (err) {
            setPhase({tag: "error", message: String(err)});
        }
    };

    const reset = () => setPhase({tag: "idle"});

    // ── Render ───────────────────────────────────────────────────────────────

    if (phase.tag === "idle") {
        return (
            <button className={styles.primaryBtn} onClick={checkDevice}>
                Scan for device
            </button>
        );
    }

    if (phase.tag === "checking") {
        return <p className={styles.statusText}><span className={styles.spinner} />Checking device…</p>;
    }

    if (phase.tag === "no_device") {
        return (
            <div className={styles.block}>
                <p className={styles.warn}>No device found via adb</p>
                <button className={styles.ghostBtn} onClick={checkDevice}>Retry</button>
            </div>
        );
    }

    if (phase.tag === "device_ready") {
        return (
            <div className={styles.block}>
                <p className={styles.statusText}>
                    <span className={styles.dotGreen} />
                    {phase.devices[0]}
                </p>
                <button className={styles.primaryBtn} onClick={buildPlan}>
                    Plan sync
                </button>
            </div>
        );
    }

    if (phase.tag === "planning") {
        return <p className={styles.statusText}><span className={styles.spinner} />Scanning library…</p>;
    }

    if (phase.tag === "plan_ready") {
        const {plan} = phase;
        const count = plan.files_to_transfer.length;

        // Derive the android_dest prefix from the first remote path so we can
        // display relative paths without knowing the config value in the client.
        const remoteRoot = plan.files_to_transfer[0]?.remote_path
            .split("/").slice(0, -1).join("/") ?? "";
        const commonRoot = plan.dirs_to_create.length > 0
            ? plan.dirs_to_create[0].split("/").slice(0, -1).join("/")
            : remoteRoot;

        return (
            <div className={styles.block}>
                <div className={styles.planSummary}>
                    <div className={styles.planRow}>
                        <span className={styles.planLabel}>Transfer</span>
                        <span className={styles.planValue}>
                            {count} file{count !== 1 ? "s" : ""} &middot; {formatBytes(plan.total_transfer_bytes)}
                        </span>
                    </div>
                    <div className={styles.planRow}>
                        <span className={styles.planLabel}>Already synced</span>
                        <span className={styles.planValue}>{plan.skipped_count}</span>
                    </div>
                    <div className={styles.planRow}>
                        <span className={styles.planLabel}>New dirs</span>
                        <span className={styles.planValue}>{plan.dirs_to_create.length}</span>
                    </div>
                </div>

                <button
                    className={styles.detailsToggle}
                    onClick={() => setShowDetails((v) => !v)}
                >
                    {showDetails ? "▲ Hide details" : "▼ Show details"}
                </button>

                {showDetails && (
                    <div className={styles.detailsPanel}>
                        {(() => {
                            // Group files by remote parent directory.
                            const groups = new Map<string, typeof plan.files_to_transfer>();
                            for (const op of plan.files_to_transfer) {
                                const dir = op.remote_path.split("/").slice(0, -1).join("/");
                                if (!groups.has(dir)) groups.set(dir, []);
                                groups.get(dir)!.push(op);
                            }

                            return (
                                <>
                                    {/* Section 1: all directories to create */}
                                    {plan.dirs_to_create.length > 0 && (
                                        <div className={styles.detailSection}>
                                            <p className={styles.detailHeading}>
                                                Directories to create ({plan.dirs_to_create.length})
                                            </p>
                                            <ul className={styles.detailList}>
                                                {plan.dirs_to_create.map((d) => (
                                                    <li key={d} className={styles.detailItem} title={d}>
                                                        <span className={styles.detailIcon}>📁</span>
                                                        <span className={styles.detailName}>{stripPrefix(d, commonRoot)}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {/* Section 2: files grouped by their remote directory */}
                                    {groups.size > 0 && (
                                        <div className={styles.detailSection}>
                                            <p className={styles.detailHeading}>
                                                Files to transfer ({count})
                                            </p>
                                            {Array.from(groups.entries()).map(([dir, files]) => {
                                                const dirBytes = files.reduce((s, f) => s + f.size_bytes, 0);
                                                const label = stripPrefix(dir, commonRoot) || dir;
                                                return (
                                                    <div key={dir} className={styles.fileGroup}>
                                                        <p className={styles.fileGroupHeader} title={dir}>
                                                            📁 {label}
                                                            <span className={styles.detailHeadingMeta}>
                                                                {files.length} file{files.length !== 1 ? "s" : ""} · {formatBytes(dirBytes)}
                                                            </span>
                                                        </p>
                                                        <ul className={styles.detailList}>
                                                            {files.map((op) => (
                                                                <li key={op.remote_path} className={styles.detailItem} title={op.remote_path}>
                                                                    <span className={styles.detailIcon}>♪</span>
                                                                    <span className={styles.detailName}>{op.filename}</span>
                                                                    <span className={styles.detailSize}>{formatBytes(op.size_bytes)}</span>
                                                                </li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </>
                            );
                        })()}
                    </div>
                )}

                <div className={styles.btnRow}>
                    <button className={styles.ghostBtn} onClick={reset}>Cancel</button>
                    <button
                        className={styles.primaryBtn}
                        onClick={() => confirmSync(plan)}
                        disabled={count === 0}
                    >
                        {count === 0 ? "Already up to date" : "Confirm sync →"}
                    </button>
                </div>
            </div>
        );
    }

    if (phase.tag === "syncing") {
        const {plan, progress} = phase;
        const total = plan.files_to_transfer.length;
        const current = progress?.current ?? 0;
        const pct = total > 0 ? Math.round((current / total) * 100) : 0;
        return (
            <div className={styles.block}>
                <p className={styles.statusText}>
                    <span className={styles.spinner} />
                    Syncing… {current}/{total}
                </p>
                <div className={styles.progressTrack}>
                    <div className={styles.progressFill} style={{width: `${pct}%`}} />
                </div>
                {progress && (
                    <p className={styles.currentFile} title={progress.remote_path}>
                        {progress.filename}
                    </p>
                )}
            </div>
        );
    }

    if (phase.tag === "complete") {
        const {result} = phase;
        return (
            <div className={styles.block}>
                <p className={styles.successText}>Sync complete</p>
                <div className={styles.planSummary}>
                    <div className={styles.planRow}>
                        <span className={styles.planLabel}>Uploaded</span>
                        <span className={styles.planValueGreen}>{result.uploaded}</span>
                    </div>
                    <div className={styles.planRow}>
                        <span className={styles.planLabel}>Skipped</span>
                        <span className={styles.planValue}>{result.skipped}</span>
                    </div>
                    {result.failed > 0 && (
                        <div className={styles.planRow}>
                            <span className={styles.planLabel}>Failed</span>
                            <span className={styles.planValueRed}>{result.failed}</span>
                        </div>
                    )}
                </div>
                <button className={styles.ghostBtn} onClick={reset}>New sync</button>
            </div>
        );
    }

    if (phase.tag === "error") {
        return (
            <div className={styles.block}>
                <p className={styles.warn}>{phase.message}</p>
                <button className={styles.ghostBtn} onClick={reset}>Dismiss</button>
            </div>
        );
    }

    return null;
};

export default SyncPanel;
