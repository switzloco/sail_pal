#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::path::PathBuf;
use std::time::{Duration, Instant};
use tauri::Manager;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const BACKEND_PORT: u16 = 8000;
const BACKEND_READY_TIMEOUT_SECS: u64 = 30;

/// Compute the same logs directory the Python backend writes to.
/// Must mirror backend/entrypoint.py::_resolve_data_dir + backend/logger.py.
fn vessel_ops_logs_dir() -> PathBuf {
    let base = if cfg!(target_os = "macos") {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        PathBuf::from(home).join("Library/Application Support/VesselOpsAI")
    } else if cfg!(target_os = "windows") {
        let appdata = std::env::var("APPDATA").unwrap_or_else(|_| ".".to_string());
        PathBuf::from(appdata).join("VesselOpsAI")
    } else {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        PathBuf::from(home).join(".local/share/VesselOpsAI")
    };
    base.join("logs")
}

/// Open the logs directory in the system file manager.
/// Creates the directory first so a fresh install doesn't fail to open it.
#[tauri::command]
fn open_logs_dir() -> Result<(), String> {
    let dir = vessel_ops_logs_dir();
    std::fs::create_dir_all(&dir).map_err(|e| format!("create dir: {e}"))?;
    let path = dir.as_os_str();

    #[cfg(target_os = "windows")]
    let opener = "explorer";
    #[cfg(target_os = "macos")]
    let opener = "open";
    #[cfg(target_os = "linux")]
    let opener = "xdg-open";

    std::process::Command::new(opener)
        .arg(path)
        .spawn()
        .map_err(|e| format!("spawn {opener}: {e}"))?;
    Ok(())
}

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
        .invoke_handler(tauri::generate_handler![open_logs_dir])
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
