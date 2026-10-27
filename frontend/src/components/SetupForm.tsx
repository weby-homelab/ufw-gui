import { useState } from "react";
import type { FormEvent } from "react";
import LanguageSwitcher from "./LanguageSwitcher";
import { useI18n } from "../i18n";

interface SetupProps {
  onComplete: () => void;
}

function SetupForm({ onComplete }: SetupProps) {
  const { t } = useI18n();
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
      setError(t("setup.error_https"));
      return;
    }
    if (Array.from(password).length < 12 || new TextEncoder().encode(password).length > 72) {
      tokenInput.value = "";
      setError(t("setup.error_password"));
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
        setError(t("setup.error_unavailable"));
      } else if (res.status === 403) {
        setError(t("setup.error_forbidden"));
      } else {
        setError(t("setup.error_generic"));
      }
    } catch {
      setError(t("setup.error_network"));
    } finally {
      tokenInput.value = "";
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-screen">
      <form className="glass-card auth-card" onSubmit={handleSubmit}>
        <div className="auth-lang"><LanguageSwitcher /></div>
        <h2>{t("setup.title")}</h2>
        <p className="auth-hint" id="setup-help">{t("setup.hint")}</p>
        <label className="auth-field" htmlFor="setup-user">
          {t("setup.username")}
          <input id="setup-user" name="user" autoComplete="username" maxLength={64} required />
        </label>
        <label className="auth-field" htmlFor="setup-pass">
          {t("setup.password")}
          <input id="setup-pass" name="pass" type="password" autoComplete="new-password" maxLength={72} required />
        </label>
        <label className="auth-field" htmlFor="setup-token">
          {t("setup.token")}
          <input id="setup-token" name="setup_token" type="password" autoComplete="off" maxLength={256} aria-describedby="setup-help" required />
        </label>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <button className="btn-reload" type="submit" disabled={submitting}>
          {submitting ? t("setup.submitting") : t("setup.submit")}
        </button>
      </form>
    </div>
  );
}

export default SetupForm;
