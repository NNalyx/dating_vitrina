async def test_index_served(aiohttp_client):
    from web_app import create_app

    app = create_app()
    client = await aiohttp_client(app)
    resp = await client.get("/")
    assert resp.status == 200
    text = await resp.text()
    assert "<title>Dating App</title>" in text
