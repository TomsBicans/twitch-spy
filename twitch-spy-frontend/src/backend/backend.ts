import { z } from "zod";

export const BACKEND_URL = "http://localhost:5000";

const percentageSchema = z.number().min(0).max(100);
const bytesSchema = z.number().nonnegative();
const hertzSchema = z.number().positive();

const JobDataInputSchema = z.object({
  job_id: z.string(),
});

const JobDataOutputSchema = z.object({
  url: z.string(),
  url_valid: z.boolean(),
  platform: z.string(),
  single_item: z.boolean(),
  content_type: z.string(),
  content_name: z.string().optional(),
  download_dir: z.string(),
  status: z.string(),
});

const FormSubmitInputSchema = z.object({
  urls: z.string(),
});

const FormSubmitOutputSchema = z.object({
  success: z.boolean(),
  message: z.string(),
});
// System stat schemas

const cpuSchema = z.object({
  usage: z.object({
    total: percentageSchema,
    perCore: z.array(percentageSchema),
  }),
  frequency: z.object({
    current: hertzSchema,
    min: hertzSchema,
    max: hertzSchema,
  }),
  temperature: z.object({
    current: z.number(),
    critical: z.number().optional(),
  }),
  loadAverage: z.object({
    "1min": z.number(),
    "5min": z.number(),
    "15min": z.number(),
  }),
});

const memorySchema = z.object({
  total: bytesSchema,
  used: bytesSchema,
  free: bytesSchema,
  shared: bytesSchema,
  buffer: bytesSchema,
  available: bytesSchema,
  usagePercentage: percentageSchema,
});

const diskSchema = z.object({
  totalSpace: bytesSchema,
  usedSpace: bytesSchema,
  freeSpace: bytesSchema,
  usagePercentage: percentageSchema,
  readSpeed: bytesSchema,
  writeSpeed: bytesSchema,
  iops: z.number().nonnegative(),
});

const networkSchema = z.object({
  interfaces: z.array(
    z.object({
      name: z.string(),
      macAddress: z.string(),
      ipv4: z.string().optional(),
      ipv6: z.string().optional(),
      status: z.enum(["up", "down"]),
    })
  ),
  traffic: z.object({
    received: bytesSchema,
    transmitted: bytesSchema,
  }),
  bandwidth: z.object({
    download: bytesSchema,
    upload: bytesSchema,
  }),
  latency: z.number().nonnegative(),
  packetLoss: percentageSchema,
});

// Flattened API structure
const api = {
  "job_data.GET": {
    input: JobDataInputSchema,
    output: JobDataOutputSchema,
  },
  "job_data.POST": {
    input: z.object({}).strict(),
    output: z.object({}).strict(),
  },
  "all_jobs.GET": {
    input: z.object({}).strict(),
    output: z.array(JobDataOutputSchema),
  },
  "form_submit.POST": {
    input: FormSubmitInputSchema,
    output: FormSubmitOutputSchema,
  },
  "system_stats_CPU.GET": {
    input: z.object({}).strict(),
    output: cpuSchema,
  },
  "system_stats_memory.GET": {
    input: z.object({}).strict(),
    output: memorySchema,
  },
  "system_stats_disk.GET": {
    input: z.object({}).strict(),
    output: diskSchema,
  },
  "system_stats_network.GET": {
    input: z.object({}).strict(),
    output: networkSchema,
  },
} as const;

type API = typeof api;
type EndpointMethod = keyof API;

type InputType<EM extends EndpointMethod> = z.infer<API[EM]["input"]>;
type OutputType<EM extends EndpointMethod> = z.infer<API[EM]["output"]>;

// Helper type to enforce empty object
type StrictEmpty<T> =
  T extends Record<string, never> ? T & Record<string, never> : T;

async function apiRequest<EM extends EndpointMethod>(
  endpointMethod: EM,
  data: StrictEmpty<InputType<EM>>
): Promise<OutputType<EM>> {
  const [endpoint, method] = endpointMethod.split(".") as [string, string];
  let url = `${BACKEND_URL}/${endpoint}`;

  const options: RequestInit = {
    method,
    headers: {
      "Content-Type": "application/json",
    },
  };

  if (method !== "GET" && data) {
    options.body = JSON.stringify(data);
  } else if (method === "GET" && Object.keys(data).length > 0) {
    const params = new URLSearchParams(data as Record<string, string>);
    url += `?${params}`;
  }

  const response = await fetch(url, options);
  return response.json();
}

// Example usage
export async function exampleUsage() {
  const jobData = await apiRequest("job_data.GET", { job_id: "123" });
  console.log(jobData.url);

  const allJobs = await apiRequest("all_jobs.GET", {});
  console.log(allJobs.length);
}

export { api, apiRequest };
