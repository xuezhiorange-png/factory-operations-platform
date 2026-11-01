// This endpoint reports process liveness, not authentication, database or integration readiness.
export async function checkHealth(): Promise<boolean> {
  const response = await fetch('/api/v1/health', { signal: AbortSignal.timeout(5000) })
  const data: unknown = await response.json()
  return (
    response.ok &&
    typeof data === 'object' && data !== null &&
    'status' in data && data.status === 'ok' &&
    'service' in data && data.service === 'factory-operations' &&
    'stage' in data && data.stage === 'M0'
  )
}
