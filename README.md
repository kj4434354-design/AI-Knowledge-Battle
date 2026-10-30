# AI Knowledge Battle

A real-time multiplayer quiz game for 2–8 players, built with Python, FastAPI, WebSockets, HTML, CSS and JavaScript.

## Run on Windows 10/11

1. Install Python 3.10 or newer from https://www.python.org/downloads/ and select **Add Python to PATH** during setup.
2. Extract this ZIP file.
3. Open the extracted `ai_knowledge_battle` folder.
4. Click the address bar in File Explorer, type `cmd`, and press Enter.
5. Run:

   ```bash
   py -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   py -m uvicorn app:app --host 0.0.0.0 --port 8000
   ```

6. On the host laptop, open http://localhost:8000
7. For same-Wi-Fi multiplayer, other players can open `http://YOUR-LAPTOP-IP:8000`. Find the IP by running `ipconfig` in Command Prompt and using the IPv4 Address. Allow Python through Windows Firewall on private networks if prompted.

## AI question generation

The game works immediately using its built-in question bank. To enable live AI-generated questions, set an OpenAI API key in the same Command Prompt before starting the server:

```bash
set OPENAI_API_KEY=your_api_key_here
```

Optionally set `OPENAI_MODEL` to a model available to your API account. API usage may incur charges. Never publish your API key or commit it to GitHub.

## Notes before public deployment

- This is a challenge-ready prototype, not a hardened production service.
- For internet play outside the same Wi-Fi, deploy the app to a public host that supports persistent WebSocket connections and HTTPS/WSS.
- Add authentication, abuse controls, persistent scores, and server-side answer validation review before production use.
- Test with at least two separate browsers/devices. The host must have at least one other player before starting.
