export function renderCaptcha(container, { question, token }, onSubmit) {
    container.innerHTML = `
        <div class="captcha">
            <h3>Подтверди, что ты не робот 🤖</h3>
            <p class="captcha-question">${question} = ?</p>
            <div class="captcha-display" id="captchaDisplay"></div>
            <div class="captcha-keyboard">
                ${[1, 2, 3, 4, 5, 6, 7, 8, 9, 0].map(n => `<button class="captcha-key" data-value="${n}">${n}</button>`).join("")}
            </div>
            <button class="secondary" id="captchaClear">Стереть</button>
            <p class="captcha-error" id="captchaError"></p>
        </div>
    `;

    const display = document.getElementById("captchaDisplay");
    const errorEl = document.getElementById("captchaError");
    let value = "";

    function updateDisplay() {
        display.textContent = value || "_";
        display.classList.remove("shake");
        void display.offsetWidth;
    }

    container.querySelectorAll(".captcha-key").forEach(btn => {
        btn.addEventListener("click", () => {
            if (value.length >= 2) return;
            value += btn.dataset.value;
            updateDisplay();
            if (value.length === 2 || (value.length === 1 && parseInt(value, 10) > 1 && question.includes("-"))) {
                // Auto-submit for single-digit answers if appropriate.
            }
        });
    });

    document.getElementById("captchaClear").addEventListener("click", () => {
        value = "";
        updateDisplay();
        errorEl.textContent = "";
    });

    return {
        getValue: () => value,
        submit: () => {
            if (!value) return;
            onSubmit(value);
        },
        showError: (msg) => {
            errorEl.textContent = msg;
            display.classList.add("shake");
            value = "";
            updateDisplay();
        },
    };
}
