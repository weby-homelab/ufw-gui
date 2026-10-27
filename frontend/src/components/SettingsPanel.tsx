import { useI18n } from "../i18n";

interface SettingsPanelProps {
  tgConfig: any;
  setTgConfig: (config: any) => void;
  apiAction: (url: string, method: string, body?: any) => void;
}

function SettingsPanel({ tgConfig, setTgConfig, apiAction }: SettingsPanelProps) {
  const { t } = useI18n();
  return (
    <div className="wide-pane">
      <section className="glass-card">
        <h2>{t("settings.title")}</h2>
        <div className="add-form-col">
          <label>{t("settings.token_label")}</label>
          <p role="note">
            {tgConfig.tg_token_configured
              ? t("settings.token_configured")
              : t("settings.token_missing")}
          </p>
          <input
            value={tgConfig.tg_token}
            onChange={(e) => setTgConfig({ ...tgConfig, tg_token: e.target.value })}
            placeholder={
              tgConfig.tg_token_configured
                ? t("settings.token_placeholder_keep")
                : t("settings.token_placeholder_new")
            }
          />
          <label>{t("settings.chat_id")}</label>
          <input
            value={tgConfig.tg_chat_id}
            onChange={(e) => setTgConfig({ ...tgConfig, tg_chat_id: e.target.value })}
            placeholder={t("settings.chat_placeholder")}
          />
          <button
            className="btn-reload"
            onClick={() => apiAction("/api/settings", "POST", tgConfig)}
            style={{ width: "150px", marginTop: "10px" }}
          >
            {t("settings.save")}
          </button>
        </div>
      </section>
    </div>
  );
}

export default SettingsPanel;
