import { api } from "./api.js";
import { renderWelcome } from "./screens/welcome.js";
import { renderRegistration } from "./screens/registration.js";
import { renderFeed } from "./screens/feed.js";
import { renderLikes } from "./screens/likes.js";
import { renderProfile } from "./screens/profile.js";
import { renderSettings } from "./screens/settings.js";
import { renderNav } from "./components/nav.js";

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
            showMain("feed");
        } else {
            renderWelcome(app, () => renderRegistration(app, api, () => showMain("feed")));
        }
    } catch (e) {
        app.innerHTML = `<div class="screen active"><p>Ошибка: ${e.message}</p></div>`;
    }
}

function showMain(screenName) {
    app.innerHTML = `
        <div id="screen-root" class="screen-root"></div>
        <div id="nav-root"></div>
    `;
    const screenRoot = document.getElementById("screen-root");
    const navRoot = document.getElementById("nav-root");

    function switchScreen(name) {
        renderNav(navRoot, api, name, switchScreen);
        if (name === "feed") renderFeed(screenRoot, api);
        else if (name === "likes") renderLikes(screenRoot, api);
        else if (name === "profile") renderProfile(screenRoot, api);
        else if (name === "settings") renderSettings(screenRoot, api);
    }

    switchScreen(screenName);
}

init();
