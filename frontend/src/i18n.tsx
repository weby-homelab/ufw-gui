import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export const en = {
  "language.label": "Language",
  "nav.dashboard": "Dashboard",
  "nav.snapshots": "Snapshots",
  "nav.admin": "Admin",
  "nav.settings": "Settings",
  "action.logout": "Logout",
  "app.recovery_notice_title": "Automatic test and rollback are unavailable.",
  "app.recovery_notice_body":
    "Firewall changes apply immediately; verify each change yourself before applying it. No automatic rollback is provided.",
  "app.manual_recovery_title": "Manual recovery required.",
  "app.manual_recovery_body":
    "An unresolved legacy recovery marker is preserved. Firewall mutations are blocked until an operator inspects and resolves it.",
  "app.footer": "© 2026 Weby Homelab • UFW-GUI (Debian/Ubuntu)",
  "alert.action_failed": "Action failed (HTTP {status})",
  "alert.backend_unreachable": "Action failed: the backend could not be reached.",
  "alert.test_active":
    "Cannot modify firewall rules while a test is active. Please confirm or wait for rollback.",
  "role.superadmin": "superadmin",
  "role.admin": "admin",
  "login.title": "UFW-GUI Login",
  "login.username": "Username",
  "login.password": "Password",
  "login.submit": "Login",
  "login.failed": "Login failed",
  "setup.title": "UFW-GUI Setup",
  "setup.hint":
    "Use the separate setup token configured on the server over a trusted HTTPS connection.",
  "setup.username": "Username",
  "setup.password": "Password (at least 12 characters; at most 72 UTF-8 bytes)",
  "setup.token": "Setup token",
  "setup.submit": "Create Admin",
  "setup.submitting": "Creating administrator…",
  "setup.error_https":
    "Setup requires HTTPS. Open the dashboard through your trusted HTTPS proxy.",
  "setup.error_password":
    "Password must have at least 12 characters and at most 72 UTF-8 bytes.",
  "setup.error_unavailable":
    "Setup is unavailable. Check the server configuration and storage.",
  "setup.error_forbidden": "Setup authorization failed. Check the setup token.",
  "setup.error_generic":
    "Could not create the administrator. Check the username and password.",
  "setup.error_network":
    "Could not contact the server. Check your connection and try again.",
  "dashboard.rules_tab": "Global Rules",
  "dashboard.drops_tab": "Live Drops (Logs)",
  "dashboard.fail2ban_tab": "Fail2Ban",
  "ufw.title": "UFW Status",
  "ufw.running": "running",
  "ufw.inactive": "inactive",
  "ufw.unavailable": "unavailable",
  "ufw.loading": "loading",
  "ufw.enable": "Enable UFW",
  "ufw.disable": "Disable UFW",
  "ufw.resolve_first": "Resolve the UFW connection problem first",
  "ufw.unavailable_default": "The backend could not read the host firewall.",
  "diag.ufw_binary_missing":
    "The ufw binary is missing from the container image; use an official image built after 1.6.3 or rebuild from this repository.",
  "diag.ufw_config_missing":
    "The host /etc/ufw directory is not mounted. Add the volume '/etc/ufw:/etc/ufw' and restart the container.",
  "diag.ufw_config_not_mounted":
    "/etc/ufw exists in the container but is not a host bind mount. Rules shown here may not match the host firewall.",
  "diag.fail2ban_socket_missing":
    "The Fail2Ban socket is not mounted; Fail2Ban status will be unavailable. Mount '/var/run/fail2ban/fail2ban.sock' to enable it.",
  "quick.title": "Quick Actions",
  "quick.port_proto": "Port & Protocol",
  "quick.any": "Any",
  "quick.target": "Target IP / Subnet (Optional)",
  "quick.target_placeholder": "192.168.1.0/24 or Any",
  "quick.allow": "Allow",
  "quick.deny": "Deny",
  "quick.quick_ban": "Quick Ban IP Address",
  "quick.ban": "Ban IP",
  "rules.title": "Active Firewall Rules",
  "rules.id": "ID",
  "rules.to": "To (Port/Target)",
  "rules.action": "Action",
  "rules.from": "From (IP/Source)",
  "rules.manage": "Manage",
  "rules.delete": "Delete",
  "rules.empty": "No rules configured",
  "drops.title": "Live UFW Blocks",
  "drops.time": "Time",
  "drops.source": "Source IP",
  "drops.proto": "Proto",
  "drops.port": "Port",
  "drops.action": "Action",
  "drops.ban": "Ban IP",
  "drops.empty": "No dropped packets found in UFW logs. Ensure UFW logging is ON.",
  "stats.title": "Attack Statistics (Last 24h)",
  "f2b.title": "Fail2Ban Active Bans",
  "f2b.empty": "No active bans from Fail2Ban",
  "admin.audit_title": "Audit Logs",
  "admin.time": "Time",
  "admin.user": "User",
  "admin.action": "Action",
  "admin.details": "Details",
  "admin.no_logs": "No logs",
  "admin.users_title": "User Management",
  "admin.user_placeholder": "User",
  "admin.pass_placeholder": "Pass",
  "admin.add": "+ Add",
  "settings.title": "Settings",
  "settings.token_label": "Telegram Bot Token",
  "settings.token_configured":
    "A token is configured. Leave this blank to keep it unchanged, or enter a replacement. The saved token is never returned by the API.",
  "settings.token_missing":
    "No token is configured. Enter one to enable Telegram alerts.",
  "settings.token_placeholder_keep": "Leave blank to keep current token",
  "settings.token_placeholder_new": "Telegram bot token",
  "settings.chat_id": "Telegram Chat ID",
  "settings.chat_placeholder": "Chat ID",
  "settings.save": "Save Settings",
  "snapshots.title": "Snapshots (Manual Review Only)",
  "snapshots.notice":
    "Snapshot creation and restore are disabled. Existing snapshots are retained for manual inspection.",
  "snapshots.empty": "No snapshots are available for manual review.",
} as const;

