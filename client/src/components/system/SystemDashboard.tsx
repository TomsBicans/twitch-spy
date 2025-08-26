import React, { useState, useEffect, ReactNode } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Laptop, Cpu, HardDrive, Wifi, LucideIcon } from "lucide-react";
import { getAllSystemStats } from "./model.ts";

interface CardProps {
  children: ReactNode;
  className?: string;
}

const Card: React.FC<CardProps> = ({ children, className = "" }) => (
  <div className={`border rounded-lg p-4 ${className}`}>{children}</div>
);

interface CardHeaderProps {
  children: ReactNode;
}

const CardHeader: React.FC<CardHeaderProps> = ({ children }) => (
  <div className="mb-2">{children}</div>
);

interface CardContentProps {
  children: ReactNode;
}

const CardContent: React.FC<CardContentProps> = ({ children }) => (
  <div>{children}</div>
);

interface ProgressProps {
  value: number;
}

const Progress: React.FC<ProgressProps> = ({ value }) => (
  <div className="w-full bg-gray-200 rounded-full h-2.5">
    <div
      className="bg-blue-600 h-2.5 rounded-full"
      style={{ width: `${value}%` }}
    ></div>
  </div>
);

interface SystemStats {
  cpu: number;
  memory: number;
  disk: number;
  network: number;
}

const generateMockData = async ({ mock = true }): Promise<SystemStats> => {
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
  <Card className="w-full">
    <CardHeader>
      <div className="flex justify-between items-center">
        <h3 className="text-sm font-medium">{title}</h3>
        <Icon className="h-4 w-4 text-gray-500" />
      </div>
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold mb-2">
        {value}
        {absoluteValue ? (unitOfMeasure ? ` ${unitOfMeasure}` : "") : "%"}
      </div>
      <Progress value={value} />
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
      <XAxis dataKey="name" />
      <YAxis />
      <Tooltip />
      <Line
        type="monotone"
        dataKey="cpu"
        stroke="#8884d8"
        isAnimationActive={isAnimationActive}
      />
      <Line
        type="monotone"
        dataKey="memory"
        stroke="#82ca9d"
        isAnimationActive={isAnimationActive}
      />
      <Line
        type="monotone"
        dataKey="disk"
        stroke="#ffc658"
        isAnimationActive={isAnimationActive}
      />
      <Line
        type="monotone"
        dataKey="network"
        stroke="#ff7300"
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
        const stats = await generateMockData({ mock: false });
        const timestamp = new Date().toLocaleTimeString();

        setCurrentStats(stats);
        setHistoricalData((prevData) => [
          ...prevData.slice(-MAX_HISTORY_LENGTH + 1),
          { name: timestamp, ...stats },
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

  if (isLoading) {
    return <div>Loading system stats...</div>;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-3xl font-bold">System Stats</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
          title="Network Usage"
          value={Number((currentStats.network / 1024 / 1024).toFixed(2))}
          icon={Wifi}
          absoluteValue={true}
          unitOfMeasure="MB/s"
        />
      </div>
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold">Historical Usage</h3>
        </CardHeader>
        <CardContent>
          <SystemStatsChart data={historicalData} isAnimationActive={false} />
        </CardContent>
      </Card>
    </div>
  );
};

export default SystemDashboard;
