import { useI18n } from "../i18n";

interface SnapshotsPanelProps {
  snapshots: string[];
}

function SnapshotsPanel({ snapshots }: SnapshotsPanelProps) {
  const { t } = useI18n();
  return (
    <div className="wide-pane">
      <section className="glass-card">
        <h2>{t("snapshots.title")}</h2>
        <p className="recovery-alert" role="note">
          {t("snapshots.notice")}
        </p>
        <div className="snap-list">
          {snapshots.map((s: string) => (
            <div key={s} className="snap-item">
              <span>{s}</span>
            </div>
          ))}
          {snapshots.length === 0 && (
            <p className="empty">
              {t("snapshots.empty")}
            </p>
          )}
        </div>
      </section>
    </div>
  );
}

export default SnapshotsPanel;
