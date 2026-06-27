import { useState } from "react";
import RulesTable from "./RulesTable";
import LiveDropsTable from "./LiveDropsTable";
import Fail2BanPanel from "./Fail2BanPanel";
import QuickActions from "./QuickActions";
import UfwStatus from "./UfwStatus";
import StatsChart from "./StatsChart";

interface DashboardProps {
  status: any;
  rules: any[];
  bannedIps: any[];
  fwLogs: any[];
  stats: any[];
  inputs: any;
  setInputs: (inputs: any) => void;
  apiAction: (url: string, method: string, body?: any) => void;
  testTime: number;
}

function Dashboard({
  status,
  rules,
  bannedIps,
  fwLogs,
  stats,
  inputs,
  setInputs,
  apiAction,
  testTime,
}: DashboardProps) {
  const [monitorView, setMonitorView] = useState("rules");

  return (
    <>
      <div className="side-pane">
        <UfwStatus status={status} apiAction={apiAction} />
        <QuickActions inputs={inputs} setInputs={setInputs} apiAction={apiAction} />
      </div>

      <div className="main-pane">
        <section className="glass-card" style={{ paddingBottom: "0" }}>
          <div className="sub-nav">
            <button
              className={monitorView === "rules" ? "sub-nav-btn active" : "sub-nav-btn"}
              onClick={() => setMonitorView("rules")}
            >
              Global Rules
            </button>
            <button
              className={monitorView === "drops" ? "sub-nav-btn active" : "sub-nav-btn"}
              onClick={() => setMonitorView("drops")}
            >
              Live Drops (Logs)
            </button>
            <button
              className={monitorView === "fail2ban" ? "sub-nav-btn active" : "sub-nav-btn"}
              onClick={() => setMonitorView("fail2ban")}
            >
              Fail2Ban
            </button>
          </div>
        </section>

        {monitorView === "rules" && <RulesTable rules={rules} apiAction={apiAction} />}
        {monitorView === "drops" && (
          <>
            <StatsChart data={stats} />
            <LiveDropsTable logs={fwLogs} apiAction={apiAction} />
          </>
        )}
        {monitorView === "fail2ban" && <Fail2BanPanel bannedIps={bannedIps} apiAction={apiAction} />}
      </div>
    </>
  );
}

export default Dashboard;
