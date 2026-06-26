import { withLoading } from "../components/loading.js";

export function renderFeed(container, api, onMutual) {
    let current = null;
    let isLoading = false;

    async function load() {
        if (isLoading) return;
        isLoading = true;
        try {
            const data = await withLoading(container, () => api.feed());
            current = data.done ? null : data;
            render();
        } catch (e) {
            container.innerHTML = `<div class="screen active feed-empty"><p>Ошибка: ${e.message}</p></div>`;
        } finally {
            isLoading = false;
        }
    }

    function render() {
        if (!current) {
            container.innerHTML = `
                <div class="screen active feed-empty">
                    <h2>Пока нет подходящих анкет</h2>
                    <p>Попробуй изменить фильтры в настройках.</p>
                </div>
            `;
            return;
        }

        const photoHtml = current.photo_file_id
            ? `<img class="card-photo" src="${api.photoUrl(current.photo_file_id)}" alt="">`
            : `<div class="card-photo card-photo-placeholder">${current.name[0]}</div>`;

        const interests = current.interests
            ? current.interests.split(",").map((s) => s.trim()).filter(Boolean).join(" · ")
            : "";

        container.innerHTML = `
            <div class="screen active feed" id="feed-screen">
                <div class="card" id="card">
                    ${photoHtml}
                    <div class="card-gradient"></div>
                    <button class="action-report" id="reportBtn" aria-label="Пожаловаться">🚩</button>
                    <div class="card-info">
                        <div class="card-name">${current.name}, ${current.age}</div>
                        <div class="card-meta">${current.city || ""}${current.city ? " · " : ""}${current.compatibility}% ❤️</div>
                        <div class="card-goal">🎯 ${_label(current.goal)}</div>
                        <div class="card-tags">${interests}</div>
                    </div>
                </div>
                <div class="feed-actions">
                    <button class="secondary action-skip" id="skipBtn">✕</button>
                    <button class="action-like" id="likeBtn">♥</button>
                </div>
            </div>
        `;

        document.getElementById("skipBtn").addEventListener("click", () => act("skip"));
        document.getElementById("likeBtn").addEventListener("click", () => act("like"));
        document.getElementById("reportBtn").addEventListener("click", async (e) => {
            e.stopPropagation();
            if (!current) return;
            const reason = window.prompt("Причина жалобы:");
            if (!reason) return;
            try {
                await api.report(current.user_id, reason);
                window.alert("Жалоба отправлена.");
            } catch (e) {
                window.alert("Ошибка: " + e.message);
            }
        });
        initSwipe();
    }

    function _label(goal) {
        const map = { relationship: "Отношения", friendship: "Дружба", flirt: "Флирт" };
        return map[goal] || goal;
    }

    async function act(type) {
        if (!current || isLoading) return;
        const card = document.getElementById("card");
        if (card) {
            card.style.transition = "transform 0.25s ease-out";
            card.style.transform = `translateX(${type === "like" ? "120%" : "-120%"}) rotate(${type === "like" ? "12deg" : "-12deg"})`;
        }
        const id = current.user_id;
        try {
            if (type === "like") {
                const result = await api.like(id);
                if (result.mutual && onMutual) onMutual();
            } else {
                await api.skip(id);
            }
        } catch (e) {
            container.innerHTML = `<div class="screen active feed-empty"><p>Ошибка: ${e.message}</p></div>`;
            return;
        }
        setTimeout(load, 220);
    }

    function initSwipe() {
        const card = document.getElementById("card");
        if (!card) return;

        let startX = 0;
        let currentX = 0;
        let dragging = false;

        const start = (x) => {
            startX = x;
            dragging = true;
            card.style.transition = "none";
        };
        const move = (x) => {
            if (!dragging) return;
            currentX = x - startX;
            const rotate = currentX * 0.05;
            card.style.transform = `translateX(${currentX}px) rotate(${rotate}deg)`;
        };
        const end = () => {
            if (!dragging) return;
            dragging = false;
            card.style.transition = "transform 0.2s ease-out";
            if (currentX > 80) {
                act("like");
            } else if (currentX < -80) {
                act("skip");
            } else {
                card.style.transform = "translateX(0) rotate(0deg)";
            }
            currentX = 0;
        };

        card.addEventListener("touchstart", (e) => start(e.touches[0].clientX), { passive: true });
        card.addEventListener("touchmove", (e) => move(e.touches[0].clientX), { passive: true });
        card.addEventListener("touchend", end);
        card.addEventListener("mousedown", (e) => start(e.clientX));
        window.addEventListener("mousemove", (e) => move(e.clientX));
        window.addEventListener("mouseup", end);
    }

    load();
}
