import { renderInterestPicker } from "../components/interestPicker.js";
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
                    ${photo}
                    <button class="profile-edit-photo" id="editPhoto">📷</button>
                    <input type="file" id="photoInput" class="photo-input" accept="image/*">
                    <div class="profile-fields">
                        ${field("Имя", user.name, () => editText("name", "Введи имя", user.name))}
                        ${field("Возраст", user.age, () => editText("age", "Введи возраст", user.age))}
                        ${field("Пол", _label(GENDER_OPTIONS, user.gender), () => editChoice("gender", GENDER_OPTIONS))}
                        ${field("Ищу", _label(LOOKING_OPTIONS, user.looking_for), () => editChoice("looking_for", LOOKING_OPTIONS))}
                        ${field("Цель", _label(GOAL_OPTIONS, user.goal), () => editChoice("goal", GOAL_OPTIONS))}
                        ${field("Интересы", interests, () => editInterests(user.interests))}
                        ${field("Город", user.city || "—", () => editText("city", "Введи город", user.city || ""))}
                    </div>
                </div>
            </div>
        `;

        container.querySelectorAll(".profile-field-edit").forEach((btn, idx) => {
            const handlers = [
                () => editText("name", "Введи имя", user.name),
                () => editText("age", "Введи возраст", user.age),
                () => editChoice("gender", GENDER_OPTIONS),
                () => editChoice("looking_for", LOOKING_OPTIONS),
                () => editChoice("goal", GOAL_OPTIONS),
                () => editInterests(user.interests),
                () => editText("city", "Введи город", user.city || ""),
            ];
            btn.addEventListener("click", handlers[idx]);
        });

        document.getElementById("editPhoto").addEventListener("click", () => document.getElementById("photoInput").click());
        document.getElementById("photoInput").addEventListener("change", async () => {
            const file = document.getElementById("photoInput").files[0];
            if (!file) return;
            try {
                const data = await api.uploadPhoto(file);
                await api.updateMe({ photo_file_id: data.file_id });
                load();
            } catch (e) {
                alert(e.message);
            }
        });
    }

    function field(label, value, onEdit) {
        return `
            <div class="profile-field">
                <div class="profile-field-label">${label}</div>
                <div class="profile-field-value">${value}</div>
                <button class="profile-field-edit">Изменить</button>
            </div>
        `;
    }

    async function editText(field, message, current) {
        const value = prompt(message, current);
        if (value === null) return;
        try {
            await api.updateMe({ [field]: value });
            load();
        } catch (e) {
            alert(e.message);
        }
    }

    async function editChoice(field, options) {
        const value = prompt(`${field}\n${options.map((o) => `${o.value} — ${o.label}`).join("\n")}`);
        if (!value || !options.find((o) => o.value === value)) return;
        try {
            await api.updateMe({ [field]: value });
            load();
        } catch (e) {
            alert(e.message);
        }
    }

    async function editInterests(currentInterests) {
        const currentSet = new Set(
            currentInterests ? currentInterests.split(",").map((s) => s.trim()).filter(Boolean) : []
        );
        const editor = document.createElement("div");
        editor.className = "screen active profile-editor";
        editor.innerHTML = `
            <h2>Редактировать интересы</h2>
            <div id="interest-editor-content" style="flex:1; overflow-y:auto;"></div>
            <div id="editor-error" class="error"></div>
            <button id="saveInterests">Сохранить</button>
            <button class="secondary" id="cancelInterests">Отмена</button>
        `;
        container.appendChild(editor);

        const content = document.getElementById("interest-editor-content");
        const errorEl = document.getElementById("editor-error");
        const picker = await renderInterestPicker(content, api, currentSet, {
            minCount: 3,
            errorEl,
        });

        document.getElementById("saveInterests").addEventListener("click", async () => {
            const err = picker.validate();
            if (err) {
                errorEl.textContent = err;
                return;
            }
            try {
                await api.updateMe({ interests: Array.from(currentSet) });
                editor.remove();
                load();
            } catch (e) {
                errorEl.textContent = e.message;
            }
        });

        document.getElementById("cancelInterests").addEventListener("click", () => {
            editor.remove();
        });
    }

    function _label(options, value) {
        return options.find((o) => o.value === value)?.label || value;
    }

    load();
}
