using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace AIProject1
{
    internal static class Theme
    {
        public static readonly Color Sidebar = Color.FromArgb(17, 24, 39);
        public static readonly Color SidebarCard = Color.FromArgb(31, 41, 55);
        public static readonly Color SidebarInput = Color.FromArgb(55, 65, 81);
        public static readonly Color Main = Color.FromArgb(245, 247, 251);
        public static readonly Color Surface = Color.White;
        public static readonly Color Text = Color.FromArgb(17, 24, 39);
        public static readonly Color Muted = Color.FromArgb(107, 114, 128);
        public static readonly Color SidebarMuted = Color.FromArgb(209, 213, 219);
        public static readonly Color Accent = Color.FromArgb(59, 130, 246);
        public static readonly Color AccentDark = Color.FromArgb(37, 99, 235);
        public static readonly Color UserBubble = Color.FromArgb(149, 236, 105);
        public static readonly Color AssistantBubble = Color.White;
        public static readonly Color SystemBubble = Color.FromArgb(229, 234, 242);
        public static readonly Color Line = Color.FromArgb(224, 229, 237);

        public static readonly Font UiFont = new Font("Microsoft YaHei UI", 9F, FontStyle.Regular);
        public static readonly Font UiFontBold = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold);
        public static readonly Font TitleFont = new Font("Microsoft YaHei UI", 15F, FontStyle.Bold);
        public static readonly Font MessageFont = new Font("Microsoft YaHei UI", 10F, FontStyle.Regular);
    }

    public sealed class ChatForm : Form
    {
        private readonly string configDir;
        private readonly string configPath;
        private readonly JavaScriptSerializer json = new JavaScriptSerializer();
        private string currentLanguage = "zh";
        private bool loadingSettings;

        private TextBox serverBox;
        private TextBox tokenBox;
        private TextBox clientBox;
        private ComboBox uiLanguageBox;
        private CheckBox selfSignedBox;
        private CheckBox autoStartHubBox;
        private CheckBox liveSearchBox;
        private CheckBox autoLookupBox;
        private ComboBox searchEngineBox;
        private TextBox customSearchBox;
        private Label statusLabel;
        private Label hubLabel;
        private Label memoryLabel;
        private Label knowledgeLabel;
        private Label searchLabel;
        private FlowLayoutPanel messageList;
        private TextBox inputBox;
        private Button sendButton;
        private ColumnStyle settingsColumn;
        private Panel sidebarPanel;
        private Button hubControlButton;
        private Process localHubProcess;
        private readonly object localHubLock = new object();
        private bool autoConnectStarted;
        private bool settingsVisible;

        public ChatForm()
        {
            configDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "AI Project 1"
            );
            configPath = Path.Combine(configDir, "desktop_client_settings.json");

            Text = "AI Project 1";
            MinimumSize = new Size(960, 640);
            Size = new Size(1160, 780);
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Theme.Main;
            Font = Theme.UiFont;
            Icon = LoadAppIcon();
            DoubleBuffered = true;
            currentLanguage = LoadLanguagePreference();

            BuildUi();
            LoadSettings();
            AddMessage(T("systemName"), T("welcome"), false, true);
            Shown += AutoConnectShown;
        }

        private void AutoConnectShown(object sender, EventArgs e)
        {
            if (autoConnectStarted)
            {
                return;
            }
            autoConnectStarted = true;
            if (autoStartHubBox.Checked && IsLocalServer())
            {
                ConnectClicked(this, EventArgs.Empty);
            }
        }

        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            try
            {
                StopLocalHub();
            }
            catch
            {
            }
            base.OnFormClosed(e);
        }

        private Icon LoadAppIcon()
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            string iconPath = Path.Combine(baseDir, "assets", "app_icon.ico");
            if (!File.Exists(iconPath))
            {
                iconPath = Path.Combine(baseDir, "app_icon.ico");
            }
            if (File.Exists(iconPath))
            {
                return new Icon(iconPath);
            }
            return Icon.ExtractAssociatedIcon(Application.ExecutablePath);
        }

        private string LoadLanguagePreference()
        {
            if (!File.Exists(configPath))
            {
                return "zh";
            }
            try
            {
                var data = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(configPath, Encoding.UTF8));
                return NormalizeLanguage(GetString(data, "ui_language", "zh"));
            }
            catch
            {
                return "zh";
            }
        }

        private void BuildUi()
        {
            var root = new TableLayoutPanel();
            root.Dock = DockStyle.Fill;
            root.ColumnCount = 2;
            root.RowCount = 1;
            settingsColumn = new ColumnStyle(SizeType.Absolute, 0);
            root.ColumnStyles.Add(settingsColumn);
            root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            Controls.Add(root);

            sidebarPanel = new Panel();
            sidebarPanel.Dock = DockStyle.Fill;
            sidebarPanel.BackColor = Theme.Sidebar;
            sidebarPanel.Padding = new Padding(18);
            sidebarPanel.Visible = false;
            root.Controls.Add(sidebarPanel, 0, 0);

            var sideFlow = new FlowLayoutPanel();
            sideFlow.Dock = DockStyle.Fill;
            sideFlow.FlowDirection = FlowDirection.TopDown;
            sideFlow.WrapContents = false;
            sideFlow.AutoScroll = true;
            sideFlow.BackColor = Theme.Sidebar;
            sidebarPanel.Controls.Add(sideFlow);

            sideFlow.Controls.Add(BuildBrand());

            serverBox = new TextBox();
            tokenBox = new TextBox();
            tokenBox.UseSystemPasswordChar = true;
            clientBox = new TextBox();
            uiLanguageBox = new ComboBox();
            uiLanguageBox.DropDownStyle = ComboBoxStyle.DropDownList;
            uiLanguageBox.Items.AddRange(new object[] { "中文", "日本語", "English" });
            uiLanguageBox.SelectedIndexChanged += LanguageChanged;
            AddCard(sideFlow, T("languageTitle"), new Control[]
            {
                Field(T("uiLanguage"), uiLanguageBox)
            });

            selfSignedBox = Check(T("selfSigned"));
            AddCard(sideFlow, T("connectionTitle"), new Control[]
            {
                Field(T("server"), serverBox),
                Field(T("token"), tokenBox),
                Field(T("client"), clientBox),
                autoStartHubBox = Check(T("autoStartHub")),
                selfSignedBox,
                SidebarButton(T("startLocalHub"), StartLocalHubClicked, false),
                SidebarButton(T("stopLocalHub"), StopLocalHubClicked, false),
                SidebarButton(T("connect"), ConnectClicked, true),
                SidebarButton(T("save"), SaveClicked, false)
            });

            liveSearchBox = Check(T("liveSearch"));
            autoLookupBox = Check(T("autoLookup"));
            searchEngineBox = new ComboBox();
            searchEngineBox.DropDownStyle = ComboBoxStyle.DropDownList;
            searchEngineBox.Items.AddRange(new object[] { "Google", "Baidu", T("customEngine") });
            searchEngineBox.SelectedIndexChanged += delegate { UpdateCustomSearchState(); };
            customSearchBox = new TextBox();
            AddCard(sideFlow, T("searchTitle"), new Control[]
            {
                liveSearchBox,
                autoLookupBox,
                Field(T("searchEngine"), searchEngineBox),
                Field(T("customSearch"), customSearchBox)
            });

            statusLabel = SideStatus(T("statusNotConnected"));
            hubLabel = SideStatus(T("hubEmpty"));
            memoryLabel = SideStatus(T("memoryEmpty"));
            knowledgeLabel = SideStatus(T("knowledgeEmpty"));
            searchLabel = SideStatus(T("searchEmpty"));
            AddCard(sideFlow, T("sessionTitle"), new Control[]
            {
                SidebarButton(T("hideSettings"), ToggleSettingsClicked, false),
                SidebarButton(T("clear"), ClearClicked, false),
                statusLabel,
                hubLabel,
                memoryLabel,
                knowledgeLabel,
                searchLabel
            });

            var main = new TableLayoutPanel();
            main.Dock = DockStyle.Fill;
            main.RowCount = 3;
            main.ColumnCount = 1;
            main.RowStyles.Add(new RowStyle(SizeType.Absolute, 76));
            main.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            main.RowStyles.Add(new RowStyle(SizeType.Absolute, 82));
            main.BackColor = Theme.Main;
            root.Controls.Add(main, 1, 0);

            main.Controls.Add(BuildHeader(), 0, 0);
            main.Controls.Add(BuildMessages(), 0, 1);
            main.Controls.Add(BuildComposer(), 0, 2);
        }

        private Control BuildBrand()
        {
            var panel = new Panel();
            panel.Width = 282;
            panel.Height = 82;
            panel.Margin = new Padding(0, 0, 0, 18);
            panel.BackColor = Theme.Sidebar;

            var avatar = new AvatarControl();
            avatar.Text = "AI";
            avatar.FillColor = Theme.Accent;
            avatar.Location = new Point(0, 12);
            panel.Controls.Add(avatar);

            var title = new Label();
            title.Text = "AI Project 1";
            title.ForeColor = Color.White;
            title.BackColor = Theme.Sidebar;
            title.Font = new Font("Microsoft YaHei UI", 17F, FontStyle.Bold);
            title.Location = new Point(56, 12);
            title.Size = new Size(220, 30);
            panel.Controls.Add(title);

            var sub = new Label();
            sub.Text = T("brandSubtitle");
            sub.ForeColor = Theme.SidebarMuted;
            sub.BackColor = Theme.Sidebar;
            sub.Font = Theme.UiFont;
            sub.Location = new Point(58, 45);
            sub.Size = new Size(220, 24);
            panel.Controls.Add(sub);
            return panel;
        }

        private Control BuildHeader()
        {
            var header = new Panel();
            header.Dock = DockStyle.Fill;
            header.BackColor = Theme.Surface;
            header.Padding = new Padding(22, 0, 22, 0);

            var avatar = new AvatarControl();
            avatar.Text = "她";
            avatar.FillColor = Color.FromArgb(236, 72, 153);
            avatar.Location = new Point(22, 17);
            header.Controls.Add(avatar);

            var title = new Label();
            title.Text = "AI Project 1";
            title.Font = Theme.TitleFont;
            title.ForeColor = Theme.Text;
            title.BackColor = Theme.Surface;
            title.Location = new Point(78, 13);
            title.Size = new Size(420, 30);
            header.Controls.Add(title);

            var subtitle = new Label();
            subtitle.Text = T("headerSubtitle");
            subtitle.Font = Theme.UiFont;
            subtitle.ForeColor = Theme.Muted;
            subtitle.BackColor = Theme.Surface;
            subtitle.Location = new Point(80, 43);
            subtitle.Size = new Size(420, 24);
            header.Controls.Add(subtitle);

            var settings = HeaderButton(T("settingsButton"));
            settings.Width = 82;
            settings.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            settings.Click += ToggleSettingsClicked;
            header.Controls.Add(settings);

            hubControlButton = HeaderButton(T("hubStartButton"));
            hubControlButton.Width = 92;
            hubControlButton.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            hubControlButton.Click += HubControlClicked;
            header.Controls.Add(hubControlButton);

            var reconnect = HeaderButton(T("reconnect"));
            reconnect.Width = 92;
            reconnect.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            reconnect.Click += ConnectClicked;
            header.Controls.Add(reconnect);

            Action layoutButtons = delegate
            {
                reconnect.Location = new Point(header.Width - 114, 20);
                hubControlButton.Location = new Point(header.Width - 214, 20);
                settings.Location = new Point(header.Width - 304, 20);
            };
            header.Resize += delegate { layoutButtons(); };
            layoutButtons();

            var line = new Panel();
            line.BackColor = Theme.Line;
            line.Dock = DockStyle.Bottom;
            line.Height = 1;
            header.Controls.Add(line);
            return header;
        }

        private Control BuildMessages()
        {
            messageList = new FlowLayoutPanel();
            messageList.Dock = DockStyle.Fill;
            messageList.FlowDirection = FlowDirection.TopDown;
            messageList.WrapContents = false;
            messageList.AutoScroll = true;
            messageList.BackColor = Theme.Main;
            messageList.Padding = new Padding(22, 18, 22, 18);
            messageList.Resize += delegate { RelayoutMessages(); };
            return messageList;
        }

        private Control BuildComposer()
        {
            var outer = new Panel();
            outer.Dock = DockStyle.Fill;
            outer.BackColor = Theme.Surface;
            outer.Padding = new Padding(18, 10, 18, 12);

            var line = new Panel();
            line.BackColor = Theme.Line;
            line.Dock = DockStyle.Top;
            line.Height = 1;
            outer.Controls.Add(line);

            var table = new TableLayoutPanel();
            table.Dock = DockStyle.Fill;
            table.ColumnCount = 2;
            table.RowCount = 1;
            table.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            table.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 72));
            table.BackColor = Theme.Surface;
            table.Padding = new Padding(0, 6, 0, 0);
            outer.Controls.Add(table);

            inputBox = new TextBox();
            inputBox.Multiline = true;
            inputBox.BorderStyle = BorderStyle.None;
            inputBox.Dock = DockStyle.Fill;
            inputBox.Font = new Font("Microsoft YaHei UI", 11F);
            inputBox.BackColor = Color.FromArgb(243, 246, 250);
            inputBox.ForeColor = Theme.Text;
            inputBox.KeyDown += InputKeyDown;
            inputBox.Margin = new Padding(8, 7, 8, 6);

            var inputShell = new RoundedPanel();
            inputShell.FillColor = Color.FromArgb(243, 246, 250);
            inputShell.BorderColor = Color.FromArgb(232, 236, 242);
            inputShell.Radius = 12;
            inputShell.Padding = new Padding(8, 7, 8, 7);
            inputShell.Dock = DockStyle.Fill;
            inputShell.Controls.Add(inputBox);
            table.Controls.Add(inputShell, 0, 0);

            sendButton = HeaderButton(T("send"));
            sendButton.Width = 58;
            sendButton.Height = 40;
            sendButton.BackColor = Theme.Accent;
            sendButton.ForeColor = Color.White;
            sendButton.Font = Theme.UiFontBold;
            sendButton.Click += SendClicked;
            var sendPanel = new Panel();
            sendPanel.Dock = DockStyle.Fill;
            sendPanel.BackColor = Theme.Surface;
            sendPanel.Controls.Add(sendButton);
            sendPanel.Resize += delegate
            {
                sendButton.Location = new Point(
                    Math.Max(0, (sendPanel.Width - sendButton.Width) / 2),
                    Math.Max(0, (sendPanel.Height - sendButton.Height) / 2)
                );
            };
            table.Controls.Add(sendPanel, 1, 0);
            return outer;
        }

        private void AddCard(FlowLayoutPanel parent, string title, Control[] controls)
        {
            var card = new RoundedFlowPanel();
            card.FlowDirection = FlowDirection.TopDown;
            card.WrapContents = false;
            card.Width = 282;
            card.AutoSize = true;
            card.Padding = new Padding(14, 12, 14, 14);
            card.Margin = new Padding(0, 0, 0, 14);
            card.FillColor = Theme.SidebarCard;
            card.BorderColor = Color.FromArgb(55, 65, 81);
            card.Radius = 18;

            var label = new Label();
            label.Text = title;
            label.ForeColor = Color.White;
            label.BackColor = Theme.SidebarCard;
            label.Font = new Font("Microsoft YaHei UI", 10F, FontStyle.Bold);
            label.Width = 248;
            label.Height = 26;
            card.Controls.Add(label);

            foreach (Control control in controls)
            {
                card.Controls.Add(control);
            }
            parent.Controls.Add(card);
        }

        private Control Field(string labelText, Control input)
        {
            var panel = new Panel();
            panel.Width = 248;
            panel.Height = 58;
            panel.BackColor = Theme.SidebarCard;
            panel.Margin = new Padding(0, 4, 0, 3);

            var label = new Label();
            label.Text = labelText;
            label.ForeColor = Theme.SidebarMuted;
            label.BackColor = Theme.SidebarCard;
            label.Font = Theme.UiFont;
            label.Location = new Point(0, 0);
            label.Size = new Size(248, 20);
            panel.Controls.Add(label);

            input.Location = new Point(0, 23);
            input.Width = 248;
            input.Height = 27;
            input.Font = Theme.UiFont;
            input.BackColor = Theme.SidebarInput;
            input.ForeColor = Color.White;
            input.Margin = new Padding(0);
            if (input is TextBox)
            {
                ((TextBox)input).BorderStyle = BorderStyle.FixedSingle;
            }
            panel.Controls.Add(input);
            return panel;
        }

        private CheckBox Check(string text)
        {
            var box = new CheckBox();
            box.Text = text;
            box.Width = 248;
            box.Height = 30;
            box.ForeColor = Color.White;
            box.BackColor = Theme.SidebarCard;
            box.FlatStyle = FlatStyle.Flat;
            box.Font = Theme.UiFont;
            box.Margin = new Padding(0, 2, 0, 2);
            return box;
        }

        private Button SidebarButton(string text, EventHandler handler, bool accent)
        {
            var button = new RoundedButton();
            button.Radius = 10;
            button.Text = text;
            button.Width = 248;
            button.Height = 36;
            button.Margin = new Padding(0, 8, 0, 0);
            button.FlatStyle = FlatStyle.Flat;
            button.FlatAppearance.BorderSize = 0;
            button.BackColor = accent ? Theme.Accent : Color.FromArgb(55, 65, 81);
            button.ForeColor = Color.White;
            button.Font = Theme.UiFontBold;
            button.Cursor = Cursors.Hand;
            button.Click += handler;
            return button;
        }

        private Button HeaderButton(string text)
        {
            var button = new RoundedButton();
            button.Radius = 10;
            button.Text = text;
            button.Width = 110;
            button.Height = 36;
            button.FlatStyle = FlatStyle.Flat;
            button.FlatAppearance.BorderSize = 0;
            button.BackColor = Theme.Accent;
            button.ForeColor = Color.White;
            button.Font = Theme.UiFontBold;
            button.Cursor = Cursors.Hand;
            return button;
        }

        private Label SideStatus(string text)
        {
            var label = new Label();
            label.Text = text;
            label.Width = 248;
            label.AutoSize = false;
            label.Height = 28;
            label.ForeColor = Theme.SidebarMuted;
            label.BackColor = Theme.SidebarCard;
            label.Font = Theme.UiFont;
            label.Margin = new Padding(0, 5, 0, 0);
            return label;
        }

        private void LoadSettings()
        {
            loadingSettings = true;
            serverBox.Text = "http://127.0.0.1:8765";
            clientBox.Text = Environment.MachineName;
            autoStartHubBox.Checked = true;
            liveSearchBox.Checked = true;
            autoLookupBox.Checked = true;
            uiLanguageBox.SelectedItem = LanguageDisplayName(currentLanguage);
            searchEngineBox.SelectedItem = "Google";

            if (File.Exists(configPath))
            {
                try
                {
                    var data = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(configPath, Encoding.UTF8));
                    SetText(serverBox, data, "server", serverBox.Text);
                    SetText(tokenBox, data, "token", "");
                    SetText(clientBox, data, "client_id", clientBox.Text);
                    currentLanguage = NormalizeLanguage(GetString(data, "ui_language", currentLanguage));
                    uiLanguageBox.SelectedItem = LanguageDisplayName(currentLanguage);
                    autoStartHubBox.Checked = GetBool(data, "auto_start_local_hub", true);
                    selfSignedBox.Checked = GetBool(data, "insecure", false);
                    liveSearchBox.Checked = GetBool(data, "search_enabled", true);
                    autoLookupBox.Checked = GetBool(data, "search_auto_lookup", true);
                    string engine = GetString(data, "search_engine", "google");
                    searchEngineBox.SelectedItem = EngineDisplayName(engine);
                    SetText(customSearchBox, data, "custom_search_url", "");
                }
                catch
                {
                }
            }
            loadingSettings = false;
            UpdateCustomSearchState();
        }

        private void SaveSettings()
        {
            Directory.CreateDirectory(configDir);
            var data = new Dictionary<string, object>();
            data["server"] = serverBox.Text.Trim();
            data["token"] = tokenBox.Text.Trim();
            data["client_id"] = clientBox.Text.Trim();
            data["ui_language"] = currentLanguage;
            data["auto_start_local_hub"] = autoStartHubBox.Checked;
            data["insecure"] = selfSignedBox.Checked;
            data["search_enabled"] = liveSearchBox.Checked;
            data["search_auto_lookup"] = autoLookupBox.Checked;
            data["search_engine"] = SelectedEngine();
            data["custom_search_url"] = customSearchBox.Text.Trim();
            File.WriteAllText(configPath, json.Serialize(data), Encoding.UTF8);
        }

        private void SaveClicked(object sender, EventArgs e)
        {
            SaveSettings();
            statusLabel.Text = T("settingsSaved");
        }

        private void ToggleSettingsClicked(object sender, EventArgs e)
        {
            SetSettingsVisible(!settingsVisible);
        }

        private void SetSettingsVisible(bool visible)
        {
            settingsVisible = visible;
            if (settingsColumn != null)
            {
                settingsColumn.Width = visible ? 330 : 0;
            }
            if (sidebarPanel != null)
            {
                sidebarPanel.Visible = visible;
            }
        }

        private void HubControlClicked(object sender, EventArgs e)
        {
            if (IsLocalHubRunning())
            {
                StopLocalHubClicked(sender, e);
            }
            else
            {
                StartLocalHubClicked(sender, e);
            }
        }

        private void StartLocalHubClicked(object sender, EventArgs e)
        {
            SaveSettings();
            statusLabel.Text = T("startingLocalHub");
            ThreadPool.QueueUserWorkItem(delegate
            {
                try
                {
                    StartLocalHub();
                    BeginInvoke(new Action(delegate
                    {
                        statusLabel.Text = T("localHubStarted");
                        UpdateHubButtonText();
                        AddMessage(T("systemName"), T("localHubStartedMessage"), false, true);
                    }));
                }
                catch (Exception ex)
                {
                    BeginInvoke(new Action(delegate
                    {
                        statusLabel.Text = T("localHubFailed");
                        AddMessage(T("systemName"), T("localHubFailedPrefix") + ex.Message, false, true);
                    }));
                }
            });
        }

        private void StopLocalHubClicked(object sender, EventArgs e)
        {
            ThreadPool.QueueUserWorkItem(delegate
            {
                try
                {
                    StopLocalHub();
                    BeginInvoke(new Action(delegate
                    {
                        statusLabel.Text = T("localHubStopped");
                        UpdateHubButtonText();
                        AddMessage(T("systemName"), T("localHubStoppedMessage"), false, true);
                    }));
                }
                catch (Exception ex)
                {
                    BeginInvoke(new Action(delegate
                    {
                        statusLabel.Text = T("localHubFailed");
                        AddMessage(T("systemName"), T("localHubFailedPrefix") + ex.Message, false, true);
                    }));
                }
            });
        }

        private void ConnectClicked(object sender, EventArgs e)
        {
            SaveSettings();
            bool shouldStartLocalHub = autoStartHubBox.Checked && IsLocalServer();
            statusLabel.Text = shouldStartLocalHub ? T("startingLocalHub") : T("connecting");
            ThreadPool.QueueUserWorkItem(delegate
            {
                try
                {
                    if (shouldStartLocalHub)
                    {
                        StartLocalHub();
                    }
                    var status = RequestStatusWithRetry(shouldStartLocalHub ? 24 : 1);
                    BeginInvoke(new Action(delegate
                    {
                        ShowStatus(status);
                        UpdateHubButtonText();
                    }));
                }
                catch (Exception ex)
                {
                    BeginInvoke(new Action(delegate
                    {
                        statusLabel.Text = T("connectionFailed");
                        AddMessage(T("systemName"), T("connectionFailedPrefix") + ex.Message, false, true);
                    }));
                }
            });
        }

        private Dictionary<string, object> RequestStatusWithRetry(int attempts)
        {
            Exception last = null;
            for (int i = 0; i < Math.Max(1, attempts); i++)
            {
                try
                {
                    return Request("GET", "/api/status", null);
                }
                catch (Exception ex)
                {
                    last = ex;
                    Thread.Sleep(500);
                }
            }
            throw last ?? new InvalidOperationException(T("connectionFailed"));
        }

        private void SendClicked(object sender, EventArgs e)
        {
            SendMessage();
        }

        private void InputKeyDown(object sender, KeyEventArgs e)
        {
            if (e.KeyCode == Keys.Enter && !e.Shift)
            {
                e.SuppressKeyPress = true;
                SendMessage();
            }
        }

        private void SendMessage()
        {
            string message = inputBox.Text.Trim();
            if (message.Length == 0)
            {
                return;
            }
            SaveSettings();
            inputBox.Clear();
            AddMessage(T("meName"), message, true, false);
            sendButton.Enabled = false;
            sendButton.Text = T("thinkingButton");
            statusLabel.Text = T("thinking");

            ThreadPool.QueueUserWorkItem(delegate
            {
                try
                {
                    var payload = new Dictionary<string, object>();
                    payload["message"] = message;
                    payload["web_search"] = WebSearchOptions();
                    var response = Request("POST", "/api/chat", payload);
                    string reply = GetString(response, "reply", "");
                    BeginInvoke(new Action(delegate
                    {
                        AddMessage(T("assistantName"), reply, false, false);
                        statusLabel.Text = T("connected");
                        sendButton.Text = T("send");
                        sendButton.Enabled = true;
                    }));
                }
                catch (Exception ex)
                {
                    BeginInvoke(new Action(delegate
                    {
                        AddMessage(T("systemName"), T("sendFailedPrefix") + ex.Message, false, true);
                        statusLabel.Text = T("sendFailed");
                        sendButton.Text = T("send");
                        sendButton.Enabled = true;
                    }));
                }
            });
        }

        private Dictionary<string, object> Request(string method, string path, Dictionary<string, object> payload)
        {
            string baseUrl = serverBox.Text.Trim().TrimEnd('/');
            if (!baseUrl.StartsWith("http://") && !baseUrl.StartsWith("https://"))
            {
                throw new InvalidOperationException(T("serverUrlError"));
            }

            if (selfSignedBox.Checked)
            {
                ServicePointManager.ServerCertificateValidationCallback = delegate { return true; };
            }

            var request = (HttpWebRequest)WebRequest.Create(baseUrl + path);
            request.Method = method;
            request.Timeout = 15000;
            request.ReadWriteTimeout = 120000;
            request.Accept = "application/json";
            request.Headers["X-Companion-Token"] = tokenBox.Text.Trim();
            request.Headers["X-Companion-Client"] = clientBox.Text.Trim();

            if (payload != null)
            {
                string body = json.Serialize(payload);
                byte[] bytes = Encoding.UTF8.GetBytes(body);
                request.ContentType = "application/json; charset=utf-8";
                request.ContentLength = bytes.Length;
                using (var stream = request.GetRequestStream())
                {
                    stream.Write(bytes, 0, bytes.Length);
                }
            }

            try
            {
                using (var response = (HttpWebResponse)request.GetResponse())
                using (var stream = response.GetResponseStream())
                using (var reader = new StreamReader(stream, Encoding.UTF8))
                {
                    return json.Deserialize<Dictionary<string, object>>(reader.ReadToEnd());
                }
            }
            catch (WebException ex)
            {
                string details = ex.Message;
                if (ex.Response != null)
                {
                    using (var stream = ex.Response.GetResponseStream())
                    using (var reader = new StreamReader(stream, Encoding.UTF8))
                    {
                        details = reader.ReadToEnd();
                    }
                }
                throw new InvalidOperationException(details, ex);
            }
        }

        private Dictionary<string, object> WebSearchOptions()
        {
            var data = new Dictionary<string, object>();
            data["enabled"] = liveSearchBox.Checked;
            data["auto_lookup"] = autoLookupBox.Checked;
            data["search_engine"] = SelectedEngine();
            data["custom_search_url"] = customSearchBox.Text.Trim();
            return data;
        }

        private void StartLocalHub()
        {
            lock (localHubLock)
            {
                if (localHubProcess != null && !localHubProcess.HasExited)
                {
                    LoadLocalTokenIfAvailable(FindAppRoot(), true);
                    return;
                }

                string root = FindAppRoot();
                string serveScript = Path.Combine(root, "scripts", "serve_lan.py");
                if (!File.Exists(serveScript))
                {
                    throw new FileNotFoundException(T("localHubFilesMissing"), serveScript);
                }

                string python = FindPythonExecutable();
                int port = LocalServerPort();
                string args = Quote(serveScript) + " --host 0.0.0.0 --port " + port + " --live-web";
                string checkpoint = Path.Combine(root, "runs", "tiny-lover", "ckpt.pt");
                if (File.Exists(checkpoint))
                {
                    args += " --checkpoint " + Quote(checkpoint);
                }

                var startInfo = new ProcessStartInfo();
                startInfo.FileName = python;
                startInfo.Arguments = args;
                startInfo.WorkingDirectory = root;
                startInfo.UseShellExecute = false;
                startInfo.CreateNoWindow = true;
                startInfo.WindowStyle = ProcessWindowStyle.Hidden;
                localHubProcess = Process.Start(startInfo);
                if (localHubProcess == null)
                {
                    throw new InvalidOperationException(T("localHubProcessMissing"));
                }

                LoadLocalTokenIfAvailable(root, false);
            }
        }

        private void StopLocalHub()
        {
            lock (localHubLock)
            {
                if (localHubProcess == null || localHubProcess.HasExited)
                {
                    localHubProcess = null;
                    return;
                }
                localHubProcess.Kill();
                localHubProcess.WaitForExit(2500);
                localHubProcess = null;
            }
        }

        private bool IsLocalHubRunning()
        {
            return localHubProcess != null && !localHubProcess.HasExited;
        }

        private void UpdateHubButtonText()
        {
            if (hubControlButton != null)
            {
                hubControlButton.Text = IsLocalHubRunning() ? T("hubStopButton") : T("hubStartButton");
            }
        }

        private void LoadLocalTokenIfAvailable(string root, bool quick)
        {
            string tokenPath = Path.Combine(root, "data", "server_token.txt");
            int attempts = quick ? 1 : 30;
            for (int i = 0; i < attempts; i++)
            {
                if (File.Exists(tokenPath))
                {
                    string token = File.ReadAllText(tokenPath, Encoding.UTF8).Trim();
                    if (!String.IsNullOrEmpty(token))
                    {
                        tokenBox.Text = token;
                        serverBox.Text = "http://127.0.0.1:" + LocalServerPort();
                        return;
                    }
                }
                Thread.Sleep(300);
            }
        }

        private string FindAppRoot()
        {
            string dir = AppDomain.CurrentDomain.BaseDirectory;
            for (int i = 0; i < 5 && !String.IsNullOrEmpty(dir); i++)
            {
                if (File.Exists(Path.Combine(dir, "scripts", "serve_lan.py")))
                {
                    return dir;
                }
                DirectoryInfo parent = Directory.GetParent(dir.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
                dir = parent == null ? "" : parent.FullName;
            }
            return AppDomain.CurrentDomain.BaseDirectory;
        }

        private string FindPythonExecutable()
        {
            string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string[] candidates = new string[]
            {
                Path.Combine(local, "Programs", "Python", "Python312", "python.exe"),
                Path.Combine(local, "Programs", "Python", "Python313", "python.exe"),
                Path.Combine(local, "Programs", "Python", "Python311", "python.exe"),
                "python"
            };
            foreach (string candidate in candidates)
            {
                if (candidate == "python" || File.Exists(candidate))
                {
                    return candidate;
                }
            }
            return "python";
        }

        private bool IsLocalServer()
        {
            string value = serverBox.Text.Trim().ToLowerInvariant();
            return value.StartsWith("http://127.0.0.1")
                || value.StartsWith("http://localhost")
                || value.StartsWith("https://127.0.0.1")
                || value.StartsWith("https://localhost");
        }

        private int LocalServerPort()
        {
            try
            {
                Uri uri = new Uri(serverBox.Text.Trim());
                if (uri.Port > 0)
                {
                    return uri.Port;
                }
            }
            catch
            {
            }
            return 8765;
        }

        private static string Quote(string value)
        {
            return "\"" + value.Replace("\"", "\\\"") + "\"";
        }

        private void ShowStatus(Dictionary<string, object> status)
        {
            var ready = GetBool(status, "ready", false);
            statusLabel.Text = T("statusPrefix") + (ready ? T("modelReady") : T("modelMissing"))
                + " · " + GetString(status, "device", "-");
            hubLabel.Text = T("hubEmpty");
            if (status.ContainsKey("hub") && status["hub"] is Dictionary<string, object>)
            {
                var hub = (Dictionary<string, object>)status["hub"];
                hubLabel.Text = T("hubPrefix") + GetString(hub, "hub_name", "-");
            }
            memoryLabel.Text = String.Format(T("memoryStatus"), GetString(status, "memory_facts", "0"), GetString(status, "memory_turns", "0"));
            knowledgeLabel.Text = String.Format(T("knowledgeStatus"), GetString(status, "knowledge_entries", "0"));
            searchLabel.Text = GetBool(status, "live_web", false) ? T("searchHubOn") : T("searchHubOff");
            AddMessage(T("systemName"), ready ? T("connectedMessage") : T("connectedWithoutModelMessage"), false, true);
        }

        private void AddMessage(string speaker, string text, bool mine, bool system)
        {
            int listWidth = Math.Max(680, messageList.ClientSize.Width - 48);
            var row = new Panel();
            row.Width = listWidth;
            row.Height = 10;
            row.Margin = new Padding(0, 0, 0, 14);
            row.BackColor = messageList.BackColor;

            var avatar = new AvatarControl();
            avatar.Text = mine ? "我" : (system ? "i" : "她");
            avatar.FillColor = mine ? Color.FromArgb(34, 197, 94) : (system ? Theme.Muted : Color.FromArgb(236, 72, 153));
            avatar.Size = new Size(38, 38);

            var bubble = new RoundedPanel();
            bubble.FillColor = system ? Theme.SystemBubble : (mine ? Theme.UserBubble : Theme.AssistantBubble);
            bubble.BorderColor = mine ? Color.FromArgb(126, 211, 33) : Theme.Line;
            bubble.Radius = 18;
            bubble.Padding = new Padding(14, 10, 14, 10);

            var meta = new Label();
            meta.Text = speaker + " · " + DateTime.Now.ToString("HH:mm");
            meta.Font = new Font("Microsoft YaHei UI", 8F);
            meta.ForeColor = Theme.Muted;
            meta.BackColor = Color.Transparent;
            meta.AutoSize = true;
            meta.Location = new Point(14, 8);
            bubble.Controls.Add(meta);

            var body = new Label();
            body.Text = text;
            body.Font = Theme.MessageFont;
            body.ForeColor = Theme.Text;
            body.BackColor = Color.Transparent;
            body.MaximumSize = new Size(Math.Max(330, listWidth * 58 / 100), 0);
            body.AutoSize = true;
            body.Location = new Point(14, 29);
            bubble.Controls.Add(body);

            int bubbleWidth = Math.Max(120, Math.Max(meta.Width, body.Width) + 28);
            int bubbleHeight = meta.Height + body.Height + 30;
            bubble.Size = new Size(bubbleWidth, bubbleHeight);

            row.Controls.Add(avatar);
            row.Controls.Add(bubble);
            if (mine)
            {
                avatar.Location = new Point(listWidth - avatar.Width - 4, 2);
                bubble.Location = new Point(Math.Max(6, avatar.Left - bubble.Width - 10), 0);
            }
            else
            {
                avatar.Location = new Point(4, 2);
                bubble.Location = new Point(avatar.Right + 10, 0);
            }

            row.Height = Math.Max(avatar.Height, bubble.Height) + 6;
            messageList.Controls.Add(row);
            messageList.ScrollControlIntoView(row);
        }

        private void RelayoutMessages()
        {
            foreach (Control row in messageList.Controls)
            {
                row.Width = Math.Max(680, messageList.ClientSize.Width - 48);
            }
        }

        private void ClearClicked(object sender, EventArgs e)
        {
            messageList.Controls.Clear();
            AddMessage(T("systemName"), T("screenCleared"), false, true);
        }

        private void LanguageChanged(object sender, EventArgs e)
        {
            if (loadingSettings)
            {
                return;
            }
            currentLanguage = SelectedLanguage();
            SaveSettings();
            Controls.Clear();
            BuildUi();
            LoadSettings();
            AddMessage(T("systemName"), T("languageChanged"), false, true);
        }

        private void UpdateCustomSearchState()
        {
            customSearchBox.Enabled = SelectedEngine() == "custom";
        }

        private string SelectedEngine()
        {
            if (searchEngineBox.SelectedItem == null)
            {
                return "google";
            }
            string text = searchEngineBox.SelectedItem.ToString();
            if (text == "Baidu")
            {
                return "baidu";
            }
            if (text == "自定义" || text == "カスタム" || text == "Custom" || text == T("customEngine"))
            {
                return "custom";
            }
            return "google";
        }

        private string SelectedLanguage()
        {
            if (uiLanguageBox == null || uiLanguageBox.SelectedItem == null)
            {
                return currentLanguage;
            }
            return NormalizeLanguage(uiLanguageBox.SelectedItem.ToString());
        }

        private static string NormalizeLanguage(string value)
        {
            if (String.IsNullOrEmpty(value))
            {
                return "zh";
            }
            string lowered = value.Trim().ToLowerInvariant();
            if (lowered == "ja" || lowered == "jp" || lowered == "日本語")
            {
                return "ja";
            }
            if (lowered == "en" || lowered == "english")
            {
                return "en";
            }
            return "zh";
        }

        private static string LanguageDisplayName(string code)
        {
            if (code == "ja")
            {
                return "日本語";
            }
            if (code == "en")
            {
                return "English";
            }
            return "中文";
        }

        private string EngineDisplayName(string engine)
        {
            if (engine == "baidu")
            {
                return "Baidu";
            }
            if (engine == "custom")
            {
                return T("customEngine");
            }
            return "Google";
        }

        private string T(string key)
        {
            Dictionary<string, string> map;
            if (!Texts.TryGetValue(currentLanguage, out map))
            {
                map = Texts["zh"];
            }
            string value;
            if (map.TryGetValue(key, out value))
            {
                return value;
            }
            return Texts["zh"].ContainsKey(key) ? Texts["zh"][key] : key;
        }

        private static readonly Dictionary<string, Dictionary<string, string>> Texts =
            new Dictionary<string, Dictionary<string, string>>
            {
                {
                    "zh",
                    new Dictionary<string, string>
                    {
                        {"brandSubtitle", "私人陪伴中枢"},
                        {"headerSubtitle", "三语陪伴模型 · 中文 / 日本語 / English"},
                        {"languageTitle", "语言"},
                        {"uiLanguage", "界面语言"},
                        {"connectionTitle", "连接设置"},
                        {"server", "服务地址"},
                        {"token", "访问令牌"},
                        {"client", "设备名称"},
                        {"selfSigned", "信任自签 HTTPS"},
                        {"autoStartHub", "打开软件时自动启动本机 Hub"},
                        {"startLocalHub", "启动本机 Hub"},
                        {"stopLocalHub", "停止本机 Hub"},
                        {"connect", "连接主设备"},
                        {"save", "保存设置"},
                        {"settingsButton", "设置"},
                        {"hideSettings", "隐藏设置"},
                        {"hubStartButton", "Hub开"},
                        {"hubStopButton", "Hub关"},
                        {"searchTitle", "联网搜索"},
                        {"liveSearch", "允许联网搜索"},
                        {"autoLookup", "按触发词自动搜索"},
                        {"searchEngine", "搜索引擎"},
                        {"customSearch", "自定义搜索页"},
                        {"customEngine", "自定义"},
                        {"sessionTitle", "会话"},
                        {"clear", "清空屏幕"},
                        {"statusNotConnected", "状态：未连接"},
                        {"hubEmpty", "主设备：-"},
                        {"memoryEmpty", "记忆：-"},
                        {"knowledgeEmpty", "知识库：-"},
                        {"searchEmpty", "搜索：-"},
                        {"reconnect", "重新连接"},
                        {"send", "发送"},
                        {"systemName", "系统"},
                        {"meName", "我"},
                        {"assistantName", "她"},
                        {"welcome", "我会尝试自动启动本机 Hub 并连接。没有训练出 ckpt.pt 时可以连接，但模型会显示未加载。"},
                        {"languageChanged", "界面语言已切换。"},
                        {"settingsSaved", "状态：设置已保存"},
                        {"connecting", "状态：正在连接..."},
                        {"connectionFailed", "状态：连接失败"},
                        {"connectionFailedPrefix", "连接失败：请先在主设备运行 scripts\\start_hub.ps1。详细原因："},
                        {"startingLocalHub", "状态：正在启动本机 Hub..."},
                        {"localHubStarted", "状态：本机 Hub 已启动"},
                        {"localHubFailed", "状态：本机 Hub 启动失败"},
                        {"localHubStopped", "状态：本机 Hub 已停止"},
                        {"localHubStartedMessage", "本机 Hub 已在后台启动，我会连接到 127.0.0.1。"},
                        {"localHubStoppedMessage", "本机 Hub 已停止。需要聊天时可以再启动。"},
                        {"localHubFailedPrefix", "本机 Hub 启动失败："},
                        {"localHubFilesMissing", "找不到 Hub 脚本。请确认安装包包含 scripts 和 companion_ai 目录。"},
                        {"localHubProcessMissing", "Hub 进程没有启动成功。"},
                        {"thinkingButton", "思考中"},
                        {"thinking", "状态：思考中..."},
                        {"connected", "状态：已连接"},
                        {"sendFailed", "状态：发送失败"},
                        {"sendFailedPrefix", "发送失败："},
                        {"serverUrlError", "服务地址必须以 http:// 或 https:// 开头"},
                        {"statusPrefix", "状态："},
                        {"modelReady", "模型已就绪"},
                        {"modelMissing", "未加载模型"},
                        {"hubPrefix", "主设备："},
                        {"memoryStatus", "记忆：{0} 条事实，{1} 轮对话"},
                        {"knowledgeStatus", "知识库：{0} 条记录"},
                        {"searchHubOn", "搜索：主设备已开启"},
                        {"searchHubOff", "搜索：主设备未开启"},
                        {"connectedMessage", "已连接到主设备，模型已就绪。"},
                        {"connectedWithoutModelMessage", "已连接到主设备，但还没有加载模型。请先训练生成 runs\\tiny-lover\\ckpt.pt，或用 -NoModel 只测试连接。"},
                        {"screenCleared", "屏幕已清空。"}
                    }
                },
                {
                    "ja",
                    new Dictionary<string, string>
                    {
                        {"brandSubtitle", "プライベート伴侶ハブ"},
                        {"headerSubtitle", "三言語コンパニオン · 中文 / 日本語 / English"},
                        {"languageTitle", "言語"},
                        {"uiLanguage", "表示言語"},
                        {"connectionTitle", "接続設定"},
                        {"server", "サーバー"},
                        {"token", "アクセストークン"},
                        {"client", "端末名"},
                        {"selfSigned", "自己署名 HTTPS を信頼"},
                        {"autoStartHub", "起動時にローカル Hub を自動起動"},
                        {"startLocalHub", "ローカル Hub を起動"},
                        {"stopLocalHub", "ローカル Hub を停止"},
                        {"connect", "主端末に接続"},
                        {"save", "設定を保存"},
                        {"settingsButton", "設定"},
                        {"hideSettings", "設定を隠す"},
                        {"hubStartButton", "Hub起動"},
                        {"hubStopButton", "Hub停止"},
                        {"searchTitle", "Web 検索"},
                        {"liveSearch", "Web 検索を許可"},
                        {"autoLookup", "トリガーで自動検索"},
                        {"searchEngine", "検索エンジン"},
                        {"customSearch", "カスタム検索ページ"},
                        {"customEngine", "カスタム"},
                        {"sessionTitle", "会話"},
                        {"clear", "画面をクリア"},
                        {"statusNotConnected", "状態：未接続"},
                        {"hubEmpty", "主端末：-"},
                        {"memoryEmpty", "記憶：-"},
                        {"knowledgeEmpty", "知識庫：-"},
                        {"searchEmpty", "検索：-"},
                        {"reconnect", "再接続"},
                        {"send", "送信"},
                        {"systemName", "システム"},
                        {"meName", "私"},
                        {"assistantName", "彼女"},
                        {"welcome", "ローカル Hub を自動起動して接続します。ckpt.pt がまだ無い場合、接続はできますがモデル未読み込みになります。"},
                        {"languageChanged", "表示言語を切り替えました。"},
                        {"settingsSaved", "状態：設定を保存しました"},
                        {"connecting", "状態：接続中..."},
                        {"connectionFailed", "状態：接続失敗"},
                        {"connectionFailedPrefix", "接続失敗：主端末で scripts\\start_hub.ps1 を実行してください。詳細："},
                        {"startingLocalHub", "状態：ローカル Hub 起動中..."},
                        {"localHubStarted", "状態：ローカル Hub 起動済み"},
                        {"localHubFailed", "状態：ローカル Hub 起動失敗"},
                        {"localHubStopped", "状態：ローカル Hub 停止済み"},
                        {"localHubStartedMessage", "ローカル Hub をバックグラウンドで起動しました。127.0.0.1 に接続します。"},
                        {"localHubStoppedMessage", "ローカル Hub を停止しました。必要な時にまた起動できます。"},
                        {"localHubFailedPrefix", "ローカル Hub 起動失敗："},
                        {"localHubFilesMissing", "Hub スクリプトが見つかりません。インストールに scripts と companion_ai が含まれているか確認してください。"},
                        {"localHubProcessMissing", "Hub プロセスを起動できませんでした。"},
                        {"thinkingButton", "考え中"},
                        {"thinking", "状態：考え中..."},
                        {"connected", "状態：接続済み"},
                        {"sendFailed", "状態：送信失敗"},
                        {"sendFailedPrefix", "送信失敗："},
                        {"serverUrlError", "サーバーは http:// または https:// で始めてください"},
                        {"statusPrefix", "状態："},
                        {"modelReady", "モデル準備完了"},
                        {"modelMissing", "モデル未読み込み"},
                        {"hubPrefix", "主端末："},
                        {"memoryStatus", "記憶：事実 {0} 件、会話 {1} 往復"},
                        {"knowledgeStatus", "知識庫：{0} 件"},
                        {"searchHubOn", "検索：主端末で有効"},
                        {"searchHubOff", "検索：主端末で無効"},
                        {"connectedMessage", "主端末に接続しました。モデルは準備完了です。"},
                        {"connectedWithoutModelMessage", "主端末に接続しましたが、モデルはまだ読み込まれていません。先に runs\\tiny-lover\\ckpt.pt を作成するか、-NoModel で接続だけ確認してください。"},
                        {"screenCleared", "画面をクリアしました。"}
                    }
                },
                {
                    "en",
                    new Dictionary<string, string>
                    {
                        {"brandSubtitle", "private companion hub"},
                        {"headerSubtitle", "Trilingual companion · 中文 / 日本語 / English"},
                        {"languageTitle", "Language"},
                        {"uiLanguage", "Interface language"},
                        {"connectionTitle", "Connection"},
                        {"server", "Server"},
                        {"token", "Access token"},
                        {"client", "Device name"},
                        {"selfSigned", "Trust self-signed HTTPS"},
                        {"autoStartHub", "Auto-start local Hub when app opens"},
                        {"startLocalHub", "Start local Hub"},
                        {"stopLocalHub", "Stop local Hub"},
                        {"connect", "Connect to main device"},
                        {"save", "Save settings"},
                        {"settingsButton", "Settings"},
                        {"hideSettings", "Hide settings"},
                        {"hubStartButton", "Hub on"},
                        {"hubStopButton", "Hub off"},
                        {"searchTitle", "Web Search"},
                        {"liveSearch", "Allow web search"},
                        {"autoLookup", "Auto lookup triggers"},
                        {"searchEngine", "Search engine"},
                        {"customSearch", "Custom search page"},
                        {"customEngine", "Custom"},
                        {"sessionTitle", "Session"},
                        {"clear", "Clear screen"},
                        {"statusNotConnected", "Status: not connected"},
                        {"hubEmpty", "Main device: -"},
                        {"memoryEmpty", "Memory: -"},
                        {"knowledgeEmpty", "Knowledge: -"},
                        {"searchEmpty", "Search: -"},
                        {"reconnect", "Reconnect"},
                        {"send", "Send"},
                        {"systemName", "System"},
                        {"meName", "Me"},
                        {"assistantName", "Her"},
                        {"welcome", "I will try to auto-start the local Hub and connect here. If ckpt.pt has not been trained yet, the app can connect but the model will show as not loaded."},
                        {"languageChanged", "Interface language changed."},
                        {"settingsSaved", "Status: settings saved"},
                        {"connecting", "Status: connecting..."},
                        {"connectionFailed", "Status: connection failed"},
                        {"connectionFailedPrefix", "Connection failed: start scripts\\start_hub.ps1 on the main device first. Details: "},
                        {"startingLocalHub", "Status: starting local Hub..."},
                        {"localHubStarted", "Status: local Hub started"},
                        {"localHubFailed", "Status: local Hub failed"},
                        {"localHubStopped", "Status: local Hub stopped"},
                        {"localHubStartedMessage", "The local Hub has started in the background. I will connect to 127.0.0.1."},
                        {"localHubStoppedMessage", "The local Hub has stopped. Start it again when you want to chat."},
                        {"localHubFailedPrefix", "Local Hub failed: "},
                        {"localHubFilesMissing", "Hub scripts were not found. Make sure the install includes scripts and companion_ai."},
                        {"localHubProcessMissing", "The Hub process did not start."},
                        {"thinkingButton", "Thinking"},
                        {"thinking", "Status: thinking..."},
                        {"connected", "Status: connected"},
                        {"sendFailed", "Status: send failed"},
                        {"sendFailedPrefix", "Send failed: "},
                        {"serverUrlError", "Server must start with http:// or https://"},
                        {"statusPrefix", "Status: "},
                        {"modelReady", "model ready"},
                        {"modelMissing", "model not loaded"},
                        {"hubPrefix", "Main device: "},
                        {"memoryStatus", "Memory: {0} facts, {1} turns"},
                        {"knowledgeStatus", "Knowledge: {0} notes"},
                        {"searchHubOn", "Search: enabled on main device"},
                        {"searchHubOff", "Search: disabled on main device"},
                        {"connectedMessage", "Connected to the main device. Model is ready."},
                        {"connectedWithoutModelMessage", "Connected to the main device, but no model is loaded yet. Train runs\\tiny-lover\\ckpt.pt first, or use -NoModel only to test the connection."},
                        {"screenCleared", "Screen cleared."}
                    }
                }
            };

        private static void SetText(TextBox box, Dictionary<string, object> data, string key, string fallback)
        {
            box.Text = GetString(data, key, fallback);
        }

        private static string GetString(Dictionary<string, object> data, string key, string fallback)
        {
            if (!data.ContainsKey(key) || data[key] == null)
            {
                return fallback;
            }
            return Convert.ToString(data[key]);
        }

        private static bool GetBool(Dictionary<string, object> data, string key, bool fallback)
        {
            if (!data.ContainsKey(key) || data[key] == null)
            {
                return fallback;
            }
            try
            {
                return Convert.ToBoolean(data[key]);
            }
            catch
            {
                return fallback;
            }
        }
    }

    internal class RoundedPanel : Panel
    {
        public Color FillColor { get; set; }
        public Color BorderColor { get; set; }
        public int Radius { get; set; }

        public RoundedPanel()
        {
            FillColor = Color.White;
            BorderColor = Theme.Line;
            Radius = 16;
            BackColor = Color.Transparent;
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.SupportsTransparentBackColor, true);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            Rectangle rect = new Rectangle(0, 0, Width - 1, Height - 1);
            using (GraphicsPath path = RoundedRect(rect, Radius))
            using (SolidBrush brush = new SolidBrush(FillColor))
            using (Pen pen = new Pen(BorderColor))
            {
                e.Graphics.FillPath(brush, path);
                e.Graphics.DrawPath(pen, path);
            }
        }

        public static GraphicsPath RoundedRect(Rectangle bounds, int radius)
        {
            int diameter = radius * 2;
            var path = new GraphicsPath();
            path.AddArc(bounds.Left, bounds.Top, diameter, diameter, 180, 90);
            path.AddArc(bounds.Right - diameter, bounds.Top, diameter, diameter, 270, 90);
            path.AddArc(bounds.Right - diameter, bounds.Bottom - diameter, diameter, diameter, 0, 90);
            path.AddArc(bounds.Left, bounds.Bottom - diameter, diameter, diameter, 90, 90);
            path.CloseFigure();
            return path;
        }
    }

    internal sealed class RoundedFlowPanel : FlowLayoutPanel
    {
        public Color FillColor { get; set; }
        public Color BorderColor { get; set; }
        public int Radius { get; set; }

        public RoundedFlowPanel()
        {
            FillColor = Color.White;
            BorderColor = Theme.Line;
            Radius = 16;
            BackColor = Color.Transparent;
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.SupportsTransparentBackColor, true);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            Rectangle rect = new Rectangle(0, 0, Width - 1, Height - 1);
            using (GraphicsPath path = RoundedPanel.RoundedRect(rect, Radius))
            using (SolidBrush brush = new SolidBrush(FillColor))
            using (Pen pen = new Pen(BorderColor))
            {
                e.Graphics.FillPath(brush, path);
                e.Graphics.DrawPath(pen, path);
            }
            base.OnPaint(e);
        }
    }

    internal sealed class RoundedButton : Button
    {
        public int Radius { get; set; }

        public RoundedButton()
        {
            Radius = 10;
            FlatStyle = FlatStyle.Flat;
            FlatAppearance.BorderSize = 0;
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer, true);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            Rectangle rect = new Rectangle(0, 0, Width - 1, Height - 1);
            Color fill = Enabled ? BackColor : Color.FromArgb(156, 163, 175);
            using (GraphicsPath path = RoundedPanel.RoundedRect(rect, Radius))
            using (SolidBrush brush = new SolidBrush(fill))
            {
                e.Graphics.FillPath(brush, path);
            }
            TextRenderer.DrawText(
                e.Graphics,
                Text,
                Font,
                ClientRectangle,
                ForeColor,
                TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.EndEllipsis
            );
        }
    }

    internal sealed class AvatarControl : Control
    {
        public Color FillColor { get; set; }

        public AvatarControl()
        {
            FillColor = Theme.Accent;
            Size = new Size(42, 42);
            ForeColor = Color.White;
            Font = new Font("Microsoft YaHei UI", 10F, FontStyle.Bold);
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer, true);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            using (SolidBrush brush = new SolidBrush(FillColor))
            {
                e.Graphics.FillEllipse(brush, 1, 1, Width - 2, Height - 2);
            }
            TextRenderer.DrawText(e.Graphics, Text, Font, ClientRectangle, ForeColor, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
        }
    }

    internal static class Program
    {
        [STAThread]
        private static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new ChatForm());
        }
    }
}
