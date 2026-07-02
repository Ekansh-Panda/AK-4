import { Outlet } from "react-router-dom";
import { LeftRail } from "./LeftRail";
import { RightPanel } from "./RightPanel";
import { TopBar } from "./TopBar";

/**
 * The shell. Left rail · center workspace (with its own composer per view) ·
 * right contextual panel · slim top status bar. Generous spacing, glassy calm.
 */
export function AppShell() {
  return (
    <div className="flex h-screen w-screen overflow-hidden text-ink">
      <LeftRail />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="min-h-0 flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>

      <RightPanel />
    </div>
  );
}
