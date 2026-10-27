import { useState, useEffect } from "react"
import "./App.css"
import SetupForm from "./components/SetupForm"
import LoginForm from "./components/LoginForm"
import Dashboard from "./components/Dashboard"
import AdminPanel from "./components/AdminPanel"
import SnapshotsPanel from "./components/SnapshotsPanel"
import SettingsPanel from "./components/SettingsPanel"
import LanguageSwitcher from "./components/LanguageSwitcher"
import { useI18n } from "./i18n"

function App() {
  const { t, roleLabel } = useI18n()
  const [token, setToken] = useState(localStorage.getItem("ufw_token"))
  const [user, setUser] = useState<any>(null)
  const [setupNeeded, setSetupNeeded] = useState<boolean | null>(null)
  const [view, setView] = useState("config")

  // Dashboard state
  const [status, setStatus] = useState<any>(null)
  const [diagnostics, setDiagnostics] = useState<any>(null)
  const [rules, setRules] = useState<any[]>([])
  const [bannedIps, setBannedIps] = useState<any[]>([])
  const [fwLogs, setFwLogs] = useState<any[]>([])
  const [stats, setStats] = useState<any[]>([])
  const [apiLoading, setApiLoading] = useState(false)
  const [recoveryStatus, setRecoveryStatus] = useState<any>(null)

  // Admin state
  const [auditLogs, setAuditLogs] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])

  // Snapshots state
  const [snapshots, setSnapshots] = useState<string[]>([])

  // Settings state
  const [tgConfig, setTgConfig] = useState({ tg_token: "", tg_chat_id: "", tg_token_configured: false })

  // Shared form inputs
  const [inputs, setInputs] = useState({ port: "", proto: "", action: "allow", banIp: "", ruleIp: "", user: "", pass: "" })

  const authHeaders = { "Authorization": "Bearer " + token, "Content-Type": "application/json" }

  const logout = () => {
    localStorage.removeItem("ufw_token")
    setToken(null)
    setUser(null)
  }

  const handleLogin = (newToken: string) => {
    localStorage.setItem("ufw_token", newToken)
    setToken(newToken)
  }

  const checkSetup = async () => {
    try {
      const res = await fetch("/api/auth/setup-needed")
      const data = await res.json()
      setSetupNeeded(data.setup_needed)
    } catch (e) { console.error(e) }
  }

  const fetchProfile = async () => {
    if (!token) return
    try {
      const res = await fetch("/api/auth/me", { headers: authHeaders })
      if (res.ok) setUser(await res.json())
      else logout()
    } catch (e) { logout() }
  }

  const apiAction = async (url: string, method: string, body?: any) => {
    setApiLoading(true)
    try {
      const res = await fetch(url, { method, headers: authHeaders, body: body ? JSON.stringify(body) : null })
      if (res.ok) {
        fetchData()
        return
      }

      let error: any = {}
      try { error = await res.json() } catch { /* Keep the HTTP status as a fallback. */ }
      if (res.status === 503 && String(error.detail || "").includes("manual_recovery_required")) {
        setRecoveryStatus({
          mode: "manual_recovery_required",
          unresolved_marker: true,
          automatic_rollback: false,
          firewall_mutations_blocked: true,
        })
      }
      alert(error.detail || t("alert.action_failed", { status: res.status }))
    } catch {
      alert(t("alert.backend_unreachable"))
    } finally {
      setApiLoading(false)
    }
  }

  const fetchData = async () => {
    if (!token || !user) return
    const f = async (u: string) => {
      const r = await fetch(u, { headers: authHeaders })
      if (r.status === 401) { logout(); return {} }
      const data = await r.json().catch(() => ({}))
      if (!r.ok) {
        return { ...data, __error: data.detail || `Request failed (HTTP ${r.status})` }
      }
      return data
    }
    try {
      setRecoveryStatus(await f("/api/reload/status"))
      setStatus(await f("/api/status"))
      setDiagnostics(await f("/api/diagnostics"))

      if (view === "config") {
        setRules((await f("/api/rules")).rules || [])
        setBannedIps((await f("/api/fail2ban/status")).banned || [])
        setFwLogs((await f("/api/logs")).logs || [])
        setStats((await f("/api/stats")).hourly || [])
      }

      if (view === "snapshots") {
        const snData = await f("/api/snapshots/all")
        const filteredSnaps = (snData.snapshots || []).filter((s: string) => !s.startsWith("test_"))
        setSnapshots(filteredSnaps)
      }

      if (view === "admin" && user.role === "superadmin") {
        setAuditLogs((await f("/api/audit-logs")).logs || [])
        const uData = await f("/api/users")
        setUsers(Array.isArray(uData) ? uData : [])
      }

      if (view === "settings" && user.role === "superadmin") {
        const settings = await f("/api/settings")
        setTgConfig({
          tg_token: "",
          tg_chat_id: settings.tg_chat_id || "",
          tg_token_configured: Boolean(settings.tg_token_configured),
        })
      }
    } catch (e) { console.error(e) }
  }

  useEffect(() => { checkSetup() }, [])
  useEffect(() => { if (token) fetchProfile() }, [token])
  useEffect(() => { if (token && user) fetchData() }, [token, user, view])

  if (setupNeeded === true) return <SetupForm onComplete={() => setSetupNeeded(false)} />
  if (!token) return <LoginForm onLogin={handleLogin} />

  return (
    <div className="container-fluid">
      <header className="glass-card header">
        <div className="brand"><h1>UFW-GUI</h1><span className="badge">v{__APP_VERSION__}</span></div>
        <nav className="view-nav">
          <button className={view === "config" ? "nav-btn active" : "nav-btn"} onClick={() => setView("config")}>{t("nav.dashboard")}</button>
          <button className={view === "snapshots" ? "nav-btn active" : "nav-btn"} onClick={() => setView("snapshots")}>{t("nav.snapshots")}</button>
          {user?.role === "superadmin" && <button className={view === "admin" ? "nav-btn active" : "nav-btn"} onClick={() => setView("admin")}>{t("nav.admin")}</button>}
          {user?.role === "superadmin" && <button className={view === "settings" ? "nav-btn active" : "nav-btn"} onClick={() => setView("settings")}>{t("nav.settings")}</button>}
        </nav>
        <div className="header-actions">
          <LanguageSwitcher />
          <div className="user-tag">{user?.username} ({roleLabel(user?.role || "")})</div>
          <button className="btn-logout" onClick={logout}>{t("action.logout")}</button>
        </div>
      </header>

      <aside className="recovery-notice" role="note">
        <strong>{t("app.recovery_notice_title")}</strong> {t("app.recovery_notice_body")}
      </aside>
      {recoveryStatus?.unresolved_marker && (
        <aside className="recovery-alert" role="alert" aria-live="assertive">
          <strong>{t("app.manual_recovery_title")}</strong> {t("app.manual_recovery_body")}
        </aside>
      )}

      <main className="dashboard-grid">
        {view === "config" && (
          <Dashboard
            status={status}
            diagnostics={diagnostics}
            rules={rules}
            bannedIps={bannedIps}
            fwLogs={fwLogs}
            stats={stats}
            inputs={inputs}
            setInputs={setInputs}
            apiAction={apiAction}
          />
        )}

        {view === "admin" && (
          <AdminPanel
            auditLogs={auditLogs}
            users={users}
            inputs={inputs}
            setInputs={setInputs}
            apiAction={apiAction}
          />
        )}

        {view === "settings" && (
          <SettingsPanel
            tgConfig={tgConfig}
            setTgConfig={setTgConfig}
            apiAction={apiAction}
          />
        )}

        {view === "snapshots" && (
          <SnapshotsPanel snapshots={snapshots} />
        )}
      </main>

      <footer className="footer">{t("app.footer")}</footer>
    </div>
  )
}

export default App
