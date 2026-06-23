import { renderInterestPicker } from "../components/interestPicker.js";

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

export async function renderEditField(container, api, field, user, onSave) {
    const wrapper = document.createElement("div");
    wrapper.className = "screen active profile-editor";
    wrapper.innerHTML = `
        <h2>${fieldTitle(field)}</h2>
        <div id="edit-field-content" style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:16px;"></div>
        <div id="edit-field-error" class="error"></div>
        <button id="editFieldSave">Сохранить</button>
        <button class="secondary" id="editFieldCancel">Отмена</button>
    `;
    container.appendChild(wrapper);

    const content = document.getElementById("edit-field-content");
    const errorEl = document.getElementById("edit-field-error");
    let picker = null;
    let value = user[field];

    if (field === "name" || field === "age") {
        content.innerHTML = `<input type="${field === "age" ? "number" : "text"}" id="fieldInput" value="${escapeHtml(String(value || ""))}">`;
    } else if (field === "city") {
        content.innerHTML = `<input type="text" id="fieldInput" value="${escapeHtml(String(value || ""))}" placeholder="Город">`;
        const input = document.getElementById("fieldInput");
        const saveBtn = document.getElementById("editFieldSave");
        saveBtn.disabled = true;
        let cityTimeout;
        input.addEventListener("input", () => {
            clearTimeout(cityTimeout);
            value = "";
            saveBtn.disabled = true;
            const raw = input.value.trim();
            if (!raw) {
                errorEl.textContent = "";
                return;
            }
            cityTimeout = setTimeout(async () => {
                try {
                    const data = await api.validateCity(raw);
                    if (data.valid) {
                        errorEl.textContent = "";
                        value = data.normalized;
                        saveBtn.disabled = false;
                    } else {
                        errorEl.textContent = data.error;
                    }
                } catch (e) {
                    errorEl.textContent = e.message;
                }
            }, 400);
        });
    } else if (field === "gender") {
        value = value || "";
        content.innerHTML = renderOptions(GENDER_OPTIONS, value);
        content.querySelectorAll(".option").forEach((btn) => {
            btn.addEventListener("click", () => {
                value = btn.dataset.value;
                content.querySelectorAll(".option").forEach((b) => b.classList.remove("selected"));
                btn.classList.add("selected");
                errorEl.textContent = "";
            });
        });
    } else if (field === "looking_for") {
        value = value || "";
        content.innerHTML = renderOptions(LOOKING_OPTIONS, value);
        content.querySelectorAll(".option").forEach((btn) => {
            btn.addEventListener("click", () => {
                value = btn.dataset.value;
                content.querySelectorAll(".option").forEach((b) => b.classList.remove("selected"));
                btn.classList.add("selected");
                errorEl.textContent = "";
            });
        });
    } else if (field === "goal") {
        value = value || "";
        content.innerHTML = renderOptions(GOAL_OPTIONS, value);
        content.querySelectorAll(".option").forEach((btn) => {
            btn.addEventListener("click", () => {
                value = btn.dataset.value;
                content.querySelectorAll(".option").forEach((b) => b.classList.remove("selected"));
                btn.classList.add("selected");
                errorEl.textContent = "";
            });
        });
    } else if (field === "interests") {
        const currentSet = new Set(
            value ? String(value).split(",").map((s) => s.trim()).filter(Boolean) : []
        );
        picker = await renderInterestPicker(content, api, currentSet, {
            minCount: 3,
            errorEl,
        });
        value = currentSet;
    } else if (field === "photo_file_id") {
        content.innerHTML = `
            <p>Загрузи новое фото профиля.</p>
            <img id="editPhotoPreview" class="photo-preview" src="${user.photo_file_id ? api.photoUrl(user.photo_file_id) : ""}" alt="" style="${user.photo_file_id ? "" : "display:none;"}">
            <input type="file" id="editPhotoInput" class="photo-input" accept="image/*">
            <button class="secondary" id="editChoosePhoto">Выбрать фото</button>
        `;
        const input = document.getElementById("editPhotoInput");
        const chooseBtn = document.getElementById("editChoosePhoto");
        const preview = document.getElementById("editPhotoPreview");
        chooseBtn.addEventListener("click", () => input.click());
        input.addEventListener("change", async () => {
            const file = input.files[0];
            if (!file) return;
            preview.src = URL.createObjectURL(file);
            preview.style.display = "block";
            chooseBtn.textContent = "Загрузка...";
            chooseBtn.disabled = true;
            try {
                const data = await api.uploadPhoto(file);
                value = data.file_id;
                chooseBtn.textContent = "Фото загружено";
            } catch (e) {
                errorEl.textContent = e.message;
                chooseBtn.textContent = "Выбрать фото";
                chooseBtn.disabled = false;
            }
        });
    }

    document.getElementById("editFieldSave").addEventListener("click", async () => {
        if (field === "interests" && picker) {
            const err = picker.validate();
            if (err) {
                errorEl.textContent = err;
                return;
            }
        }
        if (field !== "interests" && field !== "photo_file_id") {
            if (field === "name" || field === "age" || field === "city") {
                const input = document.getElementById("fieldInput");
                value = input.value.trim();
                if (field === "age") {
                    const age = parseInt(value, 10);
                    if (!age || age < 16 || age > 100) {
                        errorEl.textContent = "Введи возраст от 16 до 100";
                        return;
                    }
                    value = age;
                }
                if (field === "name" && value.length < 2) {
                    errorEl.textContent = "Имя слишком короткое";
                    return;
                }
            }
            if (!value) {
                errorEl.textContent = "Выбери значение";
                return;
            }
        }

        const payload = field === "interests"
            ? { interests: Array.from(value) }
            : { [field]: value };

        try {
            await api.updateMe(payload);
            wrapper.remove();
            onSave();
        } catch (e) {
            errorEl.textContent = e.message;
        }
    });

    document.getElementById("editFieldCancel").addEventListener("click", () => {
        wrapper.remove();
    });
}

function renderOptions(options, selected) {
    return `<div class="options">${options.map((o, i) =>
        `<button class="secondary option ${selected === o.value ? "selected" : ""}" data-value="${o.value}" style="animation-delay: ${i * 50}ms">${o.label}</button>`
    ).join("")}</div>`;
}

function fieldTitle(field) {
    const titles = {
        name: "Имя",
        age: "Возраст",
        gender: "Пол",
        looking_for: "Кого ищу",
        goal: "Цель",
        interests: "Интересы",
        city: "Город",
        photo_file_id: "Фото профиля",
    };
    return titles[field] || field;
}

function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
