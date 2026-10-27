import { useI18n } from "../i18n";

interface LiveDropsTableProps {
  logs: any[];
  apiAction: (url: string, method: string, body?: any) => void;
}

function LiveDropsTable({ logs, apiAction }: LiveDropsTableProps) {
  const { t } = useI18n();
  return (
    <section className="glass-card">
      <h2>{t("drops.title")}</h2>
      <div className="table-container">
        <table className="log-table">
          <thead>
            <tr>
              <th>{t("drops.time")}</th>
              <th>{t("drops.source")}</th>
              <th>{t("drops.proto")}</th>
              <th>{t("drops.port")}</th>
              <th>{t("drops.action")}</th>
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
                    {t("drops.ban")}
                  </button>
                </td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr>
                <td colSpan={5} className="empty">
                  {t("drops.empty")}
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
