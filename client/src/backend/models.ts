export interface Atom {
  id: string; // UUID
  url: string;
  url_valid: boolean;
  platform: PLATFORM;
  single_item: boolean;
  content_type: CONTENT_MODE;
  content_name: string; // Optional
  download_dir: string;
  thumbnail_image_in_base64?: string;
  media_file_os_path?: string;
  status: ProcessingStates;
}
export const PLATFORM = {
  YOUTUBE: "YOUTUBE",
  UNDEFINED: "UNDEFINED",
} as const;
export type PLATFORM = (typeof PLATFORM)[keyof typeof PLATFORM];

export const CONTENT_MODE = {
  AUDIO: "AUDIO",
} as const;
export type CONTENT_MODE = (typeof CONTENT_MODE)[keyof typeof CONTENT_MODE];

export const ProcessingStates = {
  QUEUED: "queued",
  PROCESSING: "processing",
  FINISHED: "finished",
  CANCELLED: "cancelled",
  FAILED: "failed",
  INVALID: "invalid",
} as const;
export type ProcessingStates =
  (typeof ProcessingStates)[keyof typeof ProcessingStates];

export interface JobStatistics {
  [ProcessingStates.QUEUED]: number;
  [ProcessingStates.PROCESSING]: number;
  [ProcessingStates.FINISHED]: number;
  [ProcessingStates.CANCELLED]: number;
  [ProcessingStates.FAILED]: number;
  [ProcessingStates.INVALID]: number;
}

export type JobStatKey = keyof JobStatistics;

// ── Android sync ──────────────────────────────────────────────────────────────

export interface FileTransferOp {
  local_path: string;
  remote_path: string;
  size_bytes: number;
  filename: string;
}

export interface SyncPlan {
  dirs_to_create: string[];
  files_to_transfer: FileTransferOp[];
  skipped_count: number;
  total_transfer_bytes: number;
}

export interface SyncProgress {
  current: number;
  total: number;
  filename: string;
  remote_path: string;
  status: "ok" | "failed";
}

export interface SyncResult {
  uploaded: number;
  skipped: number;
  failed: number;
  errors: string[];
}
