import { useState } from "react";
import type { FormEvent } from "react";

interface SetupProps {
  onComplete: () => void;
}

function SetupForm({ onComplete }: SetupProps) {
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const formData = new FormData(form);
    const username = formData.get("user") as string;
    const password = formData.get("pass") as string;
    const setupToken = formData.get("setup_token") as string;
    const tokenInput = form.elements.namedItem("setup_token") as HTMLInputElement;

    setError("");
    if (window.location.protocol !== "https:") {
      tokenInput.value = "";
      setError("Setup requires HTTPS. Open the dashboard through your trusted HTTPS proxy.");
      return;
    }
    if (Array.from(password).length < 12 || new TextEncoder().encode(password).length > 72) {
      tokenInput.value = "";
      setError("Password must have at least 12 characters and at most 72 UTF-8 bytes.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch("/api/auth/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, setup_token: setupToken }),
      });

      if (res.ok) {
        form.reset();
        onComplete();
      } else if (res.status === 503) {
        setError("Setup is unavailable. Check the server configuration and storage.");
      } else if (res.status === 403) {
        setError("Setup authorization failed. Check the setup token.");
      } else {
        setError("Could not create the administrator. Check the username and password.");
      }
    } catch {
      setError("Could not contact the server. Check your connection and try again.");
    } finally {
      tokenInput.value = "";
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-screen">
      <form className="glass-card auth-card" onSubmit={handleSubmit}>
        <h2>UFW-GUI Setup</h2>
        <p className="auth-hint" id="setup-help">
          Use the separate setup token configured on the server over a trusted HTTPS connection.
        </p>
        <label className="auth-field" htmlFor="setup-user">
          Username
          <input id="setup-user" name="user" autoComplete="username" maxLength={64} required />
        </label>
        <label className="auth-field" htmlFor="setup-pass">
          Password (at least 12 characters; at most 72 UTF-8 bytes)
          <input id="setup-pass" name="pass" type="password" autoComplete="new-password" maxLength={72} required />
        </label>
        <label className="auth-field" htmlFor="setup-token">
          Setup token
          <input id="setup-token" name="setup_token" type="password" autoComplete="off" maxLength={256} aria-describedby="setup-help" required />
        </label>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <button className="btn-reload" type="submit" disabled={submitting}>
          {submitting ? "Creating administrator…" : "Create Admin"}
        </button>
      </form>
    </div>
  );
}

export default SetupForm;
