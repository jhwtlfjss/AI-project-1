using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace AIProject1
{
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
            MinimumSize = new Size(900, 600);
            Size = new Size(1120, 760);
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.FromArgb(238, 242, 245);
            Icon = LoadAppIcon();

            BuildUi();
            LoadSettings();
            AddMessage("System", "连接主设备 Hub 后就可以开始聊天。", false, true);
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
            root.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 310));
            root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            Controls.Add(root);

            var sidebar = new Panel();
            sidebar.Dock = DockStyle.Fill;
            sidebar.BackColor = Color.FromArgb(32, 34, 37);
            sidebar.Padding = new Padding(14);
            root.Controls.Add(sidebar, 0, 0);

            var sideFlow = new FlowLayoutPanel();
            sideFlow.Dock = DockStyle.Fill;
            sideFlow.FlowDirection = FlowDirection.TopDown;
            sideFlow.WrapContents = false;
            sideFlow.AutoScroll = true;
            sideFlow.BackColor = sidebar.BackColor;
            sidebar.Controls.Add(sideFlow);

            var brand = new Label();
            brand.Text = "AI Project 1\r\nprivate companion hub";
            brand.ForeColor = Color.White;
            brand.BackColor = sidebar.BackColor;
            brand.Font = new Font("Segoe UI", 16, FontStyle.Bold);
            brand.Width = 260;
            brand.Height = 70;
            sideFlow.Controls.Add(brand);

            serverBox = new TextBox();
            tokenBox = new TextBox();
            tokenBox.UseSystemPasswordChar = true;
            clientBox = new TextBox();
            selfSignedBox = new CheckBox();
            selfSignedBox.Text = "Self-signed HTTPS";
            AddCard(sideFlow, "Connection", new Control[]
            {
                Field("Server", serverBox),
                Field("Token", tokenBox),
                Field("Client", clientBox),
                StyledCheck(selfSignedBox),
                SidebarButton("Connect", ConnectClicked, true),
                SidebarButton("Save Settings", SaveClicked, false)
            });

            liveSearchBox = new CheckBox();
            liveSearchBox.Text = "Live web search";
            autoLookupBox = new CheckBox();
            autoLookupBox.Text = "Auto lookup triggers";
            searchEngineBox = new ComboBox();
            searchEngineBox.DropDownStyle = ComboBoxStyle.DropDownList;
            searchEngineBox.Items.AddRange(new object[] { "google", "baidu", "custom" });
            searchEngineBox.SelectedIndexChanged += delegate { UpdateCustomSearchState(); };
            customSearchBox = new TextBox();
            AddCard(sideFlow, "Search", new Control[]
            {
                StyledCheck(liveSearchBox),
                StyledCheck(autoLookupBox),
                Field("Engine", searchEngineBox),
                Field("Custom URL", customSearchBox)
            });

            statusLabel = SideStatus("Not connected");
            hubLabel = SideStatus("Hub: -");
            memoryLabel = SideStatus("Memory: -");
            knowledgeLabel = SideStatus("Knowledge: -");
            searchLabel = SideStatus("Search: -");
            AddCard(sideFlow, "Chat", new Control[]
            {
                SidebarButton("Clear Screen", ClearClicked, false),
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
            main.RowStyles.Add(new RowStyle(SizeType.Absolute, 72));
            main.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            main.RowStyles.Add(new RowStyle(SizeType.Absolute, 94));
            main.BackColor = Color.FromArgb(238, 242, 245);
            root.Controls.Add(main, 1, 0);

            var header = new Panel();
            header.BackColor = Color.White;
            header.Dock = DockStyle.Fill;
            main.Controls.Add(header, 0, 0);

            var title = new Label();
            title.Text = "AI Project 1\r\n三语陪伴模型 · 主设备 Hub";
            title.Font = new Font("Microsoft YaHei UI", 13, FontStyle.Bold);
            title.ForeColor = Color.FromArgb(17, 24, 39);
            title.AutoSize = false;
            title.Location = new Point(20, 14);
            title.Size = new Size(450, 50);
            header.Controls.Add(title);

            var reconnect = new Button();
            reconnect.Text = "Reconnect";
            reconnect.Width = 110;
            reconnect.Height = 34;
            reconnect.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            reconnect.Location = new Point(header.Width - 130, 19);
            reconnect.Click += ConnectClicked;
            header.Resize += delegate { reconnect.Location = new Point(header.Width - 130, 19); };
            header.Controls.Add(reconnect);

            messageList = new FlowLayoutPanel();
            messageList.Dock = DockStyle.Fill;
            messageList.FlowDirection = FlowDirection.TopDown;
            messageList.WrapContents = false;
            messageList.AutoScroll = true;
            messageList.BackColor = Color.FromArgb(238, 242, 245);
            messageList.Padding = new Padding(18, 12, 18, 12);
            main.Controls.Add(messageList, 0, 1);

            var composer = new TableLayoutPanel();
            composer.BackColor = Color.White;
            composer.Dock = DockStyle.Fill;
            composer.ColumnCount = 2;
            composer.RowCount = 1;
            composer.Padding = new Padding(18, 14, 18, 14);
            composer.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            composer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 96));
            main.Controls.Add(composer, 0, 2);

            inputBox = new TextBox();
            inputBox.Multiline = true;
            inputBox.Dock = DockStyle.Fill;
            inputBox.BorderStyle = BorderStyle.FixedSingle;
            inputBox.Font = new Font("Microsoft YaHei UI", 10);
            inputBox.KeyDown += InputKeyDown;
            composer.Controls.Add(inputBox, 0, 0);

            sendButton = new Button();
            sendButton.Text = "Send";
            sendButton.Dock = DockStyle.Fill;
            sendButton.BackColor = Color.FromArgb(88, 101, 242);
            sendButton.ForeColor = Color.White;
            sendButton.FlatStyle = FlatStyle.Flat;
            sendButton.Click += SendClicked;
            composer.Controls.Add(sendButton, 1, 0);
        }

        private void AddCard(FlowLayoutPanel parent, string title, Control[] controls)
        {
            var card = new FlowLayoutPanel();
            card.FlowDirection = FlowDirection.TopDown;
            card.WrapContents = false;
            card.Width = 270;
            card.AutoSize = true;
            card.Padding = new Padding(12);
            card.Margin = new Padding(0, 0, 0, 12);
            card.BackColor = Color.FromArgb(47, 49, 54);

            var label = new Label();
            label.Text = title;
            label.ForeColor = Color.White;
            label.BackColor = card.BackColor;
            label.Font = new Font("Segoe UI", 10, FontStyle.Bold);
            label.Width = 238;
            label.Height = 24;
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
            panel.Width = 238;
            panel.Height = 54;
            panel.BackColor = Color.FromArgb(47, 49, 54);

            var label = new Label();
            label.Text = labelText;
            label.ForeColor = Color.FromArgb(185, 187, 190);
            label.BackColor = panel.BackColor;
            label.Font = new Font("Segoe UI", 9);
            label.Location = new Point(0, 0);
            label.Size = new Size(238, 18);
            panel.Controls.Add(label);

            input.Location = new Point(0, 20);
            input.Width = 238;
            input.Height = 24;
            input.BackColor = Color.FromArgb(64, 68, 75);
            input.ForeColor = Color.White;
            panel.Controls.Add(input);
            return panel;
        }

        private Control StyledCheck(CheckBox box)
        {
            box.Width = 238;
            box.Height = 28;
            box.ForeColor = Color.White;
            box.BackColor = Color.FromArgb(47, 49, 54);
            return box;
        }

        private Button SidebarButton(string text, EventHandler handler, bool accent)
        {
            var button = new Button();
            button.Text = text;
            button.Width = 238;
            button.Height = 34;
            button.Margin = new Padding(0, 6, 0, 0);
            button.FlatStyle = FlatStyle.Flat;
            button.BackColor = accent ? Color.FromArgb(88, 101, 242) : Color.FromArgb(64, 68, 75);
            button.ForeColor = Color.White;
            button.Click += handler;
            return button;
        }

        private Label SideStatus(string text)
        {
            var label = new Label();
            label.Text = text;
            label.Width = 238;
            label.AutoSize = false;
            label.Height = 34;
            label.ForeColor = Color.FromArgb(185, 187, 190);
            label.BackColor = Color.FromArgb(47, 49, 54);
            label.Font = new Font("Segoe UI", 9);
            return label;
        }

        private void LoadSettings()
        {
            serverBox.Text = "http://127.0.0.1:8765";
            clientBox.Text = Environment.MachineName;
            liveSearchBox.Checked = true;
            autoLookupBox.Checked = true;
            searchEngineBox.SelectedItem = "google";

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
                    searchEngineBox.SelectedItem = searchEngineBox.Items.Contains(engine) ? engine : "google";
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
            statusLabel.Text = "Settings saved";
        }

        private void ConnectClicked(object sender, EventArgs e)
        {
            SaveSettings();
            statusLabel.Text = "Connecting...";
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
                        statusLabel.Text = "Connection failed";
                        AddMessage("System", "Connection failed: " + ex.Message, false, true);
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
            sendButton.Text = "...";
            statusLabel.Text = "Thinking...";

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
                        AddMessage("AI Project 1", reply, false, false);
                        statusLabel.Text = "Connected";
                        sendButton.Text = "Send";
                        sendButton.Enabled = true;
                    }));
                }
                catch (Exception ex)
                {
                    BeginInvoke(new Action(delegate
                    {
                        AddMessage("System", "Send failed: " + ex.Message, false, true);
                        statusLabel.Text = "Send failed";
                        sendButton.Text = "Send";
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
                throw new InvalidOperationException("Server must start with http:// or https://");
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
            statusLabel.Text = "Connected: " + (GetBool(status, "ready", false) ? "ready" : "no model")
                + ", device=" + GetString(status, "device", "-");
            hubLabel.Text = "Hub: -";
            if (status.ContainsKey("hub") && status["hub"] is Dictionary<string, object>)
            {
                var hub = (Dictionary<string, object>)status["hub"];
                hubLabel.Text = "Hub: " + GetString(hub, "hub_name", "-");
            }
            memoryLabel.Text = "Memory: " + GetString(status, "memory_facts", "0") + " facts, "
                + GetString(status, "memory_turns", "0") + " turns";
            knowledgeLabel.Text = "Knowledge: " + GetString(status, "knowledge_entries", "0") + " notes";
            searchLabel.Text = GetBool(status, "live_web", false) ? "Search: enabled on Hub" : "Search: disabled on Hub";
            AddMessage("System", "已连接到主设备 Hub。", false, true);
        }

        private void AddMessage(string speaker, string text, bool mine, bool system)
        {
            var row = new Panel();
            row.Width = Math.Max(600, messageList.ClientSize.Width - 40);
            row.Height = 10;
            row.Margin = new Padding(0, 0, 0, 10);
            row.BackColor = messageList.BackColor;

            var bubble = new Label();
            bubble.Text = speaker + " · " + DateTime.Now.ToString("HH:mm") + "\r\n" + text;
            bubble.Font = new Font("Microsoft YaHei UI", 10);
            bubble.ForeColor = Color.FromArgb(17, 24, 39);
            bubble.BackColor = system ? Color.FromArgb(221, 227, 234) : (mine ? Color.FromArgb(149, 236, 105) : Color.White);
            bubble.Padding = new Padding(12, 8, 12, 8);
            bubble.MaximumSize = new Size(Math.Max(320, messageList.ClientSize.Width * 58 / 100), 0);
            bubble.AutoSize = true;
            bubble.BorderStyle = BorderStyle.FixedSingle;

            row.Controls.Add(bubble);
            bubble.Location = mine
                ? new Point(Math.Max(0, row.Width - bubble.Width - 16), 0)
                : new Point(16, 0);
            row.Height = bubble.Height + 4;
            messageList.Controls.Add(row);
            messageList.ScrollControlIntoView(row);
        }

        private void ClearClicked(object sender, EventArgs e)
        {
            messageList.Controls.Clear();
            AddMessage("System", "屏幕已清空。", false, true);
        }

        private void UpdateCustomSearchState()
        {
            customSearchBox.Enabled = SelectedEngine() == "custom";
        }

        private string SelectedEngine()
        {
            return searchEngineBox.SelectedItem == null ? "google" : searchEngineBox.SelectedItem.ToString();
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
