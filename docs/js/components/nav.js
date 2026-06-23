export function renderNav(container, api, current, onChange) {
    async function loadMe() {
        try {
            const user = await api.me();
            render(user);
        } catch (e) {
            render(null);
        }
    }

    function render(user) {
        const profilePhoto = user?.photo_file_id
            ? `<img class="nav-photo" src="${api.photoUrl(user.photo_file_id)}" alt="">`
            : `<div class="nav-photo nav-photo-placeholder">${user?.name?.[0] || "?"}</div>`;

        container.innerHTML = `
            <nav class="bottom-nav">
                <button class="nav-item ${current === "feed" ? "active" : ""}" data-screen="feed">
                    <span class="nav-icon">🔍</span>
                    <span class="nav-label">Лента</span>
                </button>
                <button class="nav-item ${current === "likes" ? "active" : ""}" data-screen="likes">
                    <span class="nav-icon">❤️</span>
                    <span class="nav-label">Лайки</span>
                </button>
                <button class="nav-item ${current === "profile" ? "active" : ""}" data-screen="profile">
                    ${profilePhoto}
                    <span class="nav-label">Профиль</span>
                </button>
                <button class="nav-item ${current === "settings" ? "active" : ""}" data-screen="settings">
                    <span class="nav-icon">⚙️</span>
                    <span class="nav-label">Настройки</span>
                </button>
            </nav>
        `;

        container.querySelectorAll(".nav-item").forEach((btn) => {
            btn.addEventListener("click", () => onChange(btn.dataset.screen));
        });
    }

    loadMe();
}
