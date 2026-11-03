// The host chooses a fixed same-origin namespace, never a user-supplied URL.
const hotData = import.meta.hot?.data;
let monitorPortal = hotData?.monitorPortal === true;
export function enableMonitorPortal() {
  monitorPortal = true;
  // Keep the host namespace stable when a reused component is hot-reloaded.
  if (hotData) hotData.monitorPortal = true;
}
export function isMonitorPortal() { return monitorPortal; }
export function operationsApiPath(path: string) {
  if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Invalid API path');
  return (monitorPortal ? '/operations-api/v1' : '/api/v1') + path;
}
