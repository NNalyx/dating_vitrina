export function renderHome(app, api) {
    app.innerHTML = `
        <div class="screen active" id="home">
            <h1>Готово!</h1>
            <p>Регистрация завершена. Здесь скоро появится лента анкет.</p>
            <div style="flex:1"></div>
            <button disabled>Смотреть анкеты</button>
        </div>
    `;
}
