//! Miori Core — Tauri host process.
//!
//! For v0.1 this is intentionally minimal: the React shell talks to the
//! Python FastAPI backend over HTTP/WebSocket directly. Native commands
//! (filesystem, device, system tray, etc.) will be added here as they land.

/// A trivial command kept as a wiring example for the frontend `invoke` path.
#[tauri::command]
fn ping(name: &str) -> String {
    format!("Miori is here, {name}.")
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![ping])
        .run(tauri::generate_context!())
        .expect("error while running Miori Core");
}
