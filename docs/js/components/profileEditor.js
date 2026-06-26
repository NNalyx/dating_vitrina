import { renderInterestPicker } from "./interestPicker.js";

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

const FIELDS = {
    name: { title: "Как тебя зовут?", type: "text", placeholder: "Имя", minLength: 2 },
    age: { title: "Сколько тебе лет?", type: "number", placeholder: "Возраст", min: 16, max: 100 },
    gender: { title: "Твой пол", type: "choice", options: GENDER_OPTIONS },
    looking_for: { title: "Кого ты ищешь?", type: "choice", options: LOOKING_OPTIONS },
    goal: { title: "Что ищешь?", type: "choice", options: GOAL_OPTIONS },
    interests: { title: "Выбери интересы (минимум 3)", type: "interests" },
    city: { title: "Твой город", type: "city", placeholder: "Город" },
    photo_file_id: { title: "Фото профиля", type: "photo" },
};

export async function renderProfileEditor(container, api, field, user, onSave) {
    const config = FIELDS[field];
    if (!config) return;

    const editor = document.createElement("div");
    editor.className = "screen active profile-editor";
    editor.innerHTML = `
        <h2>${config.title}</h2>
        <div id="editor-content" style="flex:1; display:flex; flex-direction:column; gap:16px; justify-content:flex-start; padding-top: 20px;"></div>
        <div id="editor-error" class="error"></div>
        <button id="editorSave">Сохранить</button>
        <button class="secondary" id="editorCancel">Отмена</button>
    `;
    container.appendChild(editor);

    const content = document.getElementById("editor-content");
    const errorEl = document.getElementById("editor-error");
    let interestPicker = null;
    let interestSet = null;
    let cityValue = field === "city" ? (user.city || "") : "";
    let photoFileId = field === "photo_file_id" ? (user.photo_file_id || null) : null;

    if (config.type === "text") {
        content.innerHTML = `<input type="text" id="editor-input" placeholder="${config.placeholder}" value="${escapeHtml(user[field] || "")}">`;
    } else if (config.type === "number") {
        content.innerHTML = `<input type="number" id="editor-input" placeholder="${config.placeholder}" value="${user[field] || ""}">`;
    } else if (config.type === "choice") {
        content.innerHTML = `<div class="options">${config.options.map((o, i) =>
            `<button class="secondary option ${user[field] === o.value ? "selected" : ""}" data-value="${o.value}" style="animation-delay: ${i * 50}ms">${o.label}</button>`
        ).join("")}</div>`;
        content.querySelectorAll(".option").forEach((btn) => {
            btn.addEventListener("click", () => {
                content.querySelectorAll(".option").forEach((b) => b.classList.remove("selected"));
                btn.classList.add("selected");
            });
        });
    } else if (config.type === "interests") {
        interestSet = new Set(
            user.interests ? user.interests.split(",").map((s) => s.trim()).filter(Boolean) : []
        );
        interestPicker = await renderInterestPicker(content, api, interestSet, {
            minCount: 3,
            errorEl,
        });
    } else if (config.type === "city") {
        content.innerHTML = `<input type="text" id="editor-input" placeholder="${config.placeholder}" value="${escapeHtml(user.city || "")}">`;
        const input = document.getElementById("editor-input");
        const saveBtn = document.getElementById("editorSave");
        saveBtn.disabled = !cityValue;
        let cityTimeout;
        input.addEventListener("input", () => {
            clearTimeout(cityTimeout);
            cityValue = "";
            saveBtn.disabled = true;
            const city = input.value.trim();
            if (!city) {
                errorEl.textContent = "";
                return;
            }
            cityTimeout = setTimeout(async () => {
                try {
                    const data = await api.validateCity(city);
                    if (data.valid) {
                        errorEl.textContent = "";
                        cityValue = data.normalized;
                        saveBtn.disabled = false;
                    } else {
                        errorEl.textContent = data.error;
                    }
                } catch (e) {
                    errorEl.textContent = e.message;
                }
            }, 400);
        });
    } else if (config.type === "photo") {
        const previewSrc = user.photo_file_id ? api.photoUrl(user.photo_file_id) : "";
        content.innerHTML = `
            <p>Фото повышает количество лайков. Можешь заменить или удалить.</p>
            <img id="photoPreview" class="photo-preview" src="${previewSrc}" alt="" style="${previewSrc ? "" : "display:none;"}">
            <input type="file" id="photoInput" class="photo-input" accept="image/*">
            <button class="secondary" id="choosePhoto">Выбрать фото</button>
            <button class="secondary" id="removePhoto">Удалить фото</button>
        `;
        const photoInput = document.getElementById("photoInput");
        const photoPreview = document.getElementById("photoPreview");
        const choosePhoto = document.getElementById("choosePhoto");
        choosePhoto.addEventListener("click", () => photoInput.click());
        photoInput.addEventListener("change", async () => {
            const file = photoInput.files[0];
            if (!file) return;
            photoPreview.src = URL.createObjectURL(file);
            photoPreview.style.display = "block";
            choosePhoto.textContent = "Загрузка...";
            choosePhoto.disabled = true;
            try {
                const data = await api.uploadPhoto(file);
                photoFileId = data.file_id;
                choosePhoto.textContent = "Фото загружено";
            } catch (e) {
                errorEl.textContent = e.message;
                choosePhoto.textContent = "Выбрать фото";
                choosePhoto.disabled = false;
            }
        });
        document.getElementById("removePhoto").addEventListener("click", () => {
            photoFileId = null;
            photoPreview.style.display = "none";
            photoPreview.src = "";
            choosePhoto.textContent = "Выбрать фото";
        });
    }

    document.getElementById("editorCancel").addEventListener("click", close);

    document.getElementById("editorSave").addEventListener("click", async () => {
        const payload = buildPayload(config, field, cityValue, photoFileId, interestSet);
        if (payload === null) {
            errorEl.textContent = "Заполните поле корректно";
            return;
        }
        if (payload.error) {
            errorEl.textContent = payload.error;
            return;
        }
        try {
            await api.updateMe(payload.data);
            close();
            onSave();
        } catch (e) {
            errorEl.textContent = e.message;
        }
    });

    function close() {
        editor.remove();
    }
}

function buildPayload(config, field, cityValue, photoFileId, interestSet) {
    if (config.type === "text") {
        const value = document.getElementById("editor-input").value.trim();
        if (value.length < config.minLength) return { error: "Слишком коротко" };
        return { data: { [field]: value } };
    }
    if (config.type === "number") {
        const value = parseInt(document.getElementById("editor-input").value, 10);
        if (isNaN(value) || value < config.min || value > config.max) {
            return { error: `Введите число от ${config.min} до ${config.max}` };
        }
        return { data: { [field]: value } };
    }
    if (config.type === "choice") {
        const selected = document.querySelector(".option.selected");
        if (!selected) return { error: "Выберите вариант" };
        return { data: { [field]: selected.dataset.value } };
    }
    if (config.type === "interests") {
        if (!interestSet) return { error: "Ошибка загрузки интересов" };
        if (interestSet.size < 3) return { error: "Выбери минимум 3 интереса" };
        return { data: { interests: Array.from(interestSet) } };
    }
    if (config.type === "city") {
        if (!cityValue) return { error: "Введи и подожди проверку города" };
        return { data: { city: cityValue } };
    }
    if (config.type === "photo") {
        return { data: { photo_file_id: photoFileId } };
    }
    return null;
}

function escapeHtml(text) {
    if (!text) return "";
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
