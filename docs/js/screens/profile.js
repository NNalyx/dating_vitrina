import { renderProfileEditor } from "../components/profileEditor.js";
import { withLoading } from "../components/loading.js";

const GENDER_LABELS = { male: "Парень", female: "Девушка", other: "Другое" };
const LOOKING_LABELS = { male: "Парней", female: "Девушек", all: "Всех" };
const GOAL_LABELS = { relationship: "Отношения", friendship: "Дружба", flirt: "Флирт" };

export function renderProfile(container, api) {
    async function load() {
        try {
            const user = await withLoading(container, () => api.me());
            render(user);
        } catch (e) {
            container.innerHTML = `<div class="screen active"><p>Ошибка: ${e.message}</p></div>`;
        }
    }

    function render(user) {
        const photo = user.photo_file_id
            ? `<img class="profile-photo" src="${api.photoUrl(user.photo_file_id)}" alt="">`
            : `<div class="profile-photo profile-photo-placeholder">${user.name[0]}</div>`;

        const interests = user.interests
            ? user.interests.split(",").map((s) => s.trim()).filter(Boolean).join(" · ")
            : "—";

        container.innerHTML = `
            <div class="screen active profile">
                <h2>Моя анкета</h2>
                <div class="profile-card">
                    <div class="profile-photo-wrap" data-field="photo_file_id">
                        ${photo}
                        <button class="profile-edit-photo" id="editPhoto">📷</button>
                    </div>
                    <div class="profile-fields">
                        ${field("Имя", user.name, "name")}
                        ${field("Возраст", user.age, "age")}
                        ${field("Пол", GENDER_LABELS[user.gender] || user.gender, "gender")}
                        ${field("Ищу", LOOKING_LABELS[user.looking_for] || user.looking_for, "looking_for")}
                        ${field("Цель", GOAL_LABELS[user.goal] || user.goal, "goal")}
                        ${field("Интересы", interests, "interests")}
                        ${field("Город", user.city || "—", "city")}
                    </div>
                </div>
            </div>
        `;

        container.querySelectorAll("[data-field]").forEach((el) => {
            el.addEventListener("click", () => {
                const field = el.dataset.field;
                renderProfileEditor(container, api, field, user, load);
            });
        });
    }

    function field(label, value, fieldName) {
        return `
            <div class="profile-field" data-field="${fieldName}">
                <div class="profile-field-label">${label}</div>
                <div class="profile-field-value">${value}</div>
                <button class="profile-field-edit">Изменить</button>
            </div>
        `;
    }

    load();
}
