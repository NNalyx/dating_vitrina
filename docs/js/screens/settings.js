import { renderEditField } from "./editField.js";
import { withLoading } from "../components/loading.js";

const GENDER_OPTIONS = [
    { value: "male", label: "Парень" },
    { value: "female", label: "Девушка" },
    { value: "other", label: "Другое" },
];

const LOOKING_OPTIONS = [
    { value: "male", label: "Парней" },
    { value: "female", label: "Девушек" },
    { value: "all", label: "Всех" },
];

const GOAL_OPTIONS = [
    { value: "relationship", label: "Отношения" },
    { value: "friendship", label: "Дружба" },
    { value: "flirt", label: "Флирт" },
];

export function renderSettings(container, api) {
    async function load() {
        try {
            const [settings, user] = await withLoading(container, () =>
                Promise.all([api.getSettings(), api.me()])
            );
            render(settings, user);
        } catch (e) {
            container.innerHTML = `<div class="screen active"><p>Ошибка: ${e.message}</p></div>`;
        }
    }

    function render(settings, user) {
        const photo = user.photo_file_id
            ? `<img class="settings-profile-photo" src="${api.photoUrl(user.photo_file_id)}" alt="">`
            : `<div class="settings-profile-photo settings-profile-photo-placeholder">${user.name[0]}</div>`;

        const interests = user.interests
            ? user.interests.split(",").map((s) => s.trim()).filter(Boolean).join(" · ")
            : "—";

        container.innerHTML = `
            <div class="screen active settings">
                <h2>Настройки</h2>
                <div class="settings-card">
                    <h3>Моя анкета</h3>
                    <div class="settings-profile-header" data-profile-field="photo_file_id">
                        ${photo}
                        <div class="settings-profile-name">${user.name}</div>
                    </div>
                    ${profileRow("Имя", user.name, "name")}
                    ${profileRow("Возраст", user.age, "age")}
                    ${profileRow("Пол", _label(GENDER_OPTIONS, user.gender), "gender")}
                    ${profileRow("Ищу", _label(LOOKING_OPTIONS, user.looking_for), "looking_for")}
                    ${profileRow("Цель", _label(GOAL_OPTIONS, user.goal), "goal")}
                    ${profileRow("Интересы", interests, "interests")}
                    ${profileRow("Город", user.city || "—", "city")}
                </div>
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
            </div>
        `;

        container.querySelectorAll("[data-profile-field]").forEach((el) => {
            el.addEventListener("click", () => {
                const field = el.dataset.profileField;
                renderEditField(container, api, field, user, () => load());
            });
        });

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
    }

    function profileRow(label, value, field) {
        return `
            <div class="settings-row settings-profile-row" data-profile-field="${field}">
                <span>${label}</span>
                <div class="settings-profile-value">${value}</div>
            </div>
        `;
    }

    async function saveSettings(settings) {
        try {
            await api.updateSettings(settings);
            load();
        } catch (e) {
            container.innerHTML = `<div class="screen active"><p>Ошибка: ${e.message}</p></div>`;
        }
    }

    function _label(options, value) {
        return options.find((o) => o.value === value)?.label || value;
    }

    load();
}
