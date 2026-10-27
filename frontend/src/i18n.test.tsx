import { act } from "react";
import App from "./App";
import LoginForm from "./components/LoginForm";
import UfwStatus from "./components/UfwStatus";
import { useI18n, I18nProvider, detectLanguage } from "./i18n";
import LanguageSwitcher from "./components/LanguageSwitcher";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });

function Probe() {
  const { language, t } = useI18n();
  return (
    <>
      <span data-testid="language">{language}</span>
      <h1>{t("login.title")}</h1>
      <LanguageSwitcher />
    </>
  );
}

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

describe("language preference", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    window.localStorage.clear();
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("prefers a valid saved language over the browser language", () => {
    expect(
      detectLanguage({ getItem: () => "uk" }, "zh-CN"),
    ).toBe("uk");
  });

  it.each([
    { browserLanguage: "zh-TW", expected: "zh-CN" },
    { browserLanguage: "uk-UA", expected: "uk" },
    { browserLanguage: "fr-FR", expected: "en" },
  ])("detects $expected from $browserLanguage", ({ browserLanguage, expected }) => {
    expect(detectLanguage(null, browserLanguage)).toBe(expected);
  });

  it("switches language, updates the document, and persists through reload", async () => {
    Object.defineProperty(window.navigator, "language", {
      configurable: true,
      value: "en-US",
    });
    await act(async () => root.render(<I18nProvider><Probe /></I18nProvider>));
    expect(container.querySelector("h1")?.textContent).toBe("UFW-GUI Login");

    const selector = container.querySelector("select")!;
    await act(async () => {
      selector.value = "zh-CN";
      selector.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(container.querySelector("h1")?.textContent).toBe("UFW-GUI 登录");
    expect(document.documentElement.lang).toBe("zh-CN");
    expect(window.localStorage.getItem("ufw_language")).toBe("zh-CN");

    await act(async () => root.unmount());
    root = createRoot(container);
    await act(async () => root.render(<I18nProvider><Probe /></I18nProvider>));
    expect(container.querySelector('[data-testid="language"]')?.textContent).toBe("zh-CN");
    expect(container.querySelector("h1")?.textContent).toBe("UFW-GUI 登录");
  });

  it("falls back to in-memory language when browser storage is blocked", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("storage is blocked", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("storage is blocked", "SecurityError");
    });
    Object.defineProperty(window.navigator, "language", {
      configurable: true,
      value: "en-US",
    });

    await act(async () => root.render(<I18nProvider><Probe /></I18nProvider>));
    const selector = container.querySelector("select")!;
    await act(async () => {
      selector.value = "uk";
      selector.dispatchEvent(new Event("change", { bubbles: true }));
    });

    expect(container.querySelector('[data-testid="language"]')?.textContent).toBe("uk");
    expect(container.querySelector("h1")?.textContent).toBe("Вхід до UFW-GUI");
    expect(document.documentElement.lang).toBe("uk");
  });

  it("renders the real app when authentication storage is blocked", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("storage is blocked", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("storage is blocked", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
      throw new DOMException("storage is blocked", "SecurityError");
    });
    const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
    const requests: Array<{ url: string; authorization?: string }> = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const headers = new Headers(init?.headers);
      requests.push({ url, authorization: headers.get("Authorization") ?? undefined });

      if (url === "/api/auth/setup-needed") return jsonResponse({ setup_needed: false });
      if (url === "/api/auth/login") return jsonResponse({ access_token: "in-memory-token" });
      if (url === "/api/auth/me") return jsonResponse({ username: "admin", role: "superadmin" });
      if (url === "/api/toggle") return jsonResponse({ detail: "private API detail sentinel" }, 400);
      if (url === "/api/status") return jsonResponse({ status: "running" });
      if (url === "/api/diagnostics") return jsonResponse({ hint_codes: [], hints: [] });
      if (url === "/api/rules") return jsonResponse({ rules: [] });
      if (url === "/api/fail2ban/status") return jsonResponse({ banned: [] });
      if (url === "/api/logs") return jsonResponse({ logs: [] });
      if (url === "/api/stats") return jsonResponse({ hourly: [] });
      return jsonResponse({ unresolved_marker: false });
    }));

    await act(async () => {
      root.render(
        <I18nProvider>
          <App />
        </I18nProvider>,
      );
    });

    expect(container.querySelector("h2")?.textContent).toBe("UFW-GUI Login");

    const userInput = container.querySelector<HTMLInputElement>('input[name="user"]')!;
    const passwordInput = container.querySelector<HTMLInputElement>('input[name="pass"]')!;
    userInput.value = "admin";
    passwordInput.value = "test-password";
    await act(async () => {
      container.querySelector("form")!.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(requests).toContainEqual({
      url: "/api/auth/me",
      authorization: "Bearer in-memory-token",
    });
    expect(container.textContent).toContain("admin");

    const disableButton = Array.from(container.querySelectorAll("button")).find(
      (button) => button.textContent === "Disable UFW",
    )!;
    await act(async () => {
      disableButton.click();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    expect(alert).toHaveBeenCalledWith(
      "The request contains invalid values. Check your input and try again.",
    );
    expect(alert).not.toHaveBeenCalledWith("private API detail sentinel");
    expect(requests).toContainEqual({
      url: "/api/toggle",
      authorization: "Bearer in-memory-token",
    });

    const logout = Array.from(container.querySelectorAll("button")).find(
      (button) => button.textContent === "Logout",
    )!;
    await act(async () => logout.click());
    expect(container.querySelector("h2")?.textContent).toBe("UFW-GUI Login");
  });

  it("shows translated diagnostics and never renders raw backend details", async () => {
    window.localStorage.setItem("ufw_language", "zh-CN");
    await act(async () => {
      root.render(
        <I18nProvider>
          <UfwStatus
            status={{
              status: "unknown",
              error_code: "ufw_status_unrecognized",
              error: "private backend detail sentinel",
            }}
            diagnostics={{
              hint_codes: [
                "ufw_config_not_mountpoint",
                "net_admin_missing",
                "fail2ban_socket_missing",
              ],
            }}
            apiAction={vi.fn()}
          />
        </I18nProvider>,
      );
    });

    expect(container.textContent).toContain("无法识别 UFW 状态输出。");
    expect(container.textContent).toContain("容器中存在 /etc/ufw，但它不是挂载点");
    expect(container.textContent).toContain("容器进程缺少 NET_ADMIN。");
    expect(container.textContent).toContain("Fail2Ban 套接字未挂载");
    expect(container.textContent).not.toContain("private backend detail sentinel");
    expect(container.querySelector("button")?.disabled).toBe(true);
  });

  it("shows a localized login message when the request fails", async () => {
    window.localStorage.setItem("ufw_language", "uk");
    const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
    const onLogin = vi.fn();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("private network detail")));

    await act(async () => {
      root.render(
        <I18nProvider>
          <LoginForm onLogin={onLogin} />
        </I18nProvider>,
      );
    });
    await act(async () => {
      container.querySelector("form")!.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });

    expect(alert).toHaveBeenCalledWith(
      "Не вдалося виконати вхід. Перевірте з'єднання та спробуйте ще раз.",
    );
    expect(onLogin).not.toHaveBeenCalled();
  });

  it("rejects malformed successful login responses without exposing details", async () => {
    const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
    const onLogin = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => {
          throw new Error("private response detail");
        },
      }),
    );

    await act(async () => {
      root.render(
        <I18nProvider>
          <LoginForm onLogin={onLogin} />
        </I18nProvider>,
      );
    });
    await act(async () => {
      container.querySelector("form")!.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });

    expect(alert).toHaveBeenCalledWith(
      "Unable to complete sign-in. Check the connection and try again.",
    );
    expect(alert).not.toHaveBeenCalledWith("private response detail");
    expect(onLogin).not.toHaveBeenCalled();
  });
});
