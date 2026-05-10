# Kaggle Writeup: Vessel Ops AI

**Title:** Vessel Ops AI: Precision Assistance for Remote Operations
**Subtitle:** Bringing life-saving Gemma 4 intelligence to austere, disconnected maritime environments.
**Tracks:** Main Track, Global Resilience, Health & Sciences, Ollama

## 1. The Problem: Isolation at Sea
When a crew member is injured 200 miles offshore, there is no internet connection, no doctor, and no opportunity for a second opinion. Vessels operate in highly austere environments where bandwidth is either non-existent or prohibitively expensive. In an emergency, the Medical Person In Charge (MPIC) relies on static textbooks and intuition. This isolation also extends to the engine room, where the Chief Engineer must diagnose complex machinery faults without OEM support.

## 2. The Solution: Vessel Ops AI
Vessel Ops AI is an offline-first application designed to serve as that critical second opinion. Powered entirely by Gemma 4 running locally on the ship's existing hardware, it requires zero cloud connectivity at sea. It provides AI-assisted medical triage grounded in official maritime literature and aids engineering operations through intelligent component and maintenance analysis.

## 3. Architecture & Technical Choices
Our primary engineering constraint was absolute reliance on an offline environment. The architecture is explicitly designed for local durability, low latency, and ease of deployment for non-technical crews.

*   **AI Engine (Ollama + Gemma 4):** We utilize `gemma4:12b` for mid-range laptops and `gemma4:27b` (Mixture-of-Experts) for higher-end hardware (32GB+ RAM). Ollama was chosen as the inference engine because of its incredible efficiency, robust local API, and cross-platform reliability.
*   **Backend (FastAPI + SQLite):** The backend is built on Python 3.11 with FastAPI. We bypassed heavy database engines in favor of SQLite in WAL (Write-Ahead Logging) mode, providing a robust, concurrent, zero-config data store perfectly suited for a single-server deployment on a laptop.
*   **Frontend (Next.js + Tauri):** The interface is a Next.js App Router application. To package the entire stack for end-users, we used Tauri to bundle the Next.js frontend and a PyInstaller-compiled Python backend into a single, zero-dependency executable (.exe / .dmg / AppImage).
*   **Data Synchronization:** To bridge the gap between offline operations and shore-side management, we engineered an offline-first queuing mechanism. Actions taken at sea (health events, maintenance logs) are queued locally and automatically synced to Firebase Firestore the moment the vessel comes into port and regains connectivity.

## 4. How We Used Gemma 4
Gemma 4 is the core intelligence of Vessel Ops AI. We leveraged its advanced reasoning and multimodal capabilities in the following ways:

*   **Retrieval-Augmented Generation (RAG):** Medical advice must be accurate. We indexed the *World Health Organization (WHO) International Medical Guide for Ships (IMGS, 3rd Edition)* into a local ChromaDB vector store. When the MPIC asks Gemma 4 a question, the model synthesizes a grounded response citing specific chapters and protocols, drastically reducing hallucination risks.
*   **Multimodal Image Parsing:** When a user uploads a photo of a broken engine component or a physical injury, Gemma 4’s multimodal capabilities analyze the image locally to provide diagnostic suggestions or maintenance logging context.
*   **Intelligent Routing:** The application intelligently routes user queries—distinguishing between a casual conversation, a database search, or an emergency triage request—triggering the appropriate internal function calls.

## 5. Challenges Overcame
*   **Running Frontier AI on "Potato" Hardware:** Many vessels have older laptops. We optimized the system to run `gemma4:12b` efficiently, leveraging the model's high capability-to-size ratio, ensuring responses are generated fast enough to be useful in an emergency.
*   **Deployment Complexity:** Installing Python, Node, and Ollama is beyond the typical crew member's capability. We overcame this by using Tauri to wrap the entire environment into a one-click installer that doesn't even require administrator privileges, ensuring seamless adoption.
*   **Data Integrity & State Management:** Handling state transitions between disconnected (at sea) and connected (in port) required careful engineering. We built a robust offline queue in the frontend that persists pending operations to local storage until an active backend connection is detected, ensuring no critical health or maintenance logs are ever lost during network transitions.

## 6. Conclusion
Vessel Ops AI proves that frontier intelligence doesn't have to be tethered to a massive data center. By bringing Gemma 4 directly to the edge, we are empowering maritime crews with the tools they need to stay safe, healthy, and operational, no matter how far they are from shore.
