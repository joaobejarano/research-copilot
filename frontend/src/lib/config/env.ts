const REQUIRED_API_BASE_URL_ENV = "NEXT_PUBLIC_API_BASE_URL";

export function getApiBaseUrl(): string {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!apiBaseUrl) {
    throw new Error(`${REQUIRED_API_BASE_URL_ENV} is not set.`);
  }

  return apiBaseUrl.endsWith("/") ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
}
