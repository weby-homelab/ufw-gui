interface LoginProps {
  onLogin: (token: string) => void;
}

function LoginForm({ onLogin }: LoginProps) {
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
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
      alert("Login failed");
    }
  };

  return (
    <div className="auth-screen">
      <form className="glass-card auth-card" onSubmit={handleSubmit}>
        <h2>UFW-GUI Login</h2>
        <input name="user" placeholder="Username" />
        <input name="pass" type="password" placeholder="Password" />
        <button className="btn-reload">Login</button>
      </form>
    </div>
  );
}

export default LoginForm;
