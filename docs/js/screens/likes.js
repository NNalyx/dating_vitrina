export function renderLikes(container, api) {
    async function load() {
        try {
            const likes = await api.likes();
            render(likes);
        } catch (e) {
            container.innerHTML = `<div class="screen active likes-empty"><p>Ошибка: ${e.message}</p></div>`;
        }
    }

    function render(likes) {
        if (!likes.length) {
            container.innerHTML = `
                <div class="screen active likes-empty">
                    <h2>У тебя пока нет новых лайков</h2>
                    <p>Свайпай вправо, чтобы получить больше ❤️</p>
                </div>
            `;
            return;
        }

        const items = likes.map((u, i) => {
            const photo = u.photo_file_id
                ? `<img class="like-photo" src="${api.photoUrl(u.photo_file_id)}" alt="">`
                : `<div class="like-photo like-photo-placeholder">${u.name[0]}</div>`;
            return `
                <div class="like-card" style="animation-delay: ${i * 60}ms">
                    ${photo}
                    <div class="like-info">
                        <div class="like-name">${u.name}, ${u.age}</div>
                        <div class="like-city">${u.city || ""}</div>
                    </div>
                    <div class="like-actions">
                        <button class="secondary" data-id="${u.user_id}" data-action="skip">✕</button>
                        <button data-id="${u.user_id}" data-action="like">♥</button>
                    </div>
                </div>
            `;
        }).join("");

        container.innerHTML = `
            <div class="screen active likes">
                <h2>Тебя лайкнули</h2>
                <div class="likes-list">${items}</div>
            </div>
        `;

        container.querySelectorAll("[data-action]").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const id = parseInt(btn.dataset.id, 10);
                try {
                    if (btn.dataset.action === "like") {
                        await api.likeBack(id);
                    } else {
                        await api.skipLike(id);
                    }
                    load();
                } catch (e) {
                    container.innerHTML = `<div class="screen active likes-empty"><p>Ошибка: ${e.message}</p></div>`;
                }
            });
        });
    }

    load();
}
