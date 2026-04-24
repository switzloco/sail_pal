#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::time::{Duration, Instant};
use tauri::Manager;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const BACKEND_PORT: u16 = 8000;
const BACKEND_READY_TIMEOUT_SECS: u64 = 30;

fn wait_for_backend(port: u16, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(250));
    }
    false
}

fn spawn_backend(app: &tauri::AppHandle) -> Result<CommandChild, String> {
    let sidecar = app
        .shell()
        .sidecar("vessel-ops-backend")
        .map_err(|e| format!("sidecar lookup failed: {e}"))?;

    let (mut rx, child) = sidecar
        .spawn()
        .map_err(|e| format!("failed to spawn backend: {e}"))?;

    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    println!("[backend] {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Stderr(line) => {
                    eprintln!("[backend] {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Terminated(payload) => {
                    eprintln!("[backend] exited with {:?}", payload.code);
                    break;
                }
                _ => {}
            }
        }
    });

    Ok(child)
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let dev = cfg!(debug_assertions);
            if dev {
                // In dev, the developer runs backend via scripts/start.sh or uvicorn.
                println!("[tauri] dev mode — expecting backend on :{}", BACKEND_PORT);
                return Ok(());
            }

            let child = spawn_backend(&app.handle())?;
            app.manage(BackendProcess(std::sync::Mutex::new(Some(child))));

            if !wait_for_backend(BACKEND_PORT, Duration::from_secs(BACKEND_READY_TIMEOUT_SECS)) {
                eprintln!("[tauri] backend did not become ready within timeout");
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(state) = window.app_handle().try_state::<BackendProcess>() {
                    if let Some(child) = state.0.lock().unwrap().take() {
                        let _ = child.kill();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

struct BackendProcess(std::sync::Mutex<Option<CommandChild>>);
