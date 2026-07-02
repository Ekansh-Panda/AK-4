import {
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { BottomNav } from "@/components/BottomNav";
import { ChatProvider } from "@/state/chat";
import { useConnection } from "@/state/connection";
import { LoginScreen } from "@/screens/LoginScreen";
import { ChatScreen } from "@/screens/ChatScreen";
import { DeviceScreen } from "@/screens/DeviceScreen";
import { PowerScreen } from "@/screens/PowerScreen";
import { FilesScreen } from "@/screens/FilesScreen";
import { SettingsScreen } from "@/screens/SettingsScreen";

/**
 * Authed shell: gates the tab routes behind a live connection, mounts the chat
 * provider (so the conversation survives tab switches), and renders the
 * persistent bottom nav. Settings is reachable even when not "connected" so a
 * person can fix their host/token, but the data tabs require a session.
 */
function AppShell() {
  const { isConnected } = useConnection();
  const location = useLocation();

  // Allow Settings without a session; everything else needs connecting first.
  if (!isConnected && location.pathname !== "/settings") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return (
    <ChatProvider>
      <div className="relative mx-auto min-h-dvh w-full max-w-md">
        <Outlet />
        <BottomNav />
      </div>
    </ChatProvider>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginScreen />} />

      <Route element={<AppShell />}>
        <Route path="/chat" element={<ChatScreen />} />
        <Route path="/device" element={<DeviceScreen />} />
        <Route path="/power" element={<PowerScreen />} />
        <Route path="/files" element={<FilesScreen />} />
        <Route path="/settings" element={<SettingsScreen />} />
      </Route>

      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  );
}
