import React, {useEffect, useState, type ReactNode} from "react";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
} from "recharts";
import {Laptop, Cpu, HardDrive, Wifi, type LucideIcon} from "lucide-react";
import {getAllSystemStats} from "./model.ts";
import styles from "./SystemDashboard.module.css";

interface CardProps {
    children: ReactNode;
    className?: string;
}

const Card: React.FC<CardProps> = ({children, className = ""}) => (
    <div className={`${styles.card} ${className}`.trim()}>{children}</div>
);

interface CardHeaderProps {
    children: ReactNode;
}

const CardHeader: React.FC<CardHeaderProps> = ({children}) => (
    <div className={styles.cardHeader}>{children}</div>
);

interface CardContentProps {
    children: ReactNode;
}

const CardContent: React.FC<CardContentProps> = ({children}) => (
    <div className={styles.cardBody}>{children}</div>
);

interface ProgressProps {
    value: number;
}

const Progress: React.FC<ProgressProps> = ({value}) => (
    <div className={styles.progressTrack}>
        <div className={styles.progressFill} style={{width: `${Math.min(100, value)}%`}} />
    </div>
);

interface SystemStats {
    cpu: number;
    memory: number;
    disk: number;
    network: number;
}

const generateMockData = async ({mock = true}): Promise<SystemStats> => {
    if (mock) {
        return {
            cpu: Math.floor(Math.random() * 100),
            memory: Math.floor(Math.random() * 100),
            disk: Math.floor(Math.random() * 100),
            network: Math.floor(Math.random() * 100),
        };
    } else {
        const bulk = true;
        const systemStats = await getAllSystemStats(mock, bulk);
        return {
            cpu: systemStats.cpu.usage.total,
            memory: systemStats.memory.usagePercentage,
            disk: systemStats.disk.usagePercentage,
            network: systemStats.network.bandwidth.download,
        };
    }
};

interface SystemStatCardProps {
    title: string;
    value: number;
    icon: LucideIcon;
    absoluteValue?: boolean;
    unitOfMeasure?: string;
}

const SystemStatCard: React.FC<SystemStatCardProps> = ({
                                                           title,
                                                           value,
                                                           icon: Icon,
                                                           absoluteValue = false,
                                                           unitOfMeasure = "",
                                                       }) => (
    <Card>
        <CardHeader>
            <div className={styles.cardHeadingRow}>
                <h3 className={styles.cardTitle}>{title}</h3>
                <span className={styles.iconBadge}>
                    <Icon size={16} />
                </span>
            </div>
        </CardHeader>
        <CardContent>
            <div className={styles.cardMetric}>
                {value}
                {absoluteValue ? (unitOfMeasure ? ` ${unitOfMeasure}` : "") : "%"}
            </div>
            <Progress value={value}/>
        </CardContent>
    </Card>
);

interface HistoricalDataPoint extends SystemStats {
    name: string;
}

interface SystemStatsChartProps {
    data: HistoricalDataPoint[];
    isAnimationActive?: boolean;
}

const SystemStatsChart: React.FC<SystemStatsChartProps> = ({
                                                               data,
                                                               isAnimationActive = true,
                                                           }) => (
    <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
            <XAxis
                dataKey="name"
                stroke="rgba(216, 223, 241, 0.4)"
                tick={{fill: "rgba(216, 223, 241, 0.55)", fontSize: 12}}
            />
            <YAxis
                stroke="rgba(216, 223, 241, 0.38)"
                tick={{fill: "rgba(216, 223, 241, 0.55)", fontSize: 12}}
            />
            <Tooltip
                contentStyle={{
                    background: "rgba(13, 17, 26, 0.88)",
                    border: "1px solid rgba(124, 92, 255, 0.35)",
                    borderRadius: 12,
                    color: "var(--text-primary)",
                    backdropFilter: "blur(12px)",
                }}
                labelStyle={{color: "var(--text-secondary)", fontWeight: 600}}
            />
            <Line
                type="monotone"
                dataKey="cpu"
                stroke="#7c5cff"
                isAnimationActive={isAnimationActive}
            />
            <Line
                type="monotone"
                dataKey="memory"
                stroke="#3ed6be"
                isAnimationActive={isAnimationActive}
            />
            <Line
                type="monotone"
                dataKey="disk"
                stroke="#ffb677"
                isAnimationActive={isAnimationActive}
            />
            <Line
                type="monotone"
                dataKey="network"
                stroke="#ff8777"
                isAnimationActive={isAnimationActive}
            />
        </LineChart>
    </ResponsiveContainer>
);

const SystemDashboard: React.FC = () => {
    const REFRESH_DELAY = 100000;
    const MAX_HISTORY_LENGTH = 20;

    const [currentStats, setCurrentStats] = useState<SystemStats>({
        cpu: 0,
        memory: 0,
        disk: 0,
        network: 0,
    });
    const [historicalData, setHistoricalData] = useState<HistoricalDataPoint[]>(
        []
    );

    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchAndUpdateStats = async () => {
            try {
                const stats = await generateMockData({mock: false});
                const timestamp = new Date().toLocaleTimeString();

                setCurrentStats(stats);
                setHistoricalData((prevData) => [
                    ...prevData.slice(-MAX_HISTORY_LENGTH + 1),
                    {name: timestamp, ...stats},
                ]);

                setIsLoading(false);
            } catch (error) {
                console.error("Error fetching system stats:", error);
                // Optionally set an error state here
            }
        };

        // Initial fetch
        fetchAndUpdateStats();

        // Set up interval for subsequent fetches
        const intervalId = setInterval(fetchAndUpdateStats, REFRESH_DELAY);

        // Cleanup function
        return () => {
            if (intervalId) clearInterval(intervalId);
        };
    }, []); // Empty dependency array means this effect runs once on mount

    return (
        <div className={styles.dashboard}>
            <div className={styles.headlineRow}>
                <h2 className={styles.title}>System tempo</h2>
                <p className={styles.subtitle}>
                    Keep an eye on the workstation while downloads run in the background.
                </p>
            </div>

            {isLoading ? (
                <div className={styles.loadingState}>
                    <span className={styles.loadingSpinner} aria-hidden="true"/>
                    <p>Gathering system vitals…</p>
                </div>
            ) : (
                <>
                    <div className={styles.metricsGrid}>
                        <SystemStatCard
                            title="CPU Usage"
                            value={currentStats.cpu}
                            icon={Cpu}
                            absoluteValue={false}
                        />
                        <SystemStatCard
                            title="Memory Usage"
                            value={currentStats.memory}
                            icon={Laptop}
                            absoluteValue={false}
                        />
                        <SystemStatCard
                            title="Disk Usage"
                            value={currentStats.disk}
                            icon={HardDrive}
                            absoluteValue={false}
                        />
                        <SystemStatCard
                            title="Network Throughput"
                            value={Number((currentStats.network / 1024 / 1024).toFixed(2))}
                            icon={Wifi}
                            absoluteValue={true}
                            unitOfMeasure="MB/s"
                        />
                    </div>
                    <Card className={styles.chartCard}>
                        <CardHeader>
                            <h3 className={styles.cardTitle}>Historical usage</h3>
                        </CardHeader>
                        <CardContent>
                            <SystemStatsChart data={historicalData} isAnimationActive={false}/>
                        </CardContent>
                    </Card>
                </>
            )}
        </div>
    );
};

export default SystemDashboard;
