import { api } from "./api.js";
import { renderWelcome } from "./screens/welcome.js";
import { renderRegistration } from "./screens/registration.js";
import { renderHome } from "./screens/home.js";

const app = document.getElementById("app");
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.ready();
    tg.expand();
}

async function init() {
    try {
        const { is_registered } = await api.auth();
        if (is_registered) {
            renderHome(app, api);
        } else {
            renderWelcome(app, () => renderRegistration(app, api, () => renderHome(app, api)));
        }
    } catch (e) {
        app.innerHTML = `<div class="screen active"><p>Ошибка: ${e.message}</p></div>`;
    }
}

init();
