import { API_BASE_URL } from "./config.js";

const initData = window.Telegram?.WebApp?.initData || "";

async function request(method, path, body = null) {
    const options = {
        method,
        headers: {
            "Content-Type": "application/json",
            "X-Init-Data": initData,
        },
    };
    if (body) {
        options.body = JSON.stringify(body);
    }
    const resp = await fetch(`${API_BASE_URL}${path}`, options);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
        throw new Error(data.error || `HTTP ${resp.status}`);
    }
    return data;
}

async function uploadRequest(path, formData) {
    const resp = await fetch(`${API_BASE_URL}${path}`, {
        method: "POST",
        headers: {
            "X-Init-Data": initData,
        },
        body: formData,
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
        throw new Error(data.error || `HTTP ${resp.status}`);
    }
    return data;
}

export const api = {
    auth: () => request("POST", "/api/auth", { initData }),
    register: (profile) => request("POST", "/api/register", { initData, ...profile }),
    me: () => request("GET", "/api/me"),
    uploadPhoto: (file) => {
        const formData = new FormData();
        formData.append("photo", file);
        return uploadRequest("/api/upload-photo", formData);
    },
};
