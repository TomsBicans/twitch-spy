export interface Atom {
  id: string; // UUID
  url: string;
  url_valid: boolean;
  platform: PLATFORM;
  single_item: boolean;
  content_type: CONTENT_MODE;
  content_name?: string; // Optional
  download_dir: string;
  thumbnail_os_path?: string;
  media_file_os_path?: string;
  status: ProcessingStates;
}
export enum PLATFORM {
  TWITCH = "TWITCH",
  YOUTUBE = "YOUTUBE",
  UNDEFINED = "UNDEFINED",
}

export enum CONTENT_MODE {
  VIDEO = "VIDEO",
  AUDIO = "AUDIO",
  BOTH = "BOTH",
}
export enum ProcessingStates {
  QUEUED = "queued",
  PROCESSING = "processing",
  FINISHED = "finished",
  CANCELLED = "cancelled",
  FAILED = "failed",
  INVALID = "invalid",
}

export interface JobStatistics {
  [ProcessingStates.QUEUED]: number;
  [ProcessingStates.PROCESSING]: number;
  [ProcessingStates.FINISHED]: number;
  [ProcessingStates.CANCELLED]: number;
  [ProcessingStates.FAILED]: number;
  [ProcessingStates.INVALID]: number;
}

export type JobStatKey = keyof JobStatistics;
