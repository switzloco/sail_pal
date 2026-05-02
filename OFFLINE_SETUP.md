# Local Network Setup Guide for Vessel Ops AI

To use Vessel Ops AI in an offline, local-first environment (e.g., at sea), follow these steps to configure your primary server and connect mobile devices.

## 1. Configure the Primary Server (The "Hub")

This device will host the LLM (Ollama) and the Vessel Ops AI backend.

1.  **Static IP Address**:
    -   Connect the server to your boat's Wi-Fi.
    -   In your OS network settings, assign a **Static IP** to the server (e.g., `192.168.1.100`). This ensures mobile devices don't lose the connection if the server restarts.
2.  **Ollama Configuration**:
    -   Install Ollama from [ollama.com](https://ollama.com).
    -   Set the environment variable `OLLAMA_HOST=0.0.0.0` to allow the backend to reach Ollama if they are on different containers/processes.
    -   Run `ollama run llama3` (or your preferred model) to pull it locally.
3.  **Start the Backend**:
    -   Ensure you are using the `entrypoint.py` or `uv run backend.main:app --host 0.0.0.0`.
    -   Verify the server is listening: Open `http://192.168.1.100:8000/healthz` on the server itself.

## 2. Connect Mobile Devices (The "Clients")

1.  **Join Boat Wi-Fi**:
    -   Connect your phone or tablet to the same Wi-Fi network as the server.
2.  **Access the App**:
    -   Open your mobile browser and enter the server's IP address and frontend port (e.g., `http://192.168.1.100:3000`).
3.  **Trust the Network**:
    -   If using HTTPS locally with self-signed certificates, you may need to "Proceed anyway" in the mobile browser. (Recommended: Use plain HTTP for local-only offline use to avoid certificate complexity).

## 3. Network Troubleshooting

-   **Ping Check**: From a mobile device, try to ping the server's IP.
-   **Firewall**: Ensure the server's firewall (Windows Firewall or `ufw`) allows incoming traffic on ports `8000` (API) and `3000` (Frontend).
-   **No Internet**: If your router tries to redirect to a "Login/Guest" page because there is no internet, look for a "Stay Connected" or "Use without Internet" option in your mobile Wi-Fi settings.
