export type ApiRequestOptions = RequestInit & {
  headers?: HeadersInit;
};

const DEFAULT_HEADERS: HeadersInit = {
  "Content-Type": "application/json",
};

export async function apiFetch<T = unknown>(
  input: RequestInfo | URL,
  { headers, ...init }: ApiRequestOptions = {},
): Promise<T> {
  const response = await fetch(input, {
    ...init,
    headers: {
      ...DEFAULT_HEADERS,
      ...headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}
