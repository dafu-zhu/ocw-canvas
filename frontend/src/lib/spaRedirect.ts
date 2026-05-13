// Companion to public/404.html. GitHub Pages serves 404.html for unknown deep
// links; it bounces to `<base>/?/<path>`. This rewrites that back to `<base>/<path>`
// before react-router boots so the SPA sees the intended route.
export function applySpaRedirect(): void {
  const { search } = window.location;
  if (search.startsWith("?/")) {
    const path = search.slice(2);
    const base = import.meta.env.BASE_URL.replace(/\/$/, "");
    window.history.replaceState(null, "", `${base}/${path}${window.location.hash}`);
  }
}
