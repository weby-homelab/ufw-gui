import { useI18n } from "../i18n";

interface Fail2BanPanelProps {
  bannedIps: any[];
  apiAction: (url: string, method: string, body?: any) => void;
}

function Fail2BanPanel({ bannedIps, apiAction }: Fail2BanPanelProps) {
  const { t } = useI18n();
  return (
    <section className="glass-card" style={{ marginTop: "-10px" }}>
      <h2>{t("f2b.title")}</h2>
      <div className="tag-container">
        {bannedIps.map((b: any, i: number) => (
          <span key={i} className="tag banned">
            {b.ip} ({b.jail}){" "}
            <i onClick={() => apiAction("/api/fail2ban/unban", "POST", { ip: b.ip, jail: b.jail })}>
              ×
            </i>
          </span>
        ))}
        {bannedIps.length === 0 && <p className="empty">{t("f2b.empty")}</p>}
      </div>
    </section>
  );
}

export default Fail2BanPanel;
