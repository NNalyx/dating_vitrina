export async function renderInterestPicker(container, api, selectedSet, options = {}) {
    const { minCount = 3, errorEl = null } = options;
    let categories = [];
    try {
        categories = await api.getInterests();
    } catch (e) {
        container.innerHTML = `<p class="error">Не удалось загрузить интересы</p>`;
        return { validate: () => `Ошибка загрузки интересов` };
    }

    container.innerHTML = `
        <div class="interest-picker">
            ${categories.map((cat, cidx) => `
                <div class="interest-category" style="animation-delay: ${cidx * 60}ms">
                    <div class="interest-category-label">${escapeHtml(cat.label)}</div>
                    <div class="chips">
                        ${cat.items.map((item, idx) => `
                            <span class="chip ${selectedSet.has(item) ? "selected" : ""}" data-value="${escapeHtml(item)}" style="animation-delay: ${idx * 25}ms">${escapeHtml(item)}</span>
                        `).join("")}
                    </div>
                </div>
            `).join("")}
        </div>
    `;

    container.querySelectorAll(".chip").forEach((chip) => {
        chip.addEventListener("click", () => {
            const value = chip.dataset.value;
            if (selectedSet.has(value)) {
                selectedSet.delete(value);
                chip.classList.remove("selected");
            } else {
                selectedSet.add(value);
                chip.classList.add("selected");
            }
            if (errorEl) errorEl.textContent = "";
        });
    });

    return {
        validate: () => {
            if (selectedSet.size < minCount) {
                return `Выбери минимум ${minCount} интереса`;
            }
            return null;
        },
    };
}

function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
