import { withLoading } from "../components/loading.js";
import { attachPullToRefresh } from "../components/pullToRefresh.js";

export function renderMatches(container, api) {
    async function load() {
        try {
            const matches = await withLoading(container, () => api.matches());
            render(matches);
        } catch (e) {
            container.innerHTML = `<div class="screen active"><p>Ошибка: ${e.message}</p></div>`;
        }
    }

    function render(matches) {
        if (!matches || matches.length === 0) {
            container.innerHTML = `
                <div class="screen active matches">
                    <div class="empty-state">
                        <div class="empty-icon">💞</div>
                        <h3>Пока нет мэтчей</h3>
                        <p>Лайкай анкеты — взаимные симпатии появятся здесь.</p>
                    </div>
                </div>
            `;
            return;
        }

        const listHtml = matches.map((u) => {
            const photo = u.photo_file_id
                ? `<img class="match-photo" src="${api.photoUrl(u.photo_file_id)}" alt="">`
                : `<div class="match-photo match-photo-placeholder">${u.name[0]}</div>`;
            const contact = u.username
                ? `<a class="button secondary" href="https://t.me/${u.username}" target="_blank">💬 Написать</a>`
                : `<span class="muted">Контакт скрыт</span>`;
            return `
                <div class="match-card">
                    ${photo}
                    <div class="match-info">
                        <div class="match-name">${u.name}, ${u.age}</div>
                        <div class="match-meta">${u.city || ""} · совместимость ${u.compatibility}%</div>
                    </div>
                    ${contact}
                </div>
            `;
        }).join("");

        container.innerHTML = `
            <div class="screen active matches">
                <h2>Мэтчи</h2>
                <div class="matches-list">${listHtml}</div>
            </div>
        `;

        const screen = container.querySelector(".screen");
        attachPullToRefresh(screen, load);
    }

    load();
}
