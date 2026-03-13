/**
 * Fetch wrapper that redirects to /login on 401 responses.
 */
export async function authFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const res = await fetch(input, { credentials: 'include', ...init })

  if (res.status === 401) {
    window.location.href = '/login'
    throw new Error('Session expired')
  }

  return res
}
