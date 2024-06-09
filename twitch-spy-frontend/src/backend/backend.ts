export {};
export const BACKEND_URL = "localhost:5000";

// export type APIRequest = {
//   endpoint: string;
//   method: "GET" | "POST" | "DELETE";
//   input: object; // Expected input type from frontend
//   output: object; // Expected output type from backend
// };

interface APIRequest<M extends "GET" | "POST" | "DELETE", I, O> {
  method: M;
  input: I;
  output: O;
}

export type BackendOpNames =
  | "job_data"
  | "all_jobs"
  | "input_form_metadata"
  | "input_form_submit";
// export type BackendOp = { name: BackendOpNames } & APIRequest;

// export type APIMap = Record<string, APIRequest>;

export interface APIRequestMap {}

// const BackendOps: BackendOp[] = [
//   {
//     name: "job_data",
//     endpoint: "/job_data",
//     method: "GET",
//     input: {
//       job_id: "string",
//     },
//     output: {},
//   },
//   {
//     name: "all_jobs",
//     endpoint: "/all_jobs",
//     method: "GET",
//     input: {},
//     output: {
//       jobs: "array",
//     },
//   },
//   {
//     name: "input_form_metadata",
//     endpoint: "/input_metadata",
//     method: "POST",
//     input: {
//       userInput: "string",
//     },
//     output: {},
//   },
//   {
//     name: "input_form_submit",
//     endpoint: "/input_form",
//     method: "POST",
//     input: {
//       userInput: "string",
//     },
//     output: {},
//   },
// ];
// Generic request sending function using axios:

export const sendRequest = async <T, O extends BackendOpNames>(
  apiEndpoint: string,
  method: "GET" | "POST" | "DELETE" = "GET",
  input: T,
  output: T,
  body?: {}
): Promise<T> => {
  const response = await fetch(apiEndpoint, {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  return response.json();
};

// Examples
