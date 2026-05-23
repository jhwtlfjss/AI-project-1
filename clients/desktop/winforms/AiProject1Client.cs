using System;
using System.Collections.Generic;
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

        private TextBox serverBox;
        private TextBox tokenBox;
        private TextBox clientBox;
        private CheckBox selfSignedBox;
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

            BuildUi();
            LoadSettings();
            AddMessage("系统", "连接主设备后就可以开始聊天。", false, true);
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

        private void BuildUi()
        {
            var root = new TableLayoutPanel();
            root.Dock = DockStyle.Fill;
            root.ColumnCount = 2;
            root.RowCount = 1;
            root.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 330));
            root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            Controls.Add(root);

            var sidebar = new Panel();
            sidebar.Dock = DockStyle.Fill;
            sidebar.BackColor = Theme.Sidebar;
            sidebar.Padding = new Padding(18);
            root.Controls.Add(sidebar, 0, 0);

            var sideFlow = new FlowLayoutPanel();
            sideFlow.Dock = DockStyle.Fill;
            sideFlow.FlowDirection = FlowDirection.TopDown;
            sideFlow.WrapContents = false;
            sideFlow.AutoScroll = true;
            sideFlow.BackColor = Theme.Sidebar;
            sidebar.Controls.Add(sideFlow);

            sideFlow.Controls.Add(BuildBrand());

            serverBox = new TextBox();
            tokenBox = new TextBox();
            tokenBox.UseSystemPasswordChar = true;
            clientBox = new TextBox();
            selfSignedBox = Check("信任自签 HTTPS");
            AddCard(sideFlow, "连接设置", new Control[]
            {
                Field("服务地址", serverBox),
                Field("访问令牌", tokenBox),
                Field("设备名称", clientBox),
                selfSignedBox,
                SidebarButton("连接主设备", ConnectClicked, true),
                SidebarButton("保存设置", SaveClicked, false)
            });

            liveSearchBox = Check("允许联网搜索");
            autoLookupBox = Check("按触发词自动搜索");
            searchEngineBox = new ComboBox();
            searchEngineBox.DropDownStyle = ComboBoxStyle.DropDownList;
            searchEngineBox.Items.AddRange(new object[] { "Google", "Baidu", "自定义" });
            searchEngineBox.SelectedIndexChanged += delegate { UpdateCustomSearchState(); };
            customSearchBox = new TextBox();
            AddCard(sideFlow, "联网搜索", new Control[]
            {
                liveSearchBox,
                autoLookupBox,
                Field("搜索引擎", searchEngineBox),
                Field("自定义搜索页", customSearchBox)
            });

            statusLabel = SideStatus("状态：未连接");
            hubLabel = SideStatus("主设备：-");
            memoryLabel = SideStatus("记忆：-");
            knowledgeLabel = SideStatus("知识库：-");
            searchLabel = SideStatus("搜索：-");
            AddCard(sideFlow, "会话", new Control[]
            {
                SidebarButton("清空屏幕", ClearClicked, false),
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
            main.RowStyles.Add(new RowStyle(SizeType.Absolute, 102));
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
            sub.Text = "私人陪伴中枢";
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
            subtitle.Text = "三语陪伴模型 · 中文 / 日语 / English";
            subtitle.Font = Theme.UiFont;
            subtitle.ForeColor = Theme.Muted;
            subtitle.BackColor = Theme.Surface;
            subtitle.Location = new Point(80, 43);
            subtitle.Size = new Size(420, 24);
            header.Controls.Add(subtitle);

            var reconnect = HeaderButton("重新连接");
            reconnect.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            reconnect.Location = new Point(header.Width - 132, 20);
            reconnect.Click += ConnectClicked;
            header.Resize += delegate { reconnect.Location = new Point(header.Width - 132, 20); };
            header.Controls.Add(reconnect);

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
            outer.Padding = new Padding(22, 16, 22, 16);

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
            table.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 100));
            table.BackColor = Theme.Surface;
            table.Padding = new Padding(0, 8, 0, 0);
            outer.Controls.Add(table);

            inputBox = new TextBox();
            inputBox.Multiline = true;
            inputBox.BorderStyle = BorderStyle.None;
            inputBox.Dock = DockStyle.Fill;
            inputBox.Font = new Font("Microsoft YaHei UI", 11F);
            inputBox.BackColor = Color.FromArgb(243, 246, 250);
            inputBox.ForeColor = Theme.Text;
            inputBox.KeyDown += InputKeyDown;
            inputBox.Margin = new Padding(12, 10, 12, 8);

            var inputShell = new RoundedPanel();
            inputShell.FillColor = Color.FromArgb(243, 246, 250);
            inputShell.BorderColor = Color.FromArgb(226, 232, 240);
            inputShell.Radius = 18;
            inputShell.Padding = new Padding(12, 10, 12, 10);
            inputShell.Dock = DockStyle.Fill;
            inputShell.Controls.Add(inputBox);
            table.Controls.Add(inputShell, 0, 0);

            sendButton = HeaderButton("发送");
            sendButton.Dock = DockStyle.Fill;
            sendButton.BackColor = Theme.Accent;
            sendButton.ForeColor = Color.White;
            sendButton.Font = Theme.UiFontBold;
            sendButton.Click += SendClicked;
            table.Controls.Add(sendButton, 1, 0);
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
            var button = new Button();
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
            var button = new Button();
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
            serverBox.Text = "http://127.0.0.1:8765";
            clientBox.Text = Environment.MachineName;
            liveSearchBox.Checked = true;
            autoLookupBox.Checked = true;
            searchEngineBox.SelectedItem = "Google";

            if (File.Exists(configPath))
            {
                try
                {
                    var data = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(configPath, Encoding.UTF8));
                    SetText(serverBox, data, "server", serverBox.Text);
                    SetText(tokenBox, data, "token", "");
                    SetText(clientBox, data, "client_id", clientBox.Text);
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
            UpdateCustomSearchState();
        }

        private void SaveSettings()
        {
            Directory.CreateDirectory(configDir);
            var data = new Dictionary<string, object>();
            data["server"] = serverBox.Text.Trim();
            data["token"] = tokenBox.Text.Trim();
            data["client_id"] = clientBox.Text.Trim();
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
            statusLabel.Text = "状态：设置已保存";
        }

        private void ConnectClicked(object sender, EventArgs e)
        {
            SaveSettings();
            statusLabel.Text = "状态：正在连接...";
            ThreadPool.QueueUserWorkItem(delegate
            {
                try
                {
                    var status = Request("GET", "/api/status", null);
                    BeginInvoke(new Action(delegate { ShowStatus(status); }));
                }
                catch (Exception ex)
                {
                    BeginInvoke(new Action(delegate
                    {
                        statusLabel.Text = "状态：连接失败";
                        AddMessage("系统", "连接失败：" + ex.Message, false, true);
                    }));
                }
            });
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
            AddMessage("我", message, true, false);
            sendButton.Enabled = false;
            sendButton.Text = "思考中";
            statusLabel.Text = "状态：思考中...";

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
                        AddMessage("她", reply, false, false);
                        statusLabel.Text = "状态：已连接";
                        sendButton.Text = "发送";
                        sendButton.Enabled = true;
                    }));
                }
                catch (Exception ex)
                {
                    BeginInvoke(new Action(delegate
                    {
                        AddMessage("系统", "发送失败：" + ex.Message, false, true);
                        statusLabel.Text = "状态：发送失败";
                        sendButton.Text = "发送";
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
                throw new InvalidOperationException("服务地址必须以 http:// 或 https:// 开头");
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

        private void ShowStatus(Dictionary<string, object> status)
        {
            statusLabel.Text = "状态：" + (GetBool(status, "ready", false) ? "模型已就绪" : "未加载模型")
                + " · " + GetString(status, "device", "-");
            hubLabel.Text = "主设备：-";
            if (status.ContainsKey("hub") && status["hub"] is Dictionary<string, object>)
            {
                var hub = (Dictionary<string, object>)status["hub"];
                hubLabel.Text = "主设备：" + GetString(hub, "hub_name", "-");
            }
            memoryLabel.Text = "记忆：" + GetString(status, "memory_facts", "0") + " 条事实，"
                + GetString(status, "memory_turns", "0") + " 轮对话";
            knowledgeLabel.Text = "知识库：" + GetString(status, "knowledge_entries", "0") + " 条记录";
            searchLabel.Text = GetBool(status, "live_web", false) ? "搜索：主设备已开启" : "搜索：主设备未开启";
            AddMessage("系统", "已连接到主设备。", false, true);
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
            AddMessage("系统", "屏幕已清空。", false, true);
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
            if (text == "自定义")
            {
                return "custom";
            }
            return "google";
        }

        private static string EngineDisplayName(string engine)
        {
            if (engine == "baidu")
            {
                return "Baidu";
            }
            if (engine == "custom")
            {
                return "自定义";
            }
            return "Google";
        }

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
