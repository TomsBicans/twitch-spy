import {useEffect, useLayoutEffect, useRef, useState} from "react";
import {BACKEND_URL} from "../backend/backend";
import styles from "./Diagnostics.module.css";

interface ProcessReading {
    pid: number;
    name: string;
    cpu_percent: number | null;
    memory_bytes: number;
    threads: number;
}

interface Snapshot {
    status: string;
    version: string;
    pid: number;
    uptime_seconds: number;
    cpu_percent: number | null;
    memory_bytes: number;
    threads: number;
    downloads_active: boolean;
    sync_active: boolean;
    tray_active: boolean;
    browser_clients: number;
    processes: ProcessReading[];
    logs: string;
}

const memory = (bytes: number) => `${(bytes / 1024 / 1024).toFixed(1)} MiB`;
const cpu = (percent: number | null) => percent === null ? "Sampling…" : `${percent.toFixed(1)}%`;

export default function Diagnostics({onClose}: {onClose: () => void}) {
    const [snapshot, setSnapshot] = useState<Snapshot>();
    const [error, setError] = useState("");
    const [paused, setPaused] = useState(false);
    const logsRef = useRef<HTMLPreElement>(null);
    const followLogsRef = useRef(true);

    useLayoutEffect(() => {
        const logs = logsRef.current;
        if (logs && followLogsRef.current) logs.scrollTop = logs.scrollHeight;
    }, [snapshot?.logs]);

    useEffect(() => {
        if (paused) return;
        const controller = new AbortController();
        let timer: ReturnType<typeof setTimeout>;
        async function refresh() {
            try {
                if (document.visibilityState === "hidden") return;
                const token = document.querySelector<HTMLMetaElement>('meta[name="twitch-spy-shutdown-token"]')?.content;
                const response = await fetch(`${BACKEND_URL}/diagnostics`, {
                    headers: {
                        "X-Twitch-Spy-Diagnostics": "1",
                        ...(token && !token.startsWith("__TWITCH_SPY_") ? {"X-Twitch-Spy-Shutdown": token} : {}),
                    },
                    signal: controller.signal,
                    cache: "no-store",
                });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                setSnapshot(await response.json());
                setError("");
            } catch (error) {
                if (!controller.signal.aborted) setError(`Backend unavailable: ${String(error)}. Readings below may be stale.`);
            } finally {
                if (!controller.signal.aborted) timer = setTimeout(refresh, 2000);
            }
        }
        void refresh();
        return () => { controller.abort(); clearTimeout(timer); };
    }, [paused]);

    return <section className={styles.panel} aria-label="Health and resource usage">
        <div className={styles.heading}>
            <h2>Health and resource usage</h2>
            <div>
                <button type="button" onClick={() => setPaused(!paused)}>{paused ? "Resume" : "Pause"}</button>
                <button type="button" onClick={onClose}>Close</button>
            </div>
        </div>
        {error && <p role="alert" className={styles.error}>{error}</p>}
        {!snapshot && !error && <p>Loading diagnostics…</p>}
        {snapshot && <>
            <p>Backend {snapshot.status} · v{snapshot.version} · PID {snapshot.pid} · Uptime {Math.floor(snapshot.uptime_seconds / 60)}m {snapshot.uptime_seconds % 60}s</p>
            <div className={styles.metrics}>
                <div><strong>{cpu(snapshot.cpu_percent)}</strong><span>CPU</span></div>
                <div><strong>{memory(snapshot.memory_bytes)}</strong><span>Memory (working set / RSS)</span></div>
                <div><strong>{snapshot.processes.length}</strong><span>Processes</span></div>
                <div><strong>{snapshot.threads}</strong><span>Threads</span></div>
            </div>
            <p>Downloads: {snapshot.downloads_active ? "active" : "idle"} · Android sync: {snapshot.sync_active ? "active" : "idle"} · Tray: {snapshot.tray_active ? "active" : "off"} · Browser connections: {snapshot.browser_clients}</p>
            <p className={styles.note}>Backend and live child processes only; browser and separate development server excluded. CPU: 100% = one logical core. Memory sums working sets and may count shared pages more than once. Short-lived processes can fall between samples. Refreshes every 2 seconds while visible.</p>
            <div className={styles.tableScroll}><table>
                <thead><tr><th>Process</th><th>PID</th><th>CPU</th><th>Memory</th></tr></thead>
                <tbody>{snapshot.processes.map(process => <tr key={process.pid}>
                    <td>{process.name}</td><td>{process.pid}</td><td>{cpu(process.cpu_percent)}</td><td>{memory(process.memory_bytes)}</td>
                </tr>)}</tbody>
            </table></div>
            <h3>Recent application logs</h3>
            <p className={styles.note}>Latest 200 lines, limited to 64 KiB. Pause updates to inspect or copy. Full logs are available through the tray’s Open logs folder action.</p>
            <pre ref={logsRef} className={styles.logs} onScroll={event => {
                const logs = event.currentTarget;
                followLogsRef.current = logs.scrollHeight - logs.clientHeight - logs.scrollTop <= 4;
            }}>{snapshot.logs || "No application log entries yet."}</pre>
        </>}
    </section>;
}
