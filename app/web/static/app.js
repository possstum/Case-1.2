const refreshSeconds = document.body.dataset.autoRefreshSeconds;

if (refreshSeconds) {
  const seconds = Number(refreshSeconds);
  if (!Number.isNaN(seconds) && seconds > 0) {
    window.setTimeout(() => {
      window.location.reload();
    }, seconds * 1000);
  }
}
