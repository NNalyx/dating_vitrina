import { api } from "./api.js";
import { renderWelcome } from "./screens/welcome.js";
import { renderRegistration } from "./screens/registration.js";
import { renderFeed } from "./screens/feed.js";
import { renderLikes } from "./screens/likes.js";
import { renderMatches } from "./screens/matches.js";
import { renderProfile } from "./screens/profile.js";
import { renderSettings } from "./screens/settings.js";
import { renderNav } from "./components/nav.js";

const app = document.getElementById("app");
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.ready();
    tg.expand();
    applyTelegramTheme(tg.themeParams);
    tg.onEvent("themeChanged", () => applyTelegramTheme(tg.themeParams));
}

function applyTelegramTheme(params) {
    if (!params) return;
    const root = document.documentElement;
    if (params.bg_color) root.style.setProperty("--bg", params.bg_color);
    if (params.secondary_bg_color) root.style.setProperty("--surface", params.secondary_bg_color);
    if (params.text_color) root.style.setProperty("--text", params.text_color);
    if (params.hint_color) root.style.setProperty("--text-muted", params.hint_color);
    if (params.button_color) root.style.setProperty("--accent", params.button_color);
    if (params.button_text_color) root.style.setProperty("--text-on-surface", params.button_text_color);
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
        else if (name === "matches") renderMatches(screenRoot, api);
        else if (name === "profile") renderProfile(screenRoot, api);
        else if (name === "settings") renderSettings(screenRoot, api);
    }

    switchScreen(screenName);
}

init();
