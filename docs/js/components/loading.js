export function showLoading(container) {
    if (!container) return;
    hideLoading(container);
    const overlay = document.createElement("div");
    overlay.className = "skeleton-overlay";
    overlay.id = "skeleton-overlay";
    overlay.innerHTML = '<div class="skeleton-shimmer"></div>';
    container.appendChild(overlay);
}

export function hideLoading(container) {
    if (!container) return;
    const overlay = container.querySelector("#skeleton-overlay");
    if (overlay) overlay.remove();
}

export async function withLoading(container, fn) {
    showLoading(container);
    try {
        return await fn();
    } finally {
        hideLoading(container);
    }
}
