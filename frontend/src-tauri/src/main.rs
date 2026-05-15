#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs::OpenOptions;
use std::io::Write;
use std::net::TcpStream;
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::Manager;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

/// Append a timestamped line to logs/launcher.log. On Windows release
/// builds stdout/stderr are discarded (windows_subsystem = "windows"),
/// so without this we'd have no record of backend spawn errors or
/// sidecar crash output. Best-effort: failures are silently swallowed.
fn launcher_log(line: &str) {
    let dir = vessel_ops_logs_dir();
    if std::fs::create_dir_all(&dir).is_err() {
        return;
    }
    let path = dir.join("launcher.log");
    let Ok(mut f) = OpenOptions::new().create(true).append(true).open(&path) else {
        return;
    };
    let ts = chrono_like_timestamp();
    let _ = writeln!(f, "{ts} {line}");
}

/// ISO-ish timestamp without pulling in chrono. Good enough to correlate
/// against the Python backend's vessel_debug.log entries.
fn chrono_like_timestamp() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format!("[{}s]", secs)
}

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
                    let s = String::from_utf8_lossy(&line);
                    println!("[backend] {}", s);
                    launcher_log(&format!("[backend stdout] {}", s.trim_end()));
                }
                CommandEvent::Stderr(line) => {
                    let s = String::from_utf8_lossy(&line);
                    eprintln!("[backend] {}", s);
                    launcher_log(&format!("[backend stderr] {}", s.trim_end()));
                }
                CommandEvent::Terminated(payload) => {
                    eprintln!("[backend] exited with {:?}", payload.code);
                    launcher_log(&format!("[backend exited] code={:?}", payload.code));
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
            launcher_log("[tauri] launcher starting");
            let dev = cfg!(debug_assertions);
            if dev {
                println!("[tauri] dev mode — expecting backend on :{}", BACKEND_PORT);
                launcher_log("[tauri] dev mode — skipping sidecar spawn");
                return Ok(());
            }

            launcher_log("[tauri] spawning backend sidecar");
            let child = match spawn_backend(&app.handle()) {
                Ok(c) => c,
                Err(e) => {
                    launcher_log(&format!("[tauri] spawn_backend FAILED: {}", e));
                    return Err(e.into());
                }
            };
            app.manage(BackendProcess(Mutex::new(Some(child))));

            if wait_for_backend(BACKEND_PORT, Duration::from_secs(BACKEND_READY_TIMEOUT_SECS)) {
                launcher_log("[tauri] backend ready on :8000");
            } else {
                launcher_log("[tauri] backend did NOT become ready within timeout");
                eprintln!("[tauri] backend did not become ready within timeout");
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            // Kill the backend on close. CloseRequested fires reliably on
            // Windows before the process tears down; Destroyed sometimes
            // doesn't run if the app exits first, which leaves the sidecar
            // orphaned in Task Manager.
            let should_kill = matches!(
                event,
                tauri::WindowEvent::CloseRequested { .. } | tauri::WindowEvent::Destroyed
            );
            if should_kill {
                if let Some(state) = window.app_handle().try_state::<BackendProcess>() {
                    if let Some(child) = state.0.lock().unwrap().take() {
                        launcher_log("[tauri] window closing — killing sidecar");
                        let _ = child.kill();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

struct BackendProcess(std::sync::Mutex<Option<CommandChild>>);
