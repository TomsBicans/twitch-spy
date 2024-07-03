export const BACKEND_URL = "http://localhost:5000";

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

export type BackendOpNames = keyof Endpoints;
export type BackendMethods<N extends BackendOpNames> = keyof Endpoints[N];

type EndpointInput<N extends BackendOpNames, M extends BackendMethods<N>> =
  Endpoints[N][M] extends APIRequest<infer _, infer I, infer _> ? I : never;

type EndpointOutput<N extends BackendOpNames, M extends BackendMethods<N>> =
  Endpoints[N][M] extends APIRequest<infer _, infer _, infer O> ? O : never;

export type BackendOp<M extends "GET" | "POST" | "DELETE", I, O> = {
  name: BackendOpNames;
} & APIRequest<M, I, O>;

const BackendOpExample: BackendOp<"GET", {}, {}> = {
  name: "job_data",
  method: "GET",
  input: {
    job_id: "string",
  },
  output: {},
};

export interface JobDataInput {
  job_id: string;
}

export interface JobDataOutput {
  url: string;
  url_valid: boolean;
  platform: string;
  single_item: boolean;
  content_type: string;
  content_name?: string;
  download_dir: string;
  status: string;
}

// Generic request sending function using axios:
export const sendRequest = async <
  N extends BackendOpNames,
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
  const resposne = await sendRequest("job_data", "GET", {});
  console.log(resposne);
};
