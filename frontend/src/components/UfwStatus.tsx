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
  const legacyHints: string[] = Array.isArray(diagnostics?.hints)
    ? diagnostics.hints
    : [];

  const hintText = (code: string, index: number) => {
    const key = `diag.${code}` as MessageKey;
    return key in en ? t(key) : legacyHints[index] || code;
  };

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
          <p>{status?.__error || t("ufw.unavailable_default")}</p>
          {hints.length > 0 && (
            <ul>
              {hints.map((code, index) => (
                <li key={code}>{hintText(code, index)}</li>
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
