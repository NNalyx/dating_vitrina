export function attachPullToRefresh(container, onRefresh) {
    let startY = 0;
    let currentY = 0;
    let pulling = false;
    const threshold = 80;

    const indicator = document.createElement("div");
    indicator.className = "pull-indicator";
    indicator.textContent = "↓ Потяни, чтобы обновить";
    container.prepend(indicator);

    function onTouchStart(e) {
        if (container.scrollTop > 0) return;
        startY = e.touches[0].clientY;
        pulling = true;
    }

    function onTouchMove(e) {
        if (!pulling) return;
        currentY = e.touches[0].clientY;
        const diff = currentY - startY;
        if (diff > 0) {
            indicator.style.transform = `translateY(${Math.min(diff / 2, threshold)}px)`;
            indicator.style.opacity = Math.min(diff / threshold, 1);
            if (diff >= threshold) {
                indicator.textContent = "Отпусти для обновления";
            }
        }
    }

    function onTouchEnd() {
        if (!pulling) return;
        pulling = false;
        const diff = currentY - startY;
        indicator.style.transform = "";
        indicator.style.opacity = "";
        indicator.textContent = "↓ Потяни, чтобы обновить";
        if (diff >= threshold) {
            onRefresh();
        }
        startY = 0;
        currentY = 0;
    }

    container.addEventListener("touchstart", onTouchStart, { passive: true });
    container.addEventListener("touchmove", onTouchMove, { passive: true });
    container.addEventListener("touchend", onTouchEnd);

    return () => {
        container.removeEventListener("touchstart", onTouchStart);
        container.removeEventListener("touchmove", onTouchMove);
        container.removeEventListener("touchend", onTouchEnd);
        indicator.remove();
    };
}
