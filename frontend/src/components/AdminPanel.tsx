interface AdminPanelProps {
  auditLogs: any[];
  users: any[];
  inputs: any;
  setInputs: (inputs: any) => void;
  apiAction: (url: string, method: string, body?: any) => void;
}

function AdminPanel({ auditLogs, users, inputs, setInputs, apiAction }: AdminPanelProps) {
  return (
    <div className="wide-pane">
      <section className="glass-card">
        <h2>Audit Logs</h2>
        <div className="table-container">
          <table className="log-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>User</th>
                <th>Action</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.map((l: any, i: number) => (
                <tr key={i}>
                  <td>{l.ts?.split("T")[1]?.slice(0, 8)}</td>
                  <td>{l.user}</td>
                  <td>
                    <b>{l.action}</b>
                  </td>
                  <td style={{ fontSize: "0.85em" }}>{l.details}</td>
                </tr>
              ))}
              {auditLogs.length === 0 && (
                <tr>
                  <td colSpan={4} className="empty">
                    No logs
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      <section className="glass-card">
        <h2>User Management</h2>
        <div className="tag-container">
          {users.map((u: any) => (
            <span key={u.username} className="tag port">
              {u.username} ({u.role}){" "}
              {u.role !== "superadmin" && (
                <i onClick={() => apiAction("/api/users/" + u.username, "DELETE")}>×</i>
              )}
            </span>
          ))}
          <div className="add-form">
            <input
              value={inputs.user}
              onChange={(e) => setInputs({ ...inputs, user: e.target.value })}
              placeholder="User"
            />
            <input
              type="password"
              value={inputs.pass}
              onChange={(e) => setInputs({ ...inputs, pass: e.target.value })}
              placeholder="Pass"
            />
            <button
              onClick={() => {
                apiAction("/api/users", "POST", {
                  username: inputs.user,
                  password: inputs.pass,
                });
                setInputs({ ...inputs, user: "", pass: "" });
              }}
            >
              + Add
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

export default AdminPanel;
