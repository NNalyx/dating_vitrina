export function showModal({ title = "", message = "", confirmText = "OK", cancelText = "Отмена", onConfirm, onCancel, input = false, inputPlaceholder = "" }) {
    const existing = document.getElementById("app-modal");
    if (existing) existing.remove();

    const backdrop = document.createElement("div");
    backdrop.id = "app-modal";
    backdrop.className = "modal-backdrop";
    backdrop.innerHTML = `
        <div class="modal-card">
            ${title ? `<h3 class="modal-title">${title}</h3>` : ""}
            <p class="modal-message">${message}</p>
            ${input ? `<input type="text" class="modal-input" id="modalInput" placeholder="${inputPlaceholder}" />` : ""}
            <div class="modal-actions">
                ${cancelText ? `<button class="secondary modal-cancel">${cancelText}</button>` : ""}
                <button class="primary modal-confirm">${confirmText}</button>
            </div>
        </div>
    `;

    document.body.appendChild(backdrop);
    requestAnimationFrame(() => backdrop.classList.add("active"));

    const close = () => {
        backdrop.classList.remove("active");
        setTimeout(() => backdrop.remove(), 200);
    };

    const cancelBtn = backdrop.querySelector(".modal-cancel");
    if (cancelBtn) {
        cancelBtn.addEventListener("click", () => {
            close();
            if (onCancel) onCancel();
        });
    }

    backdrop.querySelector(".modal-confirm").addEventListener("click", () => {
        close();
        const value = input ? backdrop.querySelector("#modalInput")?.value?.trim() : null;
        if (onConfirm) onConfirm(value);
    });

    backdrop.addEventListener("click", (e) => {
        if (e.target === backdrop) {
            close();
            if (onCancel) onCancel();
        }
    });
}
