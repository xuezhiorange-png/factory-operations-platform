// The host chooses a fixed same-origin namespace, never a user-supplied URL.
let monitorPortal = false;
export function enableMonitorPortal() { monitorPortal = true; }
export function isMonitorPortal() { return monitorPortal; }
export function operationsApiPath(path: string) {
  if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Invalid API path');
  return (monitorPortal ? '/operations-api/v1' : '/api/v1') + path;
}
