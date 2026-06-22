export function renderWelcome(app, onStart) {
    app.innerHTML = `
        <div class="screen active" id="welcome">
            <h1>Добро пожаловать</h1>
            <p>Знакомься с интересными людьми рядом. Красиво, быстро, безопасно.</p>
            <div style="flex:1"></div>
            <button id="startBtn">Начать</button>
        </div>
    `;
    document.getElementById("startBtn").addEventListener("click", onStart);
}
