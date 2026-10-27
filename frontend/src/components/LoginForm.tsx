import type { FormEvent } from "react"
import LanguageSwitcher from "./LanguageSwitcher"
import { useI18n } from "../i18n"

interface LoginProps {
  onLogin: (token: string) => void;
}

function LoginForm({ onLogin }: LoginProps) {
  const { t } = useI18n()

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const username = formData.get("user") as string;
    const password = formData.get("pass") as string;

    const fd = new FormData();
    fd.append("username", username);
    fd.append("password", password);

    const res = await fetch("/api/auth/login", { method: "POST", body: fd });
    if (res.ok) {
      const data = await res.json();
      onLogin(data.access_token);
    } else {
      alert(t("login.failed"));
    }
  };

  return (
    <div className="auth-screen">
      <form className="glass-card auth-card" onSubmit={handleSubmit}>
        <div className="auth-lang"><LanguageSwitcher /></div>
        <h2>{t("login.title")}</h2>
        <input name="user" placeholder={t("login.username")} autoComplete="username" />
        <input name="pass" type="password" placeholder={t("login.password")} autoComplete="current-password" />
        <button className="btn-reload">{t("login.submit")}</button>
      </form>
    </div>
  );
}

export default LoginForm;
