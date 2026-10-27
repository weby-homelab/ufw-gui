interface SnapshotsPanelProps {
  snapshots: string[];
}

function SnapshotsPanel({ snapshots }: SnapshotsPanelProps) {
  return (
    <div className="wide-pane">
      <section className="glass-card">
        <h2>Snapshots (Manual Review Only)</h2>
        <p className="recovery-alert" role="note">
          Snapshot creation and restore are disabled. Existing snapshots are retained for manual inspection.
        </p>
        <div className="snap-list">
          {snapshots.map((s: string) => (
            <div key={s} className="snap-item">
              <span>{s}</span>
            </div>
          ))}
          {snapshots.length === 0 && (
            <p className="empty">
              No snapshots are available for manual review.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}

export default SnapshotsPanel;
