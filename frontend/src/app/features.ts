// Deliberate build capability switch; never an authorization boundary.
// Frozen M0.6 checks out its pinned historical source and is not affected.
export const assetsApiEnabled = import.meta.env.VITE_ASSETS_API_ENABLED === 'true';
export const identityEnabled = import.meta.env.VITE_IDENTITY_ENABLED === 'true';