export type MessageKey = keyof typeof en;
type Dictionary = Record<MessageKey, string>;

export const uk: Dictionary = {
  "language.label": "Мова",
  "nav.dashboard": "Панель",
  "nav.snapshots": "Знімки",
  "nav.admin": "Адмін",
  "nav.settings": "Налаштування",
  "action.logout": "Вийти",
  "app.recovery_notice_title": "Автоматичне тестування та відкат недоступні.",
  "app.recovery_notice_body":
    "Зміни фаєрвола застосовуються негайно; перевіряйте кожну зміну самостійно перед застосуванням. Автоматичний відкат не передбачено.",
  "app.manual_recovery_title": "Потрібне ручне відновлення.",
  "app.manual_recovery_body":
    "Виявлено невирішений маркер відновлення; його збережено. Зміни фаєрвола заблоковано, доки оператор не перевірить і не усуне його.",
  "app.footer": "© 2026 Weby Homelab • UFW-GUI (Debian/Ubuntu)",
  "alert.action_failed": "Дію не виконано (HTTP {status})",
  "alert.backend_unreachable": "Дію не виконано: бекенд недоступний.",
  "alert.test_active":
    "Не можна змінювати правила, поки триває тест. Підтвердьте зміни або дочекайтеся відкату.",
  "role.superadmin": "суперадмін",
  "role.admin": "адмін",
  "login.title": "Вхід до UFW-GUI",
  "login.username": "Ім'я користувача",
  "login.password": "Пароль",
  "login.submit": "Увійти",
  "login.failed": "Не вдалося увійти",
  "setup.title": "Налаштування UFW-GUI",
  "setup.hint":
    "Використайте окремий токен налаштування, заданий на сервері, через довірене HTTPS-з'єднання.",
  "setup.username": "Ім'я користувача",
  "setup.password": "Пароль (щонайменше 12 символів; не більше 72 байтів UTF-8)",
  "setup.token": "Токен налаштування",
  "setup.submit": "Створити адміністратора",
  "setup.submitting": "Створення адміністратора…",
  "setup.error_https":
    "Для налаштування потрібен HTTPS. Відкрийте панель через довірений HTTPS-проксі.",
  "setup.error_password":
    "Пароль має містити щонайменше 12 символів і не більше 72 байтів UTF-8.",
  "setup.error_unavailable":
    "Налаштування недоступне. Перевірте конфігурацію сервера та сховище.",
  "setup.error_forbidden":
    "Помилка авторизації налаштування. Перевірте токен налаштування.",
  "setup.error_generic":
    "Не вдалося створити адміністратора. Перевірте ім'я користувача та пароль.",
  "setup.error_network":
    "Не вдалося зв'язатися із сервером. Перевірте з'єднання та спробуйте ще раз.",
  "dashboard.rules_tab": "Глобальні правила",
  "dashboard.drops_tab": "Події блокування (логи)",
  "dashboard.fail2ban_tab": "Fail2Ban",
  "ufw.title": "Статус UFW",
  "ufw.running": "активний",
  "ufw.inactive": "неактивний",
  "ufw.unavailable": "недоступний",
  "ufw.loading": "завантаження",
  "ufw.enable": "Увімкнути UFW",
  "ufw.disable": "Вимкнути UFW",
  "ufw.resolve_first": "Спочатку усуньте проблему з'єднання з UFW",
  "ufw.unavailable_default": "Бекенд не зміг прочитати хост-фаєрвол.",
  "diag.ufw_binary_missing":
    "Утиліта ufw відсутня в образі контейнера; використайте офіційний образ після 1.6.3 або зберіть його з цього репозиторію.",
  "diag.ufw_config_missing":
    "Каталог /etc/ufw хоста не змонтовано. Додайте том '/etc/ufw:/etc/ufw' і перезапустіть контейнер.",
  "diag.ufw_config_not_mounted":
    "/etc/ufw існує в контейнері, але не є bind-монтуванням хоста. Показані правила можуть не відповідати хост-фаєрволу.",
  "diag.fail2ban_socket_missing":
    "Сокет Fail2Ban не змонтовано; статус Fail2Ban буде недоступний. Змонтуйте '/var/run/fail2ban/fail2ban.sock', щоб увімкнути його.",
  "quick.title": "Швидкі дії",
  "quick.port_proto": "Порт і протокол",
  "quick.any": "Будь-який",
  "quick.target": "Цільова IP / підмережа (необов'язково)",
  "quick.target_placeholder": "192.168.1.0/24 або будь-який",
  "quick.allow": "Дозволити",
  "quick.deny": "Заборонити",
  "quick.quick_ban": "Швидкий бан IP-адреси",
  "quick.ban": "Забанити IP",
  "rules.title": "Активні правила фаєрвола",
  "rules.id": "ID",
  "rules.to": "Куди (порт/ціль)",
  "rules.action": "Дія",
  "rules.from": "Звідки (IP/джерело)",
  "rules.manage": "Керування",
  "rules.delete": "Видалити",
  "rules.empty": "Правила не налаштовані",
  "drops.title": "Поточні блокування UFW",
  "drops.time": "Час",
  "drops.source": "IP-джерело",
  "drops.proto": "Протокол",
  "drops.port": "Порт",
  "drops.action": "Дія",
  "drops.ban": "Забанити IP",
  "drops.empty":
    "У логах UFW не знайдено заблокованих пакетів. Переконайтеся, що логування UFW увімкнено.",
  "stats.title": "Статистика атак (останні 24 год)",
  "f2b.title": "Активні бани Fail2Ban",
  "f2b.empty": "Немає активних банів Fail2Ban",
  "admin.audit_title": "Журнал аудиту",
  "admin.time": "Час",
  "admin.user": "Користувач",
  "admin.action": "Дія",
  "admin.details": "Деталі",
  "admin.no_logs": "Немає записів",
  "admin.users_title": "Керування користувачами",
  "admin.user_placeholder": "Користувач",
  "admin.pass_placeholder": "Пароль",
  "admin.add": "+ Додати",
  "settings.title": "Налаштування",
  "settings.token_label": "Токен Telegram-бота",
  "settings.token_configured":
    "Токен налаштовано. Залиште поле порожнім, щоб не змінювати його, або введіть новий. Збережений токен ніколи не повертається API.",
  "settings.token_missing":
    "Токен не налаштовано. Введіть його, щоб увімкнути сповіщення Telegram.",
  "settings.token_placeholder_keep": "Залиште порожнім, щоб зберегти поточний токен",
  "settings.token_placeholder_new": "Токен Telegram-бота",
  "settings.chat_id": "ID чату Telegram",
  "settings.chat_placeholder": "ID чату",
  "settings.save": "Зберегти налаштування",
  "snapshots.title": "Знімки (лише ручний перегляд)",
  "snapshots.notice":
    "Створення та відновлення знімків вимкнено. Наявні знімки збережено для ручної перевірки.",
  "snapshots.empty": "Немає знімків для ручного перегляду.",
};

