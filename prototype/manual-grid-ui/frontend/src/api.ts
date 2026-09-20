export const API_BASE = import.meta.env.VITE_API_URL ?? "";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export class ApiError extends Error {
  constructor(public readonly endpoint: string, public readonly status: number | null, message: string, public readonly errorType: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function safeErrorBody(response: Response): Promise<string> {
  try {
    const body = await response.json() as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail.slice(0, 240) : `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const endpoint = apiUrl(path);
  try {
    const response = await fetch(endpoint, init);
    if (!response.ok) {
      const message = await safeErrorBody(response);
      console.error("Manual Grid API error", { endpoint: path, status: response.status, errorType: "http_error" });
      throw new ApiError(path, response.status, message, "http_error");
    }
    return await response.json() as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    console.error("Manual Grid API request failed", { endpoint: path, status: null, errorType: "network_error" });
    throw new ApiError(path, null, "Backend недоступен", "network_error");
  }
}
