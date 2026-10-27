import { useI18n } from "../i18n";

interface QuickActionsProps {
  inputs: any;
  setInputs: (inputs: any) => void;
  apiAction: (url: string, method: string, body?: any) => void;
}

function QuickActions({ inputs, setInputs, apiAction }: QuickActionsProps) {
  const { t } = useI18n();
  return (
    <section className="glass-card">
      <h3>{t("quick.title")}</h3>
      <div className="add-form-col">
        <label>{t("quick.port_proto")}</label>
        <div style={{ display: "flex", gap: "5px" }}>
          <input
            value={inputs.port}
            onChange={(e) => setInputs({ ...inputs, port: e.target.value })}
            placeholder="80"
            style={{ flex: 2, minWidth: 0 }}
          />
          <select
            value={inputs.proto}
            onChange={(e) => setInputs({ ...inputs, proto: e.target.value })}
            style={{ flex: 1, minWidth: 0 }}
          >
            <option value="">{t("quick.any")}</option>
            <option value="tcp">TCP</option>
            <option value="udp">UDP</option>
          </select>
        </div>
        <label style={{ marginTop: "10px" }}>{t("quick.target")}</label>
        <input
          value={inputs.ruleIp}
          onChange={(e) => setInputs({ ...inputs, ruleIp: e.target.value })}
          placeholder={t("quick.target_placeholder")}
        />
        <div style={{ display: "flex", gap: "5px", marginTop: "10px" }}>
          <button
            className="btn-success"
            onClick={() => {
              apiAction("/api/rule", "POST", {
                action: "allow",
                port: inputs.port,
                proto: inputs.proto,
                ip: inputs.ruleIp,
              });
              setInputs({ ...inputs, port: "", ruleIp: "" });
            }}
          >
            {t("quick.allow")}
          </button>
          <button
            className="btn-danger"
            onClick={() => {
              apiAction("/api/rule", "POST", {
                action: "deny",
                port: inputs.port,
                proto: inputs.proto,
                ip: inputs.ruleIp,
              });
              setInputs({ ...inputs, port: "", ruleIp: "" });
            }}
          >
            {t("quick.deny")}
          </button>
        </div>
      </div>

      <div
        className="add-form-col"
        style={{
          marginTop: "25px",
          borderTop: "1px solid rgba(255,255,255,0.1)",
          paddingTop: "15px",
        }}
      >
        <label>{t("quick.quick_ban")}</label>
        <input
          value={inputs.banIp}
          onChange={(e) => setInputs({ ...inputs, banIp: e.target.value })}
          placeholder="1.2.3.4"
        />
        <button
          className="btn-danger"
          style={{ marginTop: "5px" }}
          onClick={() => {
            apiAction("/api/ban", "POST", { ip: inputs.banIp });
            setInputs({ ...inputs, banIp: "" });
          }}
        >
          {t("quick.ban")}
        </button>
      </div>
    </section>
  );
}

export default QuickActions;
