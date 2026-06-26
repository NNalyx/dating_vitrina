import { withLoading } from "../components/loading.js";

export function renderSettings(container, api) {
    async function load() {
        try {
            const settings = await withLoading(container, () => api.getSettings());
            render(settings);
        } catch (e) {
            container.innerHTML = `<div class="screen active"><p>Ошибка: ${e.message}</p></div>`;
        }
    }

    function render(settings) {
        container.innerHTML = `
            <div class="screen active settings">
                <h2>Настройки</h2>
                <div class="settings-card">
                    <h3>Фильтры ленты</h3>
                    <div class="settings-row">
                        <span>Минимальный возраст</span>
                        <div class="stepper">
                            <button class="secondary" data-filter-field="min_age" data-delta="-1">−</button>
                            <span>${settings.min_age}</span>
                            <button class="secondary" data-filter-field="min_age" data-delta="1">+</button>
                        </div>
                    </div>
                    <div class="settings-row">
                        <span>Максимальный возраст</span>
                        <div class="stepper">
                            <button class="secondary" data-filter-field="max_age" data-delta="-1">−</button>
                            <span>${settings.max_age}</span>
                            <button class="secondary" data-filter-field="max_age" data-delta="1">+</button>
                        </div>
                    </div>
                    <div class="settings-row settings-toggle" id="cityToggle">
                        <span>Только мой город</span>
                        <div class="toggle ${settings.only_my_city ? "active" : ""}"></div>
                    </div>
                </div>
                <div class="settings-card">
                    <h3>Уведомления</h3>
                    <div class="settings-row settings-toggle" id="notifToggle">
                        <span>Новые лайки</span>
                        <div class="toggle ${settings.notifications_enabled ? "active" : ""}"></div>
                    </div>
                </div>
                <div class="settings-card">
                    <h3>Данные</h3>
                    <button class="secondary" id="resetViewsBtn">↺ Сбросить все просмотренные анкеты</button>
                </div>
            </div>
        `;

        container.querySelectorAll("[data-filter-field]").forEach((btn) => {
            btn.addEventListener("click", () => {
                const field = btn.dataset.filterField;
                const delta = parseInt(btn.dataset.delta, 10);
                settings[field] = Math.max(16, Math.min(100, settings[field] + delta));
                saveSettings(settings);
            });
        });

        document.getElementById("cityToggle").addEventListener("click", () => {
            settings.only_my_city = !settings.only_my_city;
            saveSettings(settings);
        });

        document.getElementById("notifToggle").addEventListener("click", () => {
            settings.notifications_enabled = !settings.notifications_enabled;
            saveSettings(settings);
        });

        document.getElementById("resetViewsBtn").addEventListener("click", async () => {
            if (!window.confirm("Все ранее просмотренные анкеты снова начнут показываться в ленте. Продолжить?")) return;
            try {
                await api.resetViews();
                window.alert("Готово — лента обновлена.");
            } catch (e) {
                window.alert("Ошибка: " + e.message);
            }
        });
    }

    async function saveSettings(settings) {
        try {
            await api.updateSettings(settings);
            load();
        } catch (e) {
            container.innerHTML = `<div class="screen active"><p>Ошибка: ${e.message}</p></div>`;
        }
    }

    load();
}
