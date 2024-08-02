import { z } from "zod";

export const BACKEND_URL = "http://localhost:5000";

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
} as const;

type API = typeof api;
type EndpointMethod = keyof API;

type InputType<EM extends EndpointMethod> = z.infer<API[EM]["input"]>;
type OutputType<EM extends EndpointMethod> = z.infer<API[EM]["output"]>;

// Helper type to enforce empty object
type StrictEmpty<T> =
  T extends Record<string, never> ? T & Record<string, never> : T;

export async function apiRequest<EM extends EndpointMethod>(
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
