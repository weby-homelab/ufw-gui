import type { FormEvent } from "react";

interface SetupProps {
  onComplete: () => void;
}

function SetupForm({ onComplete }: SetupProps) {
  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const username = formData.get("user") as string;
    const password = formData.get("pass") as string;

    const res = await fetch("/api/auth/setup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (res.ok) {
      alert("Admin created! Log in now.");
      onComplete();
    }
  };

  return (
    <div className="auth-screen">
      <form className="glass-card auth-card" onSubmit={handleSubmit}>
        <h2>UFW-GUI Setup</h2>
        <input name="user" placeholder="Username" required />
        <input name="pass" type="password" placeholder="Password" required />
        <button className="btn-reload" type="submit">Create Admin</button>
      </form>
    </div>
  );
}

export default SetupForm;
