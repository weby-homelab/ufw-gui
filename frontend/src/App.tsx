import { useState, useEffect } from "react"
import { LineChart, Line, XAxis, YAxis,  Tooltip, ResponsiveContainer } from "recharts"
import "./App.css"

function App() {
  const [token, setToken] = useState(localStorage.getItem("ufw_token"))
  const [user, setUser] = useState<any>(null)
  const [status, setStatus] = useState<any>(null)
  const [rules, setRules] = useState<any[]>([])
  const [bannedIps, setBannedIps] = useState<any[]>([])
  const [fwLogs, setFwLogs] = useState<any[]>([])
  const [stats, setStats] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [setupNeeded, setSetupNeeded] = useState<boolean | null>(null)
  const [testTime, setTestTime] = useState(0)
  const [view, setView] = useState("config") // ADDED VIEW STATE
  const [monitorView, setMonitorView] = useState("rules")

  const [snapshots, setSnapshots] = useState<string[]>([])
  const [auditLogs, setAuditLogs] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])
  const [tgConfig, setTgConfig] = useState({ tg_token: "", tg_chat_id: "" })

  const [inputs, setInputs] = useState({ port: "", proto: "", action: "allow", banIp: "", ruleIp: "", user: "", pass: "" })

  const authHeaders = { "Authorization": "Bearer " + token, "Content-Type": "application/json" }

  const logout = () => { localStorage.removeItem("ufw_token"); setToken(null); setUser(null) }

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
      if (res.ok) setUser(await res.json()); else logout()
    } catch (e) { logout() }
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
    let interval: any;
    if (testTime > 0) interval = setInterval(() => setTestTime(prev => prev - 1), 1000)
    else if (testTime === 0 && loading) { setLoading(false); alert("Test timeout! Configuration auto-reverted."); fetchData(); }
    return () => clearInterval(interval)
  }, [testTime])

  const apiAction = async (url: string, method: string, body?: any) => {
    setLoading(true)
    const res = await fetch(url, { method, headers: authHeaders, body: body ? JSON.stringify(body) : null })
    if (res.ok) fetchData(); else alert("Action failed")
    setLoading(false)
  }

  const handleTestChanges = async () => {
    if (!confirm("Apply changes and start a 60-second test?")) return;
    setLoading(true); setTestTime(60);
    try {
        const res = await fetch("/api/reload/test", { method: "POST", headers: authHeaders });
        if (!res.ok) throw new Error();
    } catch {
        alert("Failed to initiate test"); setLoading(false); setTestTime(0);
    }
  }

  const confirmChanges = async () => {
    try {
        await fetch("/api/reload/confirm", { method: "POST", headers: authHeaders });
        setTestTime(0); setLoading(false); fetchData();
    } catch { alert("Confirmation failed. Auto-rollback will occur.") }
  }

  if (setupNeeded === true) return (
    <div className="auth-screen">
      <form className="glass-card auth-card" onSubmit={async (e:any)=>{
        e.preventDefault();
        const res = await fetch("/api/auth/setup", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: e.target.user.value, password: e.target.pass.value })
        });
        if (res.ok) { alert("Admin created! Log in now."); setSetupNeeded(false); }
      }}>
        <h2>UFW-GUI Setup</h2>
        <input name="user" placeholder="Username" required />
        <input name="pass" type="password" placeholder="Password" required />
        <button className="btn-reload" type="submit">Create Admin</button>
      </form>
    </div>
  )

  if (!token) return <div className="auth-screen"><form className="glass-card auth-card" onSubmit={async (e:any)=>{
    e.preventDefault(); const fd=new FormData(); fd.append("username", e.target.user.value); fd.append("password", e.target.pass.value);
    const res = await fetch("/api/auth/login", {method:"POST", body:fd})
    if(res.ok){ const d=await res.json(); localStorage.setItem("ufw_token", d.access_token); setToken(d.access_token); }
    else alert("Login failed")
  }}><h2>UFW-GUI Login</h2><input name="user" placeholder="Username" /><input name="pass" type="password" placeholder="Password" /><button className="btn-reload">Login</button></form></div>

  return (
    <div className="container-fluid">
      <header className="glass-card header">
        <div className="brand"><h1>UFW-GUI</h1><span className="badge">v1.2.0</span></div>
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
            <>
                <div className="side-pane">
                  <section className="glass-card">
                    <h3>UFW Status: <span className={status?.status === "running" ? "text-success" : "text-danger"}>{status?.status}</span></h3>
                    <button className="btn-reload" style={{marginTop: "10px", width: "100%"}} onClick={() => apiAction("/api/toggle", "POST", {action: status?.status === "running" ? "disable" : "enable"})}>
                      {status?.status === "running" ? "Disable UFW" : "Enable UFW"}
                    </button>
                  </section>
                  
                  <section className="glass-card">
                    <h3>Quick Actions</h3>
                    <div className="add-form-col">
                      <label>Port & Protocol</label>
                      <div style={{display: "flex", gap: "5px"}}>
                        <input value={inputs.port} onChange={e=>setInputs({...inputs, port: e.target.value})} placeholder="80" style={{flex: 2, minWidth: 0}}/>
                        <select value={inputs.proto} onChange={e=>setInputs({...inputs, proto: e.target.value})} style={{flex: 1, minWidth: 0}}>
                          <option value="">Any</option><option value="tcp">TCP</option><option value="udp">UDP</option>
                        </select>
                      </div>
                      <label style={{marginTop:"10px"}}>Target IP / Subnet (Optional)</label>
                      <input value={inputs.ruleIp} onChange={e=>setInputs({...inputs, ruleIp: e.target.value})} placeholder="192.168.1.0/24 or Any" />
                      <div style={{display: "flex", gap: "5px", marginTop:"10px"}}>
                        <button className="btn-success" onClick={() => {apiAction("/api/rule", "POST", {action: "allow", port: inputs.port, proto: inputs.proto, ip: inputs.ruleIp}); setInputs({...inputs, port: "", ruleIp: ""})}}>Allow</button>
                        <button className="btn-danger" onClick={() => {apiAction("/api/rule", "POST", {action: "deny", port: inputs.port, proto: inputs.proto, ip: inputs.ruleIp}); setInputs({...inputs, port: "", ruleIp: ""})}}>Deny</button>
                      </div>
                    </div>
                    
                    <div className="add-form-col" style={{marginTop: "25px", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "15px"}}>
                      <label>Quick Ban IP Address</label>
                      <input value={inputs.banIp} onChange={e=>setInputs({...inputs, banIp: e.target.value})} placeholder="1.2.3.4" />
                      <button className="btn-danger" style={{marginTop:"5px"}} onClick={() => {apiAction("/api/ban", "POST", {ip: inputs.banIp}); setInputs({...inputs, banIp: ""})}}>Ban IP</button>
                    </div>
                  </section>
                </div>

                <div className="main-pane">
                  <section className="glass-card" style={{paddingBottom: "0"}}>
                    <div className="sub-nav">
                      <button className={monitorView === "rules" ? "sub-nav-btn active" : "sub-nav-btn"} onClick={() => setMonitorView("rules")}>Global Rules</button>
                      <button className={monitorView === "drops" ? "sub-nav-btn active" : "sub-nav-btn"} onClick={() => setMonitorView("drops")}>Live Drops (Logs)</button>
                      <button className={monitorView === "fail2ban" ? "sub-nav-btn active" : "sub-nav-btn"} onClick={() => setMonitorView("fail2ban")}>Fail2Ban</button>
                    </div>
                  </section>

                  {monitorView === "rules" && (
                    <section className="glass-card" style={{marginTop: "-10px"}}>
                      <h2>Active Firewall Rules</h2>
                      <div className="table-container">
                        <table className="log-table">
                          <thead><tr><th>ID</th><th>To (Port/Target)</th><th>Action</th><th>From (IP/Source)</th><th>Manage</th></tr></thead>
                          <tbody>
                            {rules.map((r, i) => (
                              <tr key={i}>
                                <td>[{r.id}]</td>
                                <td className="text-success">{r.to}</td>
                                <td style={{color: r.action.includes("ALLOW") ? "#00e676" : "#ff3d00"}}>{r.action}</td>
                                <td>{r.from}</td>
                                <td><button className="btn-mini-ban" onClick={()=>apiAction("/api/rule/"+r.id, "DELETE")}>Delete</button></td>
                              </tr>
                            ))}
                            {rules.length === 0 && <tr><td colSpan={5} className="empty">No rules configured</td></tr>}
                          </tbody>
                        </table>
                      </div>
                    </section>
                  )}

                  {monitorView === "drops" && (
                    <>
                      <section className="glass-card" style={{marginTop: "-10px"}}>
                        <h2>Attack Statistics (Last 24h)</h2>
                        <div style={{height:"150px", marginTop:"15px"}}><ResponsiveContainer width="100%" height="100%"><LineChart data={stats}><XAxis dataKey="hour" stroke="#666"/><YAxis stroke="#666"/><Tooltip/><Line type="monotone" dataKey="count" stroke="#ff4444" strokeWidth={3}/></LineChart></ResponsiveContainer></div>
                      </section>
                      <section className="glass-card">
                        <h2>Live UFW Blocks</h2>
                        <div className="table-container"><table className="log-table"><thead><tr><th>Time</th><th>Source IP</th><th>Proto</th><th>Port</th><th>Action</th></tr></thead>
                          <tbody>{fwLogs.map((l,i)=>(<tr key={i}><td>{l.time}</td><td className="text-danger">{l.src}</td><td>{l.proto}</td><td>{l.port}</td>
                            <td><button className="btn-mini-ban" onClick={()=>apiAction("/api/ban","POST",{ip:l.src})}>🚫 Ban IP</button></td></tr>))}
                            {fwLogs.length === 0 && <tr><td colSpan={5} className="empty">No dropped packets found in UFW logs. Ensure UFW logging is ON.</td></tr>}
                          </tbody></table></div>
                      </section>
                    </>
                  )}

                  {monitorView === "fail2ban" && (
                     <section className="glass-card" style={{marginTop: "-10px"}}>
                      <h2>Fail2Ban Active Bans</h2>
                      <div className="tag-container">
                        {bannedIps.map((b,i)=>(<span key={i} className="tag banned">{b.ip} ({b.jail}) <i onClick={()=>apiAction("/api/fail2ban/unban","POST",{ip:b.ip,jail:b.jail})}>×</i></span>))}
                        {bannedIps.length === 0 && <p className="empty">No active bans from Fail2Ban</p>}
                      </div>
                    </section>
                  )}
                </div>
            </>
        )}

        {view === "admin" && (
          <div className="wide-pane">
            <section className="glass-card"><h2>Audit Logs</h2><div className="table-container"><table className="log-table"><thead><tr><th>Time</th><th>User</th><th>Action</th><th>Details</th></tr></thead>
              <tbody>{auditLogs.map((l,i)=>(<tr key={i}><td>{l.ts?.split("T")[1]?.slice(0,8)}</td><td>{l.user}</td><td><b>{l.action}</b></td><td style={{fontSize:"0.85em"}}>{l.details}</td></tr>))}
              {auditLogs.length === 0 && <tr><td colSpan={4} className="empty">No logs</td></tr>}
              </tbody></table></div></section>
            <section className="glass-card"><h2>User Management</h2><div className="tag-container">
              {users.map(u => (<span key={u.username} className="tag port">{u.username} ({u.role}) {u.role !== "superadmin" && <i onClick={()=>apiAction("/api/users/"+u.username,"DELETE")}>×</i>}</span>))}
              <div className="add-form"><input value={inputs.user} onChange={e=>setInputs({...inputs,user:e.target.value})} placeholder="User" /><input type="password" value={inputs.pass} onChange={e=>setInputs({...inputs,pass:e.target.value})} placeholder="Pass" /><button onClick={()=>{apiAction("/api/users","POST",{username:inputs.user, password:inputs.pass});setInputs({...inputs,user:"",pass:""})}}>+ Add</button></div>
            </div></section>
          </div>
        )}

        {view === "settings" && (
          <div className="wide-pane">
            <section className="glass-card"><h2>Settings</h2><div className="add-form-col">
              <label>Telegram Bot Token</label><input value={tgConfig.tg_token} onChange={e=>setTgConfig({...tgConfig,tg_token:e.target.value})} placeholder="Token" />
              <label>Telegram Chat ID</label><input value={tgConfig.tg_chat_id} onChange={e=>setTgConfig({...tgConfig,tg_chat_id:e.target.value})} placeholder="Chat ID" />
              <button className="btn-reload" onClick={()=>apiAction("/api/settings","POST",tgConfig)} style={{width: "150px", marginTop: "10px"}}>Save Settings</button>
            </div></section>
          </div>
        )}

        {view === "snapshots" && (
          <div className="wide-pane"><section className="glass-card"><h2>Time Machine (Snapshots)</h2><div className="snap-list">
            {snapshots.map(s=>(<div key={s} className="snap-item"><span>{s}</span><button className="btn-reload" onClick={()=>{if(confirm("Restore?"))apiAction("/api/snapshots/restore/"+s,"POST")}} style={{background:"#ffaa00"}}>Restore</button></div>))}
            {snapshots.length === 0 && <p className="empty">No snapshots recorded yet. Try adding a rule.</p>}
          </div></section></div>
        )}

      </main>
      <footer className="footer">© 2026 Weby Homelab • UFW-GUI v1.2.0 (Debian/Ubuntu)</footer>
    </div>
  )
}

export default App
