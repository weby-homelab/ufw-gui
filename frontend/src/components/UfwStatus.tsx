interface UfwStatusProps {
  status: any;
  apiAction: (url: string, method: string, body?: any) => void;
}

function UfwStatus({ status, apiAction }: UfwStatusProps) {
  const isRunning = status?.status === "running";
  return (
    <section className="glass-card">
      <h3>
        UFW Status:{" "}
        <span className={isRunning ? "text-success" : "text-danger"}>
          {status?.status}
        </span>
      </h3>
      <button
        className="btn-reload"
        style={{ marginTop: "10px", width: "100%" }}
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
