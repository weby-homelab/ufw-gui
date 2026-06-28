import { useState, useEffect } from "react"
import "./App.css"
import SetupForm from "./components/SetupForm"
import LoginForm from "./components/LoginForm"
import Dashboard from "./components/Dashboard"
import AdminPanel from "./components/AdminPanel"
import SnapshotsPanel from "./components/SnapshotsPanel"
import SettingsPanel from "./components/SettingsPanel"

function App() {
  const [token, setToken] = useState(localStorage.getItem("ufw_token"))
  const [user, setUser] = useState<any>(null)
  const [setupNeeded, setSetupNeeded] = useState<boolean | null>(null)
  const [view, setView] = useState("config")

  // Dashboard state
  const [status, setStatus] = useState<any>(null)
  const [rules, setRules] = useState<any[]>([])
  const [bannedIps, setBannedIps] = useState<any[]>([])
  const [fwLogs, setFwLogs] = useState<any[]>([])
  const [stats, setStats] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [testTime, setTestTime] = useState(0)
  const [isTesting, setIsTesting] = useState(false)

  // Admin state
  const [auditLogs, setAuditLogs] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])

  // Snapshots state
  const [snapshots, setSnapshots] = useState<string[]>([])

  // Settings state
  const [tgConfig, setTgConfig] = useState({ tg_token: "", tg_chat_id: "" })

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
    if (testTime > 0) {
      alert("Cannot modify firewall rules while a test is active. Please confirm or wait for rollback.")
      return
    }
    setLoading(true)
    const res = await fetch(url, { method, headers: authHeaders, body: body ? JSON.stringify(body) : null })
    if (res.ok) fetchData()
    else alert("Action failed")
    setLoading(false)
  }

  const fetchData = async () => {
    if (!token || !user) return
    const f = async (u: string) => {
      const r = await fetch(u, { headers: authHeaders })
      if (r.status === 401) { logout(); return {} }
      return r.json()
    }
    try {
      setStatus(await f("/api/status"))

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
        setTgConfig(await f("/api/settings") || { tg_token: "", tg_chat_id: "" })
      }
    } catch (e) { console.error(e) }
  }

  useEffect(() => { checkSetup() }, [])
  useEffect(() => { if (token) fetchProfile() }, [token])
  useEffect(() => { if (token && user) fetchData() }, [token, user, view])

  useEffect(() => {
    let interval: any
    if (testTime > 0) interval = setInterval(() => setTestTime(prev => prev - 1), 1000)
    else if (testTime === 0 && isTesting) {
      setIsTesting(false)
      alert("Test timeout! Configuration auto-reverted.")
      fetchData()
    }
    return () => clearInterval(interval)
  }, [testTime, isTesting])

  const handleTestChanges = async () => {
    if (!confirm("Apply changes and start a 60-second test?")) return
    setLoading(true)
    try {
      const res = await fetch("/api/reload/test", { method: "POST", headers: authHeaders })
      if (!res.ok) throw new Error()
      setTestTime(60)
      setIsTesting(true)
    } catch {
      alert("Failed to initiate test")
      setTestTime(0)
      setIsTesting(false)
    } finally {
      setLoading(false)
    }
  }

  const confirmChanges = async () => {
    setLoading(true)
    try {
      const res = await fetch("/api/reload/confirm", { method: "POST", headers: authHeaders })
      if (!res.ok) throw new Error()
      setTestTime(0)
      setIsTesting(false)
      fetchData()
    } catch {
      alert("Confirmation failed. Auto-rollback will occur.")
    } finally {
      setLoading(false)
    }
  }

  if (setupNeeded === true) return <SetupForm onComplete={() => setSetupNeeded(false)} />
  if (!token) return <LoginForm onLogin={handleLogin} />

  return (
    <div className="container-fluid">
      <header className="glass-card header">
        <div className="brand"><h1>UFW-GUI</h1><span className="badge">v{__APP_VERSION__}</span></div>
        <nav className="view-nav">
          <button className={view === "config" ? "nav-btn active" : "nav-btn"} onClick={() => setView("config")}>Dashboard</button>
          <button className={view === "snapshots" ? "nav-btn active" : "nav-btn"} onClick={() => setView("snapshots")}>Snapshots</button>
          {user?.role === "superadmin" && <button className={view === "admin" ? "nav-btn active" : "nav-btn"} onClick={() => setView("admin")}>Admin</button>}
          {user?.role === "superadmin" && <button className={view === "settings" ? "nav-btn active" : "nav-btn"} onClick={() => setView("settings")}>Settings</button>}
        </nav>
        <div className="header-actions">
          <div className="user-tag">{user?.username} ({user?.role})</div>
          <button className="btn btn-test" onClick={handleTestChanges} disabled={testTime > 0}>
            {testTime > 0 ? "Testing... (" + testTime + "s)" : "Test Rule (60s)"}
          </button>
          <button className="btn-logout" onClick={logout}>Logout</button>
        </div>
      </header>

      {testTime > 0 && (
        <div className="test-banner">
          <div className="test-content">
            <h2>Testing Connection...</h2>
            <p>If you lose access, changes will be reverted in <b>{testTime}</b> seconds.</p>
            <button className="btn-confirm" onClick={confirmChanges}>Confirm Changes</button>
          </div>
        </div>
      )}

      <main className="dashboard-grid">
        {view === "config" && (
          <Dashboard
            status={status}
            rules={rules}
            bannedIps={bannedIps}
            fwLogs={fwLogs}
            stats={stats}
            inputs={inputs}
            setInputs={setInputs}
            apiAction={apiAction}
            loading={loading}
            testTime={testTime}
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
          <SnapshotsPanel
            snapshots={snapshots}
            apiAction={apiAction}
          />
        )}
      </main>

      <footer className="footer">&copy; 2026 Weby Homelab &bull; UFW-GUI (Debian/Ubuntu)</footer>
    </div>
  )
}

export default App
