import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ConnectionProvider } from "@/state/ConnectionStore";
import { PersonaProvider } from "@/state/PersonaStore";
import { PresenceProvider } from "@/state/PresenceStore";
import { ChatProvider } from "@/state/ChatStore";
import { ChatView } from "@/features/chat/ChatView";
import { FilesView } from "@/features/files/FilesView";
import { MemoryView } from "@/features/memory/MemoryView";
import { PlansView } from "@/features/plans/PlansView";
import { ProjectsView } from "@/features/projects/ProjectsView";
import { ResearchView } from "@/features/research/ResearchView";
import { TasksView } from "@/features/tasks/TasksView";
import { RemoteView } from "@/features/remote/RemoteView";
import { SettingsView } from "@/features/settings/SettingsView";
import { ComputerUseSettings } from "@/features/settings/ComputerUseSettings";

export default function App() {
  return (
    <PresenceProvider>
      <ConnectionProvider>
        <PersonaProvider>
          <ChatProvider>
            <Routes>
              <Route element={<AppShell />}>
                <Route index element={<Navigate to="/chat" replace />} />
                <Route path="/chat" element={<ChatView />} />
                <Route path="/files" element={<FilesView />} />
                <Route path="/memory" element={<MemoryView />} />
                <Route path="/projects" element={<ProjectsView />} />
                <Route path="/research" element={<ResearchView />} />
                <Route path="/tasks" element={<TasksView />} />
                <Route path="/plans" element={<PlansView />} />
                <Route path="/remote" element={<RemoteView />} />
                <Route path="/settings" element={<SettingsView />} />
                <Route path="/settings/computer-use" element={<ComputerUseSettings />} />
                <Route path="*" element={<Navigate to="/chat" replace />} />
              </Route>
            </Routes>
          </ChatProvider>
        </PersonaProvider>
      </ConnectionProvider>
    </PresenceProvider>
  );
}
