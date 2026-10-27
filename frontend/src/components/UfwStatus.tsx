interface UfwStatusProps {
  status: any;
  diagnostics: any;
  apiAction: (url: string, method: string, body?: any) => void;
}

function UfwStatus({ status, diagnostics, apiAction }: UfwStatusProps) {
  const isRunning = status?.status === "running";
  const isInactive = status?.status === "inactive";
  const isUnavailable = Boolean(status) && !isRunning && !isInactive;
  const label = isRunning ? "running" : isInactive ? "inactive" : status ? "unavailable" : "loading";

  return (
    <section className="glass-card">
      <h3>
        UFW Status:{" "}
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
          <p>{status?.__error || "The backend could not read the host firewall."}</p>
          {Array.isArray(diagnostics?.hints) && diagnostics.hints.length > 0 && (
            <ul>
              {diagnostics.hints.map((hint: string) => (
                <li key={hint}>{hint}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      <button
        className="btn-reload"
        style={{ marginTop: "10px", width: "100%" }}
        disabled={!isRunning && !isInactive}
        title={!isRunning && !isInactive ? "Resolve the UFW connection problem first" : undefined}
        onClick={() =>
          apiAction("/api/toggle", "POST", {
            action: isRunning ? "disable" : "enable",
          })
        }
      >
        {isRunning ? "Disable UFW" : "Enable UFW"}
      </button>
    </section>
  );
}

export default UfwStatus;
