export function renderCaptcha(container, { question, token }, onSubmit) {
    container.innerHTML = `
        <div class="captcha">
            <h3>Подтверди, что ты не робот 🤖</h3>
            <p class="captcha-question">${question} = ?</p>
            <input
                type="number"
                inputmode="numeric"
                pattern="[0-9]*"
                class="captcha-input"
                id="captchaInput"
                placeholder="Введи ответ"
                autocomplete="off"
            />
            <p class="captcha-error" id="captchaError"></p>
            <button class="primary" id="captchaConfirm">Подтвердить</button>
        </div>
    `;

    const input = document.getElementById("captchaInput");
    const errorEl = document.getElementById("captchaError");

    function submitValue() {
        const value = input.value.trim();
        if (!value) return;
        onSubmit(value);
    }

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") submitValue();
    });

    input.addEventListener("input", () => {
        errorEl.textContent = "";
    });

    document.getElementById("captchaConfirm").addEventListener("click", submitValue);

    input.focus();

    return {
        getValue: () => input.value.trim(),
        submit: submitValue,
        showError: (msg) => {
            errorEl.textContent = msg;
            input.value = "";
            input.focus();
        },
    };
}
