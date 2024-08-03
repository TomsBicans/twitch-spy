import { z } from "zod";
import { api, apiRequest } from "../../backend/backend";

type CPUStats = z.infer<(typeof api)["system_stats_CPU.GET"]["output"]>;
type MemoryStats = z.infer<(typeof api)["system_stats_memory.GET"]["output"]>;
type DiskStats = z.infer<(typeof api)["system_stats_disk.GET"]["output"]>;
type NetworkStats = z.infer<(typeof api)["system_stats_network.GET"]["output"]>;

export type SystemStats = {
  cpu: CPUStats;
  memory: MemoryStats;
  disk: DiskStats;
  network: NetworkStats;
};

const getCPUStats = async (mock = true): Promise<CPUStats> => {
  // Here you would make the actual API call to get CPU stats
  // For now, we'll return mock data
  if (mock) {
    return {
      usage: {
        total: Math.random() * 100,
        perCore: Array(4)
          .fill(0)
          .map(() => Math.random() * 100),
      },
      frequency: {
        current: 2500 + Math.random() * 1000,
        min: 2000,
        max: 3500,
      },
      temperature: {
        current: 40 + Math.random() * 20,
        critical: 90,
      },
      loadAverage: {
        "1min": Math.random() * 2,
        "5min": Math.random() * 1.5,
        "15min": Math.random(),
      },
    };
  } else {
    return await apiRequest("system_stats_CPU.GET", {});
  }
};

const getMemoryStats = async (mock = true): Promise<MemoryStats> => {
  // Here you would make the actual API call to get memory stats
  if (mock) {
    const total = 16 * 1024 * 1024 * 1024; // 16 GB in bytes
    const used = Math.random() * total;
    return {
      total,
      used,
      free: total - used,
      shared: Math.random() * 1024 * 1024 * 1024,
      buffer: Math.random() * 1024 * 1024 * 1024,
      available: total - used,
      usagePercentage: (used / total) * 100,
    };
  } else {
    return await apiRequest("system_stats_memory.GET", {});
  }
};

const getDiskStats = async (mock = true): Promise<DiskStats> => {
  // Here you would make the actual API call to get disk stats
  if (mock) {
    const totalSpace = 500 * 1024 * 1024 * 1024; // 500 GB in bytes
    const usedSpace = Math.random() * totalSpace;
    return {
      totalSpace,
      usedSpace,
      freeSpace: totalSpace - usedSpace,
      usagePercentage: (usedSpace / totalSpace) * 100,
      readSpeed: Math.random() * 500 * 1024 * 1024, // up to 500 MB/s
      writeSpeed: Math.random() * 500 * 1024 * 1024, // up to 500 MB/s
      iops: Math.random() * 10000,
    };
  } else {
    return await apiRequest("system_stats_disk.GET", {});
  }
};

const getNetworkStats = async (mock = true): Promise<NetworkStats> => {
  // Here you would make the actual API call to get network stats
  if (mock) {
    return {
      interfaces: [
        {
          name: "eth0",
          macAddress: "00:11:22:33:44:55",
          ipv4: "192.168.1.100",
          status: "up",
        },
      ],
      traffic: {
        received: Math.random() * 1024 * 1024 * 1024,
        transmitted: Math.random() * 1024 * 1024 * 1024,
      },
      bandwidth: {
        download: Math.random() * 100 * 1024 * 1024, // up to 100 MB/s
        upload: Math.random() * 20 * 1024 * 1024, // up to 20 MB/s
      },
      latency: Math.random() * 100, // up to 100 ms
      packetLoss: Math.random() * 5, // up to 5%
    };
  } else {
    return await apiRequest("system_stats_network.GET", {});
  }
};

const getSystemStatsBulk = async (mock = true) => {
  return await apiRequest("system_stats_ALL.GET", {});
};

const getAllSystemStats = async (
  useMockData: boolean,
  bulk: boolean
): Promise<SystemStats> => {
  if (bulk) {
    const { cpu, memory, disk, network } =
      await getSystemStatsBulk(useMockData);
    return { cpu, memory, disk, network };
  }
  const [cpu, memory, disk, network] = await Promise.all([
    getCPUStats(useMockData),
    getMemoryStats(useMockData),
    getDiskStats(useMockData),
    getNetworkStats(useMockData),
  ]);

  return { cpu, memory, disk, network };
};
export {
  getCPUStats,
  getMemoryStats,
  getDiskStats,
  getNetworkStats,
  getAllSystemStats,
};
