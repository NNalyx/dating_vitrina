# Skeleton loading overlay

## Goal
Add a universal shimmer loading state so screens feel responsive while waiting for API data.

## Design
- New component `docs/js/components/loading.js` exports `withLoading(container, asyncFn)`.
- `withLoading` renders a full-screen overlay inside the screen root, runs the async call, and removes the overlay in `finally`.
- Overlay is a dark block (`var(--surface)`) with a diagonal/horizontal shimmer gradient animation.
- Apply `withLoading` to the initial data fetch in `feed.js`, `likes.js`, `profile.js`, and `settings.js`.

## CSS
- `.skeleton-overlay`: absolute, inset 0, z-index 50, background surface, overflow hidden.
- `.skeleton-shimmer`: gradient strip animated with `@keyframes shimmer` translating from -100% to +100% over 1.2s infinitely.
- `.screen-root` gets `position: relative` so the overlay sizes to the screen area (above bottom nav).
