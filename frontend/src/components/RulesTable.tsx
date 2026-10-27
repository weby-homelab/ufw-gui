import { useI18n } from "../i18n";

interface RulesTableProps {
  rules: any[];
  apiAction: (url: string, method: string, body?: any) => void;
}

function RulesTable({ rules, apiAction }: RulesTableProps) {
  const { t } = useI18n();
  return (
    <section className="glass-card" style={{ marginTop: "-10px" }}>
      <h2>{t("rules.title")}</h2>
      <div className="table-container">
        <table className="log-table">
          <thead>
            <tr>
              <th>{t("rules.id")}</th>
              <th>{t("rules.to")}</th>
              <th>{t("rules.action")}</th>
              <th>{t("rules.from")}</th>
              <th>{t("rules.manage")}</th>
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
                    {t("rules.delete")}
                  </button>
                </td>
              </tr>
            ))}
            {rules.length === 0 && (
              <tr>
                <td colSpan={5} className="empty">
                  {t("rules.empty")}
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
