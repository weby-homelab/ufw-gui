interface SettingsPanelProps {
  tgConfig: any;
  setTgConfig: (config: any) => void;
  apiAction: (url: string, method: string, body?: any) => void;
}

function SettingsPanel({ tgConfig, setTgConfig, apiAction }: SettingsPanelProps) {
  return (
    <div className="wide-pane">
      <section className="glass-card">
        <h2>Settings</h2>
        <div className="add-form-col">
          <label>Telegram Bot Token</label>
          <input
            value={tgConfig.tg_token}
            onChange={(e) => setTgConfig({ ...tgConfig, tg_token: e.target.value })}
            placeholder="Token"
          />
          <label>Telegram Chat ID</label>
          <input
            value={tgConfig.tg_chat_id}
            onChange={(e) => setTgConfig({ ...tgConfig, tg_chat_id: e.target.value })}
            placeholder="Chat ID"
          />
          <button
            className="btn-reload"
            onClick={() => apiAction("/api/settings", "POST", tgConfig)}
            style={{ width: "150px", marginTop: "10px" }}
          >
            Save Settings
          </button>
        </div>
      </section>
    </div>
  );
}

export default SettingsPanel;
