interface SnapshotsPanelProps {
  snapshots: string[];
  apiAction: (url: string, method: string, body?: any) => void;
}

function SnapshotsPanel({ snapshots, apiAction }: SnapshotsPanelProps) {
  return (
    <div className="wide-pane">
      <section className="glass-card">
        <h2>Time Machine (Snapshots)</h2>
        <div className="snap-list">
          {snapshots.map((s: string) => (
            <div key={s} className="snap-item">
              <span>{s}</span>
              <button
                className="btn-reload"
                onClick={() => {
                  if (confirm("Restore?")) apiAction("/api/snapshots/restore/" + s, "POST");
                }}
                style={{ background: "#ffaa00" }}
              >
                Restore
              </button>
            </div>
          ))}
          {snapshots.length === 0 && (
            <p className="empty">
              No snapshots recorded yet. Try adding a rule.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}

export default SnapshotsPanel;
