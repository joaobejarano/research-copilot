import { getApiBaseUrl } from "../config/env";

interface ApiErrorPayload {
  detail?: string;
}

export class ApiClientError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(`API request failed (${status}): ${detail}`);
    this.name = "ApiClientError";
    this.status = status;
    this.detail = detail;
  }
}

interface RequestJsonOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
}

async function parseJsonSafely<T>(response: Response): Promise<T | null> {
  try {
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export async function requestJson<TResponse>(
  path: string,
  options: RequestJsonOptions = {}
): Promise<TResponse> {
  const headers = new Headers(options.headers);
  const hasBody = options.body !== undefined;

  if (hasBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...options,
    headers,
    body: hasBody ? JSON.stringify(options.body) : undefined,
    cache: "no-store"
  });

  if (!response.ok) {
    const errorPayload = await parseJsonSafely<ApiErrorPayload>(response);
    const detail =
      typeof errorPayload?.detail === "string" && errorPayload.detail.length > 0
        ? errorPayload.detail
        : response.statusText || "Unknown API error.";

    throw new ApiClientError(response.status, detail);
  }

  return (await response.json()) as TResponse;
}
