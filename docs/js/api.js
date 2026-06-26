import { API_BASE_URL } from "./config.js";

const initData = window.Telegram?.WebApp?.initData || "";
const BASE_URL = API_BASE_URL || window.location.origin || "";

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
    const resp = await fetch(`${BASE_URL}${path}`, options);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
        throw new Error(data.error || `HTTP ${resp.status}`);
    }
    return data;
}

async function uploadRequest(path, formData) {
    const resp = await fetch(`${BASE_URL}${path}`, {
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
    validateCity: (city) => request("POST", "/api/validate-city", { city }),
    getInterests: () => request("GET", "/api/interests"),
    me: () => request("GET", "/api/me"),
    updateMe: (data) => request("PUT", "/api/me", data),
    uploadPhoto: (file) => {
        const formData = new FormData();
        formData.append("photo", file);
        return uploadRequest("/api/upload-photo", formData);
    },
    photoUrl: (fileId) => `${BASE_URL}/api/photo/${fileId}`,
    feed: () => request("GET", "/api/feed"),
    like: (id) => request("POST", `/api/feed/${id}/like`),
    skip: (id) => request("POST", `/api/feed/${id}/skip`),
    likes: () => request("GET", "/api/likes"),
    likeBack: (id) => request("POST", `/api/likes/${id}/like_back`),
    skipLike: (id) => request("POST", `/api/likes/${id}/skip`),
    getSettings: () => request("GET", "/api/settings"),
    updateSettings: (data) => request("PUT", "/api/settings", data),
    resetViews: () => request("POST", "/api/reset-views"),
    report: (id, reason) => request("POST", "/api/report", { reported_id: id, reason }),
};
