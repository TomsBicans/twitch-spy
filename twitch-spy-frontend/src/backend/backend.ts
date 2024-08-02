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

export type JobDataInput = z.infer<typeof JobDataInputSchema>;
export type JobDataOutput = z.infer<typeof JobDataOutputSchema>;

type HTTPMethod = "GET" | "POST" | "DELETE";

interface APIRequest<M extends HTTPMethod, I, O> {
  method: M;
  input: I;
  output: O;
}

export interface Endpoints {
  job_data: {
    GET: APIRequest<"GET", JobDataInput, JobDataOutput>;
    POST: APIRequest<"POST", {}, {}>;
  };
  all_jobs: {
    GET: APIRequest<"GET", {}, {}>;
  };
  input_form_metadata: {
    POST: APIRequest<"POST", {}, {}>;
  };
  input_form_submit: {
    POST: APIRequest<"POST", {}, {}>;
  };
}

export type BackendMethods<N extends keyof Endpoints> = keyof Endpoints[N];

type EndpointInput<N extends keyof Endpoints, M extends BackendMethods<N>> =
  Endpoints[N][M] extends APIRequest<infer _, infer I, infer _> ? I : never;

type EndpointOutput<N extends keyof Endpoints, M extends BackendMethods<N>> =
  Endpoints[N][M] extends APIRequest<infer _, infer _, infer O> ? O : never;

export type BackendOp<M extends HTTPMethod, I, O> = {
  name: keyof Endpoints;
} & APIRequest<M, I, O>;

const BackendOpExample: BackendOp<"GET", {}, {}> = {
  name: "job_data",
  method: "GET",
  input: {
    job_id: "string",
  },
  output: {},
};

// Generic request sending function using axios:
export const sendRequest = async <
  N extends keyof Endpoints,
  M extends BackendMethods<N> & HTTPMethod,
>(
  endpointName: N,
  method: M,
  body: EndpointInput<N, M>
): Promise<EndpointOutput<N, M>> => {
  const url = `${BACKEND_URL}/${String(endpointName)}`;

  const response = await fetch(url, {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  return response.json();
};

const exampleUsage = async () => {
  const resposne = await sendRequest("job_data", "GET");
  console.log(resposne);
};
