import { act } from "react";
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
});
