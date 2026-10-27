import { en, useI18n, type MessageKey } from "../i18n";

interface UfwStatusProps {
  status: any;
  diagnostics: any;
  apiAction: (url: string, method: string, body?: any) => void;
}

function UfwStatus({ status, diagnostics, apiAction }: UfwStatusProps) {
  const { t } = useI18n();
  const isRunning = status?.status === "running";
  const isInactive = status?.status === "inactive";
  const isUnavailable = Boolean(status) && !isRunning && !isInactive;
  const label = isRunning
    ? t("ufw.running")
    : isInactive
      ? t("ufw.inactive")
      : status
        ? t("ufw.unavailable")
        : t("ufw.loading");

  const hints: string[] = Array.isArray(diagnostics?.hint_codes)
    ? diagnostics.hint_codes
    : [];
  const hintText = (code: string) => {
    const key = `diag.${code}` as MessageKey;
    return key in en ? t(key) : t("diag.unknown");
  };
  const statusMessageKey = status?.error_code
    ? (`ufw.error_${status.error_code}` as MessageKey)
    : "ufw.unavailable_default";
  const statusMessage = statusMessageKey in en
    ? t(statusMessageKey)
    : t("ufw.unavailable_default");

  return (
    <section className="glass-card">
      <h3>
        {t("ufw.title")}:{" "}
        <span
          className={
            isRunning ? "text-success" : isInactive ? "text-warning" : "text-danger"
          }
        >
          {label}
        </span>
      </h3>
      {isUnavailable && (
        <div className="diagnostic-box" role="alert">
          <p>{statusMessage}</p>
          {hints.length > 0 && (
            <ul>
              {hints.map((code, index) => (
                <li key={`${code}-${index}`}>{hintText(code)}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      <button
        className="btn-reload"
        style={{ marginTop: "10px", width: "100%" }}
        disabled={!isRunning && !isInactive}
        title={!isRunning && !isInactive ? t("ufw.resolve_first") : undefined}
        onClick={() =>
          apiAction("/api/toggle", "POST", {
            action: isRunning ? "disable" : "enable",
          })
        }
      >
        {isRunning ? t("ufw.disable") : t("ufw.enable")}
      </button>
    </section>
  );
}

export default UfwStatus;