export const zhCN: Dictionary = {
  "language.label": "语言",
  "nav.dashboard": "仪表盘",
  "nav.snapshots": "快照",
  "nav.admin": "管理",
  "nav.settings": "设置",
  "action.logout": "退出登录",
  "app.recovery_notice_title": "自动测试与回滚不可用。",
  "app.recovery_notice_body":
    "防火墙更改会立即生效；请在应用前自行验证每一项更改。系统不提供自动回滚。",
  "app.manual_recovery_title": "需要手动恢复。",
  "app.manual_recovery_body":
    "检测到未解决的旧版恢复标记，已保留该标记。在操作员检查并解决之前，防火墙更改将被阻止。",
  "app.footer": "© 2026 Weby Homelab • UFW-GUI（Debian/Ubuntu）",
  "alert.action_failed": "操作失败（HTTP {status}）",
  "alert.backend_unreachable": "操作失败：无法连接后端。",
  "alert.test_active": "测试进行中，无法修改防火墙规则。请确认更改或等待回滚。",
  "role.superadmin": "超级管理员",
  "role.admin": "管理员",
  "login.title": "UFW-GUI 登录",
  "login.username": "用户名",
  "login.password": "密码",
  "login.submit": "登录",
  "login.failed": "登录失败",
  "setup.title": "UFW-GUI 初始化",
  "setup.hint": "请通过受信任的 HTTPS 连接使用服务器上配置的独立初始化令牌。",
  "setup.username": "用户名",
  "setup.password": "密码（至少 12 个字符；最多 72 个 UTF-8 字节）",
  "setup.token": "初始化令牌",
  "setup.submit": "创建管理员",
  "setup.submitting": "正在创建管理员…",
  "setup.error_https": "初始化需要 HTTPS。请通过受信任的 HTTPS 代理打开仪表盘。",
  "setup.error_password": "密码至少 12 个字符，且最多 72 个 UTF-8 字节。",
  "setup.error_unavailable": "初始化不可用。请检查服务器配置和存储。",
  "setup.error_forbidden": "初始化授权失败。请检查初始化令牌。",
  "setup.error_generic": "无法创建管理员。请检查用户名和密码。",
  "setup.error_network": "无法连接服务器。请检查网络连接后重试。",
  "dashboard.rules_tab": "全局规则",
  "dashboard.drops_tab": "实时拦截（日志）",
  "dashboard.fail2ban_tab": "Fail2Ban",
  "ufw.title": "UFW 状态",
  "ufw.running": "运行中",
  "ufw.inactive": "未启用",
  "ufw.unavailable": "不可用",
  "ufw.loading": "加载中",
  "ufw.enable": "启用 UFW",
  "ufw.disable": "禁用 UFW",
  "ufw.resolve_first": "请先解决 UFW 连接问题",
  "ufw.unavailable_default": "后端无法读取主机防火墙。",
  "diag.ufw_binary_missing":
    "容器镜像中缺少 ufw 可执行文件；请使用 1.6.3 之后的官方镜像，或从本仓库重新构建。",
  "diag.ufw_config_missing":
    "主机的 /etc/ufw 目录未挂载。请添加卷 '/etc/ufw:/etc/ufw' 并重启容器。",
  "diag.ufw_config_not_mounted":
    "容器中存在 /etc/ufw，但它不是主机绑定挂载。此处显示的规则可能与主机防火墙不一致。",
  "diag.fail2ban_socket_missing":
    "Fail2Ban 套接字未挂载，Fail2Ban 状态将不可用。请挂载 '/var/run/fail2ban/fail2ban.sock' 以启用。",
  "quick.title": "快捷操作",
  "quick.port_proto": "端口与协议",
  "quick.any": "任意",
  "quick.target": "目标 IP / 子网（可选）",
  "quick.target_placeholder": "192.168.1.0/24 或任意",
  "quick.allow": "允许",
  "quick.deny": "拒绝",
  "quick.quick_ban": "快速封禁 IP 地址",
  "quick.ban": "封禁 IP",
  "rules.title": "活动防火墙规则",
  "rules.id": "ID",
  "rules.to": "目标（端口/目标）",
  "rules.action": "操作",
  "rules.from": "来源（IP/源）",
  "rules.manage": "管理",
  "rules.delete": "删除",
  "rules.empty": "尚未配置规则",
  "drops.title": "UFW 实时拦截",
  "drops.time": "时间",
  "drops.source": "来源 IP",
  "drops.proto": "协议",
  "drops.port": "端口",
  "drops.action": "操作",
  "drops.ban": "封禁 IP",
  "drops.empty": "UFW 日志中未发现被丢弃的数据包。请确保已开启 UFW 日志。",
  "stats.title": "攻击统计（最近 24 小时）",
  "f2b.title": "Fail2Ban 活动封禁",
  "f2b.empty": "暂无 Fail2Ban 封禁",
  "admin.audit_title": "审计日志",
  "admin.time": "时间",
  "admin.user": "用户",
  "admin.action": "操作",
  "admin.details": "详情",
  "admin.no_logs": "暂无日志",
  "admin.users_title": "用户管理",
  "admin.user_placeholder": "用户",
  "admin.pass_placeholder": "密码",
  "admin.add": "+ 添加",
  "settings.title": "设置",
  "settings.token_label": "Telegram 机器人令牌",
  "settings.token_configured":
    "已配置令牌。留空可保持不变，或输入新令牌。API 永远不会返回已保存的令牌。",
  "settings.token_missing": "尚未配置令牌。输入令牌以启用 Telegram 通知。",
  "settings.token_placeholder_keep": "留空以保留当前令牌",
  "settings.token_placeholder_new": "Telegram 机器人令牌",
  "settings.chat_id": "Telegram 聊天 ID",
  "settings.chat_placeholder": "聊天 ID",
  "settings.save": "保存设置",
  "snapshots.title": "快照（仅供手动查看）",
  "snapshots.notice": "快照创建与恢复已禁用。现有快照会保留以供手动检查。",
  "snapshots.empty": "没有可供手动查看的快照。",
};

