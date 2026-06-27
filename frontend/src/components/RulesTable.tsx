interface RulesTableProps {
  rules: any[];
  apiAction: (url: string, method: string, body?: any) => void;
}

function RulesTable({ rules, apiAction }: RulesTableProps) {
  return (
    <section className="glass-card" style={{ marginTop: "-10px" }}>
      <h2>Active Firewall Rules</h2>
      <div className="table-container">
        <table className="log-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>To (Port/Target)</th>
              <th>Action</th>
              <th>From (IP/Source)</th>
              <th>Manage</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((r: any, i: number) => (
              <tr key={i}>
                <td>[{r.id}]</td>
                <td className="text-success">{r.to}</td>
                <td style={{ color: r.action.includes("ALLOW") ? "#00e676" : "#ff3d00" }}>
                  {r.action}
                </td>
                <td>{r.from}</td>
                <td>
                  <button
                    className="btn-mini-ban"
                    onClick={() => apiAction("/api/rule/" + r.id, "DELETE")}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {rules.length === 0 && (
              <tr>
                <td colSpan={5} className="empty">
                  No rules configured
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default RulesTable;
