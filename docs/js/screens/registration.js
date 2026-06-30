import { renderInterestPicker } from "../components/interestPicker.js";
import { renderCaptcha } from "../components/captcha.js";

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

const STEPS = [
    { id: "age", title: "Сколько тебе лет?" },
    { id: "name", title: "Как тебя зовут?" },
    { id: "gender", title: "Твой пол" },
    { id: "looking_for", title: "Кого ты ищешь?" },
    { id: "goal", title: "Что ищешь?" },
    { id: "interests", title: "Выбери интересы (минимум 3)" },
    { id: "city", title: "Твой город" },
    { id: "photo", title: "Фото профиля" },
    { id: "preview", title: "Проверь анкету" },
];

export function renderRegistration(app, api, onComplete) {
    let step = 0;
    const profile = {
        age: "",
        name: "",
        gender: "",
        looking_for: "",
        goal: "",
        interests: new Set(),
        city: "",
        photo_file_id: null,
    };
    let interestPicker = null;

    function render() {
        const current = STEPS[step];
        app.innerHTML = `
            <div class="screen" id="registration">
                <div class="step-counter">Шаг ${step + 1} из ${STEPS.length}</div>
                <h2>${current.title}</h2>
                <div id="step-content"></div>
                <div id="error" class="error"></div>
                <div style="flex:1"></div>
                <button id="nextBtn">Далее</button>
            </div>
        `;
        renderStepContent(current.id).then(() => {
            requestAnimationFrame(() => {
                const screen = document.getElementById("registration");
                if (screen) screen.classList.add("active");
            });
        });
        document.getElementById("nextBtn").addEventListener("click", handleNext);
    }

    async function renderStepContent(id) {
        const container = document.getElementById("step-content");
        if (id === "age") {
            container.innerHTML = `<input type="number" id="input" placeholder="Возраст" value="${profile.age}">`;
        } else if (id === "name") {
            container.innerHTML = `<input type="text" id="input" placeholder="Имя" value="${profile.name}">`;
        } else if (id === "gender") {
            container.innerHTML = `<div class="options">${GENDER_OPTIONS.map((o, i) =>
                `<button class="secondary option ${profile.gender === o.value ? "selected" : ""}" data-value="${o.value}" style="animation-delay: ${i * 50}ms">${o.label}</button>`
            ).join("")}</div>`;
        } else if (id === "looking_for") {
            container.innerHTML = `<div class="options">${LOOKING_OPTIONS.map((o, i) =>
                `<button class="secondary option ${profile.looking_for === o.value ? "selected" : ""}" data-value="${o.value}" style="animation-delay: ${i * 50}ms">${o.label}</button>`
            ).join("")}</div>`;
        } else if (id === "goal") {
            container.innerHTML = `<div class="options">${GOAL_OPTIONS.map((o, i) =>
                `<button class="secondary option ${profile.goal === o.value ? "selected" : ""}" data-value="${o.value}" style="animation-delay: ${i * 50}ms">${o.label}</button>`
            ).join("")}</div>`;
        } else if (id === "interests") {
            const errorEl = document.getElementById("error");
            interestPicker = await renderInterestPicker(container, api, profile.interests, {
                minCount: 3,
                errorEl,
            });
        } else if (id === "city") {
            container.innerHTML = `<input type="text" id="input" placeholder="Город" value="${profile.city}">`;
            const input = document.getElementById("input");
            const nextBtn = document.getElementById("nextBtn");
            nextBtn.disabled = !profile.city;
            let cityTimeout;
            input.addEventListener("input", () => {
                clearTimeout(cityTimeout);
                profile.city = "";
                nextBtn.disabled = true;
                const city = input.value.trim();
                if (!city) {
                    document.getElementById("error").textContent = "";
                    return;
                }
                cityTimeout = setTimeout(async () => {
                    try {
                        const data = await api.validateCity(city);
                        if (data.valid) {
                            document.getElementById("error").textContent = "";
                            profile.city = data.normalized;
                            nextBtn.disabled = false;
                        } else {
                            document.getElementById("error").textContent = data.error;
                        }
                    } catch (e) {
                        document.getElementById("error").textContent = e.message;
                    }
                }, 400);
            });
        } else if (id === "photo") {
            container.innerHTML = `
                <p>Фото повышает количество лайков. Пока можешь пропустить.</p>
                <img id="photoPreview" class="photo-preview" src="" alt="" style="display:none;">
                <input type="file" id="photoInput" class="photo-input" accept="image/*">
                <button class="secondary" id="choosePhoto">Выбрать фото</button>
                <button class="secondary" id="skipPhoto">Пропустить</button>
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
                    profile.photo_file_id = data.file_id;
                    choosePhoto.textContent = "Фото загружено";
                } catch (e) {
                    document.getElementById("error").textContent = e.message;
                    choosePhoto.textContent = "Выбрать фото";
                    choosePhoto.disabled = false;
                }
            });

            document.getElementById("skipPhoto").addEventListener("click", () => handleNext());
        } else if (id === "preview") {
            const photo = profile.photo_file_id
                ? `<img class="preview-photo" src="${api.photoUrl(profile.photo_file_id)}" alt="">`
                : `<div class="preview-photo preview-photo-placeholder">${profile.name[0]}</div>`;
            const interests = Array.from(profile.interests).join(", ") || "не выбраны";
            container.innerHTML = `
                <div class="preview-card">
                    ${photo}
                    <div class="preview-info">
                        <h3>${profile.name}, ${profile.age}</h3>
                        <p>${profile.city}</p>
                        <p>Ищу: ${LOOKING_OPTIONS.find(o => o.value === profile.looking_for)?.label || ""}</p>
                        <p>Цель: ${GOAL_OPTIONS.find(o => o.value === profile.goal)?.label || ""}</p>
                        <p>Интересы: ${interests}</p>
                    </div>
                </div>
                <p class="hint">Так тебя будут видеть другие пользователи.</p>
            `;
            document.getElementById("nextBtn").textContent = "Зарегистрироваться";
        }

        container.querySelectorAll(".option").forEach(btn => {
            btn.addEventListener("click", () => {
                if (id === "gender") profile.gender = btn.dataset.value;
                if (id === "looking_for") profile.looking_for = btn.dataset.value;
                if (id === "goal") profile.goal = btn.dataset.value;
                container.querySelectorAll(".option").forEach(b => b.classList.remove("selected"));
                btn.classList.add("selected");
            });
        });
    }

    function validate() {
        const current = STEPS[step];
        if (current.id === "age") {
            const age = parseInt(document.getElementById("input").value, 10);
            if (!age || age < 16 || age > 100) return "Введи возраст от 16 до 100";
            profile.age = age;
        } else if (current.id === "name") {
            const name = document.getElementById("input").value.trim();
            if (name.length < 2) return "Имя слишком короткое";
            profile.name = name;
        } else if (current.id === "gender") {
            if (!profile.gender) return "Выбери пол";
        } else if (current.id === "looking_for") {
            if (!profile.looking_for) return "Выбери, кого ищешь";
        } else if (current.id === "goal") {
            if (!profile.goal) return "Выбери цель";
        } else if (current.id === "interests") {
            if (interestPicker) {
                const err = interestPicker.validate();
                if (err) return err;
            } else if (profile.interests.size < 3) {
                return "Выбери минимум 3 интереса";
            }
        } else if (current.id === "city") {
            if (!profile.city) return "Введи и подожди проверку города";
        }
        return null;
    }

    async function handleNext() {
        const errorEl = document.getElementById("error");
        const err = validate();
        if (err) {
            errorEl.textContent = err;
            return;
        }
        errorEl.textContent = "";
        if (step < STEPS.length - 1) {
            step++;
            render();
        } else {
            await showCaptcha();
        }
    }

    async function showCaptcha() {
        try {
            const challenge = await api.getCaptcha();
            const overlay = document.createElement("div");
            overlay.className = "profile-editor active";
            overlay.innerHTML = `
                <div class="profile-editor-content">
                    <h3>Проверка</h3>
                    <div id="captchaBox"></div>
                    <button class="primary" id="captchaSubmit">Подтвердить</button>
                    <button class="secondary" id="captchaBack">Назад</button>
                </div>
            `;
            document.body.appendChild(overlay);

            const box = document.getElementById("captchaBox");
            const controller = renderCaptcha(box, challenge, () => submit(controller, challenge, overlay));

            document.getElementById("captchaSubmit").addEventListener("click", () => controller.submit());
            document.getElementById("captchaBack").addEventListener("click", () => overlay.remove());
        } catch (e) {
            document.getElementById("error").textContent = e.message;
        }
    }

    async function submit(controller, challenge, overlay) {
        const answer = controller.getValue();
        if (!answer) return;
        try {
            await api.register(
                {
                    age: profile.age,
                    name: profile.name,
                    gender: profile.gender,
                    looking_for: profile.looking_for,
                    goal: profile.goal,
                    interests: Array.from(profile.interests),
                    city: profile.city,
                    photo_file_id: profile.photo_file_id,
                },
                {
                    captcha_token: challenge.token,
                    captcha_answer: answer,
                }
            );
            overlay.remove();
            onComplete();
        } catch (e) {
            controller.showError(e.message || "Неверный ответ");
        }
    }

    render();
}