export const LANGUAGES = [
  { id: "en", label: "English" },
  { id: "uk", label: "Українська" },
  { id: "zh-CN", label: "简体中文" },
] as const;

export type Language = (typeof LANGUAGES)[number]["id"];

const dictionaries: Record<Language, Dictionary> = {
  en,
  uk,
  "zh-CN": zhCN,
};

const STORAGE_KEY = "ufw_language";

function detectLanguage(): Language {
  if (typeof window === "undefined") return "en";
  const saved = window.localStorage.getItem(STORAGE_KEY);
  if (saved && LANGUAGES.some((language) => language.id === saved)) {
    return saved as Language;
  }
  const browserLanguage = window.navigator.language.toLowerCase();
  if (browserLanguage.startsWith("zh")) return "zh-CN";
  if (browserLanguage.startsWith("uk")) return "uk";
  return "en";
}

function interpolate(
  template: string,
  values?: Record<string, string | number>,
): string {
  if (!values) return template;
  return template.replace(/\{(\w+)\}/g, (match, name) => {
    return Object.prototype.hasOwnProperty.call(values, name)
      ? String(values[name])
      : match;
  });
}

interface I18nValue {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: MessageKey, values?: Record<string, string | number>) => string;
  roleLabel: (role: string) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(detectLanguage);

  useEffect(() => {
    document.documentElement.lang = language;
    window.localStorage.setItem(STORAGE_KEY, language);
  }, [language]);

  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next);
  }, []);

  const t = useCallback(
    (key: MessageKey, values?: Record<string, string | number>) =>
      interpolate(dictionaries[language][key] ?? en[key], values),
    [language],
  );

  const roleLabel = useCallback(
    (role: string) => {
      const key = `role.${role}` as MessageKey;
      return key in en ? t(key) : role;
    },
    [t],
  );

  const value = useMemo(
    () => ({ language, setLanguage, t, roleLabel }),
    [language, roleLabel, setLanguage, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used inside I18nProvider");
  }
  return context;
}
