interface LiveDropsTableProps {
  logs: any[];
  apiAction: (url: string, method: string, body?: any) => void;
}

function LiveDropsTable({ logs, apiAction }: LiveDropsTableProps) {
  return (
    <section className="glass-card">
      <h2>Live UFW Blocks</h2>
      <div className="table-container">
        <table className="log-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Source IP</th>
              <th>Proto</th>
              <th>Port</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l: any, i: number) => (
              <tr key={i}>
                <td>{l.time}</td>
                <td className="text-danger">{l.src}</td>
                <td>{l.proto}</td>
                <td>{l.port}</td>
                <td>
                  <button
                    className="btn-mini-ban"
                    onClick={() => apiAction("/api/ban", "POST", { ip: l.src })}
                  >
                    Ban IP
                  </button>
                </td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr>
                <td colSpan={5} className="empty">
                  No dropped packets found in UFW logs. Ensure UFW logging is ON.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default LiveDropsTable;
